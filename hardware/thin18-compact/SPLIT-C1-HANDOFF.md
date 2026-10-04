# Split-C1 current hardware handoff

## Authoritative continuation

Worktree: `/Users/isaac/workspace/AI/panda-standard-board-main-ic`.
Authoritative branch: `main`. Hardware closure is merged through PR #16
(`ebacff2`), and C301 drilling/fabrication closure through PR #17 (`d77a33c`).
Start new work from current remote main, not an old unmerged experiment.
The user wants the already routed two-board main-branch design finished for
prototype fabrication. Do NOT restart Thin7/portrait-R2 or expand unrelated
firmware. Other worktrees and the original packaging/ directory are untouched.

Native authorities under `hardware/thin18-compact/`:

```
core-c1-96x68-split/eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16/
display-c1-45x36-production-bom/
```

Core96x68mm/4 layers, Display45x36mm/2 layers, both0.8mm. Keep the main-branch
ESP32-S3-WROOM-1U-N16R8 and HCTL60-pin interconnect. Split-C1 does not claim the
separate uncompleted7mm enclosure target.

## Hardware-finish checkpoint

Read `SPLIT-C1-HARDWARE-FINISH.md` and `split-c1-hardware-finish.json`.
The two known static hardware issues are now implemented in schematic and PCB:
REGN-derived default-OFF nCE plus two series MOS permissions, and a native
GPIO2/R931 frontlight/charge inhibit that does not pass through I2C. TP19 is a
manual FORCE-LOW access point. New exact parts Q907/Q908/R930-R933 reuse reviewed
mainland identities and catalog codes. No existing component position, board
outline, rule or Display native design is changed.

PG/PSEL changes from `afd63c6` remain intact. Hardware finish builds on the
`3f350ed` baseline. The isolated candidate and fresh immutable-history rebuild
passed native DRC/open/parity/ERC0/0/0/0 with identical canonical CAD before
adoption. The source-hash checked adoption record and frozen copper delta are
`split-c1-hardware-finish-adoption.json` and `split-c1-hardware-finish-layout.json`.
Use the current generated full validation below as the source of truth.

Expected population:162 mainland system refs (Core125,Display37), with
Core123SMT plus C301 manual/TH301 offboard and Display37SMT.17 board-level
IC/module positions remain; Q907/Q908 are additional discrete MOSFETs.
Seven unmapped/unaccepted SMT refs remain:U402-U405,U902,U905,U906. New finish
parts do not add unresolved SKUs. No quote, order or assembly receipt is fabricated.

## Reproduce the prototype package

```
python3 hardware/thin18-compact/release_split_c1.py --target split-c1
python3 hardware/thin18-compact/verify_split_c1_supply.py --negative-controls
```

The pipeline checks current/rebuilt native CAD, both electrical ECO contracts,
original-maker MOS/supervisor lands,21 invalid hardware-contract cases,60-pin
mapping, host-controller compatibility, exact BOM/CPL, mechanical XY, native
rules, separate PTH/NPTH drills and ZIP CRC/hash evidence. The generated output:
`production/Panda-Split-C1-JLC-Prototype.zip`.
Read `production/jlc-prototype-orderpack/prototype-status.json` for actual
bare-board DFM versus supply status. Stale ZIPs from before hardware finish must
not be submitted. Generated outputs and transient trials stay ignored.

## Important compatibility and physical boundaries

P05 is now active-high CHG_REQUEST (defaultLOW), not old active-low BQ_CE.
P15 is NC/input, P14 remains PG/input, P16 remains PWM. GPIO2 is the independent
permit and must initialize LOW with hold disabled. The portable controller
received only the necessary binding/polarity update and direct GPIO callbacks;
old adapters intentionally cannot compile without implementing those callbacks.
No ESP firmware was flashed or claimed physically qualified.

GPIO2 LOW directly removes frontlight EN and charger permission. This does not
make the circuit an autonomous external watchdog. CPU/GPIO stuckHIGH still
requires TP19 clamped to GND or power removed. A simultaneous failure of I2C and
the native GPIO path must remain UNKNOWN in software, not a fabricated OFF.

Before battery charging, prototype tests must measure REGN/nCE startup,
source-change/reset/Hi-Z states, hot/cold margins, limits and NTC behavior. USB,
SI/PI/RF, thermal/magnetics, RTC retention, actual panel/battery/enclosure and
assembly/supplier acceptance remain physical qualification, not native CAD
connectivity. `manufacturing_release=false`; do not confuse this with the ability
to produce checked bare-board prototype Gerber/drill data.

## Main merge and fabrication entry audit

PR #16 merged the three hardware/control checkpoints into main at `ebacff2`.
The manufacturing entry is now generated from per-board manifests. See
`JLC-PROTOTYPE-HANDOFF.md` and `split-c1-fabrication-contract.json`; do not
reuse old manually maintained counts or the old inner0.5oz order text.
Core native copper construction is nominal35um on all four copper layers.
The exporter corrects only Gerber-job/file metadata (revision, nominal size,
finish/color and unsupported impedance declaration). It leaves native CAD,
drawing/aperture commands and drill coordinates unchanged and verifies them.

C301's obsolete short slots are now replaced with1.9mm round plated holes and
2.3mm lands at the same20mm pitch. All existing tracks/vias and other footprints
remain unchanged. See SPLIT-C1-CAP-DRILL.md and its independent verifier; native
current and immutable-baseline replay must remain0/0/0/0. Actual CAM/assembly
acceptance remains distinct from the completed geometry correction. Reports now distinguish native_rule_dfm_passed
from cam_accepted/automatic_fabrication_order_ready. No approval is invented.

`production/jlc-prototype-orderpack/START-HERE.md` is generated, not copied
from historical prose. `verify_split_c1_fabrication.py` rechecks layer functions,
plated/nonplated drills, per-board source identities and every package checksum.
The power verification hashes the semantic netlist rather than its changing
export timestamp; power-pin/variant validation has not been relaxed.

## SMT via-process closure — 2026-10-04

PR #17 was pushed, freshly validated and merged by explicit user request. This
process follow-up starts from the merged main, without native PCB/schematic,
footprint, layer, rule or firmware edits.

Fresh native shape screening finds269 Core through vias,13 of whose drill circles
intersect exposed SMT copper lands (including near-edge intersections); Display
has36 vias and0 such intersections. Core **requires Epoxy Filled & Capped** for
the listed sites, not mere soldermask tenting/plugging. C301 lead holes, USB slots,
component PTH and NPTH are not via-fill targets. Full via treatment may cover
Core's269-via inventory only after CAM agrees the scope.

The new native auditor compares actual filled copper polygons to drill circles,
not bounding boxes or the annular copper diameter. It rejects unsupported pad
voids/blind vias, records nominal geometry and the1um polygon tolerance, and
separately lists0.22/0.23mm WLCSP and small rectangular SMT lands for ENIG/stencil
review. It does not certify solder paste apertures, fabricated tolerances or yield.

`audit_split_c1_assembly_process.py` plus29 synthetic tests are required by the
existing release command. `split-c1-assembly-process.json` records source hashes,
via UUIDs and the measured list. The generated packet includes
`ASSEMBLY-PROCESS.md`, `assembly-process.json` and per-board `VIA-IN-PAD.csv`.
The final fabrication verifier matches the entire via inventory against actual
PTH Excellon hits and checks the copied maps and requirements. Do not silently
select ordinary open vias for Core when submitting the Gerbers.

All162 exact mainland identities and the seven supplier-acceptance gaps remain
unchanged. Actual fill/cap quote, CAM acceptance, stencil approval, assembly and
physical EVT are not closed by generating this record.
