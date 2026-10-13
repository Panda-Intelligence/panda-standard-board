# Pico47 E0.2 r3 — verified ground closures and zero-warning continuation

2026-10-13. **53 native unconnected items remain. NOT FOR FABRICATION OR POWER.**
This supersedes the current-candidate pointers in `E02-ONLINE-CLOSURE-20261013.md`,
not the product, electrical, four-layer or physical-qualification requirements.

## Current verified package

Repository: `/Users/isaac/workspace/AI/panda-standard-board`.

Dated engineering checkpoint:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261013-r3/engineering-candidate`

Requested working copy, now updated and byte-verified:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e0-20261012/engineering-candidate`

Previous r2 working contents are preserved in sibling
`engineering-candidate-pre-r3-archive-20261013`. Earlier E0.1/r2 archives and all
dated checkpoints remain unchanged. Each old/new working package has 298 files;
`CONTINUATION-R3-20261013.json` outside the repository binds every file and the
successful source-replay/ground-topology verification. Keep `packaging/` untouched.

## Combined native result

| Board | r2 opens | r3 opens | r2 warnings | r3 warnings | DRC errors | Parity | ERC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Core | 42 | 38 | 1 | 0 | 0 | 0 | 0 |
| Display | 16 | 15 | 2 | 0 | 0 | 0 | 0 |

Zero rule errors/warnings is not open=0. The 53 remaining native unconnected
items are reported in full; no error exclusion, severity, rule, via minimum or
part removal was used to hide them. Manufacturing and physical qualification
remain false.

Fresh KiCad 10.0.5 zone refill/save, all-severity/all-track DRC, schematic parity,
ERC, independent native checks and original-pad-group comparison passed.
A clean `build_pico47.py --routing-checkpoint` rebuild and independent recapture
reproduce the same counts and all critical connections. Source-replay ground
pad membership was also compared by physical reference/pad/coordinates, not
regenerated UUID equality. All original physical pad groups are preserved:
Core 237 -> 233, Display 106 -> 105; replay 233 -> 233 and 105 -> 105.

## Five real connections closed

Core C711.2, R606.2, C530.2 and J503.4 are now connected to the existing native
U501.57 ground-reference group. Their combined original-source-bound transaction
adds 26 GND tracks and one ordinary through via, removes no existing copper,
and reduces native opens by four. The C711 and R606 routes are approximately
0.585mm and 0.121mm respectively; existing pad/land/part geometry is unchanged.
Native current, RF, thermal and timing qualification are not implied.

Display J820's right MP grounding/mounting land at (28.135,115.61) is connected
to the existing C804.2 reference group. A 0.3mm-long, 0.15mm-wide F.Cu GND bridge
at y=115.3061 closes the gap. The adjacent P47_PGOOD via moves from
(29.8664,114.736) to (29.8757,114.7304), retaining 0.60/0.30mm copper/drill and
0.20mm track width. Exactly three prior PGOOD copper primitives are replaced by
three PGOOD primitives, plus the new GND bridge. PGOOD and every prior native
pad group remain connected.

The adopted dead-end cleanup removes 106 Core GND and 13 Display P47_VEE_BASE
copper primitives. Core includes a 45-segment conservative branch proposal,
accepted only after the existing original-source/native-DRC/pad-group transaction.
The remaining cleanup used per-pass native-guarded pruning. Cleanup did not lower
the open counts; the five reductions above come from actual ground connections.

Four layers, no In1 signal tracks, 16 ordered header data links, nine MCU paddle
vias, the prescribed C804 filled/capped GND via, U810 negative-EP isolation,
electrical intent, exact component identity and native design rules are retained.
The entire GPIO2/interconnect/R813/U810.EN21 direct-inhibit chain remains connected.

## Ground-report correction and exact remaining ground work

`pico47_ground_returns.py` separates **native physical connected-pad groups** from
pad zone-connection configuration. A solid/thermal setting is not proof that the
pad reaches the reference ground. `verify_pico47_native.py` now emits
`ground_return_connectivity` for both boards in `INDEPENDENT-CHECK.json`.
The existing solid-zone-mode check and all other acceptance gates remain intact;
its misleading error wording was corrected rather than changing its condition.

