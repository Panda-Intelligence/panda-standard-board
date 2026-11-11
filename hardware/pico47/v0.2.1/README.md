# Panda Standard 4.7 — rectangular board (`v0.2.1` / `E04`)

- **Board**: `Panda47-v021.kicad_pcb`. 4 layers, 0.8 mm thick, 63 × 42 mm rectangle with a mid-mount USB-C notch, placed below a 3.2 × 50 × 70 mm cell in a 117.5 × 66.2 × 7.3 mm device. See the [E04 note](../E04-V021-RECTANGULAR-BOARD-20261111.md).
- **Reference**: `../v0.2.0/` (L-shaped E03 board) has the same netlist, BOM, footprints and rules.
- **Schematic**: `Panda47-v021.kicad_sch` (index) plus 9 sheets. The netlist is identical to the board.
- **Libraries**: `Panda47v2.pretty` (the DFM-fixed footprints from v0.2.0) and `Panda7.kicad_sym`.
- **Native checks** (KiCad 10.0.7, run in this directory alone): ERC 0; DRC 0 violations, 0 unconnected, 0 schematic parity errors.
- **Status**: `manufacturing_release = false`. Open before ordering:
  - the real cell pack;
  - enclosure key positions (buttons now at y 76.4 / 84.6);
  - the panel, touch and front-light FPC poses against the supplier drawing;
  - SY7636ARMC (U810) is consigned;
  - 17 exposed-pad vias need resin fill and a plated cap.

## Build path

Run the scripts in `hardware/pico47/v020/` with `PANDA47_VARIANT=v021`:

1. `place_v020.py` with `layout/anchors_v021.json` → `placement_v021.json`.
2. `run_v020.sh` with `PANDA47_FP_DIR=hardware/pico47/v0.2.0/Panda47v2.pretty`: board build, GND stitching, 40 Freerouting passes, then DRC.
3. `finish_v020.py`, then local fixes:
   - `router_v020.py` + `apply_router_v020.py` with `layout/v021_local_spec.json`;
   - `prune_dangling_v020.py` and `trim_dangling_v020.py`;
   - `apply_router_v020.py` with `layout/v021_dead_branches.json`;
   - `silk_v020.py`.
4. `build_v020_sch.py`, `sync_board_sch_v020.py`, `set_fields_v020.py` (schematic and parity).
5. `export_orderpack_v020.py`: Gerber and drill zip, BOM, CPL, via-in-pad and consign lists (written outside Git).

Treat this KiCad project as the source of truth for later edits.
