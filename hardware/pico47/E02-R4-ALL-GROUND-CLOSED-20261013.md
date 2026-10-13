# Pico47 E0.2 r4 — all eight named ground blockers closed

2026-10-13. **ALL EIGHT NAMED GROUND CONNECTIONS VERIFIED.**
**45 other native unconnected items remain. NOT FOR FABRICATION OR POWER.**
This supersedes the route/delivery pointers in `E02-R4-SEVEN-GROUND-PROGRESS-20261013.md`
and `E02-R3-GROUND-CLOSURE-20261013.md`, not the product or qualification limits.

## Current verified delivery

Repository: `/Users/isaac/workspace/AI/panda-standard-board`.
Dated, source-bound engineering checkpoint:

`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261013-r4/engineering-candidate`

The user's requested working delivery now contains its verified copy:

`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e0-20261012/engineering-candidate`

The previous r3 working contents are retained byte-for-byte in sibling
`engineering-candidate-pre-r4-archive-20261013`; all earlier archives and dated
checkpoints remain intact. Publication used a staged copy, full file-hash checks,
then reversible renames. The prior package has 298 files; r4 has 299, including
the new `COMPLETE-GROUND-CHECK.json`. `CONTINUATION-R4-20261013.json` outside the
repository records all old/new hashes and successful source-replay verification.
Keep the user's untracked `packaging/` and unrelated worktrees untouched.

## Ground blockers: 8/8 closed

| Board | Named target | Fresh native result |
| --- | --- | --- |
| Core | J601.36 | Connected to U501.57 reference group |
| Core | J601.38 | Connected to U501.57 reference group |
| Display | J820.9 | Connected to C804.2 reference group |
| Display | J820.22 | Connected to C804.2 reference group |
| Display | R809.2 | Connected to C804.2 reference group |
| Display | R810.2 | Connected to C804.2 reference group |
| Display | U810.41 | Connected to C804.2 reference group |
| Display | U810.32 | Connected to C804.2 reference group |

All ground pads, not just these eight targets, join the selected native reference:
**Core 169/169, one group; Display 68/68, one group.** No remaining GND pad is
reported isolated. This is physical CAD connectivity, not a current/noise/thermal
or hardware qualification result.

| Board | Published r3 opens | Final r4 opens | DRC errors | DRC warnings | Parity | ERC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Core | 38 | 36 | 0 | 0 | 0 | 0 |
| Display | 15 | 9 | 0 | 0 | 0 | 0 |

Compared with the immediately preceding seven-ground intermediate, only the
remaining Display ground was closed: Display10 ->9; Core remains36. All original
physical pad groups survive relative to the published r3: Core233 ->231;
Display105 ->99. A clean rebuild and second native capture preserve231 ->231
and99 ->99, reproduce these counts and pass the complete-ground gate again.

The complete GPIO2/interconnect/R813/U810.EN21 inhibit chain and C804/R812 ground
connection are retained. Four layers, no In1 signal tracks, 16 ordered data links,
nine MCU paddle vias, the prescribed C804 return via, negative PMIC EP isolation,
component identities, footprints/pads, layout, outlines and native rules remain
unchanged. No netclass, drill/annulus minimum, severity or DRC exclusion was relaxed.

## Last U810.32 repair and its acceptance boundary

The U810.32 escape was coordinated with only the previously reviewed local
P47_VGH, P47_VEE_DRV, P47_VGH_BASE, P47_VEE_BASE, P47_VGH_FB and P47_VEE_FB copper.
Native original-pad groups, rather than every disconnected node on those nets,
defined the required restoration. Previously open R801/TP and other rail nodes
were not falsely treated as broken original connections or marked complete.

Four adjacent pin escapes were staggered; U810.32 receives a roughly3.630mm,
0.15mm-wide ground path to a 0.60/0.30mm through via at (22.4,95.3). The via
connects into the existing reference ground. The source-bound initial composite
transaction replaced279 scoped native copper items with582, passed zero native
errors/parity and retained all old pad groups; Display opens decreased10 ->9.
The larger primitive count is largely grid-generated short segments, not a
net-wide deletion of unrelated copper. Preserved outside fragments retain their
original endpoints, layers and widths.

Three resulting warnings were then resolved without suppressing them. A new
one-layer P47_VGH_BASE via that bridged two F.Cu traces was replaced by a
0.20mm F.Cu connection between (20.1,94.15) and (20.375,93.9875), preserving the
functional junction rather than deleting it. Native-guarded pruning removed
20 dead copper pieces. The final result retains all ground groups and has zero
DRC warnings. Failed earlier route orders and proposed-trunk trials remain
rejected evidence, not part of r4.

### Analog-routing review still required

