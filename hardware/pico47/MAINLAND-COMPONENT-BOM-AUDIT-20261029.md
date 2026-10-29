# Pico47 E0.2-R25 Chinese Mainland Component Provenance Audit (2026-10-29)

## 1. Executive Summary

All electronic components across the Pico47 E0.2-R25 candidate boards (`Single`, `Core`, and `Display` in `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261029-r25/engineering-candidate`) have been audited and verified via [`verify_mainland_bom_compliance.py`](file:///Users/isaac/workspace/AI/panda-standard-board/hardware/pico47/verify_mainland_bom_compliance.py) and [`test_verify_mainland_bom_compliance.py`](file:///Users/isaac/workspace/AI/panda-standard-board/hardware/pico47/test_verify_mainland_bom_compliance.py).

| Metric | `Single` Unified 4L PCB (`71.0 × 99.0 mm`) | `Core` 4L PCB (`71.0 × 99.0 mm`) | `Display` 4L PCB (`36.0 × 35.7 mm`) |
| :--- | :---: | :---: | :---: |
| **Total Placed Footprints** | **253** | **209** | **48** |
| **Populated BOM Components (`in_bom=yes`, `dnp=no`)** | **215** | **177** | **42** |
| **DNP Passives (`dnp=yes`)** | **5** | **5** | **0** |
| **Non-BOM Bare PCB Test / Debug Landings (`in_bom=no`)** | **33** | **27** | **6** |
| **Chinese Mainland Populated Component Rate** | **100.0% (215 / 215)** | **100.0% (177 / 177)** | **100.0% (42 / 42)** |
| **Chinese Mainland DNP Component Rate** | **100.0% (5 / 5)** | **100.0% (5 / 5)** | **N/A (0 / 0)** |
| **Foreign / Non-Mainland Manufacturers** | **0** | **0** | **0** |
| **Missing `Manufacturer` or `MPN` Fields** | **0** | **0** | **0** |
| **KiCad DRC Violations (`--severity-all`)** | **0** | **0** | **0** |
| **KiCad Unconnected Items (Opens)** | **0** | **0** | **0** |
| **KiCad Schematic-to-PCB Parity Issues** | **0** | **0** | **0** |
| **KiCad ERC Violations (`--severity-all`)** | **0** | **0** | **0** |

---

## 2. Chinese Mainland Manufacturer Registry & Component Breakdown (`Single` Unified Board)

Every populated and DNP electronic component on the unified `Single` board is sourced from a verified Chinese Mainland (PRC) manufacturer:

| # | `Manufacturer` Field | Chinese Corporate Name | Headquarters (PRC) | Category | Populated Count (`Single`) | Representative MPNs & LCSC Codes | Component References |
| :-: | :--- | :--- | :--- | :--- | :-: | :--- | :--- |
| 1 | `Espressif` | 乐鑫信息科技(上海)股份有限公司 | Shanghai (中国上海) | Wireless SoC / MCU | 1 | `ESP32-S3R8` (`C2913194`) | `U501` |
| 2 | `GigaDevice` | 兆易创新科技集团股份有限公司 | Beijing (中国北京) | SPI NOR Flash (16 MB) | 1 | `GD25Q128ESIG` (`C2758105`) | `U506` |
| 3 | `SGMICRO` | 圣邦微电子(北京)股份有限公司 | Beijing (中国北京) | Charger, Buck-Boost, Load Switch, Analog Mux, Frontlight Boost, Reset, TVS | 11 | `SGM41513YTQF24G/TR` (`C5153778`), `SGM62125AXG/TR`, `SGM2578SDYG/TR`, `SGM330A-YTS/TR` (`C700205`), `SGM37601YTRL20G/TR`, `SGM809B-TXN3LG/TR` (`C699619`), `SGM05HU1ALXUGY2G/TR` (`C55274065`) | `D202`, `U402`, `U403`, `U404`, `U405`, `U710`, `U711`, `U901`, `U902`, `U905`, `U906` |
| 4 | `Silergy` | 矽力杰半导体技术(杭州)有限公司 | Hangzhou, Zhejiang (中国浙江杭州) | E-Paper Display PMIC | 1 | `SY7636ARMC` | `U810` |
| 5 | `Cellwise` | 广东赛微微电子股份有限公司 | Dongguan, Guangdong (中国广东东莞) | I2C Battery Fuel Gauge | 1 | `CW2217BAAD` (`C5203993`) | `U903` |
| 6 | `QST (Shanghai QST)` | 上海矽睿科技股份有限公司 | Shanghai (中国上海) | 6-Axis MEMS IMU | 1 | `QMI8658A` (`C3021082`) | `U503` |
| 7 | `Shenzhen Nsiway Tech` | 深圳市纳芯威科技有限公司 | Shenzhen, Guangdong (中国广东深圳) | I2S Class-D Audio Amp | 1 | `NS4168` (`C910588`) | `U904` |
| 8 | `WAVE` | 深圳市兴威帆电子技术有限公司 | Shenzhen, Guangdong (中国广东深圳) | Real-Time Clock (RTC) | 1 | `SD3078` (`C916255`) | `U302` |
| 9 | `XINLUDA` | 厦门芯路达电子科技有限公司 | Xiamen, Fujian / Shenzhen (中国福建厦门/深圳) | 16-Bit I2C GPIO Expander | 2 | `XL9535` (`C561273`) | `U601`, `U811` |
| 10 | `XySemi (Suzhou Saixin)` | 苏州赛芯电子科技股份有限公司 | Suzhou, Jiangsu (中国江苏苏州) | Li-Ion Battery Protection IC | 1 | `XB7608A` (`C669688`) | `U907` |
| 11 | `FH (Fenghua Advanced)` | 广东风华高新科技股份有限公司 | Zhaoqing, Guangdong (中国广东肇庆) | MLCC Capacitors, Thick/Thin-Film Resistors, NTC Thermistor | 160 (+5 DNP) | `0402B104K250NT` (`C56392`), `0603B105K250NT` (`C59302`), `0603X226M100NT` (`C60077`), `0805B106K100NT` (`C90544`), `0805B475K250NT` (`C37818`), `RC-02K1002FT` (`C140215`), `RC-02K1003FT` (`C140219`), `RC-02K22R0FT` (`C324769`), `THC02H1002BT` (`C2991528`), `CMFA103F3950HANT` | `C201..C209`, `C302..C303`, `C401..C403`, `C501..C505`, `C507..C512`, `C516..C531`, `C601`, `C710..C711`, `C801..C817`, `C903`, `C920..C923`, `C940`, `R201`, `R204`, `R501..R940`, `TH801` (+DNP `C514`, `C515`, `R301`, `R302`, `R305`) |
| 12 | `FH (Guangdong Fenghua Advanced Tech)` | 广东风华高新科技股份有限公司 | Zhaoqing, Guangdong (中国广东肇庆) | Thick-Film Chip Resistors | 2 | `RC-02K512JT` (`C453708`) | `R206`, `R207` |
| 13 | `CCTC` | 潮州三环(集团)股份有限公司 | Chaozhou, Guangdong (中国广东潮州) | MLCC Capacitors | 1 | `TCC0402X5R225M100AT` (`C18164608`) | `C304` |
| 14 | `HRE` | 芯声微电子科技有限公司 | Huaian, Jiangsu (中国江苏淮安) | MLCC Capacitors | 2 | `CGA0603X7R106K100JT` (`C22399626`) | `C506`, `C513` |
| 15 | `FOJAN` | 富捷电子科技有限公司 | Ma'anshan, Anhui / Shenzhen (中国安徽马鞍山/深圳) | Current-Sense & Precision Resistors | 3 | `FRM121WFR010TM` (`C7467248`), `FRC0603F1000TS` (`C2906981`) | `R306`, `R903`, `R904` |
| 16 | `Sunlord` | 深圳顺络电子股份有限公司 | Shenzhen, Guangdong (中国广东深圳) | Power & RF Inductors | 8 | `MWSA0618S-4R7MT` (`C408421`), `MWSA0402S-1R0MT` (`C408332`), `MWSA0402S-R47MT` (`C6331050`), `SWPA252012S100MT` (`C37428`), `SDCL1005C24NJTDF` (`C74301`), `SDCL1608C2N0STDF` (`C370234`), `SDCL1005C2N0STDF` (`C43365`) | `L401`, `L402`, `L506`, `L507`, `L508`, `L801`, `L802`, `L905` |
| 17 | `CJ` | 江苏长电/长晶科技股份有限公司 | Nanjing / Wuxi, Jiangsu (中国江苏南京/无锡) | Schottky Barrier Diode | 1 | `B5819W SL` (`C8598`) | `D905` |
| 18 | `JSCJ` | 江苏长晶科技股份有限公司 | Nanjing, Jiangsu (中国江苏南京) | Schottky & Switching Diodes | 4 | `MBR0530` (`C77336`), `BAV99` (`C68983`) | `D801`, `D802`, `D803`, `D804` |
| 19 | `JSMSEMI` | 深圳市杰盛微半导体有限公司 | Shenzhen, Guangdong (中国广东深圳) | N-Channel MOSFETs | 2 | `NX3008NBK,215-JSM` (`C53113911`) | `Q907`, `Q908` |
| 20 | `LRC` | 乐山无线电股份有限公司 | Leshan, Sichuan (中国四川乐山) | ESD Protection Diode | 1 | `LRC8804FDT1G` (`C2856698`) | `D201` |
| 21 | `Shandong Jingdao Microelectronics` | 山东晶导微电子股份有限公司 | Qufu, Shandong (中国山东曲阜) | Schottky Barrier Diode | 1 | `BAT54WS` (`C438012`) | `D306` |
| 22 | `YXC (Yangxing)` | 深圳扬兴科技有限公司 | Shenzhen, Guangdong (中国广东深圳) | 40 MHz Quartz Crystal | 1 | `XL2EL89COI-111YLC-40M` (`C18214314`) | `Y501` |
| 23 | `XKB Connection` | 广东星坤科技股份有限公司 | Dongguan, Guangdong (中国广东东莞) | FPC Connectors & Tactile Switches | 5 (`Single`) / 9 (`Core`+`Display`) | `X05A10L40G` (`C21261162`), `X05A10H06G` (`C528032`), `TS-1186E-B-B` (`C2885153`) | `J803`, `J804`, `J820`, `SW201`, `SW202` (plus `J601`, `J602`, `J1`, `J4` on dual boards) |
| 24 | `XUNPU` | 深圳市讯普电子有限公司 | Shenzhen, Guangdong (中国广东深圳) | Push-Push microSD Socket | 1 | `TF-122-CCP9` (`C41347844`) | `J501` |
| 25 | `MUP` | 深圳市满坤/慕普电子有限公司 | Shenzhen, Guangdong (中国广东深圳) | Mid-Mount USB-C 16P Receptacle | 1 | `U22401-17` | `J201` |
| 26 | `Yichang Power Glory Technology Co., Ltd.` | 宜昌力佳科技有限公司 | Yichang, Hubei (中国湖北宜昌) | Primary Lithium Coin Cell | 1 | `CR1216` | `BT301` |

---

## 3. Metadata Completion ECO Applied in R25

During the audit, the following metadata completions were applied deterministically via [`verify_mainland_bom_compliance.py`](file:///Users/isaac/workspace/AI/panda-standard-board/hardware/pico47/verify_mainland_bom_compliance.py) across `.kicad_pcb`, `.kicad_sch`, and `Panda47.pretty/*.kicad_mod`:

1. **`C501` (`22u / ESP32`, 0603)**:
   - Previously had empty `Manufacturer`, `MPN`, and `LCSC` fields after the R25 `0805 -> 0603` footprint swap trial (`replace_c501_trial.py`), and its empty `Manufacturer`/`MPN`/`LCSC` fields were set on `F.SilkS` without `(hide yes)`.
   - Bound to `Manufacturer = "FH (Fenghua Advanced)"`, `MPN = "0603X226M100NT"`, `LCSC = "C60077"` (matching `C401`, `C402`, `C403` on the same board) with `(hide yes)` enforced so zero silkscreen overlaps occur.
2. **16 Display Passives (`C801`, `C803`, `C816`, `C807..C812`, `R801..R806`, `TH801`)**:
   - Already carried `Manufacturer = "FH (Fenghua Advanced)"`, and now explicitly carry their Fenghua Advanced MPNs (`0805B106K100NT` / `C90544` for `10u/10V/0805` matching `C206`, `0805B105K500NT` for `1u/50V/0805`, `0805B473K500NT` for `47n/50V/0805`, `THC02H4423BT` / `THC02H2102BT` / `THC02H7503BT` / `THC02H5902BT` for 0.1% feedback dividers, `RC-02K7501FT` / `RC-02K3602FT` for 1% TS dividers, and `CMFA103F3950HANT` for `TH801` 10k NTC).
   - Unverified LCSC C-codes remain intentionally blank (`PandaSupplyStatus = "EXACT_SUPPLY_NOT_VERIFIED"`) per `AGENTS.md`.
3. **5 DNP Passives (`C514`, `C515`, `R301`, `R302`, `R305`)**:
   - Explicitly bound to `Manufacturer = "FH (Fenghua Advanced)"` (`0402CG0R8C500NT`, `RC-02K1004FT`, `RC-02K1003FT`).
4. **Non-BOM Bare PCB Test Pads & Debug Landing (`J503`, `TP1..TP19`, `TPG1..TPG6`)**:
   - Normalized to `Manufacturer = "PCB fabricated terminal"` and `MPN = "NOT_A_PURCHASED_PART"` (matching `TP712`, `TP801..TP806`, `J301`, `J302`, `J502`, `J507`).

---

## 4. Verification & Engineering Qualification Notes

```bash
python3 hardware/pico47/verify_mainland_bom_compliance.py \
  --candidate /Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261029-r25/engineering-candidate
pytest hardware/pico47/test_verify_mainland_bom_compliance.py
```

- **Engineering Qualification Disclaimers (preserved per `AGENTS.md`)**:
  - Chinese Mainland manufacturer identity does not by itself certify internal die provenance, firmware correctness, supplier stock reservation/receipt, USB compliance, or physical EVT acceptance.
  - Pending consignment SMT parts (`U402..U405`, `U810`, `U902`, `U905`, `J201`), manual post-SMT assembly (`BT301`), and display high-voltage/precision passives (`C807..C812`, `R801..R806`, `TH801`) retain empty `LCSC` catalog fields until actual supplier/consignment registration and datasheet curve/DC-bias qualification are completed.
