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
| Lanyard | A lanyard hole, first asked for at the bottom-right corner; another corner is acceptable if that one does not suit. It is at the top-right corner (§6). |

## 2. What changed from v0.2.2

| Item | v0.2.2 | v0.2.4 |
|---|---|---|
| Board | 63 × 43 mm | 63 × 48 mm (y 67.4–115.4), R4 bottom corners, speaker notch x 0.5–16.6, y 67.4–79.0 |
| Device (study) | 67.0 × 118.3 × 7.3 mm | 67.0 × 133.7 × 7.3 mm |
| Cell | 3.2 × 50 × 70 mm, protection IC on the board | 3.0 × 57 × 79 mm with PCM and NTC in the pack |
| Removed parts | — | U907 (cell protection), R940, C940, J301. J302 is now a 3-pad landing: NTC / B− / B+ |
| Added parts | — | C817, 4.7 µF / 25 V 0603 (same part as C804): VN reservoir at the rectifier D802 (§4 step 10). C818, 2.2 µF / 10 V 0402 (same part as C304): input capacitor at U810 pin 24 (§4 step 11). Test pads TP5, TP6, TPG2 |
| Dropped part | — | C816 (10 µF), made redundant by C818 (§4 step 11) |
| Parts | 174 | 174 (171 + 3 test pads), plus 3 fiducials (1 mm copper, 2 mm mask opening) |
| Net classes | Default, Power | Default, Power 0.3 mm, HV 0.2 mm (panel rails, REGN, BTST), RF 0.17 mm (50 Ω over 0.1 mm prepreg) |
| Tracks / vias | 2686 / 410 | 2831 / 431 |
| Via-in-pad | 17 | 22 (new: C504 pad 2, U904 pin 7, C817 pad 2 and two in the L802 ground pad, see §4) |
| Placements / BOM lines | 155 / 73 | 153 / 72 |
| Test points | 15 | 18 |

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
11. `layout/eco_cin.py`, then the grid router (`layout/spec_cin.json`, converged at iteration 2):
    - C818 (0402, 2.2 µF) sits 1.4 mm from U810 pin 24, the supply pin of the inverting converter.
    - L802 turned 180° and moved 0.3 mm down. Its switch pad is now straight under D802 (1.9 mm of 0.6 mm track
      instead of a 4 mm diagonal), and its ground pad is next to C818's ground, with two ground vias in the pad.
    - The VSYS track that ran under L802 is gone, and C816 with it.
    - C506, the audio amplifier's 10 µF, was found 32 mm from the amplifier (a leftover of the earlier placement,
      fed through C816). It now sits on the VSYS track below U904, next to C505.
    - MODE and VEE_BASE were re-laid by the router; then prune / trim, widening (62 more segments) and silkscreen.
12. `layout/eco_tp.py` and `eco_tp_silk.py`: three more back-side test pads, each on an existing via of its net
    (`layout/tp_find.py` ranks the vias by free area): TP5 FL_VOUT, TP6 3V3_SD, TPG2 GND.

13. `layout/eco_mount.py`, then the grid router (`layout/spec_mount.json`): board fixing and locating (§7).

No power, RF or crystal net was ripped by the grid router. A trial with the VBUS trunk along the bottom edge
(candidate f1) left 8 connections open and was dropped.

## 5. Result

KiCad 10.0.7, `--severity-all`: ERC 0. DRC 0 violations, 0 unconnected, 0 schematic parity. The schematic is 8 sheets
plus the index, generated from the netlist (174 nets, identical to the board).

## 6. Not done yet

- **Panel PMIC (SY7636A) area**: patched in place (§4 steps 9–11), not re-laid as one block. What remains:
  - The VP switch node is 6.5 mm long (0.2–0.6 mm wide, no via); the VN switch node is now about 5 mm.
  - P47_VGL has 8 vias and P47_VGH has 5; their tracks are 0.127–0.3 mm. They carry the gate rails, a few mA.
- **USB D+ / D−**: left as routed, on purpose. From the series resistors to the MCU the two lines run side by side
  on B.Cu at 0.48 mm pitch. End to end D− is 35.4 mm and D+ is 28.8 mm; the difference comes from the USB-C
  crossover (A6/B6 and A7/B7 are joined at the connector). The MCU port is full speed only (12 Mbit/s): 6.6 mm is
  about 45 ps against an 83 ns bit, so matching or a 90 Ω pair would not change anything measurable. Not measured.
- **Long shared nets**: I2C has 9–10 vias per line; VSYS has 12 vias.
- **Test points**: 18. There is no UART pad: both UART0 pins are used for other signals, and the board is flashed and
  logged over the MCU's USB port.
