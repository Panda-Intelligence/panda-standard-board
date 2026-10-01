#!/usr/bin/env python3
"""Execute destructive negative controls and restore all qualification inputs."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
VERIFIER = HERE / "verify_qualification.py"
INPUTS = [
    "qualification-plan.json",
    "sample-manifest.json",
    "instrument-manifest.json",
    "approved-limits.json",
    "release-candidate.json",
    "measurements.csv",
]
TEMP_EVIDENCE = HERE / "evidence/_negative-control.csv"
backups = {name: (HERE / name).read_bytes() for name in INPUTS}
results = []


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def restore() -> None:
    for name, content in backups.items():
        (HERE / name).write_bytes(content)
    TEMP_EVIDENCE.unlink(missing_ok=True)


def expect_failure(name: str, mutate, expected_fragment: str, release: bool = False) -> None:
    restore()
    mutate()
    command = [sys.executable, str(VERIFIER)] + (["--release"] if release else [])
    completed = subprocess.run(command, capture_output=True, text=True)
    combined = completed.stdout + "\n" + completed.stderr
    passed = completed.returncode == 2 and expected_fragment in combined
    results.append({
        "name": name,
        "exit_code": completed.returncode,
        "expected_fragment": expected_fragment,
        "rejected_as_expected": passed,
        "stderr_tail": completed.stderr.strip().splitlines()[-1:] or [],
    })
    if not passed:
        raise SystemExit(
            f"negative control did not hit expected gate: {name}; "
            f"stdout={completed.stdout}; stderr={completed.stderr}"
        )


def set_q06_pass() -> list[str]:
    plan_path = HERE / "qualification-plan.json"
    plan = json.loads(plan_path.read_text())
    test = next(item for item in plan["tests"] if item["id"] == "Q06")
    test["status"] = "MEASURED_PASS"
    plan["physical_tests_completed"] = 1
    plan_path.write_text(json.dumps(plan, indent=2) + "\n")
    return test["required_metrics"]


def append_q06_rows(metrics: list[str], *, sample_id: str, limit_id: str, instruments: str, evidence_sha: str) -> None:
    evidence_path = "hardware/thin18-compact/qualification/c4d-evt/evidence/_negative-control.csv"
    with (HERE / "measurements.csv").open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        for metric in metrics:
            writer.writerow([
                "Q06", sample_id, "warm_only", metric, "14.5", "mA", limit_id,
                "0", "15", "TRUE", instruments, evidence_path, evidence_sha,
                "negative-operator", "negative-reviewer", "2026-09-30T00:00:00Z",
                "deliberate negative-control row",
            ])


def paper_only_pass() -> None:
    set_q06_pass()


def measurement_without_identity() -> None:
    metrics = set_q06_pass()
    TEMP_EVIDENCE.write_text("negative control\n")
    append_q06_rows(
        metrics,
        sample_id="EVT-FAKE",
        limit_id="LIMIT-FAKE",
        instruments="METER-FAKE;SCOPE-FAKE;SUPPLY-FAKE;LUX-FAKE",
        evidence_sha=digest(TEMP_EVIDENCE),
    )


def expired_calibration() -> None:
    metrics = set_q06_pass()
    TEMP_EVIDENCE.write_text("negative control\n")
    evidence_sha = digest(TEMP_EVIDENCE)
    readme = HERE / "README.md"
    sample = {
        "sample_id": "EVT-FAKE",
        "pcb_checkpoint": "C4D-FAKE",
        "pcb_sha256": "1" * 64,
        "assembly_bom_path": "hardware/thin18-compact/qualification/c4d-evt/README.md",
        "assembly_bom_sha256": digest(readme),
        "firmware_path_or_build_id": "fake-build",
        "firmware_sha256": "2" * 64,
        "display_mpn_and_lot": "fake-display-lot",
        "battery_mpn_and_lot": "fake-battery-lot",
        "component_lots": {"U905": "fake-lot"},
        "assembly_date": "2026-09-30",
        "assembly_vendor": "fake-vendor",
        "photos": [{
            "path": "hardware/thin18-compact/qualification/c4d-evt/evidence/_negative-control.csv",
            "sha256": evidence_sha,
        }],
    }
    (HERE / "sample-manifest.json").write_text(json.dumps({"schema": "x", "date": "2026-09-30", "samples": [sample]}, indent=2) + "\n")

    instruments = []
    for instrument_id, role in [
        ("METER-FAKE", "precision_current_meter"),
        ("SCOPE-FAKE", "oscilloscope"),
        ("SUPPLY-FAKE", "current_limited_supply"),
        ("LUX-FAKE", "lux_or_luminance_meter"),
    ]:
        instruments.append({
            "instrument_id": instrument_id,
            "role": role,
            "manufacturer": "fake",
            "model": "fake",
            "serial_number": instrument_id,
            "measurement_range": "fake",
            "calibration_status": "VALID",
            "calibration_date": "2020-01-01",
            "calibration_due_date": "2020-12-31",
            "connection_or_file_interface": "fake",
        })
    (HERE / "instrument-manifest.json").write_text(
        json.dumps({"schema": "x", "date": "2026-09-30", "instruments": instruments}, indent=2) + "\n"
    )
    limit = {
        "limit_id": "LIMIT-FAKE",
        "test_id": "Q06",
        "revision": "negative",
        "approved_by": "negative-approver",
        "approved_at_utc": "2026-09-29T00:00:00Z",
        "source_requirements": ["negative"],
        "metric_limits": {metric: {"upper": 15} for metric in metrics},
    }
    (HERE / "approved-limits.json").write_text(
        json.dumps({"schema": "x", "date": "2026-09-30", "limits": [limit]}, indent=2) + "\n"
    )
    append_q06_rows(
        metrics,
        sample_id="EVT-FAKE",
        limit_id="LIMIT-FAKE",
        instruments="METER-FAKE;SCOPE-FAKE;SUPPLY-FAKE;LUX-FAKE",
        evidence_sha=evidence_sha,
    )


def unapproved_release_flag() -> None:
    path = HERE / "release-candidate.json"
    data = json.loads(path.read_text())
    data["manufacturing_release"] = True
    path.write_text(json.dumps(data, indent=2) + "\n")


def remove_display_test() -> None:
    path = HERE / "qualification-plan.json"
    plan = json.loads(path.read_text())
    plan["tests"] = [item for item in plan["tests"] if item["id"] != "Q13"]
    path.write_text(json.dumps(plan, indent=2) + "\n")


def expect_binding_failure(name, sample, fragment) -> None:
    from verify_qualification import validate_split_sample_binding
    candidate = json.loads((HERE / "release-candidate.json").read_text())
    try:
        validate_split_sample_binding(sample, candidate)
    except ValueError as exc:
        message = str(exc)
        if fragment not in message:
            raise SystemExit(f"unexpected binding guard for {name}: {message}")
        results.append({"name":name, "expected_fragment":fragment,
                        "rejected_as_expected":True,"validator_error":message})
    else:
        raise SystemExit(f"negative binding control was accepted: {name}")


def run_pair_binding_controls() -> None:
    from copy import deepcopy
    from verify_qualification import split_artifacts, validate_release_candidate
    candidate = json.loads((HERE / "release-candidate.json").read_text())
    validate_release_candidate(candidate)
    release = split_artifacts(candidate)
    sample = {"pcb_identities":candidate["pcb_identities"],
              "pcb_sha256":candidate["pcb_identities"]["Core-C1"]["sha256"],
              "board_serial_numbers":{"Core-C1":"CONTROL-CORE","Display-C1":"CONTROL-DISPLAY"},
              "assembly_boms":{name:info["files"]["bom"] for name,info in release["boards"].items()}}
    sample["assembly_bom_path"] = sample["assembly_boms"]["Core-C1"]["path"]
    sample["assembly_bom_sha256"] = sample["assembly_boms"]["Core-C1"]["sha256"]
    from verify_qualification import validate_split_sample_binding, validate_sample_states
    validate_split_sample_binding(sample, candidate)
    wrong = deepcopy(sample); wrong["pcb_identities"]["Display-C1"]["sha256"] = "1"*64
    expect_binding_failure("wrong Display PCB rejected", wrong, "both current Split-C1 PCB identities")
    missing = deepcopy(sample); missing["board_serial_numbers"].pop("Display-C1")
    expect_binding_failure("missing Display serial rejected", missing, "both Core and Display board serials")
    wrong = deepcopy(sample); wrong["assembly_boms"]["Display-C1"]["sha256"] = "2"*64
    expect_binding_failure("wrong Display assembly BOM rejected", wrong, "BOMs differ from both current boards")
    wrong = deepcopy(sample); wrong["assembly_bom_sha256"] = "3"*64
    expect_binding_failure("wrong legacy Core assembly BOM rejected", wrong, "legacy Core BOM differs")
    test = next(item for item in json.loads((HERE/"qualification-plan.json").read_text())["tests"] if item["id"]=="Q14")
    valid_rows = [{"state":state} for state in test["required_sample_states"]]
    validate_sample_states(test, valid_rows)
    try:
        validate_sample_states(test, valid_rows[:-1])
    except ValueError as exc:
        if "missing required sample states" not in str(exc): raise
        results.append({"name":"omitted paired-board operating state rejected", "rejected_as_expected":True,
                        "validator_error":str(exc)})
    else:
        raise SystemExit("paired-board state coverage negative control was accepted")



try:
    expect_failure("Display physical test omitted rejected", remove_display_test, "qualification test coverage changed")
    expect_failure("paper-only MEASURED_PASS rejected", paper_only_pass, "measured status without rows")
    expect_failure("measurement without sample identity rejected", measurement_without_identity, "unknown sample")
    expect_failure("expired calibration rejected", expired_calibration, "calibration expired")
    expect_failure(
        "release flag without full physical evidence rejected",
        unapproved_release_flag,
        "release blocked",
        release=True,
    )
    restore()
    run_pair_binding_controls()
finally:
    restore()

# Prove restoration returns to the valid NOT_RUN state.
final = subprocess.run([sys.executable, str(VERIFIER)], capture_output=True, text=True)
if final.returncode != 0:
    raise SystemExit(f"restored current state failed: {final.stdout}\n{final.stderr}")

report = {
    "date": "2026-10-01",
    "tests": results,
    "all_rejected_as_expected": all(item["rejected_as_expected"] for item in results),
    "inputs_restored": True,
}
(HERE / "negative-controls.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(report, ensure_ascii=False, indent=2))
