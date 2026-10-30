# Panda Standard E0.2 r7 — SPV closure and coordinated panel-control fanout

2026-10-14. **SPV IS CONNECTED; 41 OTHER NATIVE UNCONNECTED ITEMS REMAIN.**
**NOT FOR FABRICATION, CHARGING OR PANEL POWER.** This supersedes the current
candidate/count pointers in `E02-R6-CKV-PROGRESS-20261014.md` and the r5 handoff,
not the product, electrical, layer-count or physical-qualification restrictions.

## Current source and verified delivery

Canonical repository: `/Users/isaac/workspace/AI/panda-standard-board`.
Dated accepted engineering checkpoint:

`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261014-r7/engineering-candidate`

The requested working directory now holds a byte-verified copy of r7:

`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e0-20261012/engineering-candidate`

Previous r6 contents are preserved in sibling
`engineering-candidate-pre-r7-archive-20261014`. This session first completed the
previously unfinished r6 publication and archived its r5 predecessor in
`engineering-candidate-pre-r6-archive-20261014`. All earlier archives remain intact.
Each working package has 299 verified files. The external
`CONTINUATION-R6-20261014.json` and `CONTINUATION-R7-20261014.json` bind old/new
file hashes and the successful reversible publications. No original was deleted.
The user's untracked `packaging/` and unrelated worktrees were not changed.

## Observed combined native result

| Board | r6 unconnected items | r7 unconnected items | DRC errors | DRC warnings | Parity | ERC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Core | 33 | 32 | 0 | 0 | 0 | 0 |
| Display | 9 | 9 | 0 | 0 | 0 | 0 |

The one-item reduction is an actual SPV connection, not orphan deletion or warning
suppression. Core's 169 ground pads and Display's 68 ground pads remain joined
to their native reference groups, including all eight named ground targets.
GPIO2/interconnect/R813/U810.EN21 and the prescribed C804 ground return remain
connected. Native pin identities, component values/MPNs, placement/outline,
project rules, pad thermal modes, four copper layers and no In1 signal routing
are unchanged. The U810 negative exposed pad remains isolated as prescribed.

Fresh zone refill/save, all-severity/all-track DRC, schematic parity, ERC,
independent pin/functional checks and original physical pad-group preservation
passed. A complete source rebuild and independent `--require-complete-ground`
recapture reproduced the exact counts and all four panel-control connections.
The replay preserves Core 227 -> 227 and Display 99 -> 99 physical pad groups.

## Exact panel-control endpoints

| Net | Source pad | Connector pad | r7 native result |
| --- | --- | --- | --- |
| P47_CKV | R729.2 | J601.39 | Connected |
| P47_SPV | R730.2 | J601.40 | **Newly connected** |
| P47_XLE | R727.2 | J601.35 | Connected, retained |
| P47_XSTL | R728.2 | J601.37 | Connected, retained |

The existing display-logic enable and audio bit-clock connections remain intact.
`I2S_DIN` remains open; a successful control-clock connection does not imply a
completed audio or parallel-display data path.

## Adopted copper change and metrics

The accepted solution coordinates only the connector-side copper of the four
ordinary panel-control nets. Resistor-side escapes are retained. Supply, ground,
USB, RF and all other-net track/via items are untouched. A separate native audit
compared UUID/net/layer/endpoint/width/drill data and proved that all **9,429
non-control copper items are identical** between r6 and r7. This refers to
tracks/vias; poured-zone fill can legitimately change on refill and is checked
by native DRC and actual ground connectivity instead of assumed byte equality.

The source-bound initial transaction replaced 182 native control primitives with
194 and reduced Core opens from 33 to 32 while preserving every old pad group.
Two initial dangling-track warnings were resolved by splitting at actual live
junctions and pruning four dead control pieces across two native-guarded passes.
The cleanup did not reduce the open count or change any other-net copper.

| Control net | r6 total track length | r7 total track length | r6 vias | r7 vias |
| --- | ---: | ---: | ---: | ---: |
| P47_SPV | 0 mm, open | 11.740718 mm | 0 | 2 |
| P47_XLE | 10.908309 mm | 8.254773 mm | 2 | 2 |
| P47_CKV | 9.913584 mm | 8.339813 mm | 3 | 3 |
| P47_XSTL | 12.768986 mm | 9.920889 mm | 4 | 2 |

All four nets retain 0.15 mm track width. New XLE/XSTL vias use 0.50/0.25 mm
copper/drill; CKV/SPV use 0.45/0.25 mm. The total via count across these four nets
remains nine. These are native whole-net copper metrics, not timing simulation,
length-matching qualification, impedance validation or measured signal integrity.
No native clearance, annulus, drilling or manufacturing restriction was relaxed.

