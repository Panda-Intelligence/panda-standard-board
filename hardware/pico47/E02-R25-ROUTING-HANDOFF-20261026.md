# Pico47 E0.2 r25 — Core 4-layer routing handoff (2026-10-26)

Status: **NOT routed to completion, NOT for fabrication.** Best legal router state is
77/81 connections on the current geometry (E26). No checkpoint has been captured and
the published r24 package is unchanged.

## 2026-10-29 contract-fixed continuation

The current R25 contract/ECO experiment is tracked separately from the older E26
count above. R533 was moved to PCB `(51.5, 100.8)` at `180°` inside the approved
reset-cluster allowance. The fixed `design.json` A/B/C/D assignment was then used
with no router group reassignment. The best Native materialization has 12 Core
opens, zero error-level DRC violations, 274 warnings, parity 1 (the existing C501
manufacturer-field warning), Display ground 68/68 and both J601 named ground
targets connected. C530.2 is still the only Core ground island, so this is not a
checkpoint. Dynamic reassignment trials that reached clean DRC were rejected when
their materialized pad nets differed from the contract.

Evidence remains ignored under `.work/r25-resume-codex-20261027/`; see the dated
Codex handoff/state files for hashes and the exact SDMMC_D2 repair audit. Core14,
complete ERC/capture/replay and manufacturing gates remain open.

The latest fixed-contract topology keeps a real C530.2-to-main-GND bridge while
jointly rerouting the dense XSTL/D8/SDMMC_D2 corridor. Its Native materialization
passes complete ground (Core 169/169, Display 68/68, J601 targets 2/2), Native
DRC errors 0 and parity 1, but still reports 25 unconnected items. It is the
current experimental routing seed, not a release checkpoint; the remaining
opens include I2C, power-enable, VSYS and SD-card segments.

Using that seed, a focused SD-card reroute closed the SDMMC_D2_CARD, SDMMC_D0_CARD
and SDMMC_CMD_CARD model islands with exact geometry 0 issues. The resulting
Native materialization is still experimental (24 opens, DRC errors 0, parity 1,
complete ground retained); it is not yet a checkpoint.

The same seed then closed `EN_VSYS_AUDIO` and `FL_PWM`, followed by a separate
`KEY_POWER_MCU` repair and the SD-card reroute replay. The latest Native trial
has 18 Core opens, zero DRC errors, parity 1, complete ground and the two J601
named targets connected. `SD_CD` and `P47_BUS_SELECT` remain blocked under their
fixed obstacles; I2C and protected power/EPD segments remain open.

The fixed-contract I2C_SCL/I2C_SDA joint search also returned no path. The
remaining ordinary SD_CD/BUS_SELECT search was similarly blocked. Disk space is
currently about 3.1 GiB, so the full-G/routing batch gate is intentionally left
closed until space recovers; no source PCB was changed.

## Starting point

- r24 engineering candidate (Core 16 unconnected, Display 0), copied unchanged to the
  ignored working directory `.work/pico47-r25-20261025/base-r24`.
- All generated geometry, router states, KiCad trial boards, DRC reports and renders stay
  in `.work/pico47-r25-20261025/` (ignored). Only the tools in `r25_router/` are source.

## Approach

The 16 r24 opens could not be closed in place, so the dense MCU/mux region was ripped
and rerouted with a custom grid router (`r25_router/`):

- 0.025 mm grid over the whole Core board; signal layers F.Cu / In2.Cu / B.Cu only.
  In1.Cu stays the solid GND plane with no signal tracks.
- Project rules are mirrored exactly and not relaxed:
  - track 0.15 mm, clearance 0.15 mm;
  - via 0.4/0.2 mm;
  - hole clearance 0.25 mm, hole-to-hole 0.25 mm;
  - board edge 0.2 mm.

  `exact_check.py` re-verifies new copper with shapely, and KiCad DRC is authoritative.
- PathFinder negotiation, then minimum-vertex-cover legalisation (CP-SAT), then
  transactional polish. `runs/loop.sh` repeats this cycle.
- Pin-swap groups solved by Hungarian assignment, within the swap ECO the user approved:
  - **A**: mux S1 pins → R710–R717.
  - **B**: direct GPIOs → R719–R725, codec and R726/R727/R729/R730.
  - **C**: SD S0 pins → R517–R522.
  - **D**: mux commons → U501 GPIO5–10.
  - **Fixed**: UART on GPIO43/44, GPIO3 strap, GPIO45 = XSTL strap.

## Geometry ECOs applied in the working copy (user-approved, not yet in source)

