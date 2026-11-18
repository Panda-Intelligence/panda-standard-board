# E12 — v0.2.8: microSD socket set back so a latched card stays inside the body (2026-11-17)

User decision (2026-11-17): a card standing 1.3 mm out of the body (v0.2.7) is not acceptable. v0.2.8 is built from
v0.2.6 and supersedes v0.2.7: the same Hanbo TF-019 socket (1.45 mm, push-push) and the 0805 front-light capacitor,
with the socket 1.66 mm further in.

## 1. Geometry

| | v0.2.6 (TF-122) | v0.2.7 | v0.2.8 |
|---|---|---|---|
| Socket body front, board x | about −1.3 | −0.36 | **1.30** (0.8 mm inside the board edge at 0.5) |
| Latched card end (2.40 mm in front of the body) | 2.1 mm outside the body | 1.3 mm outside | **0.4 mm inside** the 67 mm body outline (x −1.5) |
| Card pushed in to release (1.50 mm in front of the body) | — | — | 1.3 mm inside the outline: the shell needs a finger or nail recess at the slot |
| Ejected card (6.20 mm in front of the body) | — | — | 3.4 mm outside the outline |

Card centre line unchanged at board y 99.25. Positions from the Hanbo drawing; no sample was measured, and the shell
was not changed (enclosure CAD is outside Git).

## 2. What moved

The socket's rear pads now reach x 16.5. The footprint courtyard follows the body and the rear pads instead of one
rectangle, so only parts in the way of real metal move:

| Part | Change | Reason |
|---|---|---|
| R524 (SD_D0 pull-up) | 0.15 mm up | socket corner |
| TH801 (panel NTC) | 0.45 mm up | rear hold-down pad |
| C806 (VNEG output capacitor) | 0.8 mm down | rear hold-down pad |
| R809 (VCOM_EN pull-down) | 0.2 mm down | follows C806 |
| C513 (SD supply 10 µF) | to (11.5, 109.0), below the socket | rear hold-down pad |
| Q901, Q902 (front-light string switches, two SOT-23) | one dual N-MOSFET Q901, LRC LBSS138DW1T1G (C525406, SOT-363) at (19.9, 108.9) | the corner hold-down pad lands on the old Q901 |

- **Dual MOSFET**: same function (warm string on FL_W_EN, cool string on FL_C_EN, common source to FL_FB), one part
  fewer. 50 V rating instead of 30 V, which also covers the boost's 35.5–40.5 V over-voltage limit noted in E09 §5.
  Threshold 1.5 V max (catalogue); on-resistance at 3.3 V gate drive and 20 mA was not checked against the LRC
  datasheet. Pin order used: 1 S1, 2 G1, 3 D2, 4 S2, 5 G2, 6 D1.
- **Vias under the new pads** (TOUCH_INT, I2C_SDA, FL_W_EN, P47_VCOM_EN) and the tracks of the moved parts were laid
  again by the grid router (`v028/spec_flush.json`), with the SD nets. Nets with any copper change: the eight SD
  nets, P47_TS, P47_VNEG, P47_VCOM_EN, TOUCH_INT, I2C_SDA, the five front-light switch nets, FL_VOUT (C923) and GND.
  Nothing else changed (compared item by item with v0.2.6).
- SD_CLK 56.2 mm / 4 vias, SD_CMD 54.9 mm / 6 vias, SD_D0 53.7 mm / 3 vias (v0.2.6: 49.1 / 47.2 / 44.7 mm, 3 vias).
- P47_VNEG to C806 was re-laid and widened again (0.1–0.3 mm, 58.8 mm in total as before).
- TH801 pad 2 and one socket shell pad have a solid connection to the ground pour: the pour reached them with one
  thermal spoke and no ground via could be placed next to them.

## 3. Checks

KiCad 10.0.7, `v0.2.8/`: ERC 0, DRC 0, 0 unconnected, 0 parity. Order pack: 159 placements, 73 BOM lines, 456 vias,
23 via-in-pad. Cost against v0.2.6: about +$0.11 per board (socket +0.12, C923 +0.01, one dual MOSFET −0.02).
Part ceiling about 1.5 mm, as in v0.2.7.

To check on the first boards, in this order:
1. TF-019 land pattern and pin order with a card (the drawing prints no terminal numbers on the pattern; E11 §1).
2. Card latch, release and detect through the real shell slot; depth of the finger recess.
3. Front light on both strings with the dual MOSFET; FL_FB regulation.
4. Panel −15 V rail ripple (C806 moved 0.8 mm), panel temperature reading (TH801), touch interrupt and I2C.
5. SD at the intended clock rate.

## 4. Tool notes

- `v028/gndvia.py`: the link track of an automatic ground via is now also checked against vias on its way (it was
  only checked against tracks and pads, and produced two shorts that DRC caught).
- `v028/build_v028.sh` stops at the first failing step (`pipefail`) and starts from an empty work directory; an
  earlier run had continued with a stale intermediate board after a failed step.
- `readable_schematic.py` draws a transistor with other than three pins as a generic symbol.
