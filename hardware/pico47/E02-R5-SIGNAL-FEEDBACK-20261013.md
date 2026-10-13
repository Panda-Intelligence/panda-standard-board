# Pico47 E0.2 r5 — verified control/clock closures and shorter feedback detour

Engineering checkpoint date: 2026-10-13. **43 native unconnected items remain.**
**NOT FOR FABRICATION, BATTERY CHARGING OR PANEL POWER.**
This supersedes current-path/count references in `E02-R4-ALL-GROUND-CLOSED-20261013.md`,
not the electrical, ground-preservation, four-layer or physical-qualification gates.

## Verified continuation and publication

Repository: `/Users/isaac/workspace/AI/panda-standard-board`.
Dated candidate:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261013-r5/engineering-candidate`.

Requested working delivery, now updated to a hash-verified r5 copy:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e0-20261012/engineering-candidate`.

The complete previous working r4 is preserved in sibling
`engineering-candidate-pre-r5-archive-20261013`; all earlier archives remain.
Both old and replacement packages contain 299 verified files. Publication used
an independently checked staged copy and reversible renames, with complete old/new
hashes in external `CONTINUATION-R5-20261013.json`. `packaging/` remains untouched.

The r5 native candidate and three pending source/test files were recovered from
an interrupted continuation; they were not assumed accepted from their timestamp.
This session reread the evidence, performed another clean source rebuild and
full native recapture, reran all source suites, and only then published them.
The `.work/pico47-r6-20261013/` directory contains this resumed validation and
further experiments; its name does NOT identify an accepted r6 delivery.

## Actual combined native result

| Board | Published r4 opens | r5 opens | DRC errors | Warnings | Parity | ERC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Core | 36 | 34 | 0 | 0 | 0 | 0 |
| Display | 9 | 9 | 0 | 0 | 0 | 0 |

The reductions are two actual Core connections, not removed orphan copper or
reclassified errors. Ground remains complete: **Core169/169; Display68/68**,
including all eight specifically required targets. The direct GPIO2/interconnect/
R813/U810.EN21 and C804/R812 ground connections are retained.

All old connected physical pad groups are preserved relative to r4. Independent
replay and recapture retain Core229 ->229 and Display99 ->99 groups. Native
KiCad refill/save, all-severity/all-track DRC, schematic parity, ERC, independent
function checks and the required complete-ground capture gate passed.

## Completed physical CAD connections

1. **Display logic enable:** `EN_3V3_EPD_LOGIC`, U601.6 -> U404.B2.
   This add-only transaction adds78 copper primitives and reduces Core36 ->35.
   It does not imply that every display power rail or the final panel is qualified.
2. **Audio bit clock:** `I2S_BCLK`, U501.16 -> U904.3.
   A subsequent accepted route reduces Core35 ->34 while preserving the actual
   C523 ground thermal-relief copper. Earlier routes that retained ground-pad
   membership but reduced the native thermal spoke count were rejected.

The independent inspector now reports those two paths and separately reports
`I2S_DIN`, U501.18 -> U904.4, which **remains open**. Successful bit-clock routing
must not be used to infer a completed audio-data path.

Actual ground and thermal-relief connection quality are separate checks. The
native minimum spoke count, pad zone modes, source layout/parts/pads, source
project rules and all previous connectivity guards were kept unchanged.

## Feedback routing improvement

The r4-generated `P47_VGH_FB` detour segment was replaced by a shorter, fully
reconnected route. The reviewed replacement portion decreases from approximately
**36.852175mm to32.475867mm**, a reduction of about4.376mm, with two vias in both
that old and new portion. These numbers refer to the replaced detour, not the
entire network's total length or a simulated electrical path delay.

The accepted native transaction replaces252 copper primitives with275, keeps
all prior pad groups and complete ground, introduces no errors/warnings/parity,
and does not change the Display open count. The original fine-pitch escape,
other nets and retained outside copper are preserved. Shortening the route does
not qualify feedback noise pickup, loop stability or power integrity; those
engineering/physical reviews remain open.

## Board-specific native routing-limit helper

