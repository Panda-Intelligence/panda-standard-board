# Panda 標準電子書板：WP4 符號／封裝獨立複核清單

工作包：WP4（EVT 核心板原理圖）
日期：2026-08-11（最后更新：2026-09-07，执行者：Codex）
板號：`PANDA-STD-CORE-EVT`（修訂 `A`）
狀態：**原理图／PCB power/reset/strap/IMU/audio/U402–U405 engineering seed 已存在，部分器件有 A 阶段记录；所有不同身份 B 阶段仍未执行，WP4 不通过**

---

## 0. 使用規則與目前狀態

本文件是待執行清單，不是通過證明。仓库现已有 project symbols／footprints、可解析的
`PANDA-STD-CORE-EVT.kicad_sch` 与 pre-layout PCB seed；`lib/review/*-A-stage.md` 记录的是建立者解析与自动验证，
不是不同身份复核。2026-08-12/13 新增的 U501、U503、U502 与 U402–U405 记录只关闭受控 engineering seed 的 A-stage 留痕；
任何 placement 都不构成 C-stage/WP3 放行。所有器件仍没有不同身份 B 阶段签名，因此没有任何
symbol／footprint 子门通过。

每一個符號與封裝都必須按三階段執行：

1. **A／建立**：建立者先記錄身份、受控來源與建立時間，再建立 project-local asset；asset 尚未建立時不可能有 hash，故不要求預先提供 hash；
2. A 完成後才計算 symbol／footprint library identifier 與 SHA-256；
3. **B／複核**：**不同身份**的複核者對 A 的實際產物逐行核對資料手冊與 package drawing，填寫結果、證據定位、差異單；
4. 實作者不得在「獨立複核者」欄簽名；同一代理換一個名稱也不構成獨立身份；
5. 每一列均有證據才可關閉。章末或總表簽名**不得覆蓋空白逐項證據**；
6. 官方 KiCad 庫只是候選來源，仍須複核；
7. **C／合格使用**：只有 A+B 完成、hash 對得上目前資產，且 WP3 已形成 TPS63802 官方模型模擬或 EVM／bench fallback 結論後，才可把原理图放置／接线视为 qualified；依使用者持续 layout 指令先行建立的内容必须明确标为可撤销 A-stage engineering candidate，不关闭 C-stage；
8. 符號子門與封裝子門分開判定，任一未通過即不得在 ERC／製造輸出中宣稱該器件已驗證。

### 0.1 受控事實來源

| 器件 | 符號／引腳來源 | 封裝來源 |
| --- | --- | --- |
| TPS63802 | TI `SLVSEU9D`，Table 7-1 | TI `DLA0010A`，VSON-HR-10 |
| BQ25628E | TI `SLUSFA4C`，Table 6-1 | TI `RYK0018A`，WQFN-HR-18 |
| BQ27427 | TI `SLUSEB5B` Rev. B（2025-09），Table 4-1 | TI `YZF0009`，DSBGA-9 |
| TUSB320LI | TI `SLLSEP2D`，Pin Functions | TI `RWB0012A`，X2QFN-12 |
| LSM6DSO32XTR | ST `DS13607 Rev 1`，Table 1 | 同文件 §17.1，LGA-14L |
| ESP32-S3-WROOM-1-N16R8 | Espressif WROOM-1／1U Datasheet v1.8，Table 3-1 | 同文件 recommended land pattern |
| RV-3028-C7 | Micro Crystal Application Manual Rev. 1.4，§2.1–2.2；orderable option 待供應商報價／specification ID | C7 SON-8；package／temperature／option 在 BOM freeze 前由供應商確認；KiCad 候選見 §7 |
| MAX98357AETE+T | ADI `19-6779 Rev 16`，Pin Description | 3 mm × 3 mm TQFN-16 + EP；KiCad 候選見 §8 |
| TPS22916CYFPT | TI `SLVSDO5F`，Pin Functions／Electrical Characteristics | TI `YFP0004` DSBGA-4；0.4 mm pitch／0.23 mm example lands；见 §8A |
| TCA9535PWR | TI `SCPS201E`，Table 5-1 | TI `PW0024A`／`4220208/A`，TSSOP-24；见 §9 |

> 「EXPOSED METAL SHOWN」是 TI land-pattern 圖的圖例，不等於中央 exposed pad。只有資料手冊明列的 EP 才可
> 建立 EP pad／symbol pin。

### 0.2 每一節都要填的身份欄

| 欄位 | 填寫 |
| --- | --- |
| 實作者身份 | |
| 實作 source commit | |
| Project symbol library identifier + SHA-256 | |
| Project footprint library identifier + SHA-256 | |
| 精確訂貨號／package drawing／資料手冊 revision | |
| 獨立複核者身份（不得與實作者相同） | |
| 複核日期／時區 | |
| 差異 ID／處置 commit／closure evidence | |

A 階段建立前，hash 欄留空是正常狀態且不阻止 asset 建立；A 完成後，任一身份／來源／hash／review 欄空白、
hash 對不上目前檔案或差異 ID 未關閉，該器件不得進入 C 階段，symbol 與 footprint 子門都維持阻塞。

---

## 1. TPS63802DLA（VSON-HR-10，DLA0010A）— 最高風險

**A 階段狀態**：现有 `panda-standard:TPS63802DLA` symbol／footprint 已解析；symbol library SHA-256
`ad542f6d66b88aaeeb943ca2018b563e0a61f6728e729197b02abbf6924478f7`、footprint SHA-256
`8dd3d4cfc7132dea09d346fecd28348a99faff1812cbcc469fa4cca0cbb4f382`。建立者记录见
`lib/review/TPS63802DLA-A-stage.md`；以下每个 row 仍需不同身份 B 阶段复核。

### 1.1 引腳事實

