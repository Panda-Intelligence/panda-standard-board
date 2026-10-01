#!/usr/bin/env python3
"""Recreate both local production packages from the committed native CAD."""
import subprocess, sys
from _split_c1_common import ROOT, kicad_python

def run(script, *arguments, native=False):
    subprocess.run([kicad_python() if native else sys.executable, str(ROOT / script),
                    *map(str, arguments)], check=True, cwd=ROOT)

run("validate_split_c1.py")
run("audit_split_c1_mechanical.py", native=True)
for board, candidate, output in [
    ("Core-C1", "core-c1-96x68-split", "core-c1-96x68"),
    ("Display-C1", "display-c1-45x36-production-bom", "display-c1-45x36")]:
    extra = [] if board == "Core-C1" else [
        "--pcb-relative", "PANDA-EPD0426-SPI-EVT.kicad_pcb",
        "--schematic-relative", "PANDA-EPD0426-SPI-EVT.kicad_sch", "--nominal-size", 45, 36]
    run("export_production.py", "--candidate", ROOT / candidate,
        "--output", ROOT / "production" / output, "--board-id", board, *extra)
    run("export_jlc.py", "--production", ROOT / "production" / output)
run("freeze_split_c1_release.py")

run("package_jlc_prototype.py")