`pico47_native_routing_limits.py` reads the exact reviewed `.kicad_pro` bytes and
requires its SHA-256 binding before exposing global routing minima. It rejects
missing/invalid/changed input instead of inventing defaults. Core's native edge
clearance is0.20mm; Display's is0.50mm. Applying one shared planning default to both
boards had needlessly obstructed valid Core routes. No project rule was edited.

The helper deliberately reports **global minima only**. Netclass/custom rules,
source manufacturing restrictions, thermal relief, per-layer copper geometry,
current capacity and native DRC remain separate requirements. A number from this
helper is not a fabrication-process approval or a substitute for effective rules.
The12 new tests cover exact binding, board-specific values, malformed/missing
rules, finite positive numbers and read-only behavior.

`verify_pico47_native.py` adds three explicit Core signal-connection report fields.
Existing source/rule/ground/negative-EP and all other independent checks are retained.

## Fresh validation in this resumed session

**519 distinct local source tests pass:** Pico47 262, donor238, geometry19.
The262 Pico47 tests also pass under bundled KiCad Python and are not counted twice.
The previous stored test logs were not substituted for these new runs.

- `.work/pico47-r6-20261013/r5-fresh-source-replay/`: new build from current source.
- `.work/pico47-r6-20261013/r5-fresh-native-proof/`: new source-bound native capture
  with `--require-complete-ground`, matching r5 counts and every required ground.
- `.work/pico47-r6-20261013/REGRESSION-RESULTS.json`: fresh test counts and log paths.
- Original accepted routes/evidence remain under `.work/pico47-r5-20261013/`.

These are local/native results, not GitHub-hosted CI. Generated native CAD,
reports/manifests, intermediate geometry and routing trials remain ignored/external.

## Additional attempts are not part of r5

New bounded add-only Core trials for CKV, SPV, D0, D1, MUX0, SDMMC clock and UART
TX did not yield an accepted connection. Testing the existing native minimum
via geometry also did not produce a route; no smaller-via candidate was adopted.
The resulting diagnostic/failed plans under the r6 work directory are not release
or source-replay checkpoints and must not replace this named candidate.

A separate TP803 Display proposal was run by the parent in the actual native
transaction. It produced35 native errors and lost prior pad connectivity, was
rejected, and the native helper rolled it back. It is not in the published r5.
A local U403 supply-helper write and a later read-only metrics command were
blocked by the remote tool's safety check; neither was executed or retried through
an alternate route. No blocked/unread proposal was promoted.

## Remaining work

Core still has34 unconnected items across its supply/control, MCU/mux/data,
SDMMC, UART, clock and audio-data nets. Display still has9 across I2C_SDA, VCOM,
VGH, VNEG, VP and VPOS. Prioritize coordinated local escape/thermal-aware changes
rather than repeating add-only routes through a fully occupied region. Preserve
all completed grounds, the enable chain, exact footprints and native rules.

Clock/data timing, feedback/return noise and current paths, exact battery/full-
panel identity, <=7mm finished positive-tolerance fit, accepted supply/CAM/SMT,
USB, charge/NTC/ship/deep-sleep, frontlight/OVP, RF/thermal and physical EVT remain
unqualified. **Manufacturing release and physical qualification are false.**

## Reproduce the current engineering checkpoint

```sh
cd /Users/isaac/workspace/AI/panda-standard-board
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
DONOR="$PWD/.work/seven-mm-catalog-20261012/default-rebuild"
CHECKPOINT=/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261013-r5/engineering-candidate
NEXT="$PWD/.work/pico47-next-$(date +%Y%m%dT%H%M%S)"
"$KPY" hardware/pico47/build_pico47.py --donor "$DONOR" \
  --output "$NEXT" --routing-checkpoint "$CHECKPOINT"
"$KPY" hardware/pico47/capture_pico47_checkpoint.py --baseline "$CHECKPOINT" \
  --core "$NEXT" --display "$NEXT" --donor "$DONOR" --output "$NEXT-captured" \
  --require-complete-ground
```

Native SHA-256:
- Core: `08ad3f3ca60e6d39bce70c86cd476035a5e5ff3450e456a334d21576e116a956`
- Display: `e5ae20757677c7f66218d25c7854fdb2adf8f3a49b2495a4f43de2e5cc3cc945`

Resume through reviewed PR integration to main; do not reset pending user changes,
force-add generated evidence or choose a candidate solely by its modification time.
