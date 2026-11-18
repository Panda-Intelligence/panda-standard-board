# E14 — v0.2.9: E0470A03 panel on a centred 34-pin connector, two front-light drivers (2026-11-18)

User decision (2026-11-18): the 4.7-inch panel is E0470A03 (8-bit, 34-pin tail); panel supply stays SY7636A; each
front-light string gets its own AW9967 driver. v0.2.9 replaces v0.2.8.

**v0.2.8 must not be ordered.** Its panel connector sits right of USB-C (centre x 50.2). The panel drawings show the
tail on the centre line of the glass (x 32.0), 38 mm long: it cannot reach. This holds for E0470A01 and E0470A03.

Status: `manufacturing_release = false`. Native checks pass (§6). Nothing was ordered, powered or measured.

## 1. Sources

- E0470A03-AF-S specification, 18 pages (maker's document, drawing dated 2026-07-22): pin table §4, electrical data §5,
  mechanical drawing §7.3. Outline 62.00 × 113.45 × 0.79 mm, active area 57.798 × 102.752 mm.
- E0470A01-AF-CF drawing (2026-05-19): 40-pin, 16-bit. Its pin table equals the v0.2.8 J820 map pin by pin, so the old
  map was right; only the position was wrong.
- Reference firmware for E0470A03 (chip maker's SDK, Apache-2.0): 8-bit bus, 24 MHz pixel clock, VCOM −2.10 V with its
  waveform file. Its board uses a non-mainland panel supply and a 0.4 mm-pitch WLCSP front-light driver; neither is
  taken over (0.4 mm ball pitch cannot be fanned out with this board's 0.09 mm rules).
- AW9967DNR datasheet V1.5; XKB X05A10H drawing A1.

Copies are in `.work/ref47/ds/` (outside Git).

## 2. Panel connector

| | v0.2.8 | v0.2.9 |
|---|---|---|
| Panel | E0470A01, 16-bit | E0470A03, 8-bit |
| Connector | X05A10L40G, bottom contact | X05A10H34G (C2880755), contacts on both faces, 1.0 mm high |
| Position | (50.2, 112.4), right of USB-C | (32.0, 76.6), mouth down at y 78.5 |

Pin map (specification §4): 1 VNEG, 2 VGL, 3 VSS, 6 VDD, 7 VSS, 8 XCL, 9 VSS, 10 XLE, 11 XOE, 12 XSTL, 13–20 D0–D7,
21 VCOM, 26 VSS, 27 MODE, 28 CKV, 29 SPV, 31 BORDER, 32 VSS, 33 VPOS, 34 VGH; 4, 5, 22–25, 30 not connected.
Pin 1 is on the left seen from the front.

Why this place: the tail has two single-layer zones (0–5.7 mm and about 23–35 mm from the glass) and a component
zone between them. With the glass edge about 9 mm above the bottom of the body, the tail must fold back in the first
zone and then runs up the component side. Estimated glass edge y 106.5 (from the E07 window position); a fold 4.25 mm
from the glass gives a mouth at y 78.5. A glass edge 2.8 mm higher or lower still folds inside the first zone.

## 3. What had to move

- **3.3 V buck**: re-laid 0.85 mm to the left (U902 at (20.15, 76.6), L401 below it, input capacitor C401 directly
  under the IN pin, output capacitors right of the inductor, feedback parts above). Input loop and switch node are
  hand-laid; the links to the old 3.3 V trunks are router-made.
- **Fuel gauge** U903 with C903 / C304: above the connector at (40.6, 69.45), beside the battery connector. Only its
  sense lines moved; the battery trunk is unchanged.
- **Front light** (§4) to the bottom-right area the old connector left.
- Test pads TP4 (48.3, 69.2), TP5 (43.6, 111.6), TPG2 (22.9, 69.7); fiducial FID3 (43.9, 106.4); R726 (46.0, 109.9).

## 4. Front light

Two identical stages, U905 warm and U906 cool: AW9967DNR (C3098145, DFN-6 2 × 2), 10 µH (the L905 part), 1N5819WS,
4.7 µF / 50 V output, 4.7 µF input, RSET 10 Ω (20 mA per string; 200 mV / RSET). Open-LED limit 36–40 V.
Removed: SGM3732, the dual MOSFET Q901, R601, and the expander enables FL_W_EN / FL_C_EN.

- Warm dimming: FL_PWM on GPIO2 (as before). Cool dimming: FL_C_PWM on GPIO12, pull-down R602. PWM 20–100 kHz.
- J804: 1 warm cathode (FL_W_FB), 2 warm anode (FL_W_P), 5 cool cathode, 6 cool anode. Position and pin order of the
  front-light tail are still unconfirmed (§7).

## 5. Firmware

- Panel bus: D0–D7 on GPIO4–11, XLE GPIO3, XSTL GPIO46, XCL GPIO21 (through R726), CKV / SPV as before, MODE and XOE
  on the expander as before. GPIO13–18 are free; GPIO45 keeps its strap pull-down only.
- Expander pins 6 and 16 are free: drive them low as outputs.
- Never drive a front-light CTRL pin high with no LED string connected (the stage runs into its 38 V limit).

## 6. Checks

KiCad 10.0.7, in `v0.2.9/`: ERC 0. DRC 0 violations, 0 unconnected, 0 schematic parity (`--severity-all`). The
schematic's netlist equals the source netlist (180 nets). Read back from the saved board: all 34 connector pads carry
the nets of §2; U905 / U906 / J804 nets as in §4. 164 placements, 72 BOM lines (v0.2.8: 160 / 74).
The netlists of v0.2.4–v0.2.8, v0.3.0 and v0.3.1 are byte-identical to before.

`v029/build_v029.sh` rebuilds the project from v0.2.8 in one run. New tools: `fix_thermals.py` (solid pour connection
on pads KiCad reports as starved) and `trim_dangling.py` (from v0.3.1).

Tool note: a via written by a script takes the net of copper it touches on another layer when the board is saved.
A ground via for connector pin 32 landed on the back-side battery trunk and became part of it; it now sits under the
connector body. Check every hand via against the back and inner layers.

## 7. Open

1. **Module drawing.** The 4.7-inch module with front light and touch has no drawing here: positions and pin orders
   of the front-light and touch tails, LED count, voltage and current are unknown. J803 / J804 keep their old places.
2. **Glass edge position** is an estimate (§2). Check the fold with the enclosure CAD before ordering.
3. **Tail over parts.** The folded tail lies on the component side from y 78.5 to about 111: its component zone
   (about 26 mm wide) over y 99–107, x 19–45. Parts there are the lower SY7636A stage, USB-C and the MCU corner.
   Heights were not checked against the gap to the panel.
4. **Connector.** Land pattern from the maker's drawing; the mouth is taken to be on the anchor-pad side, as for
   J803 / J804. Confirm with a part. Both contact faces are served, so the tail's contact side does not matter.
5. **Buck.** Re-laid by hand, not measured. Check ripple and the 3.3 V level at the MCU and the microSD socket under
   Wi-Fi load on the first boards.
6. **Front-light stages**: placed compactly, switch nodes hand-laid, not measured. Diode rating 40 V against a
   36–40 V open-LED limit, as before.
7. **Waveform and VCOM.** The reference firmware's waveform needs VCOM −2.10 V; SY7636A sets VCOM over I2C. Not tried.
8. No order pack was made. All open items of E12 §3 (microSD socket) and E09 §3 (consigned SY7636A, CPL angles) apply.
