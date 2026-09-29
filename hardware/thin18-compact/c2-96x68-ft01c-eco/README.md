# Thin18 compact C2 — FT01C display ECO

This candidate derives from C1 and remains intentionally unrouted.

Changes:
- target panel contract: GDEQ0426T82-FT01C;
- J802 pin 6: GND -> NC;
- J802 pin 7: GND -> NC;
- no placement coordinates are intentionally changed.

Fresh verification:
- DRC violations: 0
- schematic parity: 0
- ERC: 0
- unconnected: 447 (expected for the unrouted compact candidate)
- netlist delta is restricted to J802 pins 6 and 7.

Touch and front-light connectors/driver are reserved by C2 but are not yet added to this candidate.
This is not a manufacturing release.