1. **Pin swap** of the GPIO matrix and the mux channels. The user authorized the
   electrical pin map on 2026-10-28. It is now recorded in `design.json`,
   `pico47_contract.py` and the contract tests. The authorization does not waive
   Native DRC, complete-ground, schematic parity, timing or firmware verification.
   The approved map keeps the physical UART terminals on GPIO43/GPIO44 and uses
   the following channel pairs in the moved U710/U711 region:

   | mux common | MCU GPIO | SD/UART select | panel select |
   |---|---:|---|---|
   | P47_MUX0 | 8 | SDMMC_D0 | P47_D0_SRC |
   | P47_MUX1 | 9 | SDMMC_D1 | P47_D2_SRC |
   | P47_MUX5 | 43 | UART0_TX | P47_D3_SRC |
   | P47_MUX3 | 44 | UART0_RX | P47_D1_SRC |
   | P47_MUX4 | 7 | SDMMC_CLK | P47_D5_SRC |
   | P47_MUX2 | 10 | SDMMC_D3 | P47_D6_SRC |
   | P47_MUX6 | 5 | SDMMC_CMD | P47_D4_SRC |
   | P47_MUX7 | 6 | SDMMC_D2 | P47_D7_SRC |
2. **Passive moves (E6)**:
   - C525, L507, C710, R513, R512, R510, R528 (`runs/moves-E6.json`);
   - C523 and C501 (`runs/moves-e24.json`).
3. **C501 22 µF 0805 → 0603** (user-approved). Kept at 22 µF.
   - The replacement mainland manufacturer part number is **not chosen yet**; a catalog
     code must not be invented.
   - The footprint, schematic and BOM change is still pending.
   - Approval also covers C525 0805 → 0603, but C525 currently keeps its 0805 land.
4. **3V3_AON bottom trunk under U501 removed.** It is replaced by:
   - an 18 mm, 0.35 mm In2 bridge along y≈109.9 (under the microSD area) to the right
     trunk end at C501/R511;
   - a 1.7 mm B.Cu link from U501.20/C523 to the left 3V3 network.

   The RF supply path to L507 is now longer: about 40 mm, estimated 17 mV drop at
   300 mA. This needs electrical review.
5. **Fixed GND escapes for pour-isolated pins** (KiCad trial findings):
   - J601.34: via at (44.225, 102.95), placed left of the FFC so the D11 lane stays open;
   - J503.4: via at (51.975, 98.215);
   - forced thermal spokes for U710.8 and C523.2;
   - five bare GND stitching vias removed from the U710/U711 corridor
     (`make_e15.py`).
6. KiCad trials show mid-segment T junctions are not recognised as connected.
   `kicad_split_tees.py` splits them and is part of `runs/trial.sh`.

## Results

| State | Geometry | Legal connections | Notes |
|---|---|---|---|
| `best-e9b-77` | E9b | 77/81 | Older geometry; J503.4 and J601.34 GND isolated in the KiCad trial |
| `route-e14-l0` | E12 | 75/81 | KiCad trial: 0 DRC errors, GND one cluster, 8 signal opens |
| `route-e26-l` | E26 | 77/81 | Current geometry. Pending: BS:U501.18 (D11_SRC), DS:U711.9 (MUX6), P47_XSTL_SRC, UART0_RX |

The bottleneck is the U501 (QFN56, 0.4 mm pitch) escape region. U501 has no spare
GPIO: pins 28 and 38–42 are reserved for octal PSRAM. Hypothetical runs that removed
C523/C501 and the bottom 3V3 trunk dropped the negotiated conflicts from 10 to 3–6,
which motivated ECOs 3–4.

## 2026-10-27 authorized large relayout study

The user authorized changing the placement region of U710, U711 and J503, moving
connectors, and adjusting the board-edge mechanical envelope while retaining four
layers and keeping In1.Cu as the GND plane. The study therefore tested a large
left/up MCU/mux relocation, a moved J503, a rotated R518, and several J501 poses.
The formal r24 source and all generated R25 CAD remain unchanged.

The best complete router state on the first relayout reached 81/81 only while the
old J503 rule-area keepout was still at its old position. After moving that keepout
with J503, the verified legal state was 80/81 (`BS:U501.43` pending); transactional
polish tried budgets 2 through 512 and rolled back every attempt. The related J501
position study produced a 79/81 state with `exact_check.py` at 0 issues, but its
fresh Native trial still had 23 unconnected items, 62 error-level DRC violations, 38 parity items
and board-edge/courtyard/keepout failures. It is rejected.

The stable working baseline remains the previously verified 79/81 geometry with
`UART0_RX` and the SD command-side endpoint unresolved. No relayout candidate has
been adopted as a fabrication checkpoint. The source pin contract now records the
user-authorized R25 electrical permutation, while the formal r24 source and all
generated R25 CAD remain separate and reversible. No fabrication or Core14 claim is
made.

