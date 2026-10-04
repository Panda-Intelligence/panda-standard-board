# Split-C1 current handoff

## Correct project and worktree

Continue from `/Users/isaac/workspace/AI/panda-standard-board-main-ic`, branch
`hw/split-c1-main-ic-audit`, based on remote main `6906a246`.
The user explicitly selected the already split, routed **Core-C1 + Display-C1**
main baseline. Do not resume Thin7/portrait-R2; its 9-airwire checkpoint is not
this board. All other worktrees, including the original root's packaging/, are
left alone.

Native authorities under `hardware/thin18-compact/`:

```text
core-c1-96x68-split/eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16/
display-c1-45x36-production-bom/
```

Core stays 96x68mm, four copper layers; Display stays45x36mm, two layers; both
0.8mm. Main's ESP32-S3-WROOM-1U-N16R8 module and HCTL60-pin mating pair stay.
The incomplete 7mm enclosure redesign is separate from this bench prototype.

## Current electrical change

Read `SPLIT-C1-POWER-INTEGRITY.md` and `split-c1-power-integrity.json`.
U906 SGM809B-TXN3LG/TR supplies real monitored AON status to PG_3V3_MAIN.
R2041.2k/R2015.6k now bias PSEL from the charger's pre-AON REGN output. C204330nF
is reused and relocated as U906 bypass. No existing power IC, connector or host
module is moved. Only C204 moves; U906 is new. Display native files, existing
unrelated copper, board outlines and project rules are unchanged.

The isolated edited candidate passed DRC/open/parity/ERC0/0/0/0. A fresh rebuild
from immutable Git history reproduced the same canonical native CAD and passed
0/0/0/0. Adoption checks source hashes and records exact changed native files in
`split-c1-power-integrity-adoption.json`. The current saved source must still
pass the full release command below; its generated evidence is authoritative.

Expected populated totals after this additive ECO:156 mainland-manufacturer
system refs (Core119,Display37);17 board-level IC refs (Core14,Display3).
Core117SMT plusC301/TH301 manual-or-offboard;Display37SMT. The exact domestic
identity audit must be regenerated, never edited to manufacture a passing count.

## Reproduction and evidence

```sh
python3 hardware/thin18-compact/release_split_c1.py --target split-c1
python3 hardware/thin18-compact/verify_split_c1_supply.py --negative-controls
```

The pipeline requires explicit design selection, both current/rebuilt native
checks, independent power pin/variant checks,22 unit tests, exact identity and
BOM/CPL checks,60-pin interface, mechanical screen and CRC/hash-bound outputs.
Thin7 audit cannot export Split-C1 data, even if its own audit someday passes.

Read `split-c1-validation.json`, `split-c1-power-integrity-verification.json`,
`split-c1-domestic-audit.json`, `split-c1-interface.json` and
`production/jlc-prototype-orderpack/prototype-status.json` after generation.
The reusable package is `production/Panda-Split-C1-JLC-Prototype.zip`; it is
local generated output, not a manufacturing release or purchase authorization.
Transient candidates/backups are under repo-root `.work/split-c1-power-eco/`.

## Next functional and supply work

Seven exact SMT refs remain unaccepted/unmapped:U902,U905,U402-U405,U906.
The last one is a newly added domestic supervisor, not an imported exception.
Do not omit it or assign a similar part's code. `split-c1-smt-consignment.json`
and `split-c1-supply-plan.json` retain real-receipt requirements. Historical
public stock observations keep their original dates and are not reservations.

PG is status only, not MCU reset, overvoltage protection or regulator-current
reporting. XL9535P14 must remain input; its firmware behavior is not yet proven.
A REGN-derived PSEL removes dependence on downstream AON startup, but does not
prove all analog ramps or a hard500mA ceiling. Integrate/verify reset-watchdog
IINDPM policy,5Vsink/noOTG,USB enumeration/suspend,charger/NTC,regulator,gauge,
RTC and frontlight sequencing before declaring a functional prototype complete.

Physical PG/REGN/PSEL/current traces, thermal/charging, real-board EVT, actual
supply, assembly acceptance and battery/enclosure qualification remain open.
Mainland manufacturer identity does not establish Flash/PSRAM origin inside the
ESP module or all ICs inside externally supplied display/touch modules.
