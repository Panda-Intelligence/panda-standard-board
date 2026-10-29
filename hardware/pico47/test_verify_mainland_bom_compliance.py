"""Unit tests for Chinese Mainland (PRC) component provenance verifier."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from verify_mainland_bom_compliance import (
    MAINLAND_MANUFACTURERS,
    NON_PURCHASED_PCB_FEATURE_MANUFACTURER,
    NON_PURCHASED_PCB_FEATURE_MPN,
    apply_mainland_metadata_eco,
    verify_all_boards,
    verify_board_mainland_compliance,
)


def _sample_pcb_and_sch(
    candidate_dir: Path,
    board: str = "Single",
    u501_mfg: str = "Espressif",
    c501_mfg: str = "FH (Fenghua Advanced)",
    c501_mpn: str = "0603X226M100NT",
    c501_lcsc: str = "C60077",
    sch_c501_mpn: str = "0603X226M100NT",
) -> None:
    pcb_text = f"""(kicad_pcb (version 20241229) (generator "pcbnew")
  (footprint "Panda47:U501_Core" (layer "F.Cu")
    (at 10 10)
    (property "Reference" "U501" (at 0 0 0) (layer "F.SilkS"))
    (property "Value" "ESP32-S3R8" (at 0 0 0) (layer "F.Fab"))
    (property "Manufacturer" "{u501_mfg}" (at 0 0 0) (layer "F.Fab") (hide yes))
    (property "MPN" "ESP32-S3R8" (at 0 0 0) (layer "F.Fab") (hide yes))
    (property "LCSC" "C2913194" (at 0 0 0) (layer "F.Fab") (hide yes))
    (attr smd)
  )
  (footprint "Panda47:C501_Core" (layer "F.Cu")
    (at 20 20)
    (property "Reference" "C501" (at 0 0 0) (layer "F.SilkS"))
    (property "Value" "22u / ESP32" (at 0 0 0) (layer "F.Fab"))
    (property "Manufacturer" "{c501_mfg}" (at 0 0 0) (layer "F.Fab") (hide yes))
    (property "MPN" "{c501_mpn}" (at 0 0 0) (layer "F.Fab") (hide yes))
    (property "LCSC" "{c501_lcsc}" (at 0 0 0) (layer "F.Fab") (hide yes))
    (attr smd)
  )
  (footprint "Panda47:C514_Core" (layer "F.Cu")
    (at 25 25)
    (property "Reference" "C514" (at 0 0 0) (layer "F.SilkS"))
    (property "Value" "DNP / USB tuning" (at 0 0 0) (layer "F.Fab"))
    (property "Manufacturer" "FH (Fenghua Advanced)" (at 0 0 0) (layer "F.Fab") (hide yes))
    (property "MPN" "0402CG0R8C500NT" (at 0 0 0) (layer "F.Fab") (hide yes))
    (property "LCSC" "C40459" (at 0 0 0) (layer "F.Fab") (hide yes))
    (attr smd dnp)
  )
  (footprint "Panda47:TP1_Core" (layer "F.Cu")
    (at 30 30)
    (property "Reference" "TP1" (at 0 0 0) (layer "F.SilkS"))
    (property "Value" "VBUS_USB" (at 0 0 0) (layer "F.Fab"))
    (property "Manufacturer" "{NON_PURCHASED_PCB_FEATURE_MANUFACTURER}" (at 0 0 0) (layer "F.Fab") (hide yes))
    (property "MPN" "{NON_PURCHASED_PCB_FEATURE_MPN}" (at 0 0 0) (layer "F.Fab") (hide yes))
    (property "LCSC" "" (at 0 0 0) (layer "F.Fab") (hide yes))
    (attr smd exclude_from_bom)
  )
)
"""
    sch_text = f"""(kicad_sch (version 20250114) (generator "eeschema")
  (lib_symbols
    (symbol "Panda7:U501" (in_bom yes) (on_board yes))
    (symbol "Panda7:C501" (in_bom yes) (on_board yes))
    (symbol "Panda7:C514" (in_bom yes) (on_board yes))
    (symbol "Panda7:TP1" (in_bom no) (on_board yes))
  )
  (symbol(lib_id "Panda7:U501")(at 10 10 0)(unit 1)(in_bom yes)(on_board yes)(dnp no)
    (property "Reference" "U501" (at 10 10 0) (effects (font (size 0.85 0.85))))
    (property "Value" "ESP32-S3R8" (at 10 10 0) (effects (font (size 0.85 0.85))))
    (property "Manufacturer" "{u501_mfg}" (at 10 10 0) (hide yes)(effects (font (size 0.85 0.85))))
    (property "MPN" "ESP32-S3R8" (at 10 10 0) (hide yes)(effects (font (size 0.85 0.85))))
    (property "LCSC" "C2913194" (at 10 10 0) (hide yes)(effects (font (size 0.85 0.85))))
  )
  (symbol(lib_id "Panda7:C501")(at 20 20 0)(unit 1)(in_bom yes)(on_board yes)(dnp no)
    (property "Reference" "C501" (at 20 20 0) (effects (font (size 0.85 0.85))))
    (property "Value" "22u / ESP32" (at 20 20 0) (effects (font (size 0.85 0.85))))
    (property "Manufacturer" "{c501_mfg}" (at 20 20 0) (hide yes)(effects (font (size 0.85 0.85))))
    (property "MPN" "{sch_c501_mpn}" (at 20 20 0) (hide yes)(effects (font (size 0.85 0.85))))
    (property "LCSC" "{c501_lcsc}" (at 20 20 0) (hide yes)(effects (font (size 0.85 0.85))))
  )
  (symbol(lib_id "Panda7:C514")(at 25 25 0)(unit 1)(in_bom yes)(on_board yes)(dnp yes)
    (property "Reference" "C514" (at 25 25 0) (effects (font (size 0.85 0.85))))
    (property "Value" "DNP / USB tuning" (at 25 25 0) (effects (font (size 0.85 0.85))))
    (property "Manufacturer" "FH (Fenghua Advanced)" (at 25 25 0) (hide yes)(effects (font (size 0.85 0.85))))
    (property "MPN" "0402CG0R8C500NT" (at 25 25 0) (hide yes)(effects (font (size 0.85 0.85))))
    (property "LCSC" "C40459" (at 25 25 0) (hide yes)(effects (font (size 0.85 0.85))))
  )
  (symbol(lib_id "Panda7:TP1")(at 30 30 0)(unit 1)(in_bom no)(on_board yes)(dnp no)
    (property "Reference" "TP1" (at 30 30 0) (effects (font (size 0.85 0.85))))
    (property "Value" "VBUS_USB" (at 30 30 0) (effects (font (size 0.85 0.85))))
    (property "Manufacturer" "{NON_PURCHASED_PCB_FEATURE_MANUFACTURER}" (at 30 30 0) (hide yes)(effects (font (size 0.85 0.85))))
    (property "MPN" "{NON_PURCHASED_PCB_FEATURE_MPN}" (at 30 30 0) (hide yes)(effects (font (size 0.85 0.85))))
    (property "LCSC" "" (at 30 30 0) (hide yes)(effects (font (size 0.85 0.85))))
  )
)
"""
    (candidate_dir / f"{board}.kicad_pcb").write_text(pcb_text)
    (candidate_dir / f"{board}.kicad_sch").write_text(sch_text)


class MainlandBomComplianceTests(unittest.TestCase):
    def test_all_mainland_components_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cand = Path(tmp)
            _sample_pcb_and_sch(cand, "Single")
            report = verify_all_boards(cand, boards=("Single",))
            self.assertTrue(report["all_passed"])
            single = report["boards"]["Single"]
            self.assertEqual(single["populated_bom_count"], 2)
            self.assertEqual(single["dnp_count"], 1)
            self.assertEqual(single["non_bom_pcb_feature_count"], 1)
            self.assertEqual(single["mainland_populated_rate_pct"], 100.0)

    def test_foreign_manufacturer_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cand = Path(tmp)
            _sample_pcb_and_sch(cand, "Single", u501_mfg="Texas Instruments")
            res = verify_board_mainland_compliance(cand, "Single")
            self.assertFalse(res["all_passed"])
            self.assertEqual(len(res["foreign_manufacturer_refs"]), 1)
            self.assertEqual(res["foreign_manufacturer_refs"][0]["ref"], "U501")

    def test_missing_manufacturer_is_fixed_by_eco(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cand = Path(tmp)
            _sample_pcb_and_sch(cand, "Single", c501_mfg="", c501_mpn="", c501_lcsc="", sch_c501_mpn="")
            before = verify_board_mainland_compliance(cand, "Single")
            self.assertFalse(before["all_passed"])
            self.assertIn("C501", before["missing_manufacturer_refs"])

            apply_mainland_metadata_eco(cand, boards=("Single",))
            after = verify_board_mainland_compliance(cand, "Single")
            self.assertTrue(after["all_passed"])
            self.assertEqual(after["missing_manufacturer_refs"], [])

    def test_schematic_pcb_parity_mismatch_is_caught(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cand = Path(tmp)
            _sample_pcb_and_sch(cand, "Single", sch_c501_mpn="WRONG_MPN")
            res = verify_board_mainland_compliance(cand, "Single")
            self.assertFalse(res["all_passed"])
            self.assertEqual(len(res["sch_parity_mismatches"]), 1)
            self.assertEqual(res["sch_parity_mismatches"][0]["ref"], "C501")

    def test_registry_has_26_verified_mainland_manufacturers(self) -> None:
        self.assertEqual(len(MAINLAND_MANUFACTURERS), 26)
        for mfg, info in MAINLAND_MANUFACTURERS.items():
            self.assertIn("China", info["hq_location"], f"{mfg} must be located in China")
            self.assertTrue(info["chinese_name"], f"{mfg} must have full Chinese corporate name")


if __name__ == "__main__":
    unittest.main()
