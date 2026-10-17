# Panda47 HDI6 v1 — independent six-layer upgrade

**Branch:** `hw/pico47-hdi6-v1`
**Revision:** `E0.3-HDI6`
**Status:** engineering study, **not prototype/fabrication ready**.

This variant is intentionally separate from `main`, the established two-board,
**four-layer** Panda47 E0.2 design. The new branch and worktree can evolve
independently; **do not merge six-layer sources or rules into `main`**.

| | Existing four-layer version | This HDI6 variant |
| --- | --- | --- |
| Repository checkout | `panda-standard-board` | `panda-standard-board-hdi6` |
| Git branch | `main` | `hw/pico47-hdi6-v1` |
| Source config | `hardware/pico47` | `hardware/pico47-hdi6/variant.json` |
| PCB layers | 4 | 6 |
| Baseline native checkpoint | r12 | source-bound r12 conversion |
| Fabrication release | No | No |

## Reproducible six-layer KiCad base

The script `build_hdi6.py` reads **only** the exact hash-bound r12
four-layer checkpoint and retains the same footprint/pad/net/component
identities, native electrical rules, copper, drills, board outline and
previously connected pad groups on **both** boards. It adds:

- **In3.Cu:** new signal-routing capacity, currently empty.
- **In4.Cu:** a second independent GND reference pour matching the In1 outline.
- Existing F.Cu, In1.Cu (GND), In2.Cu (signal), B.Cu and every original
  through via remain in place.
- Nominal PCB thickness remains 0.8 mm; the factory's finished 6-layer
  stackup and tolerance are not assumed or signed off.

This is a deliberately conservative migration. It does **not** silently add
microvias, use via-in-pad, delete existing copper or weaken the source project's
DRC minima. In particular, **a blind F→In3 via spanning nonadjacent layers is
not a valid HDI microvia solution**. Any future adjacent-layer blind-via routing
must receive an explicit stackup/layer-span and return-path ECO. A dedicated
In1 signal-escape variant with In2 GND may be evaluated separately; it is not
implicitly enabled in this candidate.

## Build

The initial validated r12 input and donor toolchain currently reside on the
MacBook Pro:

```sh
cd /Users/isaac/workspace/AI/panda-standard-board-hdi6
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
BASE=/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261015-r12/engineering-candidate
DONOR=/Users/isaac/workspace/AI/panda-standard-board/.work/seven-mm-catalog-20261012/default-rebuild
OUTPUT=/Users/isaac/workspace/AI/panda-board-deliverables/panda47-hdi6-v1-20261017/new-replay

"$KPY" hardware/pico47-hdi6/build_hdi6.py \
  --baseline "$BASE" --donor "$DONOR" --output "$OUTPUT"
```

The output must be a **fresh** directory. The builder fails closed on input
hash changes, native rule/shape changes, disconnected old pad groups, incomplete
native GND membership, broken panel control paths, DRC warnings/errors, ERC or
schematic-parity regressions.

## Verified initial candidate

```text
/Users/isaac/workspace/AI/panda-board-deliverables/
panda47-hdi6-v1-20261017/engineering-candidate/
```

The initial study has:

| Board | Open native items | DRC errors | Warnings | ERC | Parity |
| --- | ---: | ---: | ---: | ---: | ---: |
| Core | 24 | 0 | 0 | 0 | 0 |
| Display | 4 | 0 | 0 | 0 | 0 |

All **169 Core and 68 Display ground pads** remain reference-connected. All
eight named GND targets, existing panel-control connections, component/pad
identities and original copper remain intact. The current study is the six-layer
architecture starting point, **not a route-closure result**; it adds zero new
signal tracks.

Two independent native builds yielded **byte-identical** KiCad PCB, schematic,
DRC project-rule and source-checkpoint files:

- `engineering-candidate/`
- `verification-replay/`

The independent replay remains external/generated, not committed to Git.

Unit regressions:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s hardware/pico47-hdi6 -p 'test_*.py'
```

21 variant-contract cases passed under Homebrew Python and under KiCad Python.

## Route and manufacturing gates

Read [NEXT-STEPS.md](NEXT-STEPS.md). At minimum, both boards require **0
native unconnected items**, clean DRC/ERC and parity, preservation of original
pad groups and ground shutdown evidence, successful source replay, and complete
fab/assembly/CAM review before manufacturing release.

Unverified process gates include the exact 0.8 mm **six-layer factory stackup**,
laser microvia spanning, 0.25/0.15 mm POFV rules, copper-capping registration,
the special C804 GND return process, original panel/battery identity,
<=7 mm assembled envelope, USB-C, RF/thermal, BOM/CPL/Gerber/Excellon and EVT.

Never mark `manufacturing_release` or `physical_qualification_complete` true
just because six-layer DRC is zero. Native CAD, temporary geometry, route
sessions, reports, and production files remain outside source control.
