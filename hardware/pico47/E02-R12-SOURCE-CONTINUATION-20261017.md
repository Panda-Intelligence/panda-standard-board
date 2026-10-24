# Pico47 E0.2 r12 — source-bound engineering continuation

Routing continuation: [r24-mux0-source](E02-R24-MUX0-SOURCE-CLOSURE-20261019.md) is now the
verified four-layer r12 descendant: Core 16 / Display 0 opens, with Core MUX0 joined.
Use its named checkpoint for further routing; this document retains r12 history.
The previous [r23-d3-source](E02-R23-D3-SOURCE-CLOSURE-20261018.md) remains preserved.

2026-10-17. **NOT FOR FABRICATION OR PANEL/BATTERY POWER.**

## Reproducible four-layer engineering candidate

Canonical dated checkpoint:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261015-r12/engineering-candidate`

All future accepted native captures must use `--require-complete-ground`.
The checkpoint is bound to the current `design.json` and `ordered_core_layout.json`
by exact SHA-256. A fresh independent source rebuild and recapture at
`.work/pico47-prototype-release-20261015/r12-roundtrip-proof` reproduces
both boards' counts and complete-ground gate.

| Board | Native unconnected items | DRC errors | Warnings | Parity | ERC |
| --- | ---: | ---: | ---: | ---: | ---: |
| Core | 24 | 0 | 0 | 0 | 0 |
| Display | 4 | 0 | 0 | 0 | 0 |

All 169 Core and 68 Display ground pads remain connected to their reference.
All eight named ground targets, the GPIO2/interconnect/R813/U810.EN21 direct
inhibit, negative U810 EP isolation and prescribed C804 return remain required.
This is not an assertion of finished PCB routing, digital timing, SI/PI,
mechanical fit, manufacturing acceptance or physical qualification.

## Source changes brought into the same branch

The source now contains explicit, constrained R801, display testpoint
TP801/TP803 and VCOM testpoint TP805 source-layout ECOs and associated native
capture/verification helpers. The TP805 source ECO moves only its exact pad/net
identity; it does not silently mark new copper or fab-process constraints
qualified. `pico47_prototype_gates.py` requires explicit, independent evidence;
a zero-DRC but still unrouted board cannot be released.

The exact published r12 PCB and schematic files remain outside Git in the
dated delivery. Generated DSN/SES, derived PCB CAD, netlists, CAM and study
candidates must not be committed or confused with reproducible source.

Pico47 source tests: 347 pass under Homebrew Python and 347 pass under
KiCad bundled Python (re-run 2026-10-17). These are local results, not GitHub CI.

## Remaining native routing scope

**Core 24 opens:** MCU and U710/U711 MUX/data, SDMMC, audio data/control,
UART and related incomplete signal connections.

**Display 4 opens:** VCOM to J820.10, VPOS to J820.36, I2C_SDA at U810.18
and VP at U810.42.

Do not treat geometry-only or autorouter airwire counts as physical connections.
Move/rescue a net only if its source-bound native transaction has zero new
rule errors, complete original pad groups and no ground/shutdown regressions.

## In-progress non-adopted density studies

An isolated **six-layer** Core repositioned-mux and Specctra/Freerouting study
is under `.work/pico47-prototype-release-20261015/core/mux-relayout/`.
Its moved-mux native source has 35 opens and 33 warnings with old groups
broken, so it is **rejected** until a new complete native acceptance passes.
The subsequent Freerouting SES cannot be imported by KiCad as-is; several
network routes also contain sub-0.15 mm widths or mismatched via stacks.
Do not adopt that session as a board or route checkpoint.

An isolated six-layer Display geometry study under
`.work/pico47-prototype-release-20261015/display-final-agent/` achieves
zero geometric opens but native KiCad DRC reports 77 errors (including via
diameter/annulus/drill, shorting, clearance and hole clearance violations)
and 48 footprint-library warnings. The F-to-In3 `0.30/0.15` candidate
is NOT native accepted; some vias are shown as F-to-B through vias and
overlap unrelated copper. It must not enter the release package.

Six-layer/filled-capped-via-in-pad routing is at present a **separate process
feasibility option, not an authorized replacement** for the source four-layer
product. A new stackup, via span, hole/annulus/registration rules and exact
factory process approval are required before any such ECO can be integrated.
Do not relax DRC or reclassify warnings simply to get opens to zero.

## Fabrication and physical gates that remain

Even with 0 opens, inspect and approve:

- full display assembly E0470A01 family and exact touch/front-light FPC pinout
- actual replaceable 2050mAh LCO battery MPN, chemistry/CV/NTC/connector/dimensions
- finished two-board/enclosure stack within 7 mm maximum including tolerances
- fab house process for C804 via filling/capping and any other via-in-pad
- production netlist cross-check; Gerber, Excellon, soldermask, outline, BOM/CPL
- assembly sides, fine-pitch finish and inspection, fabrication DFM
- USB-C compliance, charging/NTC/ship/deep sleep, frontlight current/OVP,
  RF/EMI, thermal, SI/PI and physical EVT after samples arrive

`manufacturing_release=false` and
`physical_qualification_complete=false` until supported gates pass.

Next routing agent should continue from the dated r12 checkpoint and this
source history, not the latest temporary folder by modification time.