| Pad | 名稱 | 資料手冊功能 | 結果 | 證據／差異 |
| --- | --- | --- | --- | --- |
| 1 | `EN` | active-high enable；不得浮空 | A 已建立；B 阻塞 | `lib/review/TPS63802DLA-A-stage.md` §3 |
| 2 | `MODE` | LOW power-save／HIGH forced PWM；不得浮空 | A 已建立；B 阻塞 | 同上 |
| 3 | `AGND` | analog ground | A 已建立；B 阻塞 | 同上 |
| 4 | `FB` | feedback sense | A 已建立；B 阻塞 | 同上 |
| 5 | `PG` | open-drain power-good | A 已建立；B 阻塞 | 同上 |
| 6 | `VOUT` | power-stage output | A 已建立；B 阻塞 | 同上 |
| 7 | `L2` | 電感端 | A 已建立；B 阻塞 | 同上 |
| 8 | `GND` | power ground | A 已建立；B 阻塞 | 同上 |
| 9 | `L1` | 電感端 | A 已建立；B 阻塞 | 同上 |
| 10 | `VIN` | supply input | A 已建立；B 阻塞 | 同上 |

### 1.2 封裝事實與必查項

| # | 必查事實 | 結果 | 證據／差異 |
| --- | --- | --- | --- |
| TPS-F1 | Package drawing 必須是 **`DLA0010A`**，本體 nominal 3.0 mm × 2.0 mm，max height 1.0 mm | A 来源已记录；B 阻塞 | A-stage §1–3 |
| TPS-F2 | 10 個周邊 pad，0.5 mm pitch；Pin 1 index 與 top view 一致 | A 已解析；B 阻塞 | A-stage §3 |
| TPS-F3 | **沒有中央 EP／PowerPAD，也沒有第 11 pad** | A 已解析；B 阻塞 | 10 numbered copper pads；2 个无编号 paste aperture 不是 EP |
| TPS-F4 | Pad 8 `GND` 是 DLA0010A 圖中的加長周邊端子；不得誤建為中央熱焊盤 | A 已解析；B 阻塞 | A-stage §3 |
| TPS-F5 | Land pattern 必須逐尺寸轉錄 DLA0010A example board layout，不得套用 `WSON-10-1EP` | A asset 存在；B 尺寸复核阻塞 | Footprint hash 见 A-stage §2 |
| TPS-F6 | `L1`=9、`L2`=7，禁止因符號左右排列而對調 | A 已解析；B 阻塞 | A-stage §3 |

符號子門：**A 有记录／B 阻塞**　封裝子門：**A 有记录／B 阻塞**

---

## 2. BQ25628ERYKR（WQFN-HR-18，RYK0018A）

### 2.1 逐 pin 事實

| Pin | 名稱 | Pin | 名稱 | 結果 | 證據／差異 |
| --- | --- | --- | --- | --- | --- |
| 1 | `BTST` | 10 | `STAT` | 未執行 | |
| 2 | `REGN` | 11 | `INT` | 未執行 | |
| 3 | `PG` | 12 | `SDA` | 未執行 | |
| 4 | `ILIM` | 13 | `SCL` | 未執行 | |
| 5 | `TS_BIAS` | 14 | `CE` | 未執行 | |
| 6 | `TS` | 15 | `GND` | 未執行 | |
| 7 | `QON` | 16 | `SW` | 未執行 | |
| 8 | `BAT` | 17 | `PMID` | 未執行 | |
| 9 | `SYS` | 18 | `VBUS` | 未執行 | |

### 2.2 封裝與 `SW` 必查項

| # | 必查事實 | 結果 | 證據／差異 |
| --- | --- | --- | --- |
| BQ256-F1 | 精確訂貨號為 `BQ25628ERYKR`；package drawing 為 **`RYK0018A`** | 未執行 | |
| BQ256-F2 | WQFN-HR-18，本體 nominal 3.0 mm × 2.5 mm，max height 0.8 mm | 未執行 | |
| BQ256-F3 | **沒有中央 EP，也沒有第 19 pad**；不得套用一般 18-pin QFN+EP | 未執行 | |
| BQ256-F4 | Pin 16 名稱是 **`SW`**，不是 `LSW`；`SW` 接輸出電感，47 nF bootstrap capacitor 接 `SW`–`BTST` | 未執行 | |
| BQ256-F5 | `RYK0018A` 為非等距 HR 周邊 land pattern；逐 pad 幾何與 Pin 1 方向按 package drawing | 未執行 | |
| BQ256-F6 | `PG`、`STAT`、`INT` 均依資料手冊建模為 open-drain；`CE` active-low 且不得浮空 | 未執行 | |
| BQ256-F7 | `ILIM` 的 5.6 kΩ 與 1.2 kΩ + 330 nF 串聯 RC 並聯支路均進 symbol/netlist review；398–496 mA 只標 [算] 外推 | 未執行 | |

符號子門：**未執行**　封裝子門：**未執行**

---

## 3. BQ27427YZFR（DSBGA-9，YZF0009）

### 3.1 球位事實（bottom-view 方向不得與 top view 混用）

| 球位 | 名稱 | 功能 | 結果 | 證據／差異 |
| --- | --- | --- | --- | --- |
| A1 | `GPOUT` | open-drain interrupt／wake | A 已实现；B 阻塞 | `lib/review/BQ27427YZFR-A-stage.md` §3–5；接 U601 P04/R608 |
| A2 | `SDA` | I²C data | A 已实现；B 阻塞 | 同文件 §3；接 `I2C_SDA`，R302 DNP |
| A3 | `SCL` | I²C clock | A 已实现；B 阻塞 | 同文件 §3；接 `I2C_SCL`，R301 DNP |
| B1 | `BIN` | battery insertion／thermistor input | A 默认终接已实现；B/U7 阻塞 | 同文件 §3/§6；R307=10 kΩ 至 VSS，目标电芯 contract 后重审 |
| B2 | `VSS` | ground | A 已实现；B/F0 阻塞 | 同文件 §3–5；中央 VSS 局部规则有正负控 |
| B3 | `VDD` | 1.8 V regulator output；只接 2.2 µF 去耦 | A 已实现；B 阻塞 | 同文件 §3–5；只接 C304 |
| C1 | `VSS` | ground | A 已实现；B 阻塞 | 同文件 §3–5 |
| C2 | `SRX` | integrated high-side sense path 的 system-side 端 | A 拓扑已实现；B/F0 阻塞 | 同文件 §3–5；接 `PACK_BAT` |
| C3 | `BAT` | 內部 LDO input、battery-side／Kelvin sense 端 | A 拓扑已实现；B/F0 阻塞 | 同文件 §3–5；接 `BAT_PACKP`/C303 |

