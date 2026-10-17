"""HDI6 variant isolation and prototype-release safety regression tests."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from hdi6_contract import (load_variant, checked_variant, require_native_counts,
                           verified_baseline, sha256, BOARDS)


HERE = Path(__file__).resolve().parent


def sample():
    return load_variant(HERE / "variant.json")


def counts(open_core=24, open_display=4):
    return {
        "Core": dict(open=open_core, drc_errors=0, drc_warnings=0, parity=0, erc=0),
        "Display": dict(open=open_display, drc_errors=0, drc_warnings=0, parity=0, erc=0),
    }


def fixture(root: Path):
    source = root / "source"
    board = root / "r12"
    source.mkdir()
    board.mkdir()
    for name, data in (
        ("design.json", b"original source design"),
        ("ordered_core_layout.json", b"original source layout"),
    ):
        (source / name).write_bytes(data)
    for name in BOARDS:
        (board / (name + ".kicad_pcb")).write_bytes(("four layer " + name).encode())
    variant = copy.deepcopy(sample())
    baseline = variant["baseline"]
    baseline["core_pcb_sha256"] = sha256(board / "Core.kicad_pcb")
    baseline["display_pcb_sha256"] = sha256(board / "Display.kicad_pcb")
    baseline["source_design_sha256"] = sha256(source / "design.json")
    baseline["source_layout_sha256"] = sha256(source / "ordered_core_layout.json")
    (board / "ROUTING-CHECKPOINT.json").write_text(json.dumps({
        "source_design_sha256": baseline["source_design_sha256"],
        "source_layout_sha256": baseline["source_layout_sha256"],
        "boards": {
            "Core": {"pcb_sha256": baseline["core_pcb_sha256"]},
            "Display": {"pcb_sha256": baseline["display_pcb_sha256"]},
        },
    }))
    (board / "CURRENT-STATUS.json").write_text(json.dumps({
        "native_counts": counts(),
        "complete_ground_gate": {"complete": True},
        "manufacturing_release": False,
    }))
    return variant, board, source


class VariantContract(unittest.TestCase):
    def test_source_variant_is_explicitly_six_layer_and_not_released(self):
        value = sample()
        self.assertEqual(value["architecture"]["copper_layer_count"], 6)
        self.assertFalse(value["manufacturing_release"])
        self.assertFalse(value["physical_qualification_complete"])
        self.assertFalse(value["orders_submitted"])

    def test_status_must_not_be_promoted_to_release(self):
        obj = sample()
        obj["status"] = "production"
        with self.assertRaises(ValueError):
            checked_variant(obj)

    def test_board_count_and_layer_policy_cannot_be_relaxed(self):
        for key, value in [
            ("boards", ["Core"]),
            ("copper_layer_count", 4),
            ("reference_ground_layers", ["In1.Cu"]),
            ("no_non_ground_tracks_on", ["In1.Cu"]),
            ("nominal_board_thickness_mm", 1.6),
            ("whole_device_max_finished_height_mm", 7.5),
        ]:
            with self.subTest(key=key):
                obj = sample()
                obj["architecture"][key] = value
                with self.assertRaises(ValueError):
                    checked_variant(obj)

    def test_layer_order_cannot_be_rearranged_implicitly(self):
        obj = sample()
        obj["architecture"]["layer_allocation"][2]["layer"] = "In3.Cu"
        with self.assertRaises(ValueError):
            checked_variant(obj)

    def test_boolean_as_layer_count_is_not_six(self):
        obj = sample()
        obj["architecture"]["copper_layer_count"] = True
        with self.assertRaises(ValueError):
            checked_variant(obj)

    def test_factory_must_explicitly_confirm_manufacturability(self):
        for key in ("factory_stackup_confirmed", "pofv_accepted_by_factory",
                    "c804_filled_capped_return_accepted"):
            with self.subTest(key=key):
                obj = sample()
                obj["manufacturing"][key] = True
                with self.assertRaises(ValueError):
                    checked_variant(obj)

    def test_mechanical_tolerance_gate_cannot_be_self_approved(self):
        obj = sample()
        obj["architecture"]["thickness_with_tolerance_mechanically_verified"] = True
        with self.assertRaises(ValueError):
            checked_variant(obj)

    def test_general_via_minima_stay_unchanged(self):
        for key, value in [
            ("original_through_via_rules_preserved", False),
            ("standard_via_rule_relaxation_allowed", True),
        ]:
            with self.subTest(key=key):
                obj = sample()
                obj["manufacturing"][key] = value
                with self.assertRaises(ValueError):
                    checked_variant(obj)

    def test_each_release_flag_is_a_hard_stop(self):
        for key in ("manufacturing_release", "physical_qualification_complete",
                    "orders_submitted"):
            with self.subTest(key=key):
                obj = sample()
                obj[key] = True
                with self.assertRaises(ValueError):
                    checked_variant(obj)

    def test_baseline_sha_integrity_is_required(self):
        for key in sample()["baseline"]:
            if key.endswith("_sha256"):
                with self.subTest(key=key):
                    obj = sample()
                    obj["baseline"][key] = "not-a-sha"
                    with self.assertRaises(ValueError):
                        checked_variant(obj)

    def test_source_replay_gate_cannot_be_disabled(self):
        obj = sample()
        obj["source_replay_required"] = False
        with self.assertRaises(ValueError):
            checked_variant(obj)

    def test_zero_error_native_counts_allow_remaining_opens(self):
        require_native_counts(sample(), counts())

    def test_open_count_regression_rejected(self):
        with self.assertRaises(ValueError):
            require_native_counts(sample(), counts(open_core=25))
        with self.assertRaises(ValueError):
            require_native_counts(sample(), counts(open_display=5))

    def test_real_native_error_warning_erc_or_parity_rejected(self):
        for key in ("drc_errors", "drc_warnings", "erc", "parity"):
            with self.subTest(key=key):
                record = counts()
                record["Display"][key] = 1
                with self.assertRaises(ValueError):
                    require_native_counts(sample(), record)

    def test_bool_and_missing_counts_rejected(self):
        record = counts()
        record["Core"]["open"] = True
        with self.assertRaises(ValueError):
            require_native_counts(sample(), record)
        record = counts()
        del record["Display"]["parity"]
        with self.assertRaises(ValueError):
            require_native_counts(sample(), record)

    def test_exact_isolated_fixture_hashes_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            obj, base, source = fixture(Path(temporary))
            actual = verified_baseline(obj, base, source)
            self.assertEqual(actual["Core.kicad_pcb"],
                             sha256(base / "Core.kicad_pcb"))
            self.assertEqual(len(actual), 4)

    def test_changed_native_board_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            obj, base, source = fixture(Path(temporary))
            with (base / "Core.kicad_pcb").open("ab") as f:
                f.write(b"changed copper")
            with self.assertRaises(ValueError):
                verified_baseline(obj, base, source)

    def test_changed_source_layout_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            obj, base, source = fixture(Path(temporary))
            (source / "ordered_core_layout.json").write_bytes(b"different")
            with self.assertRaises(ValueError):
                verified_baseline(obj, base, source)

    def test_manifest_disagreement_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            obj, base, source = fixture(Path(temporary))
            report = json.loads((base / "ROUTING-CHECKPOINT.json").read_text())
            report["boards"]["Display"]["pcb_sha256"] = "0" * 64
            (base / "ROUTING-CHECKPOINT.json").write_text(json.dumps(report))
            with self.assertRaises(ValueError):
                verified_baseline(obj, base, source)

    def test_baseline_with_disconnected_ground_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            obj, base, source = fixture(Path(temporary))
            status = json.loads((base / "CURRENT-STATUS.json").read_text())
            status["complete_ground_gate"]["complete"] = False
            (base / "CURRENT-STATUS.json").write_text(json.dumps(status))
            with self.assertRaises(ValueError):
                verified_baseline(obj, base, source)

    def test_no_mutation_of_source_variant_during_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            obj, base, source = fixture(Path(temporary))
            original = copy.deepcopy(obj)
            verified_baseline(obj, base, source)
            self.assertEqual(obj, original)


if __name__ == "__main__":
    unittest.main()
