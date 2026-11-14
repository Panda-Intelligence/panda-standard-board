# Panda Standard 4.7 — main board v0.2.4 / E07

- **Board**: `Panda47-v024.kicad_pcb`. 4 layers, 0.8 mm. 63 × 48 mm with R4 bottom corners, the mid-mount USB-C notch
  and a speaker notch in the top-left corner, for a 67.0 × 133.7 × 7.3 mm device. See the
  [E07 note](../E07-V024-HAND-LAYOUT-SPEAKER-NOTCH-20261113.md).
- **Changes from v0.2.2**:
  - Charger, 3.3 V buck, front-light boost, RF, crystal and the VBUS / battery trunks are laid by hand
    (`../v024/design_v024.py`) and locked before autorouting. Power and HV tracks are widened after routing.
  - Cell protection moved into the pack: U907, R940, C940 and J301 are removed. J302 is a 3-pin header
    (B+ / B− / NTC) for a 3.0 × 57 × 79 mm pack with PCM and NTC.
  - Speaker notch; the audio amplifier and the speaker landing sit next to it.
  - New C817 (4.7 µF, same part as C804): VN reservoir right at the rectifier D802. New C818 (2.2 µF 0402, same
    part as C304): input capacitor at U810 pin 24. C816 dropped. C506 moved to the audio amplifier.
  - Test pads TP5 (FL_VOUT), TP6 (3V3_SD) and TPG2 (GND) added: 18 in total.
  - Connectors: the pack plugs into J302 (JST ACH 3-pin) and the antenna into J507 (MHF4); FL_PWM moved off the
    boot-strap pin (E07 note §8–9).
  - Board fixing: two soldered M1.6 nuts H2 / H3 at the top edge for screws from the back of the shell, two shell
    lips over the bottom edge, and two non-plated locating holes MH1 / MH2 for shell pins (E07 note §7 and §10).
  - Three fiducials. Net classes Power 0.3 mm, HV 0.2 mm, RF 0.17 mm.
- **Schematic**: `Panda47-v024.kicad_sch` (index) + 8 sheets, generated from the netlist. The netlist is identical to
  the board.
- **Libraries**: `Panda47v2.pretty` (the v0.2.2 set; the U901 pin-1 dot is moved). Symbols: `Panda7.kicad_sym`.
- **Native checks** (KiCad 10.0.7, in this directory): ERC 0. DRC 0 violations, 0 unconnected, 0 schematic parity
  (`--severity-all`).
- **Status**: `manufacturing_release = false`. Open items are listed in §6 of the E07 note; the main ones are a
  custom-pack quote for the cell (no datasheet exists for this size) and a speaker sample. 22 via-in-pad holes need
  resin fill and a plated cap. The order pack (153 placements, 72 BOM lines) is outside Git.

## Build path

Scripts are in `../v020/`, `../v023/` and `../v024/`; run them with `PANDA47_VARIANT=v024` and
`PANDA47_FP_DIR=hardware/pico47/v0.2.4/Panda47v2.pretty`. Freerouting is not deterministic, so this KiCad project,
not a replay, is the source of truth.

1. `make_netlist_v020.py` → netlist (174 parts including 18 test pads).
2. `v024/design_v024.py` (hand blocks → `hand.json`), `v024/make_anchors_v024.py`, `v020/place_v020.py`; run the
   three twice so the hand-copper keep-outs reach the placer. Result: `v024/layout/placement_v024.json`.
3. `build_v020_pcb.py`, `v023/precopper_v023.py` (locked hand copper), `gnd_stitch_v020.py`, Freerouting 60 passes.
4. Grid router (`router_v020.py` + `apply_router_v020.py`) with `v024/layout/spec_left.json`,
   `spec_touch_int.json` and `spec_d11.json`, with `eco_touch_int.py` and `eco_d11.py` in between (E07 note §4).
5. `finish_v020.py`, `prune_dangling_v020.py` / `trim_dangling_v020.py`, `v023/widen_v023.py`,
   `v023/fiducials_v023.py`, `silk_v020.py`, `info_silk_v02x.py` with `v024/v024_silk.json`, then
   `v024/layout/eco_final.py`.
6. `v024/layout/eco_vp.py`, `eco_pmic.py` (adds C817), the grid router with `spec_pmic.json`, prune / trim, widen
   and `silk_v020.py` again (E07 note §4 steps 9–10). The ECO scripts use `layout/ecolib.py`.
   Then `eco_cin.py` (C818, L802, C506) with `spec_cin.json`, `eco_tp.py` and `eco_tp_silk.py` (steps 11–12).
7. `build_v020_sch.py`, `sync_board_sch_v020.py`, `set_fields_v020.py`; `export_orderpack_v020.py` for the order pack.
