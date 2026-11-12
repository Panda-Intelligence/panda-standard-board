# Panda Standard 4.7 — main board v0.2.2 / E05

- **Board**: `Panda47-v022.kicad_pcb`. 4 layers, 0.8 mm. 63 × 43 mm with R4 bottom corners and the mid-mount USB-C notch,
  for a 118.3 × 67.0 × 7.3 mm device with R6 corners. See the [E05 note](../E05-V022-PORTS-ROUNDED-20261112.md).
- **Changes from v0.2.1** (same circuit except the two items marked new):
  - Ports: SD slot on the left edge, both keys on the right edge level with it, USB-C still centred.
  - Panel FPC connector J820 moved right of USB-C, under the MCU; touch / front-light FPCs (J803 / J804) moved to the
    bottom left.
  - **New**: WSON-8 flash, GD25Q128EWIGR, 0.8 mm max, instead of the SOP-8.
  - **New**: status LED D203 + R208 on the SGM41513 STAT pin.
  - Printed information on the back silkscreen.
- **Schematic**: `Panda47-v022.kicad_sch` (index) + 9 sheets, generated from the netlist. The netlist is identical to
  the board.
- **Libraries**: `Panda47v2.pretty` is the v0.2.0 set plus `WSON-8-1EP_6x5mm_P1.27mm_EP3.4x4mm` (EP unnumbered,
  floating per GD) and `LED_SideView_TJ-S1706`. Symbols: `Panda7.kicad_sym`.
- **Native checks** (KiCad 10.0.7, in this directory): ERC 0. DRC 0 violations, 0 unconnected, 0 schematic parity
  (`--severity-all`).
- **Status**: `manufacturing_release = false`. Open items:
  - the real cell pack;
  - panel / touch / front-light FPC exits against the supplier drawing (J820 is now assumed right of USB-C);
  - SD socket and USB-C positions against the enclosure openings;
  - the LED lens direction on the first build;
  - SY7636ARMC (U810) consigned;
  - 17 via-in-pad holes need resin fill and a plated cap.

## Build path

Run the scripts in `hardware/pico47/v020/` with `PANDA47_VARIANT=v022` and
`PANDA47_FP_DIR=hardware/pico47/v0.2.2/Panda47v2.pretty`.

1. Generate the anchors and the placement:
   - `make_anchors_v022.py layout/placement_v021.json anchors_v022.json` → `layout/anchors_v022.json`;
   - `place_v020.py` → `layout/placement_v022.json`.
2. `run_v020.sh` with that placement and 50 Freerouting passes (candidate b9, 2 connections left open).
3. `usb_fix_v022.py` applies the hand-laid USB-C D+/D− crossover.
4. `router_v020.py` + `apply_router_v020.py` with `layout/v022_local_spec.json` route FL_C_EN and re-lay the
   expander escapes. Zones are unfilled for the geometry export.
5. Clean-up:
   - `finish_v020.py`, `prune_dangling_v020.py`, `trim_dangling_v020.py`, then `finish_v020.py` again;
   - `silk_v020.py`, then `info_silk_v02x.py` with `layout/v022_silk.json`.
6. Schematic and fields: `build_v020_sch.py`, `sync_board_sch_v020.py`, `set_fields_v020.py`.

Treat this KiCad project as the source of truth for later edits.
