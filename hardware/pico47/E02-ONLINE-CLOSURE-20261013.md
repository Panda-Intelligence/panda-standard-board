# Pico47 E0.2 — online continuation and verified r2 checkpoint

Date: 2026-10-13. **INCOMPLETE ENGINEERING PCB — NOT FOR FABRICATION OR POWER.**
This supersedes the candidate/count pointers in `E02-20261013-HANDOFF.md` and
`E02-EN-CLOSURE-20261013.md`, not their product or physical-qualification limits.

## Current continuation entry

Repository: `/Users/isaac/workspace/AI/panda-standard-board`.
Integrate source changes through the user-requested PR to `main`; inspect current
refs before continuing. Preserve the user's untracked `packaging/`.

Dated, hash-bound candidate:

`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261013-r2/engineering-candidate`

The user-requested working directory now contains a verified copy of that candidate:

`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e0-20261012/engineering-candidate`

Its previous contents are retained byte-for-byte in sibling
`engineering-candidate-pre-r2-archive-20261013`. The original E0.1 archive,
`engineering-candidate-e01-archive-20261013`, and all earlier dated checkpoints
remain intact. Both the previous and replacement working packages contain
298 verified files. The external `CONTINUATION-R2-20261013.json` records their
individual hashes and the actual directory replacement.

## Actual combined native acceptance

KiCad 10.0.5. Both boards underwent fresh zone refill/save, all-severity and
all-track-error DRC, schematic parity, ERC, independent pin/function checks and
physical-pad-group comparison against the prior published checkpoint.

| Board | Prior published opens | r2 opens | Prior published warnings | r2 warnings | DRC errors | Parity | ERC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Core | 46 | 42 | 1 | 1 | 0 | 0 | 0 |
| Display | 21 | 16 | 3 | 2 | 0 | 0 | 0 |

**58 native unconnected items and three warnings remain.** These are native
unconnected-item counts, not counts of nets or a statement of routed completeness.
The capture tool's non-increasing-warning/non-increasing-open and native
continuity guards were kept unchanged. No existing DRC severity, exclusion,
clearance, via/drill minimum, source pad, circuit or layer-count rule was relaxed.

All previously connected physical pad groups were preserved:
Core 241 -> 237 groups, Display 111 -> 106 groups. A separate fresh source rebuild
and second native capture reproduced exactly the same counts and retained
237 -> 237 Core and 106 -> 106 Display groups. This is a complete observed
combined replay result, unlike the disconnected per-board observations in the
previous handoff.

## Work completed in this online continuation

The previous pending power run was read and verified: Display `VSYS_RAW` had
closed, reducing that working board from 17 to 16 unconnected items. Its accepted
native result, rather than an unverified newer file timestamp, was carried forward.

Two additional Core signal connections now pass the native transactions:

- `P47_D9_SRC`: the new 0.45/0.25mm via initially violated the J503 non-plated
  mounting-hole clearance. The accepted via moved from (54.175,100.300) to
  (54.175,100.425). One existing `3V3_AON` B.Cu segment was rerouted with its
  original endpoints and original 0.35mm width; no power via was added. The
  replacement path is about 6.79mm long. This is not a current/thermal/SI approval.
- `P47_D12_SRC`: accepted after explicitly protecting the R512.2 ground return.
  That preventive return adds about 1.11mm of 0.15mm ground track and no new via.
  It prevents later signal proposals from relying solely on a vulnerable poured
  ground neck. Existing pad-group connectivity and the D9 connection were retained.

The accepted new Core initially had nine warnings. Existing native-guarded
junction splitting and per-pass/per-item cleanup reduced this to one without
increasing opens. A 13.9mm SD-card-clock segment carried a live side junction:
its whole removal was correctly rejected. Splitting at the actual same-net
side contact allowed the dead portion to be removed while preserving
`R517.2 -> J501.5`. No warning suppression was used.

The four-layer policy, In1 reference plane, 16 ordered header data connections,
nine MCU ground-paddle vias, C804's prescribed filled/capped ground via and the
isolated U810 negative exposed pad are unchanged.

## Direct inhibit remains connected

The independent native inspector reports all four critical checks true:
Core GPIO2 -> interconnect; Display interconnect -> R813; R813 -> U810.EN21;
and C804 ground -> R812 ground. `P47_PGOOD` and `P47_VGH_FB` closures from the
previous work are retained. These facts do not authorize battery charging or
panel power while the rest of the design and physical qualification are incomplete.