### 3.2 封裝與電氣必查項

| # | 必查事實 | 結果 | 證據／差異 |
| --- | --- | --- | --- |
| BQ274-F1 | `YZF0009`，3×3、0.5 mm pitch、body nominal 1.62 mm × 1.58 mm、0.625 mm max | A 已核；B 阻塞 | `lib/review/BQ27427YZFR-A-stage.md` §1–2 |
| BQ274-F2 | 9 顆 NSMD land nominal Ø0.245 mm；A1 corner 與 symbol 球位一致 | A 已核；B 阻塞 | 同文件 §2–3；官方 footprint SHA 已冻结 |
| BQ274-F3 | 不存在 `REGIN`；不得沿用其他 gauge 的 `REGIN` pinout | A 已实现；B 阻塞 | 同文件 §3 |
| BQ274-F4 | PACK+ 星點→`BAT`=C3→內建 7 mΩ sense→`SRX`=C2→system；禁止 PACK+ 高流旁路；不是只接一條 Kelvin 細線。`BAT`–`VSS` 的 1 µF 本地去耦不是繞過 sense 的高流旁路，必須保留 | A 拓扑已实现；B/F0 阻塞 | 同文件 §4–5；source/netlist audit |
| BQ274-F4A | BAT/SRX pad、breakout、via 與銅寬需覆蓋長期 RMS 2 A／10% duty peak RMS 3.5 A（−40…+70 °C） | A 有候选；F0/B 阻塞 | 同文件 §4/§6；尚无板厂铜厚/热签核 |
| BQ274-F5 | `VDD`=B3 是輸出，不得接 `3V3_AON` 或供電其他器件 | A 已实现；B 阻塞 | 同文件 §3–5；netlist 只含 U301.B3/C304.1 |
| BQ274-F6 | `BAT`=C3 是內部 LDO input；依 `SLUSEB5B` Rev. B Table 4-1／§5.3，在器件附近以 1 µF ceramic 接至 `VSS`，並與高流 sense path 分開審查 | A 已实现；B 阻塞 | 同文件 §4；C303 hot 距 1.872672 mm |
| BQ274-F7 | `BIN`=B1 不得浮空或直接短接 `VDD`／`VSS`；必須依目標電芯 NTC／battery-insertion contract 明確終接，且該 contract 未凍結時保持阻塞 | A 默认终接已实现；U7/B 阻塞 | 同文件 §3/§6；R307=10 kΩ 至 VSS，不是直接短路 |
| BQ274-F8 | `GPOUT`=A1 為 open-drain；即使未使用也須有明確外部上拉／host-wake 處置，不能只在 symbol 中標註 open-drain | A 已实现；B/WP9 阻塞 | 同文件 §3/§6；U601 P04/R608 与 released contract |

KiCad 10.0.5 官方封裝候選：
`Package_BGA:Texas_DSBGA-9_1.62x1.58mm_Layout3x3_P0.5mm`；仍須獨立複核。

符號 A-stage：**已留痕**　封裝 A-stage：**已留痕**　不同身份 B-stage：**未執行**

---

## 4. TUSB320LIRWBR（X2QFN-12，RWB0012A）

### 4.1 逐 pin 事實

| Pin | 名稱 | Pin | 名稱 | 結果 | 證據／差異 |
| --- | --- | --- | --- | --- | --- |
| 1 | `CC1` | 7 | `SDA/OUT1` | 未執行 | |
| 2 | `CC2` | 8 | `SCL/OUT2` | 未執行 | |
| 3 | `PORT` | 9 | `ID` | 未執行 | |
| 4 | `VBUS_DET` | 10 | `GND` | 未執行 | |
| 5 | `ADDR` | 11 | `EN_N` | 未執行 | |
| 6 | `INT_N/OUT3` | 12 | `VDD` | 未執行 | |

### 4.2 模式、位址與封裝必查項

| # | 必查事實 | 結果 | 證據／差異 |
| --- | --- | --- | --- |
| TUSB-F1 | Package 是 **`RWB0012A` X2QFN-12**，1.6 mm × 1.6 mm、0.4 mm pitch、0.4 mm max | 未執行 | |
| TUSB-F2 | **不是 WQFN-12，沒有中央 EP，也沒有第 13 pad** | 未執行 | |
| TUSB-F3 | `ADDR`=NC 為 GPIO mode；`ADDR`=L 為 7-bit **0x47**；`ADDR`=H 為 **0x67** | 未執行 | |
| TUSB-F4 | 舊文件中的 0x60／0x61 不適用於本器件／本資料手冊，不得帶入符號屬性 | 未執行 | |
| TUSB-F5 | `VBUS_DET` 必須經資料手冊要求的約 900 kΩ 接 system VBUS | 未執行 | |
| TUSB-F6 | `EN_N` active-low 且有 internal pull-up；GPIO mode 的 OUT1／OUT2／OUT3／ID 不得無意懸空後又宣稱可讀狀態 | 未執行 | |
| TUSB-F7 | `VDD` 只接 VBUS-derived rail；每條 AON-facing GPIO/I²C/INT/EN 經 S-9 fail-safe isolation，VBUS=0 時無反灌 | 未執行 | |

