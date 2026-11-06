# Panda Standard — Single 4-Layer PCB (`v0.1.2` / `R49`)

- **Board**: `Single.kicad_pcb`, 71.0 × 99.0 mm L-step four-layer board, R49 (= R48 layout + front-light supply fix).
- **Schematic**: `Single.kicad_sch` (index page) + 11 A4/A3 sheets `Single-*.kicad_sch`, drawn in the usual style (see below). Same 265 parts, pins and 255 nets as the R49 netlist-style source.
- **Native checks** (KiCad 10.0.7, this directory alone): DRC 0 errors / 0 warnings / 0 unconnected / 0 schematic parity, ERC 0.
- **Rebuild**: `python3 build_pico47_single_r49.py --output <new dir under .work>` (KiCad Python) replays R26 → R48 → R49, writes this schematic and the JLC order pack; `--netlist-style-schematic` keeps the one-label-per-pin form.
- **Status**: `manufacturing_release = false`. Ordering prerequisites are listed in [R49 note](../E02-R49-FRONTLIGHT-SUPPLY-20261106.md) (46 Type VII via-in-pad CAM confirmation, 21 pending SMT parts, BT301 post-SMT).

## Changes vs. `v0.1.1`

1. R27–R48 layout revisions (see `../E02-R27-LAYOUT-FIXES-20261031.md` … `../E02-R48-XSTL-AND-CKV-BRIDGES-20261103.md`).
2. R49: the front-light boost input `VSYS_FL_IN` (L905 / R920 / C920) had no supply after the board merge; it now joins `VSYS_RAW` via a 0.40 mm, 29 mm link.
3. The schematic is redrawn by `../readable_schematic.py` as a hierarchical design:

| Sheet | Content |
|---|---|
| `USB_Input` | J201 USB-C, CC resistors, D201 / D202 ESD |
| `Battery_RTC` | J301 / J302 battery landings, R306 sense, U302 SD3078 RTC, BT301 |
| `Load_Switches` | U402–U405 SGM2578 rails |
| `MCU_1`, `MCU_2` | U501 ESP32-S3 with straps and bypass, U503 IMU, series resistors; U506 Flash, J501 microSD, J503 debug, Y501 |
| `IO_Expander` | U601 XL9535 and its pull resistors |
| `Panel_SD_Mux` | U710 / U711 SGM330A and their series resistors |
| `EPD_PMIC_1`, `EPD_PMIC_2` | U810 SY7636A, U811 expander, rectifiers; J820 panel, J803 touch, J804 front light, D803 / D804 charge pumps |
| `Charger_Power_1`, `_2` | U901 charger, U902 buck-boost, U903 gauge, U904 audio, U905 front light; U906 reset, U907 protection, Q907 / Q908 |

ICs and connectors are boxes with supply pins on top, ground pins at the bottom and signal pins on both sides; resistors, capacitors, inductors, diodes, the crystal, MOSFETs, buttons, the coin cell and test points use the KiCad standard-library drawings. A part with one end on ground or a supply hangs off the pin it serves (the owner is the nearest same-net pin on the PCB); decoupling groups share a supply bar; series parts sit in a column with a label at each end. Connections between parts are global labels, supplies are power symbols, unused pins carry a no-connect flag. Two power flags (`3V3_TOUCH`, `3V3_EPD_LOGIC`) are schematic-only ERC drivers.

The visible `Spec` field shows the part of `Value` before “/” (for example `100nF 25V X7R`); the full `Value` is unchanged and hidden. `Spec` is also on every footprint as a hidden Fab-layer field so the schematic-parity check stays at zero; copper, pads, positions and the Gerbers are unchanged. The build aborts if the regenerated netlist differs in any pin set or net name.

## Importing into EasyEDA Pro (嘉立创EDA专业版)

Import the project zip (all files at its root) with *File → Import → KiCad*. EasyEDA Pro documents KiCad import for versions below 10.0. The schematic files are written in the KiCad 9 format (`20250114`); the board is KiCad 10 (`20260206`), so the board import may be refused; copper zones are always rebuilt on import and must be re-checked. Fabrication itself only needs the Gerber / BOM / CPL from the order pack.