The earlier three-item SPV approaches would lose XLE connectivity or required
unavailable via locations. They were rejected and never published. Diagnostic
removal of supply items was not carried into the accepted four-control solution.

## Source reporting and fresh tests

`pico47_panel_control_report.py` now includes XSTL explicitly and requires the
complete eight-pad inventory for all four exact links. This prevents an SPV
success from hiding a broken XSTL path. Existing connected-net, short-circuit,
duplicate-ID and incomplete-evidence checks remain unchanged.

Four added tests in `test_pico47_xstl_continuity.py` independently specify the
literal pad mapping, prove that broken XSTL stays false when SPV is true, reject
a wrong net on J601.37, and reject old six-pad evidence that omits XSTL.

**539 distinct local source tests passed:** Panda Standard 282, historical donor 238 and
geometry 19. The 282 Panda Standard tests also passed under the bundled KiCad Python and
are not counted twice. These are local results, not GitHub Actions evidence.
The full native combined capture, source build and independent recapture passed
with this expanded inspector. Every reported panel control is true after replay.

All current evidence remains under `.work/pico47-r7-resume-20261014/`:

- `four-control-plan.json`, `four-control-review.json`: adopted proposal scope.
- `spv-native-reviewed/`: original-source-bound native copper transaction.
- `spv-final-clean/`: adopted cleaned Core before combined publication.
- `final-source-replay/`, `final-roundtrip-proof/`: clean rebuild and recapture.
- `COMPLETE-VERIFICATION.json`, `FINAL-REGRESSION-RESULTS.json`: observed results.
- `CONTROL-COPPER-AUDIT.json`: four-net metrics and all-other-copper identity check.

## Recovery and evidence-file caveat

Live remote state showed PR27 was already merged at
`fac6ac69030b61c3c9af48063b0551798eee73de`. The pending local inspector integration
was byte-identical to merged main; it was preserved in a named stash and an
ignored backup before fast-forwarding local main. No hard reset or force push
was used. This continuation then used `hw/pico47-r7-spv-20261014`.

The old working r5 matched its complete publication record exactly, even though
the dated r5 directory differed in two generated independent-netlist XML files.
The standalone inspector exports into its candidate directory and had regenerated
those XMLs during an earlier check. Publication compared the actual historical
publication hashes rather than treating regenerated XML as a user CAD edit.
The exact r5 working bytes were preserved in the pre-r6 archive.

A proposed separate inspection-evidence wrapper was not integrated: its patch
was blocked by the remote tool safety check and was not rerouted or retried.
The draft is preserved only as ignored `unintegrated-inspection-evidence.py`,
not in source or this PR. Therefore the standalone inspector's export behavior
is still an outstanding tooling concern. Inspect a fresh copy/capture output,
not an immutable published candidate, when generating independent netlists.
The final native metric audit reads PCB objects without saving or exporting.

## Rebuild and continue

```sh
cd /Users/isaac/workspace/AI/panda-standard-board
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
DONOR="$PWD/.work/seven-mm-catalog-20261012/default-rebuild"
CHECKPOINT=/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261014-r7/engineering-candidate
NEXT="$PWD/.work/pico47-next-$(date +%Y%m%dT%H%M%S)"
"$KPY" hardware/pico47/build_pico47.py --donor "$DONOR" \
  --output "$NEXT" --routing-checkpoint "$CHECKPOINT"
"$KPY" hardware/pico47/capture_pico47_checkpoint.py --baseline "$CHECKPOINT" \
  --core "$NEXT" --display "$NEXT" --donor "$DONOR" --output "$NEXT-captured" \
  --require-complete-ground
```

Verified dated bindings:
- Core PCB: `8e5d4111fa7e2d5b5857530ff28c5df88f38027705a97ceae1a58a5ce22179c1`
- Display PCB: `e5ae20757677c7f66218d25c7854fdb2adf8f3a49b2495a4f43de2e5cc3cc945`
- Routing checkpoint: `9806b3f33364951071648673fad63f700d44bd37d80ac7e56fa9ad316ea86a69`

## Remaining scope

Core still has 32 non-ground unconnected items across MCU/mux/data, SDMMC, audio
data, UART and supply/control nets. Display still has nine across SDA and its
remaining VCOM/VGH/VPOS/VNEG/VP routes. Native counts are not a count of nets.
This is a verified routing increment, not completion of either entire board.

Digital timing, return/current quality, feedback-loop/noise review, exact pack
and full-panel identities, <=7 mm finished positive-tolerance fit, sourcing,
CAM/SMT, USB, charging/NTC/ship/deep-sleep, frontlight/OVP, RF/thermal and physical
EVT remain separate unresolved gates. Manufacturing and physical qualification
remain **false**. Commit source/tests/handoff only; generated CAD and reports
remain ignored/external. Continue through reviewed PR integration to main.