KiCad 10.0.5 官方候選：`Interface_USB:TUSB320I` 與
`Package_DFN_QFN:Texas_X2QFN-12_1.6x1.6mm_P0.4mm`；專案值與訂貨號仍須改為 LI 精確變體並複核。

符號子門：**未執行**　封裝子門：**未執行**

---

## 5. LSM6DSO32XTR（LGA-14L）

**历史通用符号A阶段记录**：见 `lib/review/LSM6DSO32XTR-A-stage.md`。2026-08-12 source identity 为项目 symbol
SHA-256=`ad542f6d66b88aaeeb943ca2018b563e0a61f6728e729197b02abbf6924478f7`、KiCad 官方 generic footprint
SHA-256=`e78b6004d7b0ad6e304d1b4b67f331f9f4a5e7e9446fd85711432a5b8a41b5f6`；以下 A-stage 结果均仍需
不同身份 B-stage 逐项重核。

当前J501 merged的U503改用固定Mode1变体，library当前hash和类型审计见
[LSM6DSO32XTR-I2C-MODE1-A-stage.md](lib/review/LSM6DSO32XTR-I2C-MODE1-A-stage.md)。通用符号和封装几何保留，B-stage仍未完成。

### 5.1 逐 pin 事實

| Pin | 名稱 | 本設計 Mode 1 處理 | 結果 | 證據／差異 |
| --- | --- | --- | --- | --- |
| 1 | `SDO/SA0` | 接 `Vdd_IO`，I²C 位址 0x6B | 当前固定Mode1为input；B阻塞 | 3V3_AON；2026-09-07受限模式模型已消除原pin_to_pin报告，非器件资格放行 |
| 2 | `SDx` | 不用 sensor hub；接 `Vdd_IO` 或 GND，禁止當主 I²C SDA | 固定Mode1为input；B阻塞 | 接GND，ST Table18的默认输入终接 |
| 3 | `SCx` | 不用 sensor hub；接 `Vdd_IO` 或 GND，禁止當主 I²C SCL | 固定Mode1为input；B阻塞 | 接GND，ST Table18的默认输入终接 |
| 4 | `INT1` | 上電時必須 LOW／浮空；之後為可程式 interrupt | A 已实现；B 阻塞 | R501=100 kΩ pulldown；U601 P12 consumer 已接入且下拉保留 |
| 5 | `Vdd_IO` | I/O supply | A 已实现；B 阻塞 | 3V3_AON + C503 100 nF；hot-pad 距 1.49 mm |
| 6 | `GND` | ground | A 已实现；B 阻塞 | In1.Cu local return |
| 7 | `GND` | ground | A 已实现；B 阻塞 | In1.Cu local return |
| 8 | `Vdd` | main supply | A 已实现；B 阻塞 | 3V3_AON + C504 100 nF；hot-pad 距 1.28 mm |
| 9 | `INT2` | 未使用時依資料手冊處理 | A 已实现；B 阻塞 | explicit no-connect；与 pins 10/11 分离 |
| 10 | `NC` | 焊接到 PCB pad，但保持電氣未連接 | A 已实现；B 阻塞 | explicit no-connect；保留 physical pad |
| 11 | `NC` | 焊接到 PCB pad，但保持電氣未連接 | A 已实现；B 阻塞 | explicit no-connect；保留 physical pad |
| 12 | `CS` | 接 `Vdd_IO` 以啟用 I²C／I3C | A 已实现；B 阻塞 | 接 3V3_AON |
| 13 | `SCL` | 主 I²C clock | A 已实现；B 阻塞 | 接 U501 GPIO14 与 U201 SCL |
| 14 | `SDA` | 主 I²C data | A 已实现；B 阻塞 | 接 U501 GPIO15 与 U201 SDA |

### 5.2 必查項

| # | 必查事實 | 結果 | 證據／差異 |
| --- | --- | --- | --- |
| LSM-F1 | 器件只有 **14 pins**；不存在 `OCS`、重複 `SDO/SA0` 或額外 reserved pins | A 已解析；B 阻塞 | A-stage §3；14/14 unique symbol pins |
| LSM-F2 | §17.1 package outline 為 2.5 mm × 3.0 mm × 0.86 mm max；0.5 mm pitch | A 已解析；B/F0 阻塞 | A-stage §1/§4；generic candidate 不是 ST exact land pattern |
| LSM-F3 | Pins 10／11 是 NC；有實體 pad，但網表中不得接地／合併 | A 已实现；B 阻塞 | 两个独立 explicit no-connect nets；A-stage §3 |
| LSM-F4 | `INT1` 上電接 `Vdd_IO` 會選成 I3C-only；本設計下拉不得誤畫成上拉 | A 已实现；B 阻塞 | R501=100 kΩ pulldown；A-stage §3 |
| LSM-F5 | `INT1/INT2` reset 行為與 output type 可程式；symbol 電氣類型不得無條件標為固定 push-pull output | A 已解析；B 阻塞 | 两脚为 bidirectional；A-stage §3 |
| LSM-F6 | X/Y/Z 與 Pin 1 朝向須進絲印／裝配圖 | 部分完成；B/M0 阻塞 | 官方 candidate 有 Pin-1 marker；X/Y/Z 仍缺 |

官方 generic footprint 只能作候選：
`Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y`；不得使用 Bosch-specific land pattern 免檢。
其 0.35 mm pad/0.5 mm pitch 与项目全局 0.20 mm clearance 冲突；当前 `.kicad_dru` 只对 U503 内部对象设
0.15 mm，移除规则会出现 12 条全部位于 U503 内部的 clearance errors。该规则是显式 F0/DFM/B-stage 门，
不是制造豁免。

