# Pico47 E0.2 r13-vcom — four-layer routing continuation

2026-10-17 续作更新：当前具名检查点为
[r14-audio-enable](E02-R14-AUDIO-ENABLE-CLOSURE-20261017.md)，Core23/Display3。
以下保留r13的历史验证记录。

2026-10-17. Author: Codex. **27 native unconnected items remain.**
**NOT FOR FABRICATION OR PANEL/BATTERY POWER.**

Continue from the accepted r12 descendant:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261017-r13-vcom/engineering-candidate`.
The original dated r12 is preserved. This checkpoint changes copper only;
source parts, pads, placement, outline, stackup and native rules are unchanged.

| Board | Opens | DRC errors | Warnings | Parity | ERC |
| --- | ---: | ---: | ---: | ---: | ---: |
| Core | 24 | 0 | 0 | 0 | 0 |
| Display | 3 | 0 | 0 | 0 | 0 |

VCOM now connects U810.15, C813.1, TP805.1 and J820.10. Coordinated SPV
connector copper retains SPV connectivity. The source-hash-bound transaction
replaces 14 SPV primitives and adds 121 primitives. VCOM's main trace is
0.30 mm; its connector neck is 0.20 mm wide and 0.830789 mm long. New vias
are ordinary 0.60/0.30 mm through vias. There is no new via-in-pad process.
An independent native audit proves all 4,682 non-VCOM/SPV copper items identical.

The original native transaction, full capture, clean source rebuild and
independent recapture all passed. Every old physical pad group is preserved;
Display groups merge from 94 to 93. All 169 Core and 68 Display ground pads
and all eight named targets retain reference connectivity. GPIO2 direct inhibit,
four Core panel controls, negative PMIC EP isolation, prescribed C804 return,
four layers and no In1 signal tracks remain required and verified.

Evidence is in `.work/pico47-fourlayer-resume-20261017/`:
`display-vcom-native`, `vcom-complete-ground-capture`, `vcom-source-rebuild`,
`vcom-roundtrip-proof`, `VCOM-SPV-PLAN.json`, and
`VCOM-INDEPENDENT-COPPER-AUDIT.json`. The external package includes the exact
plan, audit and `PUBLICATION-VERIFICATION.json`; all 299 candidate files were
byte-verified after copying. Do not run a netlist-exporting inspector in the
published package; use a fresh copy.

Rebuild using `build_pico47.py --routing-checkpoint <r13-vcom candidate>` and
capture with `capture_pico47_checkpoint.py --require-complete-ground`.
The donor remains `.work/seven-mm-catalog-20261012/default-rebuild`.

Display still needs SDA, VP and VPOS. Core's 24 opens remain unchanged.
The bounded five-net Core Freerouting trial in `five-net-router` terminated
with a session but supplied no D1 route; D8/D15 contained 0.09/0.1124 mm
tracks. It is rejected, including its partial replacement plan. Do not adopt
it or mistake its model counts for native board counts.

This is a verified routing increment, not completed routing, timing/current,
analog-feedback, exact battery/full-panel, <=7 mm fit or physical EVT acceptance.
Manufacturing and physical qualification remain false. Generated CAD/reports
remain external or ignored; packaging and unrelated worktrees are untouched.
