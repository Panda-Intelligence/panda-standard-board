# Panda Standard — Single 4-Layer PCB (`v0.1.3` / `R50`)

- **Board**: `Single.kicad_pcb`, 71.0 × 99.0 mm L-step four-layer board, R50 = R49 + JLC-stock BOM, TI TPS651851 EPD PMIC and AWINIC AW99703 front-light driver. See [R50 note](../E02-R50-JLC-STOCK-PMIC-FRONTLIGHT-20261108.md).
- **Schematic**: `Single.kicad_sch` (index page) + 11 sheets `Single-*.kicad_sch`, same style as `v0.1.2`. Netlist identical to the board.
- **Native checks** (KiCad 10.0.7, this directory alone): DRC 0 errors / 0 warnings / 0 unconnected / 0 schematic parity, ERC 0.
- **Rebuild**: `python3 build_pico47_single_r50.py --output <new dir under .work>` (KiCad Python) replays R26 → R48 → R49 → R50 and writes this project plus the JLC order pack.
- **BOM**: 224 placed SMT lines, all with a JLC part number in stock on 2026-11-08 except U902 (SGM62125AXG/TR, consigned). R805 and C922 are DNP. BT301 is fitted after SMT.
- **Status**: `manufacturing_release = false`. Before ordering: written CAM confirmation for the 45 via-in-pad holes (resin filled and copper capped, including the 0.25/0.15 mm U905.B2 via), U902 consignment, and a stock re-check (D201 and AW99703 stocks are small).

## Changes vs. `v0.1.2`

| Area | Change |
|---|---|
| U810 | SY7636ARMC → TI TPS651851RSLR on the same 6 × 6 QFN-48 land; thermal pad on VN; WAKEUP from U811 P04; DGND, VCOM_PWR, PBKG, VEE_IN, VDDH_IN, VPOS_IN wired |
| PMIC passives | C807/C810 100 nF, C808/C811 10 nF, C815 4.7 µF, R804 39.2 k to GND, R806 43 k, R805 DNP, R801–R804 1 %, L801 2.2 µH, L802 1.5 mm part |
| U905 | SGM37601 → AWINIC AW99703CSR WLCSP-12 (LM3697-compatible), C922 DNP |
| Stock swaps | 10 k ×16, 1 µF 0402 ×4, 10 µF 0805 ×4, D202, U402–U405, U906, U907, J201, TH801 |
| Height | L401/L402 2.0 → 1.2 mm, L802 1.8 → 1.5 mm |