符號子門：**A-stage 有记录；B-stage/WP3 未执行**　封裝子門：**A-stage candidate 有记录；B-stage/F0/M0 未执行**

---

## 6. ESP32-S3-WROOM-1-N16R8

**A 阶段记录**：见 `lib/review/ESP32-S3-WROOM-1-N16R8-A-stage.md`。当前 source identity 为
KiCad 10.0.5 官方 symbol SHA-256=`5caaa848e888e9f5491edc765fef0e2eee53c4fe5aa4fe1520c01e4b0f840f2b`、
footprint SHA-256=`d0cfbb31fef0c47396c0d061ec5a3bff60f0567d8d4ea8dd4769c84f52bd656f`；
以下 “A 已解析” 均仍需不同身份 B-stage 逐项重核。

| # | 必查事實 | 結果 | 證據／差異 |
| --- | --- | --- | --- |
| ESP-F1 | 模組 nominal 18×25.5×3.1 mm，且是 **41 pads**：1–40 周邊／底部端子，41=`EPAD`/GND；不是 38 pin | A 已解析；B 阻塞 | A-stage §3；官方 symbol 有 41 个唯一编号 |
| ESP-F2 | Pad 40=`GND`、Pad 41=`EPAD`/GND，官方 footprint 的 pad 41 與 thermal-via array 對應 | A 已解析；B 阻塞 | A-stage §3–4；当前实例 pads 1/40/41=`GND` |
| ESP-F3 | N16R8 的 module pads 28/29/30 對應 IO35/36/37，已被 Octal PSRAM 使用，symbol 必須標 DNU／不可分配 | A 已解析；B 阻塞 | Current schematic 已放置三个 no-connect；A-stage §3 |
| ESP-F4 | 真正 strapping GPIO 是 **0、3、45、46**；GPIO19/20 是 USB D−/D+，不是 strapping pins | A 已解析；GPIO0/3/46 seed 已实现；GPIO45 阻塞 | R511 pull-up、R512/R513 pulldown；GPIO45 保持无外部 loading；A-stage §3、§5 |
| ESP-F5 | Module pads 13/14 對應 GPIO19/20 USB D−/D+；pads 36/37 對應 U0RXD(GPIO44)/U0TXD(GPIO43) | A 已解析；B 阻塞 | KiCad official symbol pin map；A-stage §3 |
| ESP-F6 | `RF_Module:ESP32-S3-WROOM-1` 官方 footprint 存在，但仍須核對 41 pads、天線 all-layer keepout、3D 高度與板邊方向 | A 已解析；B/M0 阻塞 | Footprint/STEP hash 与 render 见 A-stage §2、§5 |
| ESP-F7 | 精確 N16R8/R8 ambient 為 −40…+65 °C；不得引用一般 +85 °C variant。若採 ECC +85 °C，記錄 firmware/build 證據與 PSRAM −1/16 | 未執行 | |
| ESP-F8 | GPIO45 是 VDD_SPI voltage-selection strap；所需 reset level 依 exact module／chip／eFuse／board configuration。受控 contract 前不得建立外部 pull、adapter loading、connector mapping 或 placement | 未執行 | |

符号子门：**A-stage 有记录；B-stage 未执行**　封装子门：**A-stage 有记录；B-stage/M0 未执行**

---

## 7. RV-3028-C7

**A 阶段记录**：见 `lib/review/RV-3028-C7-A-stage.md`。当前正式原理图嵌入 KiCad 10.0.5 官方
`Timer_RTC:RV-3028-C7`，PCB 使用官方
`Package_SON:MicroCrystal_C7_SON-8_1.5x3.2mm_P0.9mm`；官方 symbol library SHA-256=
`1f6bdf4bc0d172a5fbdb97b0edf7e753687eb1b25f6ad34132ab6466db8080f2`、footprint SHA-256=
`dcf8e98d380a1d7fc711a4e15333c968f6a6a963ad3dd69c987c06e9942adbd1`。精确订货 suffix 与不同身份
B-stage 仍阻塞。

| Pin | 名稱 | Pin | 名稱 | 結果 | 證據／差異 |
| --- | --- | --- | --- | --- | --- |
| 1 | `CLKOUT` | 5 | `VSS` | A 已实现；B 阻塞 | A-stage §2；CLKOUT no-connect、VSS=GND |
| 2 | `INT`（open-drain active-low） | 6 | `VBACKUP` | A 已实现；B 阻塞 | A-stage §2；RTC_INT／无后备模式 10 kΩ shunt |
| 3 | `SCL` | 7 | `VDD` | A 已实现；B 阻塞 | A-stage §2；I2C_SCL／3V3_AON+C302 |
| 4 | `SDA` | 8 | `EVI` | A 已实现；B 阻塞 | A-stage §2；I2C_SDA／R303 10 kΩ pull-up |

| # | 必查事實 | 結果 | 證據／差異 |
| --- | --- | --- | --- |
| RV-F1 | C7 是 8-pad SON，body 3.2 mm × 1.5 mm × 0.8 mm，0.9 mm pitch | A 已解析；B 阻塞 | 官方 datasheet + A-stage §1/§3 |
| RV-F2 | **沒有 EP，沒有 NC**；8 個 pad 都有明確功能 | A 已解析；B 阻塞 | 8 个唯一 numbered copper pads；A-stage §2–3 |
| RV-F3 | 当前 C301 未获准，故以 `R304=10 kΩ` 将 `VBACKUP` 接 VSS；未来批准 C301 后 R304 才改 DNP。未用 `EVI` 以 `R303=10 kΩ` 上拉 RTC VDD，禁止浮空 | A 已实现；B/C301 阻塞 | App Manual Rev. 1.4 §2.2/§7.1；A-stage §2 |
| RV-F4 | KiCad 候選 `Timer_RTC:RV-3028-C7` + `Package_SON:MicroCrystal_C7_SON-8_1.5x3.2mm_P0.9mm` 逐 pin 一致 | A 已解析；B 阻塞 | XML netlist/pad-net audit；A-stage §2–4 |
| RV-F5 | 未用 `CLKOUT` 可 no-connect，但 EEPROM 35h 必須禁用並读回；預設 CLKOE=1/32.768 kHz 不得冒充未用 | A 硬件边界已实现；产线/B 阻塞 | U302.1 no-connect；A-stage §2/§5 |
| RV-F6 | supplier quote／specification ID、exact orderable suffix、reel／packaging 與 controlled datasheet 已對應同一料號；`SUPPLIER-CONFIRMED-ORDERABLE-P/N: TBD` 只可作 placeholder | 未執行 | |