- **Cell**: not chosen. Findings of 2026-11-13:
  - No supplier datasheet exists for the 3.0 × 57 × 79 mm size the bay was drawn for.
  - One documented pack fits the envelope: PC326072, 3.2 × 60 × 75.5 mm max (about 81.5 mm with the tab, 3.5 mm
    at the tab), 2000 mAh typical / 1950 min, 3.8 V, charge 4.35 V, PCM and 10 k NTC (B 3435), FPC connector
    ([sheet](https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/196/326072_2D00_2000mAh-SPC_2D00_B0.pdf)).
    It is a customer-specific part, so availability is unknown. It needs the bay ribs moved (60 mm wide), a relief
    at the tab, a 4.35 V charge setting and a connector instead of the J302 pads.
  - The pack of the 4.7-inch reference device has no public data beyond "2050 mAh, LCO, replaceable": no model,
    size, connector or spare-part listing was found, so it cannot be designed in without a sample to measure.
  - The user accepts 1800 mAh or more.
- **Volume**: U904 (NS4168) has a fixed gain and no volume pin. Volume is set in firmware by scaling the I2S
  samples, from the touch screen; the two side keys can act as volume up / down while audio plays. No hardware
  change is needed for this.
- **Speaker**: not sampled. Candidate: Soberton SP-1511L, 15 × 11 × 3.0 mm, 8 Ω, 0.7 W rated / 1 W max, wire leads
  to the J502 landing ([datasheet](https://www.soberton.com/wp-content/uploads/2018/07/SP-1511L-29-June-2018.pdf)).
- **Enclosure study** for the 133.7 mm body exists outside Git. A boolean check of the board STEP, a speaker block
  and a cell block against the shell and frame shows no overlap (one rib was moved after the first run). Openings
  are unchecked against real parts, and the panel flex length to J820 needs the panel drawing. 
- **Screen position** (user, 2026-11-13: the chin was too large): the window sits 7 mm lower than in the first
  v0.2.4 study. Bezel 10.5 mm at the top, 17.9 mm at the chin. Enclosure only; the panel is above the board and
  the cell, so nothing on the board moves. The panel flex length to J820 still needs the panel drawing.
- **Lanyard**: in the enclosure only, at the top-right corner beside the cell; the board is not involved.
  - A bottom-right version was tried first (a 2.1 × 6.8 mm board step, commit 58589b7). Between J820 and the wall
    there are only 2.5 mm, which gave a 1.2 mm channel and a bar of 1.4–2.1 mm. It was dropped and the board corner
    restored.
  - Top right has 3.5 mm beside the cell: a 1.6 × 2.0 mm channel and a bar of 2.9 mm on the straight wall, about
    2.4 mm at mid-corner, thinner only at the exit. The cell sits against the left rib (x 3.1–60.4).
  - A cell wider than 57 mm (PC326072 is 60 mm) takes that space; then the lanyard has to be reviewed again.
  - The bar needs a pull test on first samples.
- **Order pack**: generated outside Git (R2 `grace/panda47-pcb-v0.2.4-E07/`): 153 placements, 72 BOM lines, 22
  via-in-pad, U810 consigned. It is for quoting and review; the items above come first.
- All E05 §6 items (FPC exits, LED lens direction, consigned U810) still apply. `manufacturing_release = false`; no
  fabrication, charging or panel-power claim.

## 7. Board fixing and locating (user, 2026-11-14)

The board lies on the 0.8 mm floor of the rear shell, so a screw from the inside has no thread depth. The user chose
screws from the back into nuts soldered on the board.

| Feature | Position (mm) | Detail |
|---|---|---|
| MH1 datum hole | (26.6, 107.3) | 1.2 mm non-plated, 5.4 mm left of the USB-C centre line; 1.1 mm shell pin |
| MH2 slot | (62.3, 111.0) | 1.2 × 1.6 mm non-plated, long axis towards MH1, 35.9 mm away; 1.1 mm shell pin |
| H1 nut | (23.6, 112.9) | left of USB-C |
| H2, H3 nuts | (28.0, 70.0), (57.1, 69.9) | top edge |

- **Nut**: Sinhoo SMTSO1610MTJ (LCSC C2928167), M1.6, 3.18 mm hex, 1.0 mm above the board, 2.5 mm hole, 4.19 mm
  minimum pad (maker table). The footprint uses a plated 2.5 mm hole and a 4.2 mm GND pad. Whether the maker wants
  the hole plated was not confirmed.
- **Position error at the connectors**: pin-to-hole clearance is 0.1 mm on diameter, so the board can shift about
  ±0.05 mm at MH1 plus the hole and pin tolerances. USB-C is 5.4 mm from the datum and the SD slot about 25 mm, so
  rotation about MH1 adds little (0.05 mm over 35.9 mm is 0.08°, about 0.03 mm at the SD slot).
- **Board changes**: D203 and R208 moved 1.0 mm left (R208 turned 180°), so the LED light hole in the shell is at
  x 20.0. The 3V3 trunk goes round H1. FID3 moved to (54.3, 101.6). CHG_STAT was re-laid by the router.
- **Shell**: two 1.1 mm pins, 0.5 mm above the board top; three 1.8 mm screw holes with a 3.4 × 0.4 mm head recess
  on the back. A boolean check with the board STEP shows no overlap, so the pins line up with the holes.
- **Three screws, not four**: the lower half of the board has no room for a second 4.2 mm pad without moving
  connectors. The bottom-right corner is located by MH2 but not clamped by a screw.

Open points:
- Only 0.4 mm of floor is left under the screw head. It needs thin-head M1.6 screws (about 2.5 mm long under the
  head) and the toolmaker's view on strength; a metal washer plate or a local thicker floor is the fallback.
- No pull-out or torque-out figure was found for this nut size; the maker gives 1.5 kgf·cm tightening torque.
- JLC must confirm it can place this nut on a 0.8 mm board.
- The bottom-right corner should be held down by a rib from the support plate or frame; not designed yet.

## 8. Front-light control pin (2026-11-14)

Found in a netlist review: FL_PWM, the enable / dimming input of the front-light boost U905, was on GPIO0 (U501
pin 5). GPIO0 is the boot strap and has the 10 k pull-up R511, so the boost was enabled whenever the MCU did not
drive the pin: during reset, boot, download mode and any crash. Both LED switches Q901 / Q902 are off in that state
(100 k gate pull-downs), so the boost ran with no load and its output rose to the over-voltage limit. That wastes
battery, and the output then sits close to the ratings of D905 (40 V) and Q901 / Q902 (30 V). The over-voltage limit
of U905 was not checked against its datasheet.

Change (`layout/eco_gpio0.py`, router spec `layout/spec_gpio0.json`):
- FL_PWM moves to GPIO2 (U501 pin 7) with a new 100 k pull-down R515, so the boost is off unless firmware drives it.
- I2S_BCLK takes GPIO0. R511 and TP19 (BOOT) stay on GPIO0. An idle-high clock input does no harm at the amplifier.
- Both nets were laid again by the grid router. Firmware pin map changes: FL_PWM = GPIO2, I2S_BCLK = GPIO0.

## 9. Connectors instead of hand-soldered wires (user, 2026-11-14)

User direction: complete the workmanship; cost is not a concern for now; the battery stays non-removable; the MCU
stays the bare ESP32-S3; certification is handled separately later.

| Ref | Was | Now | Notes |
|---|---|---|---|
| J302 | 3 solder pads at (52.0, 78.8) | JST BM03B-ACHSS-GAN-ETF (LCSC C5118705) at (33.6, 70.05), top edge next to the cell | 1 = B+, 2 = B−, 3 = NTC. Keyed, 1.4 mm high, 2 A per contact with AWG28. Pack lead: ACHR-03V-S housing (C274397). Footprint from the KiCad library; courtyard cut to 0.25 mm in y to fit between the board edge and D905; no silk outline. |
| J507 | coax solder landing | MHF4 receptacle, Kinghelm KH-IPEX4-2020 (LCSC C530666) at (34.3, 90.95) | 1.2 mm mated with a 0.81 mm cable plug. Land pattern drawn from the maker drawing 113-0000-007: check it on the first article. |
| J502 | 2 solder pads | unchanged | No stocked 2-pin header of the same family was found, and soldered speaker leads are normal practice. |

- B+ leaves J302 through two vias onto a 0.8 mm B.Cu track that joins the existing BAT_CONN_P trunk. Keep the
  charge current at or below 2 A (contact rating).
- The old landing pad had joined two BQ_TS tracks; they are now linked directly.
- The pack is fitted at the factory. It is not user-replaceable (see the open point on the EU battery rule below).
- `layout/eco_conn.py`, router spec `layout/spec_conn.json`.

Not added, with reasons:
- **ESD array at the microSD socket**: there is no room for a 2.5 × 1.0 mm array next to the socket pins without
  moving the panel-power capacitors. Test ESD on the first build and add it in a re-spin if needed.
- **Fourth fixing screw**: see §7.

Known and deliberately left open by the user: EU Battery Regulation (EU) 2023/1542 Article 11 asks for
user-replaceable portable batteries from 18 Feb 2027; radio and safety certification; the antenna and pack part
numbers. The antenna must have an MHF4 plug; the narrow FPC antennas found in stock all had the larger MHF1 plug.
