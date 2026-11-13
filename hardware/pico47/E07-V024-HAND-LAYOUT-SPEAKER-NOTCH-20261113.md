# E07 v0.2.4 — hand-laid power stages, speaker notch, pack with its own protection (2026-11-13)

v0.2.4 answers an outside layout review of v0.2.2 ("thin traces on every current-carrying path", "every buck
converter is routed badly"). The power stages, RF, crystal and current trunks are now laid by hand, and the board
is re-shaped around a larger, thinner cell and a speaker. v0.2.3 (E06, same 63 × 43 mm outline as v0.2.2) was the
first pass of the hand layout and stays in `v0.2.3/` as the reference. v0.2.2 must not be ordered.

## 1. Decisions (user, 2026-11-12 / 13)

| Topic | Decision |
|---|---|
| Layout quality | Check and re-lay from an electrical and volume-production point of view. |
| Size | The board may grow in length. Thickness must not grow. |
| Parts | Fewer parts are welcome as long as every function stays. |
| Cell | Thinnest pack with about 2000 mAh and its own protection board: LP305779 class, 3.0 × 57 × 79 mm, catalogue 2000 mAh, PCM + 10 k NTC, 3 wires. |
| Speaker | Kept, with a sound port in the enclosure. |

## 2. What changed from v0.2.2

| Item | v0.2.2 | v0.2.4 |
|---|---|---|
| Board | 63 × 43 mm | 63 × 48 mm (y 67.4–115.4), R4 bottom corners, speaker notch x 0.5–16.6, y 67.4–79.0 |
| Device (study) | 67.0 × 118.3 × 7.3 mm | 67.0 × 133.7 × 7.3 mm |
| Cell | 3.2 × 50 × 70 mm, protection IC on the board | 3.0 × 57 × 79 mm with PCM and NTC in the pack |
| Removed parts | — | U907 (cell protection), R940, C940, J301. J302 is now a 3-pad landing: NTC / B− / B+ |
| Added part | — | C817, 4.7 µF / 25 V 0603 (same part as C804): VN reservoir at the rectifier D802 (§4 step 10) |
| Parts | 174 | 171, plus 3 fiducials (1 mm copper, 2 mm mask opening) |
| Net classes | Default, Power | Default, Power 0.3 mm, HV 0.2 mm (panel rails, REGN, BTST), RF 0.17 mm (50 Ω over 0.1 mm prepreg) |
| Tracks / vias | 2686 / 410 | 2810 / 429 (407 × 0.55/0.3, 22 × 0.6/0.3) |
| Via-in-pad | 17 | 20 (the three new ones: C504 pad 2, U904 pin 7 and C817 pad 2, see §4) |
| Placements / BOM lines | 155 / 73 | 153 / 72 |

Placement moves in v0.2.4: U601 (expander) to (11.3, 86.6), U904 (audio amplifier) to (4.2, 83.2) next to the
speaker landing J502 at (11.3, 81.2), battery landing J302 at (52.0, 78.8), shunt R306 at (56.8, 75.0). USB-C, the
panel FPC, SD socket, keys, J803 / J804 and the status LED keep their v0.2.2 positions.

## 3. Hand-laid blocks (`v024/design_v024.py`, on top of `v023/design_v023.py`)

The blocks are written as code (`handlib.Design`: place, track, via, clearance check). They are written into the
board as locked copper before the autorouter runs, so the autorouter only connects signals around them.

| Block | Layout | Measured on the board |
|---|---|---|
| Charger (SGM41513) | input, PMID and SYS caps, inductor, BTST and REGN parts placed at their pins | SW 0.5–0.7 mm wide, 6.4 mm long, no via; PMID 2.0 mm |
| 3.3 V buck (SY8089) | CIN at pin 4 with its ground straight under the IC to pin 2 | LX 0.5 mm wide, 2.3 mm long, no via |
| Front-light boost (SGM3732) | inductor and diode within 1 mm of SW, output cap at the diode | SW 0.5 mm wide, 4.5 mm long, no via |
| RF | pi match in line to the coax landing | LNA_IN 6.0 mm and RF_ANT 4.6 mm at 0.17 mm, F.Cu only, no via |
| Crystal | next to the pins | XTAL_N 9.1 mm, XTAL_P 4.6 + 1.4 mm, F.Cu only, no via |
| Trunks | VBUS and battery on B.Cu | 0.8 mm; VSYS 0.3–0.8 mm; 3V3 trunk up to 0.6 mm |

After routing, `widen_v023.py` widens every Power / HV track as far as DRC allows (739 of 965 segments widened).

## 4. Routing record

1. `loop.sh` (design → anchors → placement, twice) and Freerouting, 60 passes (candidate d1): 4 signal connections
   left open, plus VBUS to TP1 and one fenced-in ground pad.
2. TP1: a 0.4 mm B.Cu stub from the VBUS column (now part of the design source).
3. Grid router, left side (`layout/spec_left.json`): P47_HV_EN and SD_CD routed, no conflicts. The rip window had to
   start at y 96.0 so that the P47_PGOOD and I2C_SDA vias below U810 pins 18–23 could move.
4. Grid router, TOUCH_INT (`layout/spec_touch_int.json`), then `layout/eco_touch_int.py`: the router left the
   TOUCH_INT and P47_PGOOD vias 0.5 mm apart at U601. U601 pin 9 (GND) now ties to the exposed pad instead of its
   own via, and the TOUCH_INT via sits at (11.4, 89.5).
5. `layout/eco_d11.py`, then the grid router (`layout/spec_d11.json`, converged at iteration 8): U501 pin 21
   (P47_D11) was boxed in by C504 and its feed. C504's ground via moved into its pad 2, and a P47_D11 via took the
   freed spot.
6. `finalize.sh`: `finish_v020.py`, prune / trim of dangling ends (4 rounds), widening, fiducials, silkscreen.
7. `layout/eco_final.py`:
   - restores an I2C_SDA run on In2 that the trim removed (the router had left a T-junction 4 µm off the
     segment, so the trim saw a loose end);
   - narrows a BAT_CONN_P sense stub at U903 from 0.127 to 0.12 mm (it was 1.4 µm short of clearance);
   - adds a ground via in U904 pin 7. That pin was fenced in by VSYS and SPK_P and had no ground connection
     other than a pour island.
8. The pin-1 dot of U901 moved off the C203 pad, in the board and in `Panda47v2.pretty/U901_Core.kicad_mod`.
9. `layout/eco_vp.py`: P47_VP from the rectifier D801 round L801 to U810 pin 42 is 0.3 mm wide (it had 0.127 mm
   and 0.2 mm stretches). The last 1.4 mm before the pin stays at 0.127 mm, next to the ground via of pin 41.
10. `layout/eco_pmic.py`, then the grid router (`layout/spec_pmic.json`, converged at iteration 9):
    - The VN reservoir C804 sits at U810 pin 4, 9 mm and two vias away from the rectifier D802, so the pulsed
      diode current had no capacitor next to the switch. C817 (new, same part) now lands directly above the D802
      anode pad, with a ground via in its pad 2. C804 stays at pin 4.
    - R801 turned to lie under R802 to make room.
    - VEE_FB, VEE_BASE, VGH_FB, VGH and XOE were re-laid around C817 by the router.
    - Then prune, one trim pass (3 tails), the widening pass (79 more segments) and the silkscreen pass.

No power, RF or crystal net was ripped by the grid router. A trial with the VBUS trunk along the bottom edge
(candidate f1) left 8 connections open and was dropped.

## 5. Result

KiCad 10.0.7, `--severity-all`: ERC 0. DRC 0 violations, 0 unconnected, 0 schematic parity. The schematic is 8 sheets
plus the index, generated from the netlist (174 nets, identical to the board).

## 6. Not done yet

- **Panel PMIC (SY7636A) area**: reviewed and patched in place (§4 steps 9–10), not re-laid as a block. Left as is:
  - The inverting converter has no input capacitor right at pin 24. VSYS reaches that pin through one via and
    about 3 mm of In2; the nearest 10 µF capacitors (C801, C803, C816) are 4–6 mm away. A capacitor at the pin
    needs L802 and the pin 17–23 escapes moved.
  - Both switch nodes are 6.5 / 7.4 mm long (0.2–0.6 mm wide, no via).
  - P47_VGL has 8 vias and P47_VGH has 5; their tracks are 0.127–0.3 mm.
- **USB D+ / D−**: not a matched differential pair (USB_DM 21.7 mm with 2 vias, USB_DP 18.3 mm with 4 vias, tracks
  0.095–0.127 mm). At full speed (12 Mbit/s) the 3.4 mm mismatch is about 20 ps, far inside the budget, so it was
  left. It has not been measured.
- **Long shared nets**: I2C has 9–10 vias per line; VSYS has 12 vias.
- **Test points**: 15, the same set as v0.2.2.
- **Cell**: LP305779 is a catalogue size. The supplier datasheet (charge voltage, real capacity, pack outline with
  PCM, NTC curve, wire order) is still needed before the charger settings and J302 pad order are final.
- **Speaker**: no model chosen. The pocket takes a 15 × 11 mm class part up to 3.2 mm high.
- **Enclosure study** for the 133.7 mm body exists outside Git; openings are unchecked against real parts.
- **Order pack**: generated outside Git (R2 `grace/panda47-pcb-v0.2.4-E07/`): 153 placements, 72 BOM lines, 20
  via-in-pad, U810 consigned. It is for quoting and review; the items above come first.
- All E05 §6 items (FPC exits, LED lens direction, consigned U810) still apply. `manufacturing_release = false`; no
  fabrication, charging or panel-power claim.