符號子門：**A 有记录／B 阻塞**　封裝子門：**A 有记录／精确订货号/B 阻塞**

---

## 8. MAX98357AETE+T

**A 阶段记录**：见 `lib/review/MAX98357AETE+T-A-stage.md`。当前 exact candidate footprint 为
`MAX98357A_T1633_4:MAX98357AETE_T_TQFN16`，SHA-256=
`72c2dbc9427a9c50e46b2136986d8d992084d5276af8e187720d84bbdc631aa0`。它依据 ADI `90-0031 Rev C`
的 `T1633+4` land pattern 建立；KiCad generic `T1633-5`／`90-0032` 只作差异对照，不得冒充 exact。

### 8.1 TQFN pin／EP 事實

| Pin | 名稱 | Pin | 名稱 | 結果 | 證據／差異 |
| --- | --- | --- | --- | --- | --- |
| 1 | `DIN` | 9 | `OUTP` | A 已实现；B 阻塞 | U502.1=`I2S_DIN`；U502.9=`SPK_P` |
| 2 | `GAIN_SLOT` | 10 | `OUTN` | A 已实现；B 阻塞 | U502.2=`GAIN_SLOT`；U502.10=`SPK_N` |
| 3 | `GND` | 11 | `GND` | A 已实现；B 阻塞 | 两者均接 GND／EP local network |
| 4 | `SD_MODE` | 12 | `NC` | A 已实现；B 阻塞 | U502.4=`SD_MODE`；12 explicit NC |
| 5 | `NC` | 13 | `NC` | A 已实现；B 阻塞 | 两者为独立 explicit NC |
| 6 | `NC` | 14 | `LRCLK` | A 已实现；B 阻塞 | 6 explicit NC；14=`I2S_LRCLK` |
| 7 | `VDD` | 15 | `GND` | A 已实现；B 阻塞 | 7=`VSYS_AUDIO`；15=GND |
| 8 | `VDD` | 16 | `BCLK` | A 已实现；B 阻塞 | 8=`VSYS_AUDIO`；16=`I2S_BCLK` |
| EP | exposed pad（KiCad synthetic pad 17） | — | not internally connected；PCB 接 solid GND plane 散熱 | A 已实现；B/F0 阻塞 | pad17=GND；外置 local via；无 via-in-pad |

| # | 必查事實 | 結果 | 證據／差異 |
| --- | --- | --- | --- | --- |
| MAX-F1 | 3 mm × 3 mm TQFN-16 + EP，0.5 mm pitch；`T1633+4` EP 1.23 mm × 1.23 mm | A 已解析；B/F0 阻塞 | Exact `90-0031`: pads 0.80×0.30 mm、centers ±1.425 mm；A-stage §1–3 |
| MAX-F2 | Pins 5、6、12、13 必須保持 NC；不得因鄰近 GND 而合併 | A 已实现；B 阻塞 | 四个独立 auto-unconnected nets；A-stage §3–4 |
| MAX-F3 | EP **內部未連接**，但資料手冊要求 PCB 連 solid ground plane；symbol/footprint mapping 必須表達此差異 | A 已实现；B/F0 阻塞 | synthetic pad17=GND；外置 via；A-stage §3–4 |
| MAX-F4 | Synthetic pad 17 只是库映射，不是资料手册第 17 引脚 | A 已解析；B 阻塞 | Symbol/PCB/netlist 17/17 audit；A-stage §3–4 |
| MAX-F5 | `DIN`／`BCLK`／`LRCLK` 是輸入；`OUTP`／`OUTN` 是差分輸出 | A 已实现；B 阻塞 | U501 pads19/20/21→U502；SPK_P/N 保持到 J502 门；A-stage §4–5 |
| MAX-F6 | KiCad generic `T1633-5`／`90-0032` 不得替代 `MAX98357AETE+T` 的 `T1633+4`／`90-0031` | A 已修正；B 阻塞 | Exact footprint hash 与官方 PDF hash 见 A-stage §2 |

符號子門：**A-stage 有记录；B-stage 未执行**　封裝子門：**A-stage exact-copper candidate 有记录；B-stage/F0/M0 未执行**

---

## 8A. TPS22916CYFPT（U402–U405 四路負載開關）

**A 阶段记录**：见 `lib/review/TPS22916CYFPT-A-stage.md`。项目 symbol=
`panda-standard:TPS22916CYFPT`；exact-copper footprint=`panda-standard:TPS22916CYFPT_YFP0004`，
SHA-256=`f1ce2a470a3be7f2030227389b7a58569bd0f4537675a55095e52bf37787ed77`。U402–U404 于
2026-08-13 复用同一 exact OPN/asset；这不构成新的独立身份 B-stage。

### 8A.1 Pin／电气事实

