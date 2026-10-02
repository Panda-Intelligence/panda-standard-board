# Thin18 Compact EVT

## Current authoritative state — Split-C1 (2026-10-02)

The current PCB authorities are core-c1-96x68-split and
display-c1-45x36-production-bom. The Core is 96 x 68 mm / four copper layers;
Display is 45 x 36 mm / two layers. Both boards are 0.8 mm thick and pass
native KiCad DRC/open/parity/ERC = 0/0/0/0.

Run `python3 hardware/thin18-compact/release_split_c1.py` to generate local
production/core-c1-96x68 and production/display-c1-45x36 packages, with
production/split-c1-release.json as their combined hash-checked record.
Generated packages are ignored; the committed authorities are native CAD,
required libraries, replay scripts, purchasing evidence and audit summaries. Every populated BOM ref has Manufacturer and exact MPN.
Current all-domestic audit:155/155 populated system-BOM refs,0 foreign/unknown.
Core has116 SMT placements plus hand-solder C301 and offboard TH301;Display37.
Last foreign refs now use WAVE SD3078/C916255,KAMCAP SE-5R5-D105VYH3C/C2894294
and JSM NX3008NBK,215-JSM/C53113911. Symbols,primary/derived lands and copper
are replayed from guarded source ECOs. R303/R304 are removed.

Exact SMT library coverage:Core110/116,Display37/37. Six Core refs
(U902,U905,U402-U405) still require exact JLC ID/consignment acceptance.
C301 exact current H3C catalog/drawing verified;quantity unverified. D202 observation0;no reserved/accepted supply.
audit_split_c1_domestic.py --require-complete passes identity coverage;
PCBA supply/order readiness remains false.

See SPLIT-C1-DOMESTICIZATION.md and JLC-PROTOTYPE-HANDOFF.md for current
decisions. RTC >=24h isolated backup is a pending prototype validation,
with a2uA total-node engineering target and measured start>=3.15V/end>=2.3V.
Firmware port is required;Q04-Q14 remainNOT_RUN because no board exists.
The two-board side-pack space study is112x75x21mm,calculated thickness20.5mm;pack complete max input
54x36x5.5mm. No exact pack/enclosure is frozen or physical fit claimed.
X4 Pro1100mAh/5.95mm remains a reference. Manufacturing release remains false.
Older C0/C2/C4D notes below are historical and do not override Split-C1.


Thin18 Compact is an architecture fork of the validated `thin18/routing142` baseline.

## Goal

Reduce the main PCB below the JLC 100 × 100 mm coupon boundary while making the product materially shorter, without changing the electrical feature set.

C0 target:

- PCB: **70 × 64 mm** placement-feasibility candidate
- hard coupon boundary: every PCB side < 100 mm
- layers: 4
- thickness: 0.8 mm
- finish target: ENIG
- production solder mask target: green
- display architecture: raw 4.26-inch SSD1677 panel through 24-pin / 0.5-mm FPC
- display candidate family: Good Display GDEY0426T82; front-light/touch derivatives require separate stack-up and pin/FPC qualification
- screen, battery and PCB are separate mechanical objects; the PCB no longer follows the panel length

## C0 fold strategy

The routing142 placement already has two dense functional regions:

- y < 31 mm: power, battery/gauge/RTC, audio, microSD, switches
- y > 100 mm: USB-C, ESP32, display power/FPC, protection

Only five footprints occupy the 30–100 mm middle band, two of which are mounting holes. C0 folds the upper region down by 64 mm, keeps the lower region, relocates mounting holes, reduces the board outline to 70 × 64 mm, and intentionally removes all legacy tracks/vias/zones.

This candidate is **placement-only and NOT routed**. routing142 remains the authority for the old form factor.

## Gates before routing

1. no footprint/edge impossibility after connector-specific edge allowances;
2. no unintended footprint overlap;
3. schematic population and pin/net parity unchanged;
4. ERC remains zero;
5. battery/display/enclosure Z-stack is frozen;
6. exact display FPC pinout and front-light/touch variant are frozen;
7. USB-C, microSD, side switches, display FPC and antenna cable exits are mechanically frozen.

Do not fabricate the C0 board.
精确供料跟进：SPLIT-C1-SUPPLY-REQUEST.md、split-c1-supply-plan.json。verify_split_c1_supply.py核对本次8个位号的精确身份、实际回执／数量和C301独立后装路线；不把公开库存或采购准备当作完整PCBA接收。
