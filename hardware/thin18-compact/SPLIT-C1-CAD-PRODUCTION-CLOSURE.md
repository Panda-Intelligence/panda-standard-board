# Split-C1 CAD and Manufacturing-Data Closure

Date: 2026-10-01
Baseline: 60de713, branch hw/thin18-compact-evt.
Final architecture: Core-C1 + Display-C1. C4D-20 integrated outputs remain historical.

| Board | Nominal dimensions | Copper layers | DRC | Open | Parity | ERC | BOM refs | SMT CPL refs |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Core-C1 | 96 × 68 mm | 4 | 0 | 0 | 0 | 0 | 118 | 117 |
| Display-C1 | 45 × 36 mm | 2 | 0 | 0 | 0 | 0 | 37 | 37 |

Fresh native KiCad 10.0.5 checks include all severities and schematic parity.
No routing-rule reductions, new DRC exclusions, or signal no-connect substitutions were used.
All populated BOM entries have Manufacturer and exact MPN. BOM/CPL refs reconcile.

## Active artifacts

- Core candidate: core-c1-96x68-split/
- Display candidate: display-c1-45x36-production-bom/
- Core package: production/core-c1-96x68/
- Display package: production/display-c1-45x36/
- Combined frozen record: production/split-c1-release.json
- Interface contract: split-c1-interface.json
- Reviewed copper replay: core-c1-routing-closure.json

Both packages contain generic BOM/CPL, Gerbers, separate PTH/NPTH drills,
CRC-checked Gerber ZIP, JLC BOM/CPL, assembly-sourcing CSV, native check reports,
production manifest, board release-candidate record and SHA256SUMS.
Blank LCSC IDs remain explicit MPN/consigned-part sourcing tasks:
Core has 17 SMT refs requiring mapping/consignment and 1 manual assembly item;
Display has 24 refs requiring mapping/consignment. These are not claimed as
automatic JLC library matches.

## Electrical and mechanical interface

Core J601 is Hirose DF40C-60DS-0.4V(58), B.Cu, 0°, center (61,62) mm.
Display J1 is DF40C-60DP-0.4V(51), B.Cu, 0°, center (23,4) mm.
The socket orientation was corrected from the exploratory 180° placement.

All 60 pins are verified against both PCB pads and schematic netlists:
6 signals, 2 EPD logic supply pins, 23 GND pins, and 29 explicit reserved NC pins.
All adapter refs C801-C813, D801-D803, U801-U803, R801-R814, J802, L801,
Q801 and TP801-TP806 are absent from the Core PCB.

With opposite B.Cu mounting faces, the Display-to-Core transform is:
x_core = x_display + 38; y_core = 66 - y_display; z_core = -1.5 - z_display.
The display board projects to x=38..83, y=30..66 mm inside the Core outline.
All pin columns and odd/even rows align under this transform.
Socket and plug solder-land row centers differ by 0.185 mm by design;
solder lands on separate boards are not contact-position datums.
Hirose specifies this receptacle/plug mating family and 1.5-mm mated board gap.

Authoritative connector sources:
- https://www.hirose.com/en/product/p/CL0684-4004-6-58
- https://www.hirose.com/en/product/p/CL0684-4003-3-51
- https://www.hirose.com/en/product/series/DF40

## Rebuild and export

Existing candidates are preserved by default. Builders refuse to overwrite them.
Use a fresh --output directory to reproduce either candidate.
Core builds replay the reviewed copper closure and require native 0/0/0/0.
A fresh Core replay and fresh Display rebuild both passed 0/0/0/0;
the replayed Core copper digest matches the frozen routing.

export_production.py supports separate PCB/schematic paths and detects the
actual copper-layer count. It blocks exports on CAD failures, incomplete
Manufacturer/MPN, dimension mismatch, missing drill files, or ZIP corruption.
Run export_jlc.py after each board export, then freeze_split_c1_release.py
to verify all hashes and write both board records and the combined record.
The geometry-search tools are optional engineering tools; the frozen closure
rebuild requires only the standard Python library and installed KiCad.

## Gates deliberately still open

manufacturing_release=false.

The actual enclosure/component Z-stack and physical connector mating are not
verified. The existing rear-battery envelope overlaps the display XY projection;
final battery layer, swelling allowance and service clearance require mechanical
resolution. The 1.5-mm gap must be checked against component maximum heights.
Panel/FPC insertion, retention and actual fit remain physical gates.

USB-C compliance, USB2 SI, charging/NTC, ship mode, deep sleep, front-light current
accuracy, OVP/open-string behavior, capacitor DC bias, hot diode leakage, magnetics
temperature/EMI/acoustics, RF, thermal and soak require real boards and instruments.
CAD-clean manufacturing data does not mark these physical tests as passed.

Foreign parts blocked by electrical or mating contracts remain retained as
specified in the handoff. Further localization belongs in a qualified sourcing ECO.
