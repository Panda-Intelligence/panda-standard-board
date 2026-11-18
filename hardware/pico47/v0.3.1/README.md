# Panda Standard 4.26 — main board v0.3.1 / E13

- **Board**: `Panda426-v031.kicad_pcb`. The v0.2.8 board (63 × 48 mm, 4 layers, 0.8 mm) with the display block
  exchanged for a 4.26" 800 × 480 SPI panel module with front light and touch. See the
  [E13 note](../E13-V031-426-FRONTLIGHT-TOUCH-20261118.md); the display circuit is described in the
  [E08 note](../E08-V030-426-SPI-VARIANT-20261117.md).
- **Replaces v0.3.0**, which had a reversed front-light pin map, both small connectors where the tails cannot reach,
  and the three circuit faults of v0.2.4.
- **Changes from v0.2.8**:
  - Removed: SY7636A block, 16-bit panel bus, 40-pin connector J820.
  - Added: 24-pin connector J830 on the USB-C axis and the panel boost stage (L831, Q831, D831–D833).
  - J804 (front light) at (12.57, 110.95), turned 180°, for a Z-folded tail; R921 15 Ω (13.3 mA).
  - J803 (touch, FT6336U) at (51.44, 93.45); U506, C543, C523, C513 and FID3 moved for the two connectors.
  - Panel signals on GPIO4–9: BUSY, RST, DC, CS, SCK, MOSI.
- **Schematic**: `Panda426-v031.kicad_sch` (index) + sheets, generated from the netlist.
- **Native checks** (KiCad 10.0.7, in this directory): ERC 0. DRC 0 violations, 0 unconnected, 0 schematic parity
  (`--severity-all`).
- **Status**: `manufacturing_release = false`. The touch-tail pin order is not confirmed; open items are in §6 of
  the E13 note. No order pack was made.

## Build path

`../v031/build_v031.sh` rebuilds this directory from `../v0.2.8/` (work files in `.work/v031`):

1. `make_netlist_v020.py` with `PANDA47_VARIANT=v031` → netlist (154 parts including test pads).
2. `v031/eco_strip.py`, `v031/prune_stubs.py`: remove the old display block and its feed branches.
3. `v031/eco_display.py`: J830 and the boost stage with hand copper. `v031/eco_conn.py`: J803, J804 and the parts
   moved for them.
4. Grid router (`router_v020.py` + `apply_router_v020.py`) with `v031/spec_display.json`.
5. `v031/finish_v031.py`, `v031/trim_dangling.py`, `v023/widen_v023.py`, `silk_v020.py`, `info_silk_v02x.py` with
   `v031/v031_silk.json`.
6. `build_v020_sch.py`, `sync_board_sch_v020.py`, `set_fields_v020.py`, then ERC and DRC.
