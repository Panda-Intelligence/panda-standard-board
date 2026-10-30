# Panda Standard — Single Unified 4-Layer PCB (`v0.1.1` / `R26`)

- **Version Directory**: `hardware/pico47/v0.1.1/`
- **Git Tag**: `0.1.1` / `v0.1.1`
- **Board File**: `Single.kicad_pcb` (`71.0 x 99.0 mm` 4-layer L-step unified board)
- **`Single.kicad_pcb` SHA-256**: `31fa221d8a02a7cb00e9bd00a5d6f7907e60b56903269f803973590a1ed2f7b9`
- **Schematic File**: `Single.kicad_sch` (`9407b9359524ac92e9bdae0a65c94c6cdc74fc348ec47071399f9ec9c6ab3a8b`)
- **KiCad Native Checks**: `0` DRC errors, `0` DRC warnings, `0` unconnected items, `0` schematic parity errors, `0` ERC violations; `173/173` GND pads connected.
- **Key Engineering Changes vs. `v0.1.0` (`R25`)**:
  1. **Zero Battery Interference (`X = 38.0 mm` Step)**: Upper-left PCB step narrowed from `X = 30.0 mm` to `X = 38.0 mm` (`Y = 32.0..83.5 mm`), relocated 51 footprints and re-routed 27 boundary nets (`r25_router/apply_single_r26_x38_eco.py`), achieving `0.0 mm²` XY and `0.0 mm` Z overlap with the full-size `323576` (`35.0 x 76.0 x 3.2 mm`) battery assembly study (including `35.8 x 74.0 mm` foil seal, `18.0 x 1.6 mm` tabs, `30.0 x 3.8 mm` PCM, and `3.7 x 1.5 mm` wire exits).
  2. **Option 1 Upper-Right Support, Acoustic & RF Bay**: Houses `UPPER_RIGHT_RIB_GRID` (`X = 38.5..72.5, Y = 2.5..31.2, Z = 0.55..3.65 mm`), `UPPER_RIGHT_PORON_PAD` (`Z = 3.65..3.95 mm`, coplanar with the `3.95 mm` battery top surface), `SPEAKER_BOX_1511` (`15.0 x 11.0 x 2.90 mm`), and `FPC_ANTENNA_2G4` (`24.0 x 7.0 x 0.20 mm`).
  3. **Via-in-Pad Accounting**: Moved `C804.2` ground return via to an external dog-bone location at `(17.40, 104.80)` (`0.45/0.20 mm`), leaving only `U501.57` (9 thermal vias, `0.50/0.25 mm`) in `REQUIRED-VIA-IN-PAD.csv` (`supplier_process_accepted = false` until factory CAM confirmation).