| Ball | 名称 | 当前网络 | 结果／边界 |
| --- | --- | --- | --- |
| A1 | `VOUT` | U402=`3V3_SD_SW`、U403=`3V3_TOUCH_SW`、U404=`3V3_EPD_LOGIC_SW`、U405=`VSYS_AUDIO_SW`；各经 MB3–MB6 到 downstream rail | A 已实现；B 阻塞 |
| A2 | `VIN` | U402–U404=`3V3_AON` + C508/C509/C511；U405=`VSYS_RAW` + C507 | A 已实现；WP3/B 阻塞 |
| B1 | `GND` | 每颗 local via → In1.Cu GND | A 已实现；B/F0 阻塞 |
| B2 | `ON` | `EN_3V3_SD/EN_3V3_TOUCH/EN_3V3_EPD_LOGIC/EN_VSYS_AUDIO`；外部 100 kΩ pulldown | A 已实现；U601 P00–P03 consumer 已接入；B 阻塞 |

| # | 必查事实 | 结果 | 证据／差异 |
| --- | --- | --- | --- |
| TPS229-F1 | exact OPN `TPS22916CYFPT` 是 active-high、C slow-turn-on、QOD、full-time true reverse-current blocking 变体 | A 已解析；B 阻塞 | TI exact part page／`SLVSDO5F`；A-stage §1/§3 |
| TPS229-F2 | 1–5.5 V、2 A；`VIH` min 1.0 V、`VIL` max 0.35 V；`ISD` max 100 nA、reverse leakage max 300 nA @25 °C | A 已解析；WP3/B 阻塞 | A-stage §1/§3；rail min/max/热仍待 WP3 |
| TPS229-F3 | ball mapping 必须是 A1=VOUT、A2=VIN、B1=GND、B2=ON；不得把 top-view／bottom-view 对调 | A 已实现；B 阻塞 | symbol／XML netlist／PCB pad-net audit；A-stage §3–4 |
| TPS229-F4 | `YFP0004` 0.4 mm pitch、0.23 mm NSMD example lands、mask expansion ≤0.05 mm；Pin-1 marker 对应 A1 | A 已实现；B/F0 阻塞 | exact footprint；A-stage §2/§4 |
| TPS229-F5 | 全局 0.20 mm clearance 不得因 0.17 mm 器件内部 gap 被整体放宽 | A 已实现；B/F0 阻塞 | U402–U405 各自 0.15 mm internal-only rule；移除 DRU 时每颗恰 4 条 clearance error；A-stage §4/§7 |
| TPS229-F6 | CIN 靠近 VIN；VIN/VOUT/GND 走线短宽；MB3–MB6/TP5–TP8 必须保持可测 | A 已实现；M0/WP3/B 阻塞 | U402–U404：center→U=1.800 mm、hot→A2=1.700 mm、cold→via=1.513 mm；U405 见 A-stage §4 |

符号子门：**A-stage 有记录；B-stage 未执行**　封装子门：**A-stage exact-copper candidate 有记录；B-stage/F0/M0 未执行**

---

## 9. TCA9535 與通用封裝項

2026-08-13 已把 A-stage 变体固定为 `TCA9535PWR`／`PW0024A` TSSOP-24，并建立
`lib/review/TCA9535PWR-A-stage.md`。这只关闭“选择哪一个 A-stage 变体”的歧义；仍必须由不同身份 reviewer
按 TI `SCPS201E` Table 5-1 与 `4220208/A` 独立复核，不能把 PWR 记录用于 RGER／其他变体。

| # | 必查事實 | 結果 | 證據／差異 |
| --- | --- | --- | --- |
| TCA-F1 | P 埠輸出是 push-pull，不得標為 open-drain | A 已实现；B 阻塞 | 官方 symbol P00–P17 为 bidirectional；A-stage §2 |
| TCA-F2 | P04／`FUEL_GPOUT` reset／常態為 input／released，外部 pull-up；wake pulse 只允許 output-low，之後立即回 input，禁止 output-high | A 已实现；B 阻塞 | U601.8=`FUEL_GPOUT` + R608 pull-up；A-stage §2 |
| TCA-F3 | BQ27427 `GPOUT` 才是 open-drain source；symbol／ERC note 不得把 TCA9535 P04 冒充 wired-OR OD | A 已实现；B 阻塞 | A-stage §2；软件门保持 input/released 契约 |

所有封裝另須逐項確認：Pin 1、pad 尺寸、阻焊／鋼網、courtyard、3D 高度、絲印不壓 pad、裝配方向。
「若有 EP」必須以器件資料手冊判定，不能從通用 QFN 名稱推論。

### 9.1 完整 BOM 驅動的受控附表門

目前 §1–§9 只逐 pin 展開已知高風險主動器件，**不是完整 BOM coverage**。精確 BOM 尚未凍結，因此不得替
未選料號編造 pin/pad。精確料號定案後，必須生成受控附表 `lib/review/PANDA-STD-CORE-EVT-A-bom-review.md`，
逐一覆蓋下列每個 BOM row／DNP row；不是「每類抽一顆」。

