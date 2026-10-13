# Pico47 E0.2 r4 work in progress — seven of eight ground returns verified

2026-10-13. **One of the eight requested ground returns remains open.**
This is a source/test/continuation integration, not a newly published complete
PCB or a manufacturing release. The last authoritative working delivery is
still r3; do not relabel it as r4 or infer a delivery update from a Git merge.

## Exact status of the eight requested targets

| Board | Physical ground target | Latest observed native result |
| --- | --- | --- |
| Core | J601.36 | Connected to U501.57 reference group |
| Core | J601.38 | Connected to U501.57 reference group |
| Display | J820.9 | Connected to C804.2 reference group |
| Display | J820.22 | Connected to C804.2 reference group |
| Display | R809.2 | Connected to C804.2 reference group |
| Display | R810.2 | Connected to C804.2 reference group |
| Display | U810.41 | Connected to C804.2 reference group |
| Display | **U810.32** | **Still disconnected from reference ground** |

The core board now has all 169 ground pads in its reference group. Display has
67 of 68; U810.32 remains a material blocker to panel/battery power-up. All other
routing and physical acceptance requirements also remain in force.

## Verified intermediate CAD, not the published delivery

Canonical repository:
`/Users/isaac/workspace/AI/panda-standard-board`

Latest observed combined, source-bound, fresh native capture:

`.work/pico47-r4-resume-20261013/verified-seven-ground/`

This capture completed successfully through the connected desktop session on
2026-10-13 at 09:58 UTC. Its inputs were:

- Core: `.work/pico47-r4-20261013/core-native/`
- Display: `.work/pico47-r4-resume-20261013/r810-native/`
- Immutable published baseline:
  `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261013-r3/engineering-candidate`

| Board | Published r3 opens | Verified intermediate opens | DRC errors | Warnings | Parity | ERC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Core | 38 | **36** | 0 | 0 | 0 | 0 |
| Display | 15 | **10** | 0 | 0 | 0 | 0 |

**46 native unconnected items remain overall.** The reduction by seven is from
actual connections of the seven named ground pads, not hiding or deleting
unconnected pins. Original native pad groups and the existing direct-inhibit
chain are preserved. Native rules, four-layer policy, no In1 signal traces,
negative U810 exposed-pad isolation, C804 return-via prescription, part identities,
placement and source electrical intent are unchanged.

A complete clean source rebuild followed by independent r4 recapture and
promotion into the user-requested delivery directory was **not completed** before
the Mac became unavailable. Native capture is not a substitute for those final
publication steps. Do not claim a full r4 replay or update the working package
without executing them and verifying every relevant input/output hash.

Published directory still left unchanged:

`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e0-20261012/engineering-candidate/`

Earlier dated checkpoints, original r3 working files, archives and `packaging/`
were not deleted or replaced in this continuation.

## Actual accepted work and provenance

The earlier interrupted r4 session already left the two accepted Core ground
closures. Only a short local P47_XLE connector neck was coordinated; original
signal via, widths and downstream connectivity were retained. Exact plan and
native evidence are under `.work/pico47-r4-20261013/core/` and `core-native/`.
The early agent report predates desktop validation; use the later accepted
native transaction and combined capture, not its original pending status.

Display U810.41, R809.2 and J820.9 were independently captured in the previous
`verified-five-ground-checkpoint`. The accepted J820.22 follow-up is:

`.work/pico47-r4-20261013/display-lower/j820-22-thermal-native/`

Its actual native transaction preserved all prior pad groups, errors/warnings/
parity zero, and reduced Display opens from 12 to 11. Its PCB SHA-256 is
`97fd3641c5c835f017bee70948b378c8dc55587ff5744f9f173d7c2ef6e49177`.
That accepted intermediate, not an unreviewed newer trial, was the source for
this continuation's R810.2 route.

R810.2 now has a 0.936002mm-long, 0.15mm-wide F.Cu ground bridge from its existing
pad position (23.26,112.0) to an ordinary 0.60/0.30mm through via at
(22.7,112.75). It requires replacing exactly two interfering In2.Cu ordinary
signal segments, preserving their original 0.20mm widths and exact endpoints:

- P47_D11: `(20.4949,114.5267) -> (24.222,110.7996)`;
  original UUID `1d1401a5-f9ce-4d72-b995-75b654159140`.
- P47_D1: `(22.4553,113.4938) -> (24.6237,111.3254)`;
  original UUID `6fd9754d-5260-40a4-a944-027046091b52`.

The replacement paths are approximately 5.538732mm and 3.310950mm. They add no
signal vias. The complete accepted transaction removes two old primitives and
adds 72, preserving all original pad groups and reducing native opens 11 -> 10
with errors/warnings/parity zero. Its bound plan is:

`.work/pico47-r4-resume-20261013/r810-actual-rule-plan.json`

The planning-grid endpoint issue was handled by sampling a small terminal area
and then restoring the exact original endpoint coordinates before geometric and
native validation. The actual 0.20mm rule was retained. An overly conservative
additional planning margin was not represented as a new native rule or waived
violation. Native acceptance remained mandatory.

## Explicit required-target inspection and tests

`pico47_ground_returns.py` now accepts an optional required-target sequence.
`verify_pico47_native.py` checks the exact two Core and six Display target pins
instead of inferring completion from a total group count. Reports include each
physical target's coordinates and `connected_to_reference` result, the required
target count, connected count, and `all_required_ground_targets_connected`.

Missing or ambiguous physical targets, duplicate target identities and malformed
input are rejected. Joining isolated pads to one another does not count as joining
the reference group. Completing a selected subset does not imply all ground pads
are connected and does not grant physical or manufacturing qualification.
The default report remains backward-compatible and all existing native acceptance
gates are unchanged.

Fresh Mac regression runs on 2026-10-13 at 10:05 UTC passed:

- Pico47: 233 tests, including 12 new required-target regression tests.
- Historical donor: 238 tests.
- Geometry tools: 19 tests.
- **490 distinct source tests total.**
- Pico47 233 also passed under bundled KiCad Python; this repeated runtime is not
  added to the 490 total.
- `git diff --check` passed for the tested local source changes.

Logs and `REGRESSION-RESULTS.json` are under
`.work/pico47-r4-resume-20261013/`. These are observed local/native results, not
GitHub-hosted CI and not a full r4 source-rebuild claim.

## Remaining U810.32 blocker and unaccepted studies

U810.32 at (18.45,95.4) lies between P47_VGH_FB and P47_VEE_FB. A close ground via
can fit the real lands but obstruct the adjacent feedback exits. Routing those
feedbacks first can instead obstruct the neighboring P47_VGH_BASE/P47_VEE_BASE
escapes. A legal ground path alone is not accepted if any prior connection is lost.

Read the current geometric diagnostic evidence rather than blindly replaying the
failed nearest-via permutations:

- `last-return-obstacles.json`: original UUID-level conflicts.
- `pmic-corridor-review.json`: continuous free-space and legal via regions.
- `pmic-four-neck-review.json` and `pmic-staged-review.json`: rejected local
  feedback/base-rail routing orders and their concrete blocked stages.
- `pmic-via-field-review.json`: legal candidates for a staggered, coordinated
  local via arrangement without moving pads, shrinking drills or adding layers.

All files above are under `.work/pico47-r4-resume-20261013/`. Existing fixed pads
of D802/L801/L802 and the retained P47_VN/P47_VN_LX/P47_VGH_DRV copper constrain the
via field. Any broader local copper ECO must retain original widths/endpoints,
all prior pad groups and the exact negative-EP and reference-plane boundaries.
Do not change the PCB's native rules to make a planning result pass.

The independent helper was scoped to `independent-pmic/` and its separate final
report. Its final output could not be read after the device went offline. No
unread helper result, geometric-only plan or later file timestamp is accepted.
Inspect and validate any such plan independently before using it.

## Safe resumption and Git boundary

The Mac went offline before the last ground closure and publication steps.
The local work branch was `hw/pico47-r4-eight-ground-20261013`, with the two
inspection files modified and the new required-target test file untracked.
This separate remote integration branch preserves those tested source changes
and this handoff; it does not update the disconnected machine or native delivery.
Do not reset/discard local edits when synchronizing. Compare current file blobs
and archive byte-identical duplicates before any branch checkout that needs it.
The tested two source-file blobs are:

- `pico47_ground_returns.py`: `5aba9590d19d70f873825bd61b40d69937b25995`.
- `verify_pico47_native.py`: `7f357e1a7386bd14ca83b0fe8aa54e4ca1f1c746`.

Resume from `verified-seven-ground` after validating its manifest and actual
native status. Finish U810.32 without regressing the seven completed targets,
then perform combined capture, clean source rebuild, independent recapture and
all-target checks before promoting a new dated r4 checkpoint. Only afterwards
replace the requested working delivery using a verified staged copy and a
byte-preserved r3 archive. Until then the published r3 remains unchanged.

Generated native CAD, reports, routing plans, logs, renders and other temporary
outputs remain ignored/external. Reusable source, tests and engineering handoffs
alone belong in Git. No fabrication, charging or panel-power operation occurred;
`manufacturing_release` and physical qualification remain **false**.
