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


try:
    expect_failure("paper-only MEASURED_PASS rejected", paper_only_pass, "measured status without rows")
    expect_failure("measurement without sample identity rejected", measurement_without_identity, "unknown sample")
    expect_failure("expired calibration rejected", expired_calibration, "calibration expired")
    expect_failure(
        "release flag without full physical evidence rejected",
        unapproved_release_flag,
        "release blocked",
        release=True,
    )
finally:
    restore()

# Prove restoration returns to the valid NOT_RUN state.
final = subprocess.run([sys.executable, str(VERIFIER)], capture_output=True, text=True)
if final.returncode != 0:
    raise SystemExit(f"restored current state failed: {final.stdout}\n{final.stderr}")

report = {
    "date": "2026-09-30",
    "tests": results,
    "all_rejected_as_expected": all(item["rejected_as_expected"] for item in results),
    "inputs_restored": True,
}
(HERE / "negative-controls.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(report, ensure_ascii=False, indent=2))
