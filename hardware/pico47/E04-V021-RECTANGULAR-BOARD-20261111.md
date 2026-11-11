# E04 v0.2.1 — rectangular 63 × 42 mm board (2026-11-11)

v0.2.1 is v0.2.0 (E03, `E03-V020-PICO-CLASS-REDESIGN-20261110.md`) with the L-shaped board replaced by a rectangle. Unchanged from v0.2.0:

- netlist, BOM and rules;
- footprints, including the JLC DFM fixes of 2026-11-11;
- schematic content.

v0.2.0 stays in `hardware/pico47/v0.2.0/` as the reference.

## 1. Decisions (user, 2026-11-11)

- **Board shape:** rectangle, 63 × 42 mm, below the cell. The cell is shortened to 3.2 × 50 × 70 mm (about 1700–1800 mAh, against about 2000 mAh for 3.2 × 50 × 80).
- **USB-C:** the mid-mount notch stays (9.24 × 5.55 mm at the bottom edge), because mid-mount saves about 1 mm of height.
- **Panel:** same class as Read Pico (4.7" 1216 × 684, 16-bit parallel, SY7636A, 40-pin 0.5 mm FPC), plus front light and touch. Still to be checked against a supplier drawing: the exact panel suffix, the contact face and the FPC exit positions.

## 2. Outline and cavity (device-cavity coordinates, mm, y down)

| Item | v0.2.0 | v0.2.1 |
|---|---|---|
| Board | L shape: strip at x 0.5–63.5, y 82–114.8, plus side tab at x 52–63.5, y 4–82 | Rectangle at x 0.5–63.5, y 72.8–114.8 |
| Bounding box / area | 63 × 110.8 mm, ≈ 2960 mm² | 63 × 42 mm, ≈ 2595 mm² (2646 mm² minus the notch) |
| Cell bay | x 1–51, y 1–81 (3.2 × 50 × 80) | x 1–51, y 1–71.8 (3.2 × 50 × 70) |
| Buttons SW201 / SW202 | right edge, y 30 / 42 | right edge, y 76.4 / 84.6 (8.2 mm apart) |

The billed PCB area falls from 63 × 111 mm to 63 × 42 mm, about −62 %.

## 3. Placement (`v020/layout/anchors_v021.json` → `placement_v021.json`)

**Lower strip (y ≥ 82).** Every part keeps its v0.2.0 pose: 96 parts from `placement_v020f.json` are used as anchors. In a first attempt the greedy placer moved some PMIC passives (D803, D804, C809, C812, R808, C522), and the area around U810 then no longer routed.

**New band along the cell edge (y 72.8–82).** It holds everything that was in the side tab:

| Ref | Function | Pose (x, y, rot) |
|---|---|---|
| U302 + Y301 | RTC | 7.5, 76.2, 0 |
| U503 | accelerometer | 14.5, 76.0, 0 |
| U902 + L401 | 3V3 buck | 21.0, 76.4, 0 |
| U905 + L905 / D905 / C920 / C923 | front-light boost | 29.0, 76.4, 0 |
| Q902 / Q901 | front-light colour switches, next to U905 | 36.4, 75.4 / 36.4, 79.3, 0 |
| U903 | fuel gauge | 40.8, 76.6, 0 |
| U907 | cell protection | 45.8, 76.5, 0 |
| J301 / J302 | cell +/− and NTC landings, next to the cell end | 51.5, 75.0 / 52.0, 78.8, 0 |
| SW201 / SW202 | buttons on the right edge | 61.6, 76.4 / 84.6, 90 |

The pin-targeted placer puts the passives. R306 is targeted at J301.1, R601 at Q901.1 and R602 at Q902.1.

## 4. Routing

1. `run_v020.sh ../v021/b8 40 ../v021/placement_v021e.json`, with `PANDA47_FP_DIR=v0.2.0/Panda47v2.pretty` so the DFM-fixed footprints are used. Freerouting 2.5.0 ran 40 passes and KiCad reported 0 unconnected after import.
2. `finish_v020.py` widened 12 necks below 0.09 mm, which left 5 clearance errors at 0.119–0.121 mm. The grid router re-laid three signal nets in small windows (`v021_local_spec.json`: FL_C_EN, FUEL_GPOUT, P47_HV_EN).
3. `prune_dangling_v020.py` and `trim_dangling_v020.py` cleaned up router overshoots. Five dead FUEL_GPOUT branches on In2 were removed (`v021_dead_branches.json`).
4. `silk_v020.py` ran, then `build_v020_sch.py`, `sync_board_sch_v020.py` and `set_fields_v020.py` with `PANDA47_VARIANT=v021`. The files are `Panda47-v021.*` and the title block reads v0.2.1 / E04.

**Tried and dropped on the way.** Candidates b1–b6 came from the first placement or from re-using v0.2.0 strip copper. Freerouting left 4–8 connections open around U601 and U810, and the local grid router could not legally close all of them.

**Tool fix.** `corridor_spec_v020.py` had let the Power-class nets P47_VP and FL_VOUT be ripped up, and the grid router lays 0.127 mm tracks only. Its keep-list now covers every Power-class net. In the final board only Freerouting has routed power nets, at their netclass widths.

## 5. Result

| | v0.2.0 | v0.2.1 |
|---|---|---|
| Board | 63 × 110.8 mm L, ≈ 2960 mm² | 63 × 42 mm rectangle, ≈ 2595 mm² |
| Parts / placements | 172 / 153 (top side only) | same |
| Tracks / vias | 2774 / 410 | 2802 / 415 (359 × 0.55/0.3, 56 × 0.6/0.3) |
| Via-in-pad | 17 | 17 (U501 ×9, U901 ×4, U904 ×2, U601, U903) |
| NPTH | 4 × 0.75 (switch posts), 2 × 1.0 (J501) | same |
| KiCad 10.0.7 checks | ERC 0, DRC 0 / 0 unconnected / 0 parity | ERC 0, DRC 0 / 0 unconnected / 0 parity |

Order pack: R2 `grace/panda47-pcb-v0.2.1-E04/` (generated outside Git by `export_orderpack_v020.py` with `PANDA47_VARIANT=v021`).

## 6. Open items

- **Cell:** 3.2 × 50 × 70 mm is an assumption. The real pack (PCM, NTC, leads to J301/J302) and its capacity have to be confirmed.
- **Buttons:** they moved from y 30 / 42 to y 76.4 / 84.6 on the right side, so the enclosure key positions change.
- **FPC poses:** the panel, touch and front-light FPC poses (J820 / J803 / J804) still need checking against the supplier drawing, as in v0.2.0.
- **Front-light distance:** the boost (U905 at x 29, y 76) is about 42 mm from the front-light FPC J804 (x 50.8, y 112); in v0.2.0 it was about 82 mm.
- **Fuel-gauge filter:** R903 / R904 sit about 9–11 mm from U903. The RC filter is low-current, but it could be tightened in the next revision.
- **EVT:** all EVT items of E03 §9 still apply.
