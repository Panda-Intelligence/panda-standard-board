# E13 — v0.3.1: the 4.26-inch board for the module with front light and touch (2026-11-18)

User decision (2026-11-18): the 4.26-inch product uses the panel module with front light and touch. v0.3.0 is resumed
and corrected. v0.3.1 replaces v0.3.0; v0.3.0 must not be ordered.

Status: `manufacturing_release = false`. Native checks pass (§5). Nothing was ordered, powered or measured.
**Do not order before the touch-tail pin order is confirmed (§6 item 1).**

## 1. What v0.3.1 is

The v0.2.8 board (the 4.7-inch board to order) with the display block exchanged for the v0.3.0 one, and the
front-light and touch connectors matched to the module maker's drawing. Built by `v031/build_v031.sh` in one run.

| | v0.3.0 | v0.3.1 |
|---|---|---|
| Base board | v0.2.4 | v0.2.8 |
| Three circuit faults of E09 | present | fixed (gauge TS, C305, R516) |
| microSD socket | 1.85 mm, card 2.1 mm proud | TF-019 1.45 mm, card 0.4 mm inside the outline |
| Front-light connector | pin map reversed, at a place the tail cannot reach | corrected, see §3 |
| Front-light current | 20 mA | 13.3 mA |
| Touch connector | bottom left, tail is on the right | right of the MCU, see §4 |
| Placements / BOM lines | 137 / 67 | 139 / 66 |

Everything of E10–E12 is included: 0603 22 µF and 0805 10 µF capacitors, 1.0 mm nuts, dual MOSFET Q901, C923 0805.
The display circuit (J830, boost stage, GPIO4–9) is the v0.3.0 one; E08 §2–§4 still describe it.

## 2. Source documents

- Module drawing with front light and touch, from the maker's product page: 105.33 × 62.37 mm, 1.98 ± 0.2 mm thick,
  three tails at the bottom edge. Seen from the front: front-light tail 10.0–13.5 mm from the left edge, main tail
  12.5 mm wide with its left edge at 24.85 mm, touch tail 10.0–13.5 mm from the right edge. Both small tails are
  6-pin, 0.5 mm pitch, 3.5 mm wide, pin 1 on the left, 0.3 mm thick at the contacts.
- Front-light specification of the version without touch (drawing dated 2025-09-25): pins 1 C+, 2 C−, 3 NC, 4 NC,
  5 W+, 6 W−; two strings of 5 LEDs, each ≤ 15 V and ≤ 15 mA; tail 24.35 mm long.
- Touch: FT6336U on the tail, 2.8–3.6 V, I2C. **No pin table for the touch tail was found.**

With the panel centred on the USB-C axis (x 32.0), the tails leave the glass at board x 12.57 (front light) and
x 51.44 (touch).

## 3. Front light

- **Pin map.** v0.3.0 had LED+ and LED− exchanged in both pairs and warm / cool exchanged: both strings would have
  been reverse-biased. Now tail pin 1 (C+) and 5 (W+) meet FL_VOUT, pin 2 (C−) meets FL_C_N, pin 6 (W−) meets FL_W_N.
- **Current.** R921 10 Ω → 15 Ω (0402WGF150JTCE, C25083): 0.2 V / 15 Ω = 13.3 mA in total. Drive one string at a
  time or both; the sum stays at 13.3 mA.
- **Position.** A straight fold puts the end of the tail on the microSD socket. J804 therefore sits at
  (12.57, 110.95), turned 180° (mouth up, at y 109.0), and the tail is Z-folded: up over the socket, back down into
  the connector. Connector pin n meets tail pin 7 − n; the net list is written for that.
- C513 (SD supply 10 µF) moved to (6.0, 111.5) to free the place.

## 4. Touch

- J803 at (51.44, 93.45), mouth down at y 95.4, between the MCU and the flash. The tail folds once; its controller
  area and steel stiffener then lie over the flash and the area below it (parts there are ≤ 0.8 mm high).
- Pins: 1 GND, 2 3V3_AON, 3 TOUCH_RST, 4 TOUCH_INT, 5 I2C_SDA, 6 I2C_SCL. This is the order of the labels in the
  maker's interface picture, **not a confirmed pin table** (§6 item 1).
- Moved to make room: flash U506 1.55 mm down; C543 beside flash pin 8 (shorter than before); C523 (100 nF,
  3V3_AON at the MCU) to (49.05, 96.75), now about 5 mm of track from the pin it served; fiducial FID3 to
  (56.0, 104.6).
- Pull-ups R910 / R911 stay at the bottom left; TOUCH_INT / TOUCH_RST run across the board (slow signals).
- Firmware: the 4.7-inch board's touch driver does not apply; FT6336U is at I2C address 0x38.

## 5. Checks

KiCad 10.0.7, in `v0.3.1/`: ERC 0. DRC 0 violations, 0 unconnected, 0 schematic parity (`--severity-all`). The
generated schematic's netlist equals the source netlist (144 nets). Read back from the saved board: J804 / J803 nets
per §3 / §4, R921 15 Ω, U903 pin 9 open, C305 and R516 present, Q902 absent. The netlists of v0.2.4–v0.2.8 and v0.3.0
are byte-identical to before the variant was added.

Tools:
- `v031/prune_stubs.py` now drops duplicate segments first; a doubled segment hid a dead end.
- A second pruning pass over fresh router copper cut a live 3V3_AON T-junction. It is replaced by
  `v031/trim_dangling.py`: removes only what KiCad's DRC reports as dangling and stops if the unconnected count rises.
  It removed the 18-item I2C branch that fed the old display block.

## 6. Open

1. **Touch-tail pin order and contact side.** Get the pin table of the touch tail from the maker (or measure a
   module: pin to the stiffener ground, pins to FT6336U) before ordering boards. A wrong order can put 3.3 V on a
   signal pin. J803 and J804 have contacts on both faces, so the contact side does not matter for them.
2. **Front-light table for the touch version.** The pin table and string data come from the version without touch.
   The product page of the touch version says "7 LEDs, series", which does not agree. Confirm; if the strings differ,
   only R921 changes.
3. **Z-fold over the microSD socket.** Two layers of tail (about 0.25 mm) lie on the 1.45 mm socket. The enclosure
   must leave that height, or the module is ordered with a shorter front-light tail (about 9 mm, straight into J804).
   Tail positions along y depend on where the glass edge sits in the enclosure, which is not designed.
4. **Main 24-pin pinout.** Still from the earlier bare-panel datasheet; the current part's own table was not found.
   J830's land pattern is scaled from the 40-pin part of the same series.
5. **C523 distance** (§4). C501 22 µF and C502 100 nF stay at the MCU supply entry. Watch 3V3 noise on first boards.
6. E08 §6 items 2–7 (tail path over USB-C, rail capacitors 17–19 mm from the pins, capacitance under bias, Q831 pin
   order, RF, enclosure) and E12 §3 (first-article checks of the microSD socket) still apply.
7. No order pack was made.