UUID identities keep same-number mounting pads distinct. Missing/overlapping
partitions, duplicated/unknown pads, invalid coordinates and an ambiguous
reference pad reject the report. A partial engineering candidate explicitly lists
unconnected ground groups; the report never grants manufacturing approval.

Current native ground results:

| Board | Ground pads | Connected to selected reference | Still disconnected |
| --- | ---: | ---: | ---: |
| Core, relative to U501.57 | 169 | 167 | 2 |
| Display, relative to C804.2 | 68 | 62 | 6 |

Remaining Core ground pins: **J601.36 and J601.38**.
Remaining Display ground pins: **J820.9, J820.22, R809.2, R810.2, U810.32 and U810.41**.
These are real outstanding connections, including PMIC ground pins; do not
energize panel or battery circuits based on zero rule violations or connected EN.
Their exact UUIDs and positions are in the independent report. Ground current
capacity and return quality still require separate engineering/physical review.

## Tests and evidence

**478 distinct local source tests passed:** Pico47 221, donor 238, geometry 19.
Pico47's 221 tests also passed under bundled KiCad Python. The 22 new ground
report cases cover physical-vs-logical connectivity, solid-mode false positives,
duplicate connector pad numbers, stable ordering, input immutability and malformed
or incomplete native evidence. These are fresh local results, not GitHub CI.

Current work/evidence root: `.work/pico47-r3-20261013/`.

- Adopted Core: `core-four-ground-native/`; geometry predecessor `core-clean-final/`.
- Adopted Display: `display-mp-clean/`; predecessor transaction `display-mp-native/`.
- `final-source-replay/` and `final-roundtrip-proof/` reproduce the dated checkpoint.
- `REGRESSION-RESULTS.json` and `*-tests-final.log` record the actual test runs.
- `core-agent/` and `display-agent/` contain isolated parallel investigations.
  The coordinator independently validated the Display plan in the working native
  environment before adoption. A file existing in an agent directory is not approval.

The Core agent's final CKV plan was independently run by the coordinator using
`apply_patch.py`: native rule errors caused rejection and rollback. That plan,
the long I2S negotiation trial, and failed local ground/rail trials are not in r3.
Their diagnostic outputs remain under `.work`; no output is called accepted
merely because a sandboxed tool failed or a geometric route appeared complete.

## Next PCB work

Prioritize the eight explicit missing ground returns above, especially the two
PMIC grounds, then finish Display SDA/remaining power rails and Core MCU/mux/data,
SDMMC and audio/control routes. Use a scoped, source-replayed layout/copper ECO
where the existing escape region cannot support a non-regressing addition.
Preserve the current EN chain, copper/drill limits, C804 return and negative EP.

Review detour lengths, clock/data timing, reference noise and power-loop returns
before physical release. Exact battery/full-panel acceptance, <=7mm finished
positive-tolerance stack, sourcing, CAM/SMT, USB, charging/NTC/ship/deep-sleep,
frontlight/OVP, RF/thermal and physical EVT are still separate unresolved gates.

## Rebuild without using stale reports

```sh
cd /Users/isaac/workspace/AI/panda-standard-board
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
DONOR="$PWD/.work/seven-mm-catalog-20261012/default-rebuild"
CHECKPOINT=/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261013-r3/engineering-candidate
NEXT="$PWD/.work/pico47-next-$(date +%Y%m%dT%H%M%S)"
"$KPY" hardware/pico47/build_pico47.py --donor "$DONOR" \
  --output "$NEXT" --routing-checkpoint "$CHECKPOINT"
"$KPY" hardware/pico47/capture_pico47_checkpoint.py --baseline "$CHECKPOINT" \
  --core "$NEXT" --display "$NEXT" --donor "$DONOR" --output "$NEXT-captured"
```

Dated native SHA-256:
- Core: `bc97d9b7248fa90043a33faec67f0436bc592ff10a9880f978e9c2af472ae58d`
- Display: `f64d3c80794f9395f40fa77715049bfff64a40fdc15e6665542a2a60a35c9a70`

Commit reusable source, tests and handoff only. Generated native boards, reports,
manifests, renders and experimental scripts remain ignored/external.
`manufacturing_release` and `physical_qualification_complete` remain **false**.
