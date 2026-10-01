#!/usr/bin/env python3
"""Fail-closed physical qualification verifier for Thin18 Compact C4D EVT."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
EXPECTED_TEST_IDS = {f"Q{i:02d}" for i in range(4, 13)}
ALLOWED_STATUS = {"NOT_RUN", "BLOCKED", "MEASURED_PASS", "MEASURED_FAIL"}
MEASUREMENT_REQUIRED_FIELDS = {
    "test_id", "sample_id", "state", "metric", "observed_value", "unit",
    "approved_limit_id", "pass", "instrument_ids", "raw_evidence_path",
    "raw_evidence_sha256", "operator", "reviewer", "timestamp_utc",
}
SAMPLE_REQUIRED_FIELDS = {
    "sample_id", "pcb_checkpoint", "pcb_sha256", "assembly_bom_path",
    "assembly_bom_sha256", "firmware_path_or_build_id", "firmware_sha256",
    "display_mpn_and_lot", "battery_mpn_and_lot", "component_lots",
    "assembly_date", "assembly_vendor", "photos",
}
INSTRUMENT_REQUIRED_FIELDS = {
    "instrument_id", "role", "manufacturer", "model", "serial_number",
    "measurement_range", "calibration_status", "calibration_date",
    "calibration_due_date", "connection_or_file_interface",
}
RELEASE_FILE_FIELDS = {
    "checkpoint", "pcb_path", "pcb_sha256", "drc_report_path",
    "drc_report_sha256", "erc_report_path", "erc_report_sha256",
    "production_bom_path", "production_bom_sha256", "cpl_path",
    "cpl_sha256", "gerber_zip_path", "gerber_zip_sha256",
}


def load_json(name: str) -> dict[str, Any]:
    return json.loads((HERE / name).read_text())


def require(value: Any, message: str) -> None:
    if not value:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repo_file(path_text: str, *, under_evidence: bool = False) -> Path:
    relative = Path(path_text)
    require(not relative.is_absolute() and ".." not in relative.parts, f"unsafe path: {path_text}")
    path = REPO / relative
    require(path.is_file(), f"missing file: {path_text}")
    if under_evidence:
        evidence_root = (HERE / "evidence").resolve()
        require(path.resolve().is_relative_to(evidence_root), f"raw evidence outside evidence/: {path_text}")
    return path


def validate_hashed_file(path_text: str, expected: str, *, under_evidence: bool = False) -> Path:
    require(re.fullmatch(r"[0-9a-f]{64}", expected or "") is not None, f"invalid SHA-256 for {path_text}")
    path = repo_file(path_text, under_evidence=under_evidence)
    require(sha256(path) == expected, f"SHA-256 mismatch: {path_text}")
    return path


def parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, f"timestamp lacks timezone: {value}")
    return parsed


def validate_sample(sample: dict[str, Any]) -> None:
    missing = sorted(field for field in SAMPLE_REQUIRED_FIELDS if not sample.get(field))
    require(not missing, f"sample {sample.get('sample_id')} missing: {missing}")
    require(re.fullmatch(r"[0-9a-f]{64}", sample["pcb_sha256"]) is not None, "invalid PCB hash")
    validate_hashed_file(sample["assembly_bom_path"], sample["assembly_bom_sha256"])
    require(re.fullmatch(r"[0-9a-f]{64}", sample["firmware_sha256"]) is not None, "invalid firmware hash")
    firmware_path = sample.get("firmware_path")
    if firmware_path:
        validate_hashed_file(firmware_path, sample["firmware_sha256"])
    require(isinstance(sample["component_lots"], dict) and sample["component_lots"], "component lots missing")
    require(isinstance(sample["photos"], list) and sample["photos"], "sample photos missing")
    for photo in sample["photos"]:
        validate_hashed_file(photo.get("path", ""), photo.get("sha256", ""), under_evidence=True)


def validate_instrument(instrument: dict[str, Any], measurement_time: dt.datetime) -> None:
    missing = sorted(field for field in INSTRUMENT_REQUIRED_FIELDS if not instrument.get(field))
    require(not missing, f"instrument {instrument.get('instrument_id')} missing: {missing}")
    require(instrument["calibration_status"] == "VALID", f"instrument calibration not VALID: {instrument['instrument_id']}")
    due = dt.date.fromisoformat(instrument["calibration_due_date"])
    require(due >= measurement_time.date(), f"instrument calibration expired: {instrument['instrument_id']}")


def split_ids(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[;,]", value) if item.strip()]


def split_artifacts(candidate: dict[str, Any]) -> dict[str, Any]:
    generated_path = repo_file(candidate["generated_candidate_path"])
    generated = json.loads(generated_path.read_text())
    require(generated.get("schema") == "panda-generated-split-c1-qualification-v1", "wrong generated qualification schema")
    require(generated["pcb_identities"] == candidate["pcb_identities"], "qualification PCB identity differs")
    release_path = validate_hashed_file(generated["split_release_path"], generated["split_release_sha256"])
    return json.loads(release_path.read_text())


def validate_split_sample_binding(sample: dict[str, Any], candidate: dict[str, Any]) -> None:
    if candidate.get("schema") != "thin18-compact-split-release-candidate-v2":
        return
    expected = candidate["pcb_identities"]
    require(sample.get("pcb_identities") == expected, "sample must bind both current Split-C1 PCB identities")
    require(sample["pcb_sha256"] == expected["Core-C1"]["sha256"], "sample Core PCB hash differs")
    split = split_artifacts(candidate)
    expected_boms = {board: artifacts["files"]["bom"] for board,artifacts in split["boards"].items()}
    require(sample.get("assembly_boms") == expected_boms, "sample assembly BOMs differ from both current boards")
    for info in expected_boms.values():
        validate_hashed_file(info["path"], info["sha256"])


def validate_release_candidate(candidate: dict[str, Any]) -> None:
    if candidate.get("schema") == "thin18-compact-split-release-candidate-v2":
        split = split_artifacts(candidate)
        require(set(split["boards"]) == {"Core-C1", "Display-C1"}, "split release must bind both boards")
        require(split["cad_manufacturing_data_complete"], "split fabrication data incomplete")
        require(set(candidate["pcb_identities"]) == {"Core-C1", "Display-C1"}, "qualification must bind both PCB identities")
        for board, artifacts in split["boards"].items():
            require(artifacts["pcb"] == candidate["pcb_identities"][board], "qualification PCB identity differs")
            native = artifacts["native_checks"]
            require(set(native) == {"drc", "open", "parity", "erc"} and not any(native.values()), "split native gates failed")
            for info in artifacts["files"].values():
                validate_hashed_file(info["path"], info["sha256"])
            drc = json.loads(repo_file(artifacts["files"]["drc"]["path"]).read_text())
            erc = json.loads(repo_file(artifacts["files"]["erc"]["path"]).read_text())
            require(not any(drc.get(key, []) for key in ["violations", "unconnected_items", "schematic_parity"]), "split DRC/open/parity failed")
            require(not any(sheet.get("violations", []) for sheet in erc.get("sheets", [])), "split ERC failed")
        for label in ["interface_contract", "mechanical_audit", "mechanical_inputs", "sourcing_evidence", "cad_validation"]:
            info = split[label]
            validate_hashed_file(info["path"], info["sha256"])
        return
    missing = sorted(field for field in RELEASE_FILE_FIELDS if not candidate.get(field))
    require(not missing, f"release candidate fields missing: {missing}")
    pcb = validate_hashed_file(candidate["pcb_path"], candidate["pcb_sha256"])
    drc_path = validate_hashed_file(candidate["drc_report_path"], candidate["drc_report_sha256"])
    erc_path = validate_hashed_file(candidate["erc_report_path"], candidate["erc_report_sha256"])
    validate_hashed_file(candidate["production_bom_path"], candidate["production_bom_sha256"])
    validate_hashed_file(candidate["cpl_path"], candidate["cpl_sha256"])
    validate_hashed_file(candidate["gerber_zip_path"], candidate["gerber_zip_sha256"])
    require(pcb.suffix == ".kicad_pcb", "release PCB is not a KiCad PCB")
    drc = json.loads(drc_path.read_text())
    erc = json.loads(erc_path.read_text())
    require(len(drc.get("violations", [])) == 0, "release DRC violations are not zero")
    require(len(drc.get("unconnected_items", [])) == 0, "release open count is not zero")
    require(len(drc.get("schematic_parity", [])) == 0, "release schematic parity is not zero")
    erc_count = sum(len(sheet.get("violations", [])) for sheet in erc.get("sheets", []))
    require(erc_count == 0, "release ERC violations are not zero")


def main(release: bool) -> int:
    plan = load_json("qualification-plan.json")
    sample_manifest = load_json("sample-manifest.json")
    instrument_manifest = load_json("instrument-manifest.json")
    approved_limits = load_json("approved-limits.json")
    release_candidate = load_json("release-candidate.json")

    tests = {test["id"]: test for test in plan["tests"]}
    require(set(tests) == EXPECTED_TEST_IDS and len(plan["tests"]) == 9, "qualification test coverage changed")
    require(all(test.get("status") in ALLOWED_STATUS for test in tests.values()), "invalid test status")
    require(all(test.get("required_metrics") for test in tests.values()), "test required metrics missing")

    samples = {sample["sample_id"]: sample for sample in sample_manifest.get("samples", [])}
    instruments = {item["instrument_id"]: item for item in instrument_manifest.get("instruments", [])}
    limits = {item["limit_id"]: item for item in approved_limits.get("limits", [])}
    require(len(samples) == len(sample_manifest.get("samples", [])), "duplicate sample ID")
    require(len(instruments) == len(instrument_manifest.get("instruments", [])), "duplicate instrument ID")
    require(len(limits) == len(approved_limits.get("limits", [])), "duplicate approved-limit ID")

    with (HERE / "measurements.csv").open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        require(reader.fieldnames is not None and MEASUREMENT_REQUIRED_FIELDS.issubset(reader.fieldnames), "measurement schema missing fields")
        rows = list(reader)

    rows_by_test: dict[str, list[dict[str, str]]] = {test_id: [] for test_id in EXPECTED_TEST_IDS}
    for row in rows:
        require(row["test_id"] in EXPECTED_TEST_IDS, f"unknown measurement test: {row['test_id']}")
        rows_by_test[row["test_id"]].append(row)

    measured_tests = 0
    result_rows = []
    for test_id in sorted(EXPECTED_TEST_IDS):
        test = tests[test_id]
        status = test["status"]
        test_rows = rows_by_test[test_id]
        if status in {"NOT_RUN", "BLOCKED"}:
            require(not test_rows, f"{test_id} has measurements but status is {status}")
            result_rows.append({"test_id": test_id, "status": status, "rows": 0})
            continue

        measured_tests += 1
        require(test_rows, f"{test_id} measured status without rows")
        metric_rows = {row["metric"]: row for row in test_rows}
        missing_metrics = sorted(set(test["required_metrics"]) - set(metric_rows))
        require(not missing_metrics, f"{test_id} missing metrics: {missing_metrics}")
        sample_ids = {row["sample_id"] for row in test_rows}
        require(len(sample_ids) == 1, f"{test_id} must bind to exactly one sample")
        sample_id = next(iter(sample_ids))
        require(sample_id in samples, f"{test_id} unknown sample: {sample_id}")
        validate_sample(samples[sample_id])

        test_limit_ids = set()
        roles_seen = set()
        reviewers = set()
        operators = set()
        all_pass = True
        for row in test_rows:
            missing = sorted(field for field in MEASUREMENT_REQUIRED_FIELDS if not row.get(field))
            require(not missing, f"{test_id}/{row.get('metric')} missing fields: {missing}")
            timestamp = parse_time(row["timestamp_utc"])
            limit_id = row["approved_limit_id"]
            require(limit_id in limits, f"{test_id} unknown approved limit: {limit_id}")
            require(limits[limit_id].get("test_id") == test_id, f"{test_id} limit belongs to another test")
            require(limits[limit_id].get("approved_by") and limits[limit_id].get("approved_at_utc"), f"{limit_id} not approved")
            test_limit_ids.add(limit_id)
            instrument_ids = split_ids(row["instrument_ids"])
            require(instrument_ids, f"{test_id}/{row['metric']} has no instrument")
            for instrument_id in instrument_ids:
                require(instrument_id in instruments, f"unknown instrument: {instrument_id}")
                validate_instrument(instruments[instrument_id], timestamp)
                roles_seen.add(instruments[instrument_id]["role"])
            validate_hashed_file(row["raw_evidence_path"], row["raw_evidence_sha256"], under_evidence=True)
            require(row["pass"].upper() in {"TRUE", "FALSE"}, f"invalid pass value: {test_id}/{row['metric']}")
            all_pass &= row["pass"].upper() == "TRUE"
            operators.add(row["operator"])
            reviewers.add(row["reviewer"])

        validate_split_sample_binding(samples[sample_id], release_candidate)
        require(set(test["required_instrument_roles"]).issubset(roles_seen), f"{test_id} missing instrument roles")
        require(reviewers.isdisjoint(operators), f"{test_id} reviewer must be independent from operator")
        require(len(test_limit_ids) == 1, f"{test_id} must use one approved limit revision")
        if status == "MEASURED_PASS":
            require(all_pass, f"{test_id} marked PASS with failing row")
        else:
            require(not all_pass, f"{test_id} marked FAIL but all rows pass")
        result_rows.append({"test_id": test_id, "status": status, "rows": len(test_rows), "sample_id": sample_id})

    require(plan.get("physical_tests_completed") == measured_tests, "physical_tests_completed does not match measured statuses")
    require(plan.get("manufacturing_release") is False or release, "manufacturing release set outside release verification")

    release_allowed = False
    release_blockers = []
    if not all(tests[test_id]["status"] == "MEASURED_PASS" for test_id in EXPECTED_TEST_IDS):
        release_blockers.append("not all Q04-Q12 tests are MEASURED_PASS")
    if measured_tests != 9:
        release_blockers.append("physical_tests_completed is not 9")
    if not plan.get("release_approval"):
        release_blockers.append("independent release approval missing")
    if not release_candidate.get("manufacturing_release"):
        release_blockers.append("release-candidate manufacturing_release is false")

    if release:
        require(not release_blockers, f"release blocked: {release_blockers}")
        approval = plan["release_approval"]
        require(approval.get("approved_by") and approval.get("approved_at_utc"), "release approval incomplete")
        require(approval.get("approved_by") not in {row.get("operator") for row in rows}, "release approver must be independent")
        validate_release_candidate(release_candidate)
        release_allowed = True

    summary = {
        "date": "2026-09-30",
        "result": "PASS_TRUTHFUL_CURRENT_STATE",
        "tests": result_rows,
        "physical_tests_completed": measured_tests,
        "sample_count": len(samples),
        "instrument_count": len(instruments),
        "measurement_rows": len(rows),
        "approved_limit_count": len(limits),
        "release_allowed": release_allowed,
        "release_blockers": release_blockers,
        "manufacturing_release": release_allowed,
    }
    (HERE / "qualification-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if release and not release_allowed:
        return 2
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", action="store_true")
    args = parser.parse_args()
    try:
        sys.exit(main(args.release))
    except (ValueError, KeyError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(2)
