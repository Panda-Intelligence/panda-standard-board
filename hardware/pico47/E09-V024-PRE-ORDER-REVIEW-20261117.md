# E09 — v0.2.4 pre-order review, electrical and production (2026-11-17)

Scope: the 4.7-inch board `v0.2.4/Panda47-v024.*` as committed (bb65f20) and the order pack generated from it.
Method: netlist read pin by pin against the makers' datasheets where one could be fetched; native checks re-run;
fabrication limits, live JLC stock and the order pack compared with the board. Nothing was built or measured.

**Verdict: do not order v0.2.4.** Three circuit faults were found (§1). They are fixed in v0.2.5 (§4), which is the
board to order. The v0.2.4 files themselves are consistent and inside JLC's limits (§3).

## 1. Circuit faults

| # | Fault | Effect | Fix |
|---|---|---|---|
| 1 | The pack NTC (BQ_TS) goes to both the charger U901 TS and the fuel gauge U903 TS. The gauge's TS pin has its own pull-up driver (datasheet: "driving circuits (internal pull-up) are integrated"). | Two bias networks on one thermistor. The charger's hot / cold thresholds shift. Without USB the charger's divider (5.23 k + 30.1 k to ground) loads the NTC, so the gauge reads far too hot. | Disconnect U903 pin 9 from BQ_TS and select host-reported temperature in the gauge profile. The charger keeps the NTC and its hardware thresholds. |
| 2 | The RTC crystal Y301 has no capacitor on OSCI. BM8563 has one integrated capacitor (OSCO, 25 pF typ.) and its datasheet requires an external 5–25 pF on OSCI; the load is the two in series. | Y301 is a 12.5 pF crystal and sees about 2–3 pF. Estimated error: a few hundred ppm fast (tens of seconds per day). Estimate from typical 3215 crystal data, not measured. | Add 22 pF C0G 0402 (same part as C404) from RTC_OSCI to ground. |
| 3 | AUDIO_EN (U601 P06 to U904 CTRL) has no pull-down. Every other expander output has one. XL9535 pins are high-impedance inputs after power-on (datasheet §9.4). | The amplifier enable floats from power-on until firmware configures the expander, and whenever the MCU is in reset or download mode: possible 13 mA idle draw and a click. No damage. | Add 100 k 0402 (same part as R604) from AUDIO_EN to ground. |

## 2. Checked and found correct

Pin maps against datasheets: SGM41513 (charger), CW2217BAAD (pinout and high-side shunt polarity), NS4168, SGM3732,
SC7A20H, BM8563, XL9535 QFN-24, USB-C socket (land pattern, slots and 9.24 mm cut-out per the MUP drawing).

Circuit: charger support parts and thermistor network (5.23 k / 30.1 k), PSEL divider (500 mA input limit until
firmware raises it), 3.3 V buck divider (3.31 V), ESP32-S3R8 supplies, straps (GPIO0 up, GPIO3 / 45 / 46 down),
CHIP_PU RC, 40 MHz crystal load, flash on VDD_SPI, USB D+ / D− to GPIO20 / 19, CC resistors, microSD 1-bit wiring,
expander interrupt wake path, status LED.

Not checkable here:
- **SY7636A (U810)**: no datasheet could be fetched; the circuit is the one carried over from the R49 design.
- **J820 / J803 / J804 pin maps and poses**: still not confirmed against a panel-module drawing (open since E03).

## 3. Production

- Native checks re-run on a copy: ERC 0, DRC 0, 0 unconnected, 0 parity.
- The order pack in `.work/panda47-v0.2.4-deliverable/orderpack` equals a fresh export from the board: BOM, CPL,
  via-in-pad list and every Gerber file are identical.
- Fabrication: 4 layers, 0.8 mm, min track 0.095 mm, min space 0.127 mm, vias 0.3 / 0.55 mm (416) and 0.3 / 0.6 mm
  (23), top-side assembly only. Inside JLC's standard 4-layer limits. 22 vias in pads need resin fill and a plated cap.
- JLC stock read 2026-11-17, 75 lines: every code exists and matches its MPN. 15 basic, 60 extended.

| Part | Stock | Note |
|---|---|---|
| U810 SY7636ARMC | 0 | Consigned: must be bought and delivered to JLC before assembly. |
| J201 U22401-23 (USB-C) | 139 | Enough for a prototype run only. |
| J302 WAFER-ACH1.2-3PWB | 400 | |
| J501 TF-122-CCP9 | 996 | |
| all other lines | > 1100 | |

Order-time risks:
- **Placement rotation.** The CPL carries KiCad angles with no per-package correction for JLC's library. Order with
  "confirm parts placement" and check every IC, diode, transistor, connector and the side-view LED in the preview.
- **SMT nuts H2 / H3** on a 0.8 mm board and the mid-mount USB-C: ask JLC to confirm both in the order remarks.

## 4. v0.2.5: the fixes (done 2026-11-17, user go-ahead)

Project `v0.2.5/Panda47-v025.*`, built from v0.2.4 by `v025/build_v025.sh`.

- Fault 1: U903 pin 9 has no net; its BQ_TS branch (9 copper items) is removed. BQ_TS still joins U901 pin 11,
  R615, R616 and J302 pin 3.
- Fault 2: C305 (22 pF) at (46.4, 71.3), the nearest free 0402 position (`v025/spot_0402.py`). RTC_OSCI grew from
  2.5 mm to about 6.5 mm with two vias; the branch to C305 runs on In2 over the ground plane. Its stray capacitance
  adds to the 22 pF. Check the 32.768 kHz frequency on CLKOUT on the first boards and adjust C305 if needed.
- Fault 3: R516 (100 k) at (2.3, 90.1).
- No existing part moved and no other pad changed net (compared item by item). +2 placements, no new BOM line.
- Checks: ERC 0, DRC 0, 0 unconnected, 0 parity. Order pack regenerated: 160 placements, 75 BOM lines, 444 vias,
  22 via-in-pad; against the v0.2.4 pack only the C305 and R516 lines differ.

## 5. Notes for firmware and first boards (no board change)

- SGM41513's I2C address is 0x1A (datasheet). E03 lists 0x6B; that line is wrong.
- NS4168 logic-high threshold is 0.7 × VDD and VDD is VSYS (up to about 4.4 V), so 3.3 V I2S levels are below the
  datasheet minimum when VSYS is above about 3.8 V. Common practice works at 5 V; check audio at full charge.
- Front-light boost: the over-voltage limit is 35.5–40.5 V; D905 is rated 40 V and Q901 / Q902 30 V. Never enable the
  boost with both LED switches off.
- GPIO43 carries boot-ROM UART output into the amplifier data pin, and GPIO44 (SD_D0) is pulled to the switched SD rail.
  Harmless; drive the SD lines low before switching the card off.
- With USB connected, the reset key (charger QON) cannot power-cycle a hung MCU; unplug first.
- v0.3.0 (4.26-inch board) was derived from v0.2.4 and has the same three faults.

## 6. Still open from E07, unchanged by this review

Panel connector pin maps and poses; cell pack and its lead pin order (J302: 1 B+, 2 B−, 3 NTC); speaker sample;
microSD socket sticks into the shell wall; antenna with an MHF4 plug; certification.