| BOM workload | 目前精確身份 | 附表必填證據 | 當前狀態 |
| --- | --- | --- | --- |
| U201/U202/U301/U302/U401/U501/U502/U503/U601 | 部分已知；U301=`BQ27427YZFR/YZF0009`、U601=`TCA9535PWR/PW0024A` A-stage 已定 | 每 pin、每 pad、package drawing、hash、builder/reviewer、差異 ID | **U301/U601 A 有记录；全部 B-stage/其余缺项仍阻塞** |
| Core switched branches（`3V3_SD`／`3V3_TOUCH`／`3V3_EPD_LOGIC`／`VSYS_AUDIO`） | `U402–U405=TPS22916CYFPT` A-stage 已建立；前光开关不在核心板 | 每个实际 BOM row 的精确 MPN、reverse-current／leakage、symbol/footprint/3D；见 §8A | **四路 A 有记录；全部 B-stage/F0/WP3 与精确被动件未做** |
| L401/L402 | L401 只有 XFL4015 family／4.0×4.0×1.5 mm body-envelope reference；exact suffix／MPN 與 land pattern 未選；L402 未選 | orderability、tolerance/current/temperature derating、Isat definition、supplier land pattern、pad/courtyard/height | **阻塞** |
| Q201 與全部 D/TVS/ESD/ferrite | 未選或 DNP | pin/polarity、package suffix、DNP status、pad/3D | **阻塞：待 MPN** |
| C301、C401–C404、所有 decoupling/RC capacitors | 部分候選；C301 只允許已批准的 rechargeable supercapacitor／LIC，primary／rechargeable coin battery 均排除 | 每個 value/voltage/dielectric/package/DC-bias；C301 exact part／capacity／leakage／package；C204=330 nF 進 ILIM RC | **阻塞** |
| R201–R204、R301–R303、R401/R402、R500–R614、全部 pulls/series/DNP | 部分值已知 | value/tolerance/package、net role、DNP、每 pad；不得只核通用 0402 一次 | **阻塞** |
| J201/J301/J501/J502/J601 | 未選或 envelope-only；J601 僅凍結 `>=40 contacts` envelope | exact MPN、contact count/numbering、mating face、Pin 1、mechanical drawing/hash/3D | **阻塞** |
| J503 | `TC2030-IDC-NL` A-stage 已落板；KiCad 官方 symbol/footprint，六针 ESP-Prog target mapping 已机器审计 | Tag-Connect Rev B、Pin 1／mating face、六 contact pads、3 NPTH、keepout、0.508 mm other-copper clearance、治具方向与实物下载 | **A 有记录；B/M0/WP9 阻塞** |
| Power/Fn switches | Power：EP21SD1ABE工程候选；Fn未选 | Power四电气端子+两支撑PTH已核，见[记录](lib/review/EP21SD1ABE-A-stage.md)；3D/微电流寿命/整机高度待核 | **S-10实物资格仍阻塞** |
| Test points／mounting holes／fiducials／tooling features | 待板框 | pad/hole stack、mask、mechanical datum、fab capability | **阻塞：M0/F0** |

附表每列至少包含：`BOM row ID`、reference(s)、精確 MPN、datasheet revision、package drawing ID、symbol lib ID +
SHA-256、footprint lib ID + SHA-256、逐 pin/pad evidence、builder、不同身份 reviewer、review time、difference ID、
closure commit。**任一空白列使總簽名保持 BLOCKED。**

---

## 10. 獨立複核結果總表（所有 B-stage 目前均未執行）

| 器件 | 符號逐項證據 | 封裝逐項證據 | 實作者 | 獨立複核者 | 差異全關閉 | 子門狀態 |
| --- | --- | --- | --- | --- | --- | --- |
| TPS63802DLA | `lib/review/TPS63802DLA-A-stage.md` §3 | 同文件 §2–3 | Codex | | 否 | **A 有记录；B 阻塞** |
| BQ25628ERYKR | 無 | 無 | | | 否 | **未執行** |
| BQ27427YZFR | `lib/review/BQ27427YZFR-A-stage.md` §3–5 | 同文件 §1–5 | Codex | | 否 | **A 有记录；B/F0/M0 阻塞** |
| TUSB320LIRWBR | 無 | 無 | | | 否 | **未執行** |
| LSM6DSO32XTR | `lib/review/LSM6DSO32XTR-A-stage.md` §3 | 同文件 §2/§4–5 | Codex | | 否 | **A 有记录；B/F0/M0/WP3 阻塞** |
| ESP32-S3-WROOM-1-N16R8 | `lib/review/ESP32-S3-WROOM-1-N16R8-A-stage.md` §3 | 同文件 §2–5 | Codex | | 否 | **A 有记录；B 阻塞** |
| RV-3028-C7 | `lib/review/RV-3028-C7-A-stage.md` §2 | 同文件 §1/§3–4 | Codex | | 否 | **A 有记录；exact suffix/B/F0/M0 阻塞** |
| MAX98357AETE+T | `lib/review/MAX98357AETE+T-A-stage.md` §3–4 | 同文件 §1–4 | Codex | | 否 | **A 有记录；B/F0/M0/WP3 阻塞** |
| TPS22916CYFPT | `lib/review/TPS22916CYFPT-A-stage.md` §3–4 | 同文件 §2/§4 | Codex | | 否 | **A 有记录；B/F0/M0/WP3 阻塞** |
| TCA9535PWR | `lib/review/TCA9535PWR-A-stage.md` §2 | 同文件 §1/§3–4 | Codex | | 否 | **A 有记录；B/F0/M0 阻塞** |
| J503 / TC2030-IDC-NL | `lib/review/TC2030-IDC-NL-A-stage.md` §2 | 同文件 §1/§3–5 | Codex | | 否 | **A 有记录；B/M0/WP9 阻塞** |
| 完整 BOM 受控附表 | 不存在 | 不存在 | | | 否 | **阻塞：未生成／未逐 row 複核** |

總表只能彙總逐項結果，**不能**用一個「最終簽名」把任一空白列改成通過。

## 11. 門的邊界

即使本文件所有 symbol／footprint 子門日後通過，也只證明庫件的 pin mapping 與 land pattern 經獨立複核。
即使庫件子門通過，也仍然**不代表**原理圖已在 KiCad GUI 完成、ERC 已通過、板廠 stackup／DFM 已回簽、
機構板框與孔位已批准或 WP6A 已通過；更**不代表 WP7A Layout 已放行**。目前 WP6A 未通過，WP7A 必須保持
禁止開始。

WP7A 必須等待上述門各自留下可追溯證據，不能以本清單替代。

## 2026-09-08 USB工程资产补记（Codex）

USB接口及S-9器件已进入149封装工程候选，逐pin/官方footprint对应、输入哈希及限制见[USB2-S9-A-stage](lib/review/USB2-S9-A-stage.md)。
此记录不是B-stage/F0/M0签核；旧表USB待选项已由工程候选选择覆盖，但精确无源MPN/装配/实物仍待核。