## Source changes and regression evidence

`pico47_hole_clearance.py` adds validated geometry helpers for the actual
non-plated-hole failure. A planner using a via's drill radius needs an additional
(D_copper - D_drill)/2 inflation when checking an NPTH against copper. For a
0.45/0.25mm via that is 0.10mm. The old drill-only estimate incorrectly passed the
actual J503 case while the native copper-edge clearance was approximately 0.159mm,
below the unchanged 0.25mm requirement. The next Core planning trials use the
new tested helper. Native pad/copper geometry and independent DRC remain authoritative.

`pico47_branch_pruning.py` is a pure, conservative graph-proposal utility with
anchor, cycle, parallel-edge and malformed-input tests. It is **not** an enabled
native PCB deletion pipeline and was not used to adopt the r2 copper cleanup.
The actual cleanup used the existing source-bound native scripts and their
rollback checks. Its geometric/native integration remains a separate review.

**456 source tests were run and passed in this continuation:**
Pico47 199, historical donor 238, signal-path geometry 19. Pico47 also passed
under the bundled KiCad Python. The 34 added cases comprise 14 NPTH-clearance
cases and 20 branch-topology cases, including 500 deterministic randomized
anchor-connectivity graphs. These are local results, not GitHub-hosted CI.

Logs and independent source-replay evidence remain under:

- `.work/pico47-online-20261013/final-capture.log`
- `.work/pico47-online-20261013/final-source-replay/`
- `.work/pico47-online-20261013/final-roundtrip-proof/`
- `.work/pico47-online-20261013/{donor,geometry,kicad-python}-tests-final.log`

## Remaining work and rejected alternatives

1. Complete Display `I2C_SDA`, the remaining VCOM/VP/VPOS/VNEG/VGH connections and
   ground islands, and finish Core MCU/mux/data, SDMMC, clock/control and I2S routes.
2. Revisit the tightly packed PMIC escape region with an explicitly reviewed
   layout/copper ECO if necessary. Moving C810 alone or together with the first
   proposed feedback-via move caused real clearance/short/return regressions;
   **all those placement studies were rejected and rolled back**. The r2 source
   layout is unchanged. Preserve EN, C804 return, the negative EP and power widths.
3. Clean the three remaining native warnings: Core GND/In2.Cu near (47.575,97.25),
   Display P47_VEE_BASE/In2.Cu near (18.9,101.0) and (20.5,96.6). Read the exact
   current DRC UUIDs before any edit; do not delete live junctions to clear a count.
4. Review detour lengths, digital timing, analog-reference noise, current paths
   and reference-plane continuity. Then perform exact battery/full-panel identity,
   <=7mm maximum tolerance stack, sourcing, CAM/SMT, USB, charging/NTC/ship/deep-sleep,
   frontlight/OVP, RF/thermal and physical EVT qualification as separate gates.

Bounded route trials that did not preserve every original connected pad group
or failed native checks remain rejected evidence. The inspected SES output was
not imported wholesale; it contained unapproved fine widths/via types and did not
provide a newly accepted control-net closure. Do not promote any trial merely
because it is newer than this named checkpoint.

## Reproduce from current source

```sh
cd /Users/isaac/workspace/AI/panda-standard-board
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
DONOR="$PWD/.work/seven-mm-catalog-20261012/default-rebuild"
CHECKPOINT=/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261013-r2/engineering-candidate
NEXT="$PWD/.work/pico47-next-$(date +%Y%m%dT%H%M%S)"
"$KPY" hardware/pico47/build_pico47.py --donor "$DONOR" \
  --output "$NEXT" --routing-checkpoint "$CHECKPOINT"
"$KPY" hardware/pico47/capture_pico47_checkpoint.py --baseline "$CHECKPOINT" \
  --core "$NEXT" --display "$NEXT" --donor "$DONOR" --output "$NEXT-captured"
```

Verified dated-checkpoint bindings:

- Core PCB: `4830768d198f4e60b892ecb9866f04613450fecb28e76f689a2bc3fac6d24ac8`
- Display PCB: `8f21b82860941307019128f93d8adc82f7c9b91ca6781533e0fef8fed52318d1`
- Routing checkpoint: `33644dc18dc17394937c4078cad16e468a0b779585904f0264fe419cde0ca555`

Generated CAD, reports, manifests, routing proposals and rendering output stay
ignored/external. Commit reusable source, tests and this handoff only.
`manufacturing_release` and `physical_qualification_complete` remain **false**.