The latest moved U710/U711/J503 Native trial (`.work/r25-resume-codex-20261027/
trial-relayout-wide-j503left-power2`) has 7 unconnected items, 7 error-level DRC
violations, 249 warnings and 37 schematic-parity items. Its failures are retained
as engineering evidence, not accepted output. The next repair must carry the J503
keepout with the moved connector, restore J503.4/R732.2 GND returns, clear the
U711 GND-via and TP712 courtyard conflicts, and re-run the full Native gate.

## 2026-10-28 locked-assignment continuation

The approved assignment was locked during a fresh legalisation against the moved
J503 holes. The best saved router state is **79/81**, with only `CHIP_PU` and
`P47_MUX2` pending. A surgery pass rerouted `AS:U710.6` around the J503 NPTH and
removed the previous D2 hole-clearance violation without changing the approved
pin map.

The isolated Native materialisation of that state reports 25 unconnected items,
0 DRC errors, 59 dangling-track warnings, 11 dangling-via warnings and one
remaining C501 manufacturer parity warning after the approved schematic labels
are applied. A trial-only mechanical cleanup removes three redundant GND vias and
the overlapping TP712 courtyard; its independent complete-ground check still has
five GND clusters, including `U710.8`, `J503.4` and `R731.2`, so it is not adopted.
This is a useful routing experiment, not a checkpoint or fabrication candidate.

## 2026-10-28 mechanical-relayout tool and negotiation continuation

The user additionally confirmed that U710/U711/J503 may move within a revised
connector/board-edge mechanical region. A reusable geometry-only tool is now
tracked as `r25_router/relayout_components.py`. It requires an explicit
`old_rot` for every moved footprint, can carry an explicit board outline, moves
rule areas with the selected footprint, preserves pad UUIDs/net names, removes
only local signal copper, rejects non-GND In1.Cu tracks, and checks moved-pad
clearance before writing a candidate. This prevents the earlier temporary scan
from applying an absolute angle as a second rotation.

The corrected wide-left posture reproduces the previously studied coordinates
(U710 49/74, U711 68/80, J503 43.2822/80 and the y=60 left board-edge step).
With the current approved R25 design contract, fresh negotiation reached 81/81
endpoint paths in each early iteration but retained 32 conflicted nets at the
best saved iteration; the five-iteration run ended at 80/81 with 24 conflicts.
No state passed the legal-copper gate, so no Native board was materialised or
adopted. The experiment and logs remain under
`.work/r25-resume-codex-20261027/`; formal r24 and the R25 delivery directory
remain untouched.

`runs/trial.sh` now defaults to the current `hardware/pico47/design.json`
contract (override with `R25_DESIGN`) instead of the stale R24 map. This is a
workflow correctness fix; it does not relax any four-layer, In1-GND, clearance,
ground, parity, or manufacturing gate.

A follow-up width-aware local power search found a zero-conflict geometry-only
candidate for J503.4 and U710.8 at 0.30 mm copper. It could not find J601.12,
and the wider R731.2 search was blocked; the earlier 0.15 mm R731.2 candidate
remains experimental. Native refill and DRC are still required after disk space
recovers, so these local copper candidates are not adopted. Moving J601 1.0 mm
toward the board interior with the same -90° orientation made J601.12 routable
at 0.15 mm; combined with the 0.30 mm J503.4/U710.8/R731.2 escapes, the
geometry-only candidate has 11 added GND objects and zero checked conflicts. It
also rips local panel signal copper, so it remains experimental until all
affected nets are rerouted and Native-verified. The first Native materialization
was rejected because it passed the geometry centroid as the footprint origin;
the corrected origin is x=41.60523 mm for the x=43.75 mm pad-group target. The
corrected board is staged in `trial-j601-right125-native2`, awaiting the 2 GiB
Native disk gate.
The corrected `native2` run reduced Core to 131 DRC violations and 41
unconnected items with one parity item, but complete-ground stayed 165/169
(Display 68/68). Its four missing Core ground pads were J503.4, U710.8, J601.4
and J601.30. Two additional 0.15 mm J601 ground escapes are now present in the
geometry candidate; they await another Native refill after the disk gate clears.

