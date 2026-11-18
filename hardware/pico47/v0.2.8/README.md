# Panda Standard 4.7 — main board v0.2.8 / E12

- **Board**: `Panda47-v028.kicad_pcb`. v0.2.6 with a recessed 1.45 mm microSD socket; see the
  [E12 note](../E12-V028-RECESSED-SD-SOCKET-20261117.md) and, for the socket itself, the
  [E11 note](../E11-V027-LOW-SD-SOCKET-20261117.md). It supersedes v0.2.7. Circuit and open items as in
  [v0.2.5](../v0.2.5/README.md) and [v0.2.6](../v0.2.6/README.md).
- **Changes from v0.2.6**:
  - J501: Hanbo TF-019, push-push, body front at x 1.30: a latched card ends 0.4 mm inside the body outline.
  - Q901 + Q902 → one dual N-MOSFET Q901 (LBSS138DW1T1G, SOT-363, 50 V).
  - C923: 0805. R524, TH801, C806, R809 shifted by 0.15–0.8 mm; C513 moved below the socket.
  - SD nets and the nets of the moved parts laid again; nothing else changed.
- **Native checks** (KiCad 10.0.7, in this directory): ERC 0. DRC 0 violations, 0 unconnected, 0 schematic parity.
- **Order pack** (outside Git, `.work/panda47-v0.2.8-deliverable/`): 159 placements, 73 BOM lines, U810 consigned.
- **Status**: `manufacturing_release = false`. First-article checks are listed in E12 §3; the shell slot and finger
  recess have to be redrawn for the new card position.

## Build path

`../v028/build_v028.sh` rebuilds this directory from `../v0.2.6/`: `make_netlist_v020.py` with
`PANDA47_VARIANT=v028`, `v028/eco_flush.py`, the grid router with `v028/spec_flush.json`, `v028/eco_gnd.py`,
`v028/prune_stubs.py`, `v023/widen_v023.py` for 3V3_SD and P47_VNEG only, the silkscreen scripts with
`v028/v028_silk.json`, then the schematic, parity sync, fields, ERC and DRC.