Ground closure is not an analog-layout signoff. Exact native per-net metrics are
retained in `.work/pico47-r4-finish-20261013/PMIC-ROUTING-METRICS.json`.
Notably P47_VGH_FB total copper centerline length changed from23.496720mm to
55.438370mm and its via count from4 to5. P47_VEE_FB changed from29.677976mm to
35.215527mm and from2 to3 vias. P47_VGH_BASE and P47_VEE_BASE total lengths
slightly decreased; P47_VEE_DRV decreased from8.478857mm to5.529671mm.
These are total net-copper lengths, not simulated propagation or loop-gain data.
Review feedback noise pickup, return proximity and loop behavior, and improve
these detours as appropriate before hardware power or manufacturing release.
Neither the new ground gate nor native DRC claims that review has passed.

## Complete-ground capture gate

`capture_pico47_checkpoint.py --require-complete-ground` now requires both fresh
native ground reports to show one reference-connected group containing every
GND pad, and all eight exact named targets connected. The gate rejects missing,
duplicate, contradictory or incomplete evidence. It writes
`COMPLETE-GROUND-CHECK.json` and includes the result in `CURRENT-STATUS.json`.

The option is additive: existing partial engineering capture without the flag
remains available; all original non-increasing-open/non-increasing-warning,
rule/geometry/library binding, original-pad-group and failure-marker protections
remain unchanged. Use the flag for every continuation from this all-ground r4.
A failure creates no accepted `ROUTING-CHECKPOINT.json`.

Validation actually performed in this session:

- **507 distinct local source tests passed:** Pico47 250, donor238, geometry19.
  Pico47's250 also passed under bundled KiCad Python and are not counted twice.
  The 17 added tests cover full/partial native ground evidence and contradictions.
- A real fresh capture of the prior seven-ground native candidate with the flag
  failed as expected; the rejected directory has a failure marker and no accepted
  routing checkpoint. This verifies the capture path, not just a synthetic fixture.
- Fresh positive capture of both final boards, KiCad10.0.5 zone refill/save,
  all-severity/all-track DRC, parity/ERC, independent functions and physical groups.
- Clean `build_pico47.py --routing-checkpoint` replay, then an independent complete-
  ground recapture, reproduce all counts, all target states and the inhibit chain.
- `git diff --check` passed. These are local/native results, not GitHub Actions.

Evidence root: `.work/pico47-r4-finish-20261013/`.
`eight-ground-final-clean/` is the adopted Display source; Core is carried from
`.work/pico47-r4-resume-20261013/verified-seven-ground/`. Dated r4 is the canonical
published checkpoint, not any partial or newer-mtime experiment. Source-sync
preserved the previous uncommitted files in a named stash after proving they
were byte-identical to the already-merged PR24 files; it was not force-reset.

## Rebuild and verify

```sh
cd /Users/isaac/workspace/AI/panda-standard-board
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
DONOR="$PWD/.work/seven-mm-catalog-20261012/default-rebuild"
CHECKPOINT=/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261013-r4/engineering-candidate
NEXT="$PWD/.work/pico47-next-$(date +%Y%m%dT%H%M%S)"
"$KPY" hardware/pico47/build_pico47.py --donor "$DONOR" \
  --output "$NEXT" --routing-checkpoint "$CHECKPOINT"
"$KPY" hardware/pico47/capture_pico47_checkpoint.py --baseline "$CHECKPOINT" \
  --core "$NEXT" --display "$NEXT" --donor "$DONOR" --output "$NEXT-captured" \
  --require-complete-ground
```

Native bindings:
- Core PCB: `4287753eb653654ecc851e87c26c5b8a8106d136c7dab3dde4c5a7518939c596`
- Display PCB: `369f887a2a600ec5e7061299d05cafe14b5c250b0ada2f28c42fa7c36b042058`
- Routing checkpoint: `13ec7069fc90feb92b79c703025037152ff88f2808509541e80fd6028ade3b80`

## Remaining non-ground work

Core still has36 native unconnected items across MCU/mux/data, SDMMC, control,
audio, UART and supply-related nets. Display still has9 unconnected items across
I2C_SDA, VCOM, VGH, VNEG, VP and VPOS. These counts are not a number of nets.
The eight ground blockers are closed; complete PCB routing is not claimed.

Clock/data timing, analog/return quality, exact battery/full-panel acceptance,
<=7mm finished positive-tolerance fit, accepted supply/CAM/SMT, USB, charging/NTC/
ship/deep-sleep, frontlight/OVP, RF/thermal and physical EVT remain separate gates.
No fabricated hardware, power operation, production Gerber/BOM/CPL release or
purchase occurred. Manufacturing and physical qualification remain **false**.

Commit source/tests/handoff only; generated native CAD/reports/manifests and
routing trials stay ignored or external.