At x=43.75 mm, the same J601 experiment also reconnects all 21 non-GND
connector pads to their matching R7xx pads in the explicit geometry graph. The
combined candidate contains 62 new copper/via objects, passes the independent
0.15 mm conflict audit, and keeps In1.Cu GND-only. It still needs Native
materialisation, zone refill, DRC, complete-ground and parity checks. Native4
reached Core 169/169 ground with direct main-GND bridges but added 12 real
clearance/hole errors, so it was rejected. A selective-layer native5 variant
reported 132 violations and 38 unconnected items with one parity item; CKV
remains open and the variant is not accepted.
Corrected x=44.5 native9 reached complete ground (Core 169/169, Display 68/68)
and no error-level DRC violations, but retained 40 opens, 82 dangling-track
and 24 dangling-via warnings plus one parity item. Its 199 library warnings
come from the isolated duplicate-library cleanup; it is not a release board.
Adding the isolated CKV escape and rerunning Native (native10) reduced opens to
39 while preserving Core 169/169 ground, Display 68/68 and zero error-level
DRC. The remaining opens span broader baseline nets; full negotiation is still
required before any checkpoint.
Corrected x=44.0/x=44.25 Native runs remained at 128 violations, 41 opens and
one parity item, with six errors limited to J601 XLE/XSTL/CKV versus fixed GND
vias. An x=44.5 geometry-only candidate passes the 0-conflict audit and awaits
Native materialization when disk space is sufficient.

## 2026-10-28 approved CHIP_PU electrical ECO and cluster-relayout continuation

The user approved both a real CHIP_PU topology ECO and an overall U501/reset-cluster
relayout while retaining the four-layer stack. The source contract now records a
dedicated `CHIP_PU_MCU` net at U501.4, R510.2, C510.1 and TP18.1, with the existing
10 kOhm pull-up and 1 uF local reset capacitor. J503.1 is now `CHIP_PU_DEBUG` and
reaches the MCU node only through a new 1 kOhm R533 series link
(RC-02K1001FT/C140197). R529 was not repurposed: the native audit confirms it is
already the USB_DP series resistor. `hardware/pico47/firmware_reset_mapping.json`
records the active-low open-drain debug semantics; it deliberately does not invent
a firmware GPIO implementation.

The deterministic helper `r25_router/chip_pu_reset_eco.py` rewrites the five
schematic labels, adds the R533 symbol/metadata, creates the two PCB nets, removes
only old CHIP_PU copper, and accepts an explicit approved cluster pose. Its pure
parser tests pass, and KiCad netlist export independently reports exactly:

```text
CHIP_PU_MCU: U501.4, R510.2, C510.1, TP18.1, R533.1
CHIP_PU_DEBUG: J503.1, R533.2
```

Fresh ignored Native materialisations are retained under
`.work/r25-resume-codex-20261027/`. The no-relayout ECO board is four-layer and
In1 signal-free, but after removing the old shared copper it reports 18 open
items, 31 error-level DRC violations and the pre-existing C501 parity item. A
J503 move to (52,92) and a J503+TP18 trial move to (52,92)/(56.5,58) each removed
local copper as intended; the constrained two-net A* router still returned NO PATH
because the unchanged U501/RF/MCU escape field is densely occupied. These are
rejected experiments, not checkpoints. Core14, capture/replay, complete product
ERC and manufacturing gates remain unrun; no R25 CAD is adopted or fabrication
qualified.

The source test/contract gates pass, but routing acceptance remains pending. The
R25 working branch may carry the reusable contract/helper/documentation changes;
generated CAD and route states remain ignored.

## Remaining before any fabrication claim

- Close the last 4 connections (automatic routing was stopped at the user's request; restart loops from `route-e26-l`), or finish by
  hand in KiCad from a `runs/trial.sh` board.
- Bring the pin swap and the C501 (and later C525) 0603 change into the schematic, the
  library and `design.json`, then run:
  - DRC, unconnected, parity and ERC, all zero;
  - `capture_pico47_checkpoint.py --require-complete-ground`;
  - the independent pin checks.
- Unchanged open items: timing/current, analog feedback, exact battery and full panel stack,
  ≤7 mm fit, C804 via process acceptance, CAM/SMT and physical EVT. No panel or battery
  power.

## Running the tools

```sh
export R25_WORK=$PWD/.work/pico47-r25-20261025   # holds tools/, runs/, geom-*.json, base-r24/
export R25_PY=/path/to/python                      # numpy, shapely, scipy, ortools, pillow
cc -O2 -shared -o $R25_WORK/tools/libastar3.dylib hardware/pico47/r25_router/astar.c
runs/loop.sh geom-E26.json runs/spec-e26.json runs/route-e26-l.json e26a 12
runs/trial.sh geom-E26.json runs/spec-e26.json runs/loop-e26a-best.json e26a
```

`R25_WORK` must contain `tools/`, which is a copy of `r25_router/*.py` plus the
compiled `libastar3.dylib`. KiCad scripts run under KiCad 10.0.7 Python.
