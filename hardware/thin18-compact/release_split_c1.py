#!/usr/bin/env python3
"""Generate explicitly selected engineering data; never mix Split-C1 and Thin7.

Split-C1 is the populated, routed two-board baseline. Thin7 is a separate
mechanical redesign, not a prerequisite for a Split-C1 bench prototype.
Neither target grants physical qualification or authorizes an assembly order.
"""
import argparse
import json
import subprocess
import sys
from _split_c1_common import ROOT, kicad_python


def release_steps(target):
    """Return the checked pipeline without running tools on import."""
    if target == "thin7":
        return [("thin7/audit_thin7.py", ["--require-native-ready"], False)]
    if target != "split-c1":
        raise ValueError("An explicit supported design target is required")
    steps = [
        ("validate_split_c1.py", [], False),
        ("test_split_c1_fabrication.py", [], False),
        ("test_split_c1_assembly_process.py", [], False),
        ("verify_split_c1_power_integrity.py", [], False),
        ("verify_split_c1_hardware_finish.py", [], False),
        ("verify_split_c1_cap_drill.py", [], False),
        ("test_split_c1_power_integrity.py", [], False),
        ("test_split_c1_control.py", [], False),
        ("verify_split_c1_control.py", [], False),
        ("verify_split_c1_supply.py", [], False),
        ("audit_split_c1_mechanical.py", [], True),
        ("audit_split_c1_assembly_process.py", [], True),
    ]
    for board, candidate, output, width, height in [
        ("Core-C1", "core-c1-96x68-split", "core-c1-96x68", 96, 68),
        ("Display-C1", "display-c1-45x36-production-bom", "display-c1-45x36", 45, 36),
    ]:
        arguments = ["--candidate", ROOT / candidate, "--output", ROOT / "production" / output,
                     "--board-id", board, "--nominal-size", width, height]
        if board == "Display-C1":
            arguments += ["--pcb-relative", "PANDA-EPD0426-SPI-EVT.kicad_pcb",
                          "--schematic-relative", "PANDA-EPD0426-SPI-EVT.kicad_sch"]
        steps += [("export_production.py", arguments, False),
                  ("export_jlc.py", ["--production", ROOT / "production" / output], False)]
    steps += [("audit_split_c1_domestic.py", ["--require-complete"], False),
              ("freeze_split_c1_release.py", [], False),
              ("package_jlc_prototype.py", [], False),
              ("verify_split_c1_fabrication.py", [], False)]
    return steps


def execute(target, runner=None):
    """Stop on any failed check. Thin7 can never export the Split-C1 boards."""
    if runner is None:
        def runner(script, arguments, native):
            subprocess.run([kicad_python() if native else sys.executable,
                            str(ROOT / script), *map(str, arguments)], check=True, cwd=ROOT)
    for script, arguments, native in release_steps(target):
        runner(script, arguments, native)
    if target == "thin7":
        raise RuntimeError("Thin7 audit is not a release pipeline. No Split-C1 artifacts were exported.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, choices=["split-c1", "thin7"],
                        help="split-c1: routed main-branch bench prototype; thin7: audit only")
    parser.add_argument("--plan", action="store_true", help="Print selected steps without modifying files")
    args = parser.parse_args(argv)
    if args.plan:
        print(json.dumps({"design_target": args.target, "manufacturing_release": False,
                          "steps": [{"script": script, "arguments": list(map(str, arguments)),
                                     "native_python": native}
                                    for script, arguments, native in release_steps(args.target)]}, indent=2))
        return 0
    execute(args.target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
