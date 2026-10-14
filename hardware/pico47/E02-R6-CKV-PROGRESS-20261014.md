# Pico47 r6 CKV progress — 2026-10-14

**Draft engineering continuation. NOT FOR FABRICATION OR POWER.**
42 native unconnected items remain in the newly captured candidate. The formal
working delivery remains r5 until the final replay result is retrieved and verified.

## Observed native progress

The previous CKV native-review directory did not exist when the device reconnected.
The old proposed plan was checked against the exact r5 Core PCB SHA-256 and then
run through the unchanged source-bound native transaction. It passed: Core opens
34 -> 33, zero DRC errors/warnings/parity, and all prior pad groups preserved.
All 169 Core and 68 Display ground pads and the full GPIO2/EN chain remained connected.

CKV is the connector-side connection R729.2 -> J601.39, net P47_CKV. Its new copper
is approximately 9.913584mm long, 0.15mm wide, with three 0.45/0.25mm through vias.
The initial plan replaced only one XLE segment and one display-logic supply segment.
XLE's original endpoints, F.Cu layer and 0.15mm width were retained.

The initial supply replacement was 22.002758mm. It was then replaced by a
13.545332mm, 0.35mm route joining the same original power-copper groups, with
**no added power vias**. Native checks confirmed preservation of every prior
connected pad group. Five dead-end copper pieces were pruned with the existing
native rollback/continuity guard, returning warnings to zero.

These are replacement-route lengths, not the whole net. Native total copper
length for 3V3_EPD_LOGIC is 59.338330mm in r5, 78.841087mm in the initial CKV
candidate, and 69.193712mm after optimization/cleanup. Its via count remains 3.
The final total is still longer than r5, so voltage drop, return quality and
power integrity are not signed off. No rules, components, native pads, layout,
layer count or physical qualification status were relaxed or changed.

## Combined capture that was actually observed

Dated candidate created and read:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261014-r6/engineering-candidate`

| Board | r5 opens | Captured r6 opens | DRC errors | Warnings | Parity | ERC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Core | 34 | 33 | 0 | 0 | 0 | 0 |
| Display | 9 | 9 | 0 | 0 | 0 | 0 |

The full `capture_pico47_checkpoint.py --require-complete-ground` step completed
and its CURRENT-STATUS.json was returned successfully. Complete-ground and all
critical inhibit/return checks were true. Display native bytes remain identical
to r5. Manufacturing and physical qualification remain false.

Captured native hashes:
- Core: `6f1775f3c02433cf6b8b9831e0a983e8084df87c17daf711f223a689dc719259`
- Display: `e5ae20757677c7f66218d25c7854fdb2adf8f3a49b2495a4f43de2e5cc3cc945`
- ROUTING-CHECKPOINT.json: `6064bbb2b80373688aeae561bbdd348ae57d77e304be7b9204fa7ee2118f5597`

## What is NOT yet confirmed

A clean source rebuild followed by independent complete-ground recapture was
started in process `proc-35236-30`. The first capture finished and the process
continued. Before its final result was retrieved, process reads, a direct file
read, and a git-status command all returned OUTCOME_UNKNOWN/timeouts. Device
listing still said online, but its lastSeenAt stopped advancing at 1791958410.
Do not infer either success or failure of the later steps from that status.

Read these existing paths first when the device responds:
- `.work/pico47-r6-complete-20261014/final-source-replay.log`
- `.work/pico47-r6-complete-20261014/final-source-replay/`
- `.work/pico47-r6-complete-20261014/final-roundtrip-proof.log`
- `.work/pico47-r6-complete-20261014/final-roundtrip-proof/CURRENT-STATUS.json`
- `.work/pico47-r6-complete-20261014/final-roundtrip-proof/CONTINUITY-CHECK.json`
- `.work/pico47-r6-complete-20261014/final-roundtrip-proof/INDEPENDENT-CHECK.json`

Require the final counts, complete-ground gate and panel-control report to match
the captured candidate, and all original physical pad groups to be preserved.
Do not rerun capture into an existing output directory. Recover a completed
result or select a new output path after inspecting any failure marker.

No publication/rename of the user's formal `panda47-e0-20261012/engineering-candidate`
was attempted in this session. It still represents r5. No r6 merge or fabrication
release is claimed. Preserve all archived CAD and the user's untracked packaging/.

## Source/test state and draft PR boundary

A new `pico47_panel_control_report.py` validates the exact six native pads for
CKV, SPV and XLE. It distinguishes connected copper groups from identical net
labels, rejects pin swaps, missing/overlapping/shorted evidence, and reports
connectivity only, not timing or release readiness.

The 16 new tests and helper were written to the Mac and tested there. The local
working tree also wires the helper into `verify_pico47_native.py` via:

```python
from pico47_panel_control_report import inspect_panel_control_links
```

and the returned inspector dictionary adds:

```python
'core_panel_control_connections': inspect_panel_control_links(native['Core']),
```

**That two-line inspector integration is still an uncommitted local change.**
The cloud draft preserves the helper, tests and this handoff only; it does not
pretend to contain the local integration or a completed publish/merge operation.
The active local branch is `hw/pico47-r6-local-closure-20261014`, based on main
`3db5d34b3dca325ee53fcd60b026d79acac257ce`. Preserve local changes when reconciling
with the separate recovery draft branch; do not reset or overwrite them.

535 distinct tests were actually run and passed on the Mac working tree:
Pico47 278, donor 238, geometry 19. Pico47 278 also passed under bundled KiCad
Python. The copied helper/tests have exact matching SHA-256 values and the
16 isolated tests also passed in the assistant container; that rerun is not
additional native validation and is not counted toward 535.

- Helper SHA-256: `e5e9f7ab0d0c3e16bbe2be25b982a928f18acae411ea64ba806c1b5f7467a8e0`
- Test SHA-256: `71201af38775c8b3716054d30cce3180fb11aa3bb444abb24c853aacab0fab6a`

Full local test evidence:
`.work/pico47-r6-complete-20261014/REGRESSION-RESULTS.json` and `*-tests-final.log`.
These are local results, not GitHub Actions or a claim that the draft's complete
source tree has undergone native replay.

## Rejected SPV attempt and next engineering work

SPV (R730.2 -> J601.40) still has no accepted route. Its narrow-corridor trial
could connect SPV only by disconnecting XLE. It was rejected and never applied to
native CAD. The captured r6 retains the original connected XLE and open SPV.
Diagnostic cuts are not approved copper modifications.

Evidence is under `.work/pico47-r6-complete-20261014/`, particularly
`spv-cut-repaired-review.json`, `shorter-supply-review.json`,
`power-group-shortcut-review.json`, `power-clean/PRUNING-REVIEW.json`, and
`CKV-POWER-NATIVE-METRICS.json`.

After replay confirmation, integrate the pending inspector wiring, create a
verified archived replacement of the formal working delivery, review and merge
this continuation, and synchronize the local branch without losing packaging/.
Remaining 42 non-ground opens, timing/power/feedback quality, exact battery and
panel identity, <=7mm fit, sourcing/CAM/SMT and physical EVT remain open gates.
