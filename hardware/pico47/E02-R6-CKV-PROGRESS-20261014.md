# Panda Standard r6 CKV — recovered and independently replayed, 2026-10-14

**Verified engineering candidate. NOT FOR FABRICATION OR POWER.**
The previously unread source-replay result has now been retrieved and verified.
A second complete source rebuild and native recapture also passed after reconciling
PR27's source with the Mac working tree. **42 native unconnected items remain.**

The source integration is ready for PR review. The user's working delivery still
contains r5: no publication/rename command was executed. Do not equate source
merge with replacement of the external working CAD directory.

## Exact native result

Dated verified r6 candidate:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261014-r6/engineering-candidate`

| Board | Published r5 opens | Verified r6 opens | DRC errors | Warnings | Parity | ERC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Core | 34 | 33 | 0 | 0 | 0 | 0 |
| Display | 9 | 9 | 0 | 0 | 0 | 0 |

The connector-side CKV route R729.2 -> J601.39 is physically connected. Its new
copper is 9.913584mm long, 0.15mm wide, with three 0.45/0.25mm through vias.
All original connected pad groups, all169 Core and68 Display ground pads, all8
named ground targets, the full GPIO2/R813/U810.EN21 chain and C804 return survive.
The retained XLE route is connected. SPV and audio data remain open.

The initial CKV plan changed only one XLE segment and one display-logic supply
segment. XLE's original endpoints, F.Cu layer and0.15mm width were retained.
The supply replacement was first22.002758mm, then shortened to13.545332mm at
0.35mm width joining the same original power groups, with **no added power vias**.
Five dead-end copper pieces were pruned under the existing native rollback and
connectivity guards, restoring zero warnings.

These are replacement-route lengths. The whole 3V3_EPD_LOGIC net is69.193712mm
in r6, versus78.841087mm before optimization and59.338330mm in r5. Its via count
remains3. The final supply is still longer than r5; voltage drop, return quality,
current capacity and power integrity are not signed off by native connectivity.

Source components, footprints, pad/net identities, placement, outline, four
layers/no In1 signal tracks, minimum via/drill dimensions, thermal rules,
negative PMIC exposed-pad isolation and physical qualification gates are unchanged.
No DRC exclusion, severity or native rule was relaxed to obtain this result.

## Recovered replay and fresh revalidation are complete

The old process `proc-35236-30` had actually completed before the communication
failure. This resumed session read its actual files rather than inferring success:

- `.work/pico47-r6-complete-20261014/final-roundtrip-proof/CURRENT-STATUS.json`
- `.work/pico47-r6-complete-20261014/final-roundtrip-proof/CONTINUITY-CHECK.json`
- `.work/pico47-r6-complete-20261014/final-roundtrip-proof/INDEPENDENT-CHECK.json`

They reproduce Core33/Display9 with complete ground and all critical checks true.
They preserve Core228 ->228 and Display99 ->99 physical pad groups. The native
panel-control report says CKV=true, XLE=true, SPV=false; the audio-data report
is false. Regenerated PCB/pad UUIDs are not compared as electrical identities.

The Mac source was then reconciled with the existing PR27 branch, retaining all
three prior local source files byte-for-byte under:
`.work/pico47-r6-publish-20261014/preserved-local-source/`.

The two helper/test files were checked against the remote recovery branch before
switching. The tracked inspector integration was preserved, not reset. The local
branch became `hw/pico47-r6-recovery-20261014`, based on cloud commit
`cc3da7c094657dc7c1f13ac0f009d3a4acc9135f`. The user's untracked packaging/ was not
staged, moved, overwritten or included in any commit.

A NEW complete verification was then executed successfully by `proc-35236-46`:

- `.work/pico47-r6-publish-20261014/reconciled-source-replay/`
- `.work/pico47-r6-publish-20261014/reconciled-native-proof/`
- `.work/pico47-r6-publish-20261014/RECOVERY-VERIFICATION.json`
- `.work/pico47-r6-publish-20261014/*-tests.log`

Its returned exit status is0 and it explicitly reports
`RECONCILED_SOURCE_AND_NATIVE_REPLAY_VERIFIED`, with Core33/Display9 and zero
errors/warnings/parity/ERC. The verification script checked the full dated
candidate manifest, input immutability, every original pad group, complete ground,
critical connections, CKV=true/XLE=true/SPV=false and exact resulting counts.

**535 distinct source tests were freshly rerun and passed:** Panda Standard 278, donor238,
geometry19. The278 Panda Standard cases also passed under KiCad Python and are not counted
twice. These are observed local/native runs, not hosted GitHub Actions results.

## Source integration now included

`pico47_panel_control_report.py` and its16 tests validate the six exact pads for
CKV, SPV and XLE. The report distinguishes actual copper connectivity from equal
net labels and rejects pin swaps, missing/overlapping groups and cross-net shorts.
It makes no timing or fabrication claim.

`verify_pico47_native.py` now contains the exact two-line integration tested on
the Mac: importing `inspect_panel_control_links` and recording its result as
`core_panel_control_connections`. All existing independent checks remain intact.
The cloud file was checked to have exactly those two added lines against the
previous inspector blob, not an unreviewed rewrite:

- Previous inspector Git blob: `9c121dc10113dc04d05ebc481032eeef617ab22a`
- Integrated inspector Git blob: `d0f435f5b6cda88414322c9f4d989c719233dd7e`
- Integrated inspector SHA-256: `cad478b07b4f4484896dde76baaf1c350fe40fca02444cac18a6855f01222811`

The helper/test bytes remained unchanged from the Mac-tested copies. No generated
native PCB, render, report, manifest, trial file or packaging/ was committed.

## Remaining publication boundary

After successful revalidation, writing
`.work/pico47-r6-publish-20261014/publish_r6.py` timed out with OUTCOME_UNKNOWN.
The subsequent bounded file read and SPV diagnostic-process read also timed out.
**That publication script was NOT executed.** No staging copy or working-directory
rename was requested, so formal working CAD remains r5. Do not claim r6 has been
copied into `panda47-e0-20261012/engineering-candidate`.

The script's existence/contents must be read and verified before any execution.
Its intended sequence is: verify candidate against RECOVERY-VERIFICATION.json,
verify the unchanged r5 working directory, copy r6 into a fresh staging directory,
verify every file, archive old r5 as `engineering-candidate-pre-r6-archive-20261014`,
then atomically rename the staged copy. Retain all earlier archives.

Cloud PR integration can now proceed because source and native replay are verified.
Local Git synchronization and external publication remain separate unfinished
operations. On reconnection, fetch the actual current remote refs, compare the
local pending inspector bytes with the merged version, and preserve any local
changes before fast-forwarding. Do not hard-reset, force-push or discard packaging/.
The older AGENTS/README working-directory pointers still describe published r5;
update them only together with a verified external working-copy publication.

## Remaining routing and rejected experiments

SPV (R730.2 -> J601.40) still lacks an accepted route. Earlier corridor proposals
could join SPV only by breaking retained XLE, so they were rejected. The r6 native
candidate preserves XLE and keeps SPV explicitly false.

This resumed session dispatched only an additional read-only SPV/XLE-via obstacle
diagnosis in `proc-35236-47`. Its completion/output was not retrieved after the
new communication failure. No new SPV copper proposal was applied or accepted.
Read `.work/pico47-r6-publish-20261014/SPV-JUNCTION-DIAGNOSIS.json` if present,
without assuming an output filename proves successful native verification.

All42 remaining non-ground opens, digital timing, supply/feedback/return quality,
exact battery/full-panel identity, <=7mm finished fit, sourcing/CAM/SMT and physical
EVT remain open gates. **Manufacturing and physical qualification remain false.**

## Resume from the verified candidate

```sh
cd /Users/isaac/workspace/AI/panda-standard-board
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
DONOR="$PWD/.work/seven-mm-catalog-20261012/default-rebuild"
CHECKPOINT=/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261014-r6/engineering-candidate
NEXT="$PWD/.work/pico47-next-$(date +%Y%m%dT%H%M%S)"
"$KPY" hardware/pico47/build_pico47.py --donor "$DONOR" \
  --output "$NEXT" --routing-checkpoint "$CHECKPOINT"
"$KPY" hardware/pico47/capture_pico47_checkpoint.py --baseline "$CHECKPOINT" \
  --core "$NEXT" --display "$NEXT" --donor "$DONOR" --output "$NEXT-captured" \
  --require-complete-ground
```

Dated r6 native SHA-256:
- Core: `6f1775f3c02433cf6b8b9831e0a983e8084df87c17daf711f223a689dc719259`
- Display: `e5ae20757677c7f66218d25c7854fdb2adf8f3a49b2495a4f43de2e5cc3cc945`
- ROUTING-CHECKPOINT.json: `6064bbb2b80373688aeae561bbdd348ae57d77e304be7b9204fa7ee2118f5597`
