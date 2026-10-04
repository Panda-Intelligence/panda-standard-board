> **Current hardware-finish checkpoint (2026-10-04):** use the freshly regenerated
> Split-C1 package, not an older ZIP. Default-off charger authorization and direct
> GPIO2 shutdown are implemented. Population is now **162 mainland system refs**
> (Core125/123SMT + C301/TH301; Display37/37SMT). New Q907/Q908/R930-R933 reuse
> reviewed exact catalog identities; the same7 older SMT supply gaps remain.
> Read [hardware finish](SPLIT-C1-HARDWARE-FINISH.md) for TP19 FORCE-LOW access and
> incompatible old firmware. Earlier156-ref and missing-hardware-gate descriptions
> below are historical; real source-bound generated audits override old counts.

# Split-C1 CAD and Manufacturing-Data Closure

> Current Split-C1 power-integrity ECO: the saved main-derived board now adds
> U906 SGM809B-TXN3LG/TR, reuses R201/R204 for REGN-derived PSEL and moves C204
> to supervisor bypass. Expected current BOM: 156 mainland refs (Core119,
> Display37), Core117 SMT + 2 manual/offboard, Display37 SMT. Seven SMT refs
> remain unmapped (U902,U905,U402-U405,U906). Older observations below retain
> their dates; use [the current power contract](SPLIT-C1-POWER-INTEGRITY.md),
> regenerated audits and the handoff for the current source. No actual stock,
> assembly acceptance or physical EVT result is asserted.


Date: 2026-10-01
Baseline: 60de713, branch hw/thin18-compact-evt.
Final architecture: Core-C1 + Display-C1. C4D-12..20 intermediate snapshots remain in Git history.

| Board | Nominal dimensions | Copper layers | DRC | Open | Parity | ERC | BOM refs | SMT CPL refs |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Core-C1 | 96 × 68 mm | 4 | 0 | 0 | 0 | 0 | 118 | 117 |
| Display-C1 | 45 × 36 mm | 2 | 0 | 0 | 0 | 0 | 37 | 37 |

Fresh native KiCad 10.0.5 checks include all severities and schematic parity.
No routing-rule reductions, new DRC exclusions, or signal no-connect substitutions were used.
All populated BOM entries have Manufacturer and exact MPN. BOM/CPL refs reconcile.

## Native authorities and generated artifacts

- Core candidate: core-c1-96x68-split/
- Display candidate: display-c1-45x36-production-bom/
- Generated Core package: production/core-c1-96x68/
- Generated Display package: production/display-c1-45x36/
- Generated combined record: production/split-c1-release.json
- Interface contract: split-c1-interface.json
- Reviewed copper replay: core-c1-routing-closure.json

Both packages contain generic BOM/CPL, Gerbers, separate PTH/NPTH drills,
CRC-checked Gerber ZIP, JLC BOM/CPL, assembly-sourcing CSV, native check reports,
production manifest, board release-candidate record and SHA256SUMS.
Blank LCSC IDs remain explicit MPN/consigned-part sourcing tasks:
Core has6 SMT refs requiring exact mapping/consignment,plus2 manual items
(C301 on-board hand-solder and TH301 offboard);Display has0 missing IDs.
Current155-ref domestic identity audit is complete;actual PCBA supply/acceptance
is not. See SPLIT-C1-PROCUREMENT-QUESTIONS.md and split-c1-smt-consignment.json.

## Electrical and mechanical interface

Core J601 is HCTL HC-PBB40C-60DS-0.4V-1.5-02, B.Cu, 0°, center (61,62) mm.
Display J1 is HCTL HC-PBB40C-60DP-0.4V-02, B.Cu, 0°, center (23,4) mm.
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

Run this from the repository root using Python 3.10+ and KiCad 10.0.5:

```sh
python3 hardware/thin18-compact/release_split_c1.py --target split-c1
```

The command rebuilds both candidates into temporary directories, compares native
CAD and procurement properties, runs the 60-pin interface and mechanical audit,
exports both boards, checks BOM/CPL, validates ZIPs and freezes SHA256SUMS.
It also binds physical qualification to both current PCB identities.
Only native source/config/library files, scripts, purchasing evidence and concise
audit summaries are committed. Gerbers, ZIPs, XML netlists and duplicated package
reports remain generated outputs; they are covered by the local package hashes.

KiCad is discovered on PATH with the macOS application fallback. Set KICAD_CLI
and KICAD_PYTHON for other installations; KICAD_PYTHON must import wx and pcbnew.
The immutable replay source is Git commit
60de7135de31d4e49fd8351565e4e34d60a4af96. Use a full-history clone. If the source
commit is absent after a shallow or squash-only checkout, retrieve the original
PR history first:

```sh
git fetch origin refs/pull/7/head
```

The helper selects native CAD/library inputs from that commit and excludes old
verification reports, route-search outputs and intermediate snapshots.
Existing candidates are preserved by default. Builders refuse to overwrite them.
Use a fresh --output directory to reproduce either candidate.
Core builds replay the reviewed copper closure and require native 0/0/0/0.
A fresh Core replay and fresh Display rebuild both passed 0/0/0/0;
the replayed Core copper digest matches the frozen routing.

export_production.py supports separate PCB/schematic paths and detects the
actual copper-layer count. It blocks exports on CAD failures, incomplete
Manufacturer/MPN, dimension mismatch, missing drill files, or ZIP corruption.
For individual steps, run validate_split_c1.py, then audit_split_c1_mechanical.py,
export_production.py and export_jlc.py for each board, then freeze_split_c1_release.py
to verify all hashes and write both board records and the combined record.
The geometry-search tools are optional engineering tools; the frozen closure
rebuild requires only the standard Python library and installed KiCad.

## Gates deliberately still open

manufacturing_release=false.

The actual enclosure/component Z-stack and physical connector mating are not
verified. The existing rear-battery envelope overlaps the display XY projection;
the full battery rectangle intersects the mating connector region and must
sit outside the interboard gap. A parameterized rear-layer proposal and native
XY audit are now recorded in SPLIT-C1-MECHANICAL-SOURCING.md. Battery dimensions,
swelling, supports and service clearance remain unverified. J201 midmount body,
shell stakes and solder require a Z-clearance check at the Display edge.
Panel/FPC insertion, retention and actual fit remain physical gates.

USB-C compliance, USB2 SI, charging/NTC, ship mode, deep sleep, front-light current
accuracy, OVP/open-string behavior, capacitor DC bias, hot diode leakage, magnetics
temperature/EMI/acoustics, RF, thermal and soak require real boards and instruments.
CAD-clean manufacturing data does not mark these physical tests as passed.

Foreign parts blocked by electrical or mating contracts remain retained as
specified in the handoff. Further localization belongs in a qualified sourcing ECO.

## PR artifact policy

The PR previously contained 1,199 files and 825,769 added lines, including ten
C4D-12..20 candidate trees (two C4D-14 trees), copied historical reports and
three generated production packages. These trees and generated copies have
been removed from the current tree without rewriting Git history. The current
Core and Display native CAD and their required libraries remain reviewable.
No KiCad native design, custom rule or required source library is discarded.
The historical C4D-20 manifest with machine-specific absolute paths is archived;
the current exporter rejects candidates outside the checkout before writing
outputs and records repository-relative artifact paths.
