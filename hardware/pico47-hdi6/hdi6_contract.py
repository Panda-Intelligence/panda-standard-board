"""Strict source, layer and manufacturing gates for the independent HDI6 variant.

Neither this contract nor the initial six-layer conversion authorizes fabrication.
The existing four-layer source, native rules and protected physical connections
remain immutable inputs until a separately reviewed design ECO is accepted.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

BOARDS = ("Core", "Display")
LAYERS = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")
REFERENCE_LAYERS = ("In1.Cu", "In4.Cu")
SIGNAL_LAYERS = ("F.Cu", "In2.Cu", "In3.Cu", "B.Cu")
HARD_STOP_FLAGS = ("manufacturing_release", "physical_qualification_complete", "orders_submitted")


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError("HDI6 contract: " + message)


def checked_variant(data: dict) -> dict:
    require(isinstance(data, dict), "variant must be an object")
    require(data.get("schema") == "panda47-hdi6-variant-v1", "variant schema changed")
    require(data.get("variant_id") == "pico47-hdi6-v1", "variant identifier changed")
    require(data.get("revision") == "E0.3-HDI6", "variant revision changed")
    require(data.get("status") == "engineering-study", "premature release status")
    arch = data.get("architecture")
    require(isinstance(arch, dict), "missing architecture")
    require(arch.get("boards") == list(BOARDS), "two-board design must remain")
    require(type(arch.get("copper_layer_count")) is int and arch["copper_layer_count"] == 6,
            "copper layer count must be six")
    require(type(arch.get("nominal_board_thickness_mm")) in (int, float) and
            arch["nominal_board_thickness_mm"] == 0.8, "unreviewed thickness")
    layers = arch.get("layer_allocation")
    require(isinstance(layers, list) and [r.get("layer") for r in layers] == list(LAYERS),
            "layer order differs")
    require(arch.get("reference_ground_layers") == list(REFERENCE_LAYERS),
            "reference ground layer policy changed")
    require(arch.get("no_non_ground_tracks_on") == list(REFERENCE_LAYERS),
            "forbidden signal layer policy changed")
    require(arch.get("board_stackup_factory_confirmed") is False,
            "factory stackup cannot be self-approved")
    require(arch.get("whole_device_max_finished_height_mm") == 7.0,
            "seven-millimeter product limit changed")
    require(arch.get("thickness_with_tolerance_mechanically_verified") is False,
            "mechanical fit cannot be self-approved")
    mfg = data.get("manufacturing")
    require(isinstance(mfg, dict), "missing manufacturing policy")
    for key in ("factory_stackup_confirmed", "pofv_accepted_by_factory",
                "c804_filled_capped_return_accepted"):
        require(mfg.get(key) is False, key + " cannot be self-approved")
    require(mfg.get("original_through_via_rules_preserved") is True,
            "cannot silently relax through-hole via rules")
    require(mfg.get("standard_via_rule_relaxation_allowed") is False,
            "standard via relaxation forbidden")
    for key in HARD_STOP_FLAGS:
        require(data.get(key) is False, key + " cannot be true in a study variant")
    baseline = data.get("baseline")
    require(isinstance(baseline, dict), "missing baseline binding")
    require(baseline.get("immutable_checkpoint") ==
            "panda47-e02-20261015-r12/engineering-candidate", "baseline name changed")
    for k in ("core_pcb_sha256", "display_pcb_sha256",
              "source_design_sha256", "source_layout_sha256"):
        value = baseline.get(k)
        require(isinstance(value, str) and len(value) == 64 and
                all(c in "0123456789abcdef" for c in value),
                "invalid pinned hash: " + k)
    require(data.get("source_replay_required") is True, "source replay required")
    return data


def load_variant(path: Path) -> dict:
    return checked_variant(json.loads(Path(path).read_text()))


def verified_baseline(
    variant: dict, baseline_dir: Path, source_dir: Path
) -> dict:
    """Check exact source/native hashes without writing either input."""
    baseline_dir = Path(baseline_dir).resolve()
    source_dir = Path(source_dir).resolve()
    require(baseline_dir.is_dir() and not baseline_dir.is_symlink(),
            "baseline directory inaccessible")
    require(source_dir.is_dir() and not source_dir.is_symlink(),
            "source directory inaccessible")
    verified = {}
    expected = variant["baseline"]
    for board in BOARDS:
        pcb = baseline_dir / (board + ".kicad_pcb")
        require(pcb.is_file() and not pcb.is_symlink(),
                "missing baseline PCB: " + board)
        actual = sha256(pcb)
        require(actual == expected[board.lower() + "_pcb_sha256"],
                "baseline PCB changed: " + board)
        verified[board + ".kicad_pcb"] = actual
    for source_name, key in (
        ("design.json", "source_design_sha256"),
        ("ordered_core_layout.json", "source_layout_sha256"),
    ):
        p = source_dir / source_name
        require(p.is_file() and not p.is_symlink(),
                "missing original source: " + source_name)
        actual = sha256(p)
        require(actual == expected[key], "source changed: " + source_name)
        verified["source/" + source_name] = actual
    bound = json.loads((baseline_dir / "ROUTING-CHECKPOINT.json").read_text())
    require(bound.get("source_layout_sha256") == expected["source_layout_sha256"],
            "baseline manifest layout mismatch")
    require(bound.get("source_design_sha256") == expected["source_design_sha256"],
            "baseline manifest design mismatch")
    for board in BOARDS:
        require(bound["boards"][board]["pcb_sha256"] ==
                expected[board.lower() + "_pcb_sha256"],
                "baseline native binding mismatch: " + board)
    status = json.loads((baseline_dir / "CURRENT-STATUS.json").read_text())
    for board, expected_open in variant["initial_open_items"].items():
        counts = status["native_counts"][board]
        require(counts["open"] == expected_open, "baseline open count changed: " + board)
        require(all(counts[k] == 0 for k in ("drc_errors", "drc_warnings", "parity", "erc")),
                "baseline DRC/ERC is not clean: " + board)
    require(status["complete_ground_gate"]["complete"] is True,
            "baseline complete-ground gate is false")
    require(status["manufacturing_release"] is False, "unexpected released baseline")
    return verified


def require_native_counts(variant: dict, counts: dict) -> None:
    """Reject new violations, lost connectivity and pretend fabrication release."""
    for board in BOARDS:
        record = counts.get(board)
        require(isinstance(record, dict), "missing native board status: " + board)
        for key in ("open", "drc_errors", "drc_warnings", "parity", "erc"):
            require(type(record.get(key)) is int and record[key] >= 0,
                    "invalid native count: " + board + "." + key)
        require(record["open"] <= variant["initial_open_items"][board],
                "six-layer conversion lost routes: " + board)
        require(all(record[k] == 0 for k in
                    ("drc_errors", "drc_warnings", "parity", "erc")),
                "native DRC/ERC not clean: " + board)
