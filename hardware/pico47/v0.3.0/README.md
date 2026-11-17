# Panda Standard 4.26 — main board v0.3.0 / E08

- **Board**: `Panda426-v030.kicad_pcb`. The v0.2.4 board (63 × 48 mm, 4 layers, 0.8 mm) with the display block
  exchanged for a 4.26" 800 × 480 SPI panel. See the [E08 note](../E08-V030-426-SPI-VARIANT-20261117.md).
- **Changes from v0.2.4**:
  - Removed: SY7636A block, 16-bit panel bus, 40-pin connector J820 (45 parts).
  - Added: 24-pin connector J830 on the USB-C axis and the panel boost stage L831 / Q831 / D831–D833 with its
    capacitors (18 parts).
  - C524, R510, C510 (now 0402), C209 (now 0402) and TP6 moved to clear J830.
  - Panel signals on GPIO4–9: BUSY, RST, DC, CS, SCK, MOSI.
  - Everything else, including all hand-laid power, RF and crystal copper, is the v0.2.4 layout.
- **Schematic**: `Panda426-v030.kicad_sch` (index) + 8 sheets, generated from the netlist.
- **Libraries**: `Panda47v2.pretty` (the v0.2.4 set plus `FPC_XKB_X05A10L24G`, `SOT-323_SC-70`,
  `R_0603_1608Metric`). Symbols: `Panda7.kicad_sym`.
- **Native checks** (KiCad 10.0.7, in this directory): ERC 0. DRC 0 violations, 0 unconnected, 0 schematic parity
  (`--severity-all`).
- **Status**: `manufacturing_release = false`. The panel module with front light and touch is not confirmed against
  a supplier drawing; open items are in §6 of the E08 note. No order pack was made.

## Build path

`../v030/build_v030.sh` rebuilds this directory from `../v0.2.4/` (work files in `.work/v030`):

1. `make_netlist_v020.py` with `PANDA47_VARIANT=v030` → netlist (153 parts including 15 test pads).
2. `v030/eco_strip.py`, `v030/prune_stubs.py`: remove the old display block and its feed branches.
3. `v030/eco_display.py`: place J830 and the boost stage with hand copper; `prune_stubs.py` again.
4. Grid router (`router_v020.py` + `apply_router_v020.py`) with `v030/spec_display.json`.
5. `v030/finish_v030.py`, `prune_stubs.py`, `v023/widen_v023.py`, `silk_v020.py`, `info_silk_v02x.py` with
   `v030/v030_silk.json`.
6. `build_v020_sch.py`, `sync_board_sch_v020.py`, `set_fields_v020.py`, then ERC and DRC.
