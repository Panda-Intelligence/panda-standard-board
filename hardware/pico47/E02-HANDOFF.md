# Panda47 E0.2 — current partial-routing continuation

This supersedes the E0.1 current-candidate pointer. **Not for fabrication or power-on.**
It retains the user-confirmed 4.7-inch E0470A01-family 1216x684 parallel display and
same actual replaceable2050mAh battery pack requirement. The precise pack and complete
touch/frontlight module are still unverified; the132mm layout envelope remains a
study, not a finished product or proof of the required <=7mm maximum thickness.

## Current native files — preserve this checkpoint

External canonical continuation:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261012/engineering-candidate/`

Working source:
`.work/pico47-resume-20261012/integrated-current/`

The external directory includes both PCB/schematic pairs, local libraries, native
reports, `CURRENT-STATUS.json`, `INDEPENDENT-CHECK.json`, `ROUTING-CHECKPOINT.json`
and per-file checksums. Do not replace it with the newest failed trial or a freshly
built unrouted base. Generated boards, route attempts and reports stay outside Git.
The unrelated untracked `packaging/` remains untouched.

## Fresh verified results

All-severity, all-track-error DRC was rerun after copper refill/save, together with
schematic parity and ERC. Unconnected items are shown separately from DRC errors.

| Board | DRC errors | DRC warnings | Unconnected items | Parity | ERC |
|---|---:|---:|---:|---:|---:|
| Core | 0 | 26 | 48 | 0 | 0 |
| Display | 0 | 5 | 21 | 0 | 0 |

These are NOT all-zero fabrication checks. The warnings still concern unfinished
copper ends/via connections, and all69 unconnected items must be resolved.

The previous published handoff had161/49 unconnected items. Interrupted work
contained unreported but native-checkable Core50/Display23 candidates. This pass
recovered and validated that work, then reached48/21. The reduction includes real
new connections and removal of orphan copper; it is not141 newly routed nets.

## What is now explicit source, rather than an interrupted local experiment

`ordered_core_layout.json` and `pico47_placement.py` define28 reviewed Core component
poses. R710..R725 are ordered beside J601 by data bit; U711 is no longer squeezed
into the bottom edge, and C711 follows its new position. The builder creates the
sixteen short F.Cu connector-side links and nine actual MCU-paddle GND vias.
Independent native connectivity checks verify those links and via locations.
This does not mean the complete MCU-to-panel sixteen-bit bus is finished.

Ground copper policy is explicit for the reviewed pad numbers. Redundant through
vias that were only surface junctions were replaced by real surface copper where
native clearance and complete pad-group continuity allowed it. They were not
blindly deleted. USB, RF, crystal and memory-net vias were excluded from that
surface-junction conversion. Failed proposals remain unadopted.

Physical connection checks in the current candidate are:

| Path | Native connected? |
|---|---|
| Core U501 GPIO2/pin7 to J602/pin16 | Yes |
| Display J4/pin5 to R813/pin1 | Yes |
| Display R813/pin2 to U810 EN/pin21 | **No — still a routing task** |
| Display C804 GND to R812 GND | Yes |

The FFC itself still needs actual cable/contact-side verification. Do not describe
the complete hardware inhibit chain as working or authorize panel power.

A candidate clock route had no DRC errors but separated J601.32 from its existing
GND group. It was rejected. The GPIO2 route was split out and accepted only after
all old pad groups remained connected. A similar Display signal change needed a
real repair to its C804/R812 ground-return island before acceptance.

That repair uses an explicitly specified GND via inside C804.pad2 at(18.1,104.75)mm,
diameter0.65mm/drill0.30mm. It requires **resin fill and copper capping**; factory
acceptance remains false. The source builder checks the complete annulus remains
inside that specific ground land. This is not a general via-in-pad permission,
not a waiver of hole/clearance rules, and never applies to U810's negative paddle.

## Rebuild without losing the partial routing

The source builder alone produces the source placement and deterministic short
links. To reproduce the current partial routing, supply its external checkpoint:

```sh
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
"$KPY" hardware/pico47/build_pico47.py \
  --donor /Users/isaac/workspace/AI/panda-standard-board/.work/seven-mm-catalog-20261012/default-rebuild \
  --output /absolute/new/ignored-or-external/candidate \
  --routing-checkpoint /Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261012/engineering-candidate
```

`pico47_checkpoint.py` verifies source hashes, exact checkpoint bytes, schematic
and project/custom rules, and native pad/placement/outline semantics. It replays
copper only onto the fresh build, then requires the same actual DRC/open/parity/ERC
counts and the independent circuit checks. It cannot turn partial routing into a
fabrication release. A real source rebuild and checkpoint replay reproduced48/21.
The fresh test output is `.work/pico47-resume-20261012/rebuild-resumed/`.

## Tests and remaining engineering work

103 Panda Standard source/continuity/placement/checkpoint tests pass:49 electrical-contract,
9 pad-group guards,29 placement/process mutations and16 checkpoint mutations.
71 unchanged donor sourcing/routing regression tests also pass. These are software
checks of design intent and workflow safeguards, not physical performance tests.

Next priority is the remaining Core MCU/mux/SD signal fanout and Display PMIC
control/power connections, with actual return continuity checked after refill.
Finish the R813-to-PMIC EN path before any power-on qualification. Do not make a
lower airwire count a reason to accept newly disconnected grounds or signal pads.
Power-current loops, rectifier/inductor startup and fault margins, signal timing,
source-series damping, and mux handover remain unqualified. The interrupted wide
routing experiments and negotiated router outputs are not approved substitutes.

Exact battery pack MPN/max dimensions/connector/polarity/NTC/CV/protection, full panel
suffix and touch/frontlight stack, final mechanical fit and <=7mm tolerance,
filled/capped processing, exact supply and JLC CAM/SMT acceptance remain separate
open gates. No vendor enquiry, purchase, shipment, fabricated receipt or sample
order was created by this routing continuation.
