# Thin18 Compact C4A — XL9535 domestic GPIO expander

U601 is changed from TI TCA9535PWR to mainland XINLUDA XL9535 / LCSC C561273 while preserving the existing TSSOP-24 copper, pose and all nets.

Fresh checks: DRC 0; parity 0; ERC 0; open 447 (expected because compact is intentionally unrouted).
203 refs and 601 pin/net tuples are unchanged.

Firmware register/reset/interrupt regression and physical EVT remain open. Not a manufacturing release.
