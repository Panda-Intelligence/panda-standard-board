# E0.2 R50 — BOM cost-down and unit cost estimate (2026-11-08)

Prices are JLC parts API tiers read on 2026-11-08 (USD). Panel, battery, PCB fabrication and packaging are estimates, not quotes; each needs a supplier quote before a business decision.

## 1. Ten most expensive BOM lines (per board, 100-board tier)

| # | Ref | Part | $/board | Decision |
|---|---|---|---|---|
| 1 | U501 | ESP32-S3R8 | 2.28 | Keep. 8 MB PSRAM and the QFN are part of the platform. |
| 2 | U810 | TI TPS651851RSLR | 1.93 | Keep. FP9931WD is $0.37 cheaper but needs a new land, has no open driver and almost no VPOS headroom. |
| 3 | U503 | QMI8658A | 1.39 | **→ QMI8658B (C5380158) $0.95.** Same QST family; datasheet pin table and 2.5 × 3.0 mm LGA-14 identical; 0.83 mm high. |
| 4 | U302 | SD3078 (RTC with crystal) | 1.16 | Keep for R50. BM8563ESA ($0.16) + 32.768 kHz crystal saves ~$0.9 but needs a new SOP-8 150 mil land, a crystal and a backup-supply rework. |
| 5 | U506 | GD25Q128ESIG | 0.96 | Keep for the prototype. Zetta ZD25Q128CSIGT ($0.64, same SOP-8 208 mil) is the volume option once ESP32-S3 QIO boot is verified on the bench; GD25Q128E is the part ESP-IDF lists for HPM. |
| 6 | U402–U405 | SGM2578YG ×4 | 0.86 | Keep. No cheaper part on the same 0.5 mm WLCSP-4 ball map is stocked. |
| 7 | U901 | SGM41513 charger | 0.71 | Keep (functional). |
| 8 | U903 | CW2217 fuel gauge | 0.67 | Keep (functional). |
| 9 | U710/U711 | SGM330A ×2 | 0.65 | Keep (functional). |
| 10 | U601/U811 | XL9535 ×2 | 0.59 | Keep. Already the low-cost TCA9535-compatible part. |

Passives were also screened against the mainland-registered brands (FH, FOJAN, CCTC, HRE). Same-or-better-spec swaps adopted:

| Refs | Was | Now | Saving @1000 |
|---|---|---|---|
| C207, C208, C525 | FH 0805X226M250NT 22 µF 25 V X5R | FOJAN FCC0805X226M250FT (C7419435) | $0.24 |
| 9 × 1 µF 0603 25 V X7R | FH 0603B105K250NT | CCTC TCC0603X7R105K250CT (C380328) | $0.35 |
| C401–C403, C501 | FH 0603X226M100NT 22 µF 10 V X5R | CCTC TCC0603X5R226M100CT (C20416425) | $0.09 |
| C203 | FH 1206B106K250NT 10 µF 25 V X7R | CCTC TCC1206X7R106K250HT (C380364) | $0.10 |
| C809, C812 | FH 0805B105K500NT 1 µF 50 V X7R | CCTC TCC0805X7R105K500DTS (C344178) | $0.04 |

Result: placed-parts cost per board falls from $17.44 to **$16.09** (100 boards) and from $15.01 to **$14.11** (1000 boards). Gerbers, drill and CPL are unchanged; native checks stay 0.

### JLC basic library and merged lines (user decision 2026-11-08)

28 passive lines (152 placements) moved to JLC basic-library parts (Samsung Electro-Mechanics capacitors, UNI-ROYAL resistors), which carry no per-type change fee. Duplicates merged on the way: both 1 µF 0402 lines (FOJAN X7R and FH X5R) → Samsung CL05A105KA5NQNC 25 V; 4.7 µF 0805 16 V → CL21A475KAQNNNE 25 V; R910/R911 10 k 0.1 % → the shared 1 % 10 k. Where no basic part with equal spec exists the extended part is kept (PMIC 25 V X7R caps on ±16 V rails, 22 µF 0603, 2.2 µF 0402, precision dividers, RF, NTC, shunt). X7R → X5R was accepted only at a higher voltage rating (1 µF 0603/0402, 10 µF 0603/0805/1206). These exact (manufacturer, MPN) pairs are listed in `USER_APPROVED_JLC_BASIC_PASSIVES` in `verify_mainland_bom_compliance.py`.

Result: extended part types 77 → 49 (basic 3 → 29), i.e. 28 fewer change fees per order (~$84 at JLC's $3; the domestic fee schedule differs). Placed-parts cost: $16.29 / board @100 and $14.24 @1000 (+$0.2 / +$0.13 against the FOJAN/CCTC choice).

### Bottom-side parts (not changed)

Moving the 6 bottom parts to the top was attempted. C815 and C543 fit on top (3.7 mm / 5.9 mm from their pins), but there is no top-side spot for C537/C538 that can reach VDD_SPI, and none for R710 (series resistor on display data D0) or R731 (pull-down on GPIO45, a strapping pin) next to their nets within 12 mm. Because R710 and R731 must stay on the bottom, two-sided assembly remains, so all six stay where they are. Single-sided assembly needs a re-layout of the U501 / display-bus area.

## 2. Unit cost estimate

Assumptions: JLC Standard PCBA, two-sided (6 bottom parts), 218 + 6 SMT parts, 813 SMT joints; setup $25 per side, stencil $7.86 per side, $3 per extended line (49 lines), $0.0017 per joint; BT301 CR1216 tabbed cell fitted after SMT. Parts include 2 % attrition. Enclosure, FPC cables, speaker, antenna, freight, duties and test labour are not included.

| Item | 100 units | 1000 units | Basis |
|---|---|---|---|
| PCB, 4-layer 71 × 99 mm, 0.8 mm, ENIG, resin-filled capped via-in-pad, 0.15 mm drill | $2.2 (1.5–3.0) | $1.2 (0.8–1.5) | JLC 4-layer reference pricing plus ENIG / via-in-pad surcharges; needs a live quote |
| SMT parts | $16.62 | $14.52 | JLC tier prices + 2 % |
| Assembly fees (setup, stencils, extended lines, joints, BT301) | $3.9 | $2.0 | JLC fee schedule above |
| **Main board subtotal** | **$22.7** | **$17.7** | |
| 4.7" 1216 × 684 panel with front light and touch | $35 (28–45) | $26 (20–32) | No public E0470A01 price; 4.7" bare panels retail at ~$37 single, volume assumed 50–70 % of that plus FL/touch |
| 2050 mAh LCO pack (3.2 mm, PCM, NTC, connector) | $4.5 | $3.0 | Generic 2000 mAh LiPo retail $7–10; custom thin pack quote needed |
| Simple printed box, insert and leaflet | $1.2 | $0.6 | Typical Shenzhen print quote range |
| **Total (excl. enclosure)** | **≈ $63** | **≈ $47** | |

The panel module is about 55 % of the total, the main board about 35 %. Further levers, in order of effect: a panel/front-light/touch quote from the panel maker; moving the 6 bottom-side parts to the top (single-sided assembly, one setup and stencil); the U302 RTC and U506 flash cost-downs above for volume; and, if the mainland rule allows, JLC basic passives for small runs. A 5-board prototype costs roughly $100+ per board because the one-time fees (~$300 assembly + PCB minimums) dominate.
