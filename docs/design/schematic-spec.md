# Panda 標準電子書板：WP4 分頁原理圖規格

工作包：WP4（EVT 核心板原理圖）
日期：2026-08-11（最后更新：2026-09-08，执行者：Codex）
板號：`PANDA-STD-CORE-EVT`（修訂 `A`，見 [document-numbering.md](document-numbering.md)）
狀態：第二輪器件／電源域門已更正；受控 native KiCad A-stage engineering candidate 已依使用者持续指令建立，
但 **WP3 官方模型模擬或受控 EVM／bench fallback、TUSB320LI S-9、QON 隔離、GPIO45 reset strap、精確料號、
完整 ERC 與外部簽核均未關閉；不得宣称 WP4/WP7A 通过**

---

## 0. 本文件的性質與邊界

本文件是**原理圖的文字規格**；权威 native source 位于
`eda/core/PANDA-STD-CORE-EVT/Quilter_PANDA-STD-CORE-EVT.kicad_pcb_Placement_1/PANDA-STD-CORE-EVT-quilter-j501-merged.kicad_sch`，
两者必须保持一致。父目录同名seed是历史工程。当前149-component J501 merged 的ERC为19项、PCB DRC/parity0/0/0，
逐项闭合和待输入见[erc-status.md](erc-status.md)；下方带旧日期的34/36等计数仅是历史切片。

`kicad-cli` 負責 ERC、netlist、PDF 与 source validation，不要求用它创建图形。原理图背后的**设计决策、
接法约束、必须避免的错误、ERC 例外理由**仍必须先文字化，否则后续复核无法重现取证。

**使用方式**：建立者依本文件與 [kicad-gui-drawing-runbook.md](kicad-gui-drawing-runbook.md) 逐頁建立原生
KiCad 原理圖；每一條「必辦」與「禁止」都必須有對應實體或註記。完成後以 CLI、來源、PDF 與獨立複核驗收。
任何编辑方式都必须由 CLI、source audit、PDF 与不同身份复核共同验收；工具名称本身不构成可信证据。

**本文件不宣稱**任何一項已通過資格門。全部電氣結論來自
[key-calculations.md](key-calculations.md) 與 [power-datasheet-calculations.md](power-datasheet-calculations.md)
的**數據手冊計算**，未經仿真或實測。WP3 必須先形成 TPS63802 官方模型模擬，或原廠 EVM／受控 bench
fallback 的可追溯結論。当前已放置／接线内容一律保持 A-stage engineering candidate，不能把其 DRC 连通性
解释为 rail qualification；WP4 仍不能通过。

### 0.1 圖例

| 標記 | 意義 |
| --- | --- |
| **[凍]** | PRD／WP0／WP2 已凍結，WP4 不得改動 |
| **[保]** | 保留給最大顯示候選，WP1 定案後回填 |
| **[算]** | 由 [key-calculations.md](key-calculations.md) 推算得出 |
| **[估]** | 估算，不得作為承諾或採購依據 |
| 🔴 **必辦** | 遺漏會導致功能失效或安全問題 |
| ⛔ **禁止** | 違反會導致器件損壞、鎖死或不可開機 |

---

## 1. 頁面劃分

依原始实现计划 §4.1：

| 頁 | 標題 | 主要器件 |
| --- | --- | --- |
| 1 | 系統框圖與電源樹 | 無實體器件（結構頁） |
| 2 | USB-C／充電／電源路徑 | BQ25628E、TUSB320LI、USB-C |
| 3 | 電池／燃料計／RTC | BQ27427、RV-3028-C7、超級電容、電池連接器 |
| 4 | `3V3_AON` 與功能域開關 | TPS63802、負載開關 ×4 |
| 5 | ESP32-S3／儲存／音訊／IMU | ESP32-S3-WROOM-1-N16R8、microSD、MAX98357A、LSM6DSO32XTR |
| 6 | I/O 擴充器與板間連接器 | TCA9535、板間連接器 |

---

## 2. 第 1 頁：系統框圖與電源樹

無實體器件。此頁存在的目的是讓審查者在不翻閱其他頁的情況下看懂電源域從屬關係與板間邊界。

### 2.1 必須畫出的電源域層級

```text
USB-C VBUS ─┬─────────────────────────────────────→ BQ25628E VBUS
             └─→ TUSB320LI VDD + VBUS_DET network（VBUS-only；AON-facing I/O 須 fail-safe 隔離）

電池包 PACK+ → BQ27427 BAT(C3) → [內建 7 mΩ high-side sense] → SRX(C2) → BQ25628E BAT
電池包 PACK− ───────────────────────────────────────────────────→ GND

BQ25628E SYS ──→ VSYS_RAW（NVDC SYS；min/max 未凍結，須由 WP3 受控）
                    │
                    ├─→ TPS63802 ──→ 3V3_AON (常在)
                    │                   ├─→ ESP32-S3／TCA9535
                    │                   ├─→ RV-3028-C7 VDD + 超級電容後備
                    │                   ├─→ I²C／INT 上拉（含 BQ27427 通訊）
                    │                   ├─→ 負載開關 → 3V3_SD
                    │                   ├─→ 負載開關 → 3V3_TOUCH      → 轉接板
                    │                   └─→ 負載開關 → 3V3_EPD_LOGIC  → 轉接板
                    ├─→ 負載開關 → VSYS_AUDIO → MAX98357A
                    └─→ VSYS_FL_IN（核心 unswitched）→ 轉接板 load switch → VSYS_FL_SW／前光 driver
```

BQ27427 **不由 `3V3_AON` 或不存在的 `REGIN` 供電**；B3 `VDD` 是器件自身 1.8 V regulator output。
PACK+ 必須形成星點接到 `BAT`，全部充電／放電電流只可經內建 sense path 由 `SRX` 進出系統；`BAT` 的 Kelvin
要求是降低 PACK+ 感測誤差，不是允許另畫一條繞過器件的高電流路徑。

`VSYS_RAW` 不是固定 3.0–4.2 V 或 3.0–4.5 V。其穩態／瞬態 bounds 依 BQ25628E `VSYSMIN`、`VBAT`、source
mode、system／charge load、DPM／thermal regulation、BATFET 與 dropout；WP3 在這些輸入受控後才可導出
min/max，供 audio load switch、frontlight adapter、EPD input 與 TPS63802 資格使用。

### 2.2 必須標註的邊界

| 邊界 | 內容 |
| --- | --- |
| 板間連接器 | G1–G7 函數群（見 §7.2）；**G7 高壓／VCOM 腳數為 0** |
| 高壓域 | ⛔ EPD ±HV 與 VCOM **完全不進核心板**，由轉接板本地產生 |
| 天線區 | ESP32-S3-WROOM-1 天線投影區，全層禁銅 |

### 2.3 必須標註的四個電源狀態

引用 [power-tree.md](power-tree.md) §4 的四狀態表（Active／Idle／Standby／Deep Sleep），
在此頁以表格重述每個域在各狀態的開關位置。深睡目標依 **D1 決策**為 **≤50 µA 上限**（不是 35 µA typ）。

---

## 3. 第 2 頁：USB-C／充電／電源路徑

### 3.1 器件

| 位號 | 器件 | 封裝 | 位址 |
| --- | --- | --- | --- |
| `U201` | BQ25628ERYKR | **RYK0018A WQFN-HR-18（3.0×2.5 mm，無中央 EP）** | I²C **0x6A** **[凍]** |
| `U202` | TUSB320LIRWBR | **RWB0012A X2QFN-12（1.6×1.6 mm，無中央 EP）** | 模式待 S-9；I²C 僅可為 0x47／0x67 |
| `J201` | USB-C 插座（功能 sink／device-only；16-pin vs 24-pin 與 exact MPN 未凍結） | — | — |
| `D201` | USB-C 入口 ESD 陣列 | — | — |

### 3.2 🔴 `RILIM` 是必裝安全元件（新冲突一的結論）

這是 WP4 發現的最重要接法約束。詳見 [key-calculations.md](key-calculations.md) §5。

| 事實 **[手]** | 後果 |
| --- | --- |
| `IINDPM` 暫存器 POR 預設 = **3200 mA** | 韌體未介入時輸入限流是 3.2 A |
| **移除轉接器時 `IINDPM` 自動重置回 3.2 A** | 每次拔插都回到 3.2 A |
| 實際輸入限流 = `ILIM` 腳與 `IINDPM` **兩者取小** | 只有 `ILIM` 腳能提供與韌體無關的硬體夾制 |

> 🔴 PRD 要求的「硬體輸入限流默認不高於 500 mA」**只能**由 `ILIM` 腳電阻實現。
> `RILIM` 因此不是可選保護，而是**必裝且不可省的安全元件**。

**接法**：

| 位號 | 值 | 接法 |
| --- | --- | --- |
| `R201` | **5.6 kΩ ±1 %** | `ILIM` 腳 → GND |
| `R204` + `C204` | **1.2 kΩ + 330 nF，串聯支路** | 整條 RC 支路與 `R201` 並聯；🔴 必裝 |

驗算 **[算]**：把 `KILIM` 的 1.6 A 規範外推後得到 **398…496 mA**。這不是 0.4–0.5 A 的保證窗口，
不得先宣稱滿足 500 mA 門。且低端 397.9 mA 跨入 SLUSFA4C §8.3.3.3 的「below 400 mA」條件，資料手冊明文
要求上述 1.2 kΩ + 330 nF RC。WP9 必須量測上電／穩態／拔插／弱源輸入電流 ≤500 mA 才可關閉 U4。

### 3.3 🔴 500 mA 硬體默認與 1 A 電池充電互斥：採 L1 + DNP 預留 L3

固定 `RILIM` = 5.6 kΩ 時可達的電池充電電流僅 **0.43 – 0.60 A** **[算]**（尚未扣系統併載），
PRD 已凍結的「最高 1 A 電池充電」在此條件下物理不可達。

**EVT 基線（L1）**：`RILIM` 恆在；資格通過後由韌體寫 `EN_EXTILIM`=0 停用 `ILIM` 腳，改由 `IINDPM` 控制。

- 優點：零額外元件；POR 與韌體無關時為 500 mA；`WATCHDOG` 逾時自動把 `EN_EXTILIM` 復位為 1，硬體夾制自動恢復
- 代價：快充期間硬體夾制不存在，保護退為 `IINDPM` + `VINDPM` + watchdog

**同板 DNP 預留（L3）**：

| 位號 | 值 | 裝件 | 接法 |
| --- | --- | --- | --- |
| `R202` | 4.02 kΩ ±1 % | **DNP** | 與 `R201` 並聯，經 `Q201` 切入 |
| `Q201` | N-MOSFET（小信號） | **DNP** | 閘極 ← 擴充器 P15；閘極下拉 100 kΩ → 預設關斷 |
| `R203` | 100 kΩ | **DNP** | `Q201` 閘極下拉 |

L3 裝件後硬體夾制永不消失，只在刻意動作下抬升到約 0.96–1.17 A **[算]**。
EVT 兩種方案在**同一塊板**上可切換，不需改板。

⚠ **L1 拔插不對稱風險（韌體契約 + WP9 故障注入）**：拔線時 `IINDPM` 重置為 3.2 A，但 `EN_EXTILIM` **不重置**。
若韌體已寫 `EN_EXTILIM`=0 且未在拔線事件重設，則重插瞬間硬體與暫存器夾制**同時不存在**。
→ 韌體必須在 VBUS 移除中斷中把 `EN_EXTILIM` 寫回 1。此項列入 WP9 故障注入（未關閉項 U5）。

### 3.4 TUSB320LI 接法（S-9已有工程实现，实物资格未关闭）

2026-09-08当前实现覆盖本节旧待选描述：U202 GPIO模式，ADDR NC、PORT/EN_N接地；TPS70933由VBUS供3V3_USB_CC。
OUT1/2本地上拉经AUP2G07开漏缓冲到P16/P17，R602/R603改10k AON上拉；不会加入TUSB I²C地址。
TPS3700的105k/10k分压与1nF滤波经AUP1G17输出VBUS_VALID_AON至GPIO2。完整引脚/误差/失电假设见[工程记录](lib/review/USB2-S9-A-stage.md)。
本节以下未定事项保留历史来源语境，不再覆盖上述已实现接法；半掉电、漏电、3ms及ROM等仍未关闭。

精確 pinout：1=`CC1`、2=`CC2`、3=`PORT`、4=`VBUS_DET`、5=`ADDR`、6=`INT_N/OUT3`、
7=`SDA/OUT1`、8=`SCL/OUT2`、9=`ID`、10=`GND`、11=`EN_N`、12=`VDD`。

| 腳位 | 接法／事實 | 理由 |
| --- | --- | --- |
| `VDD` | ← **VBUS-derived rail**，本地去耦 | PRD／design.md VBUS-only；拔線後 VDD=0、電池側負載=0 |
| `EN_N` | internal pull-up 提供停用預設；是否跨域控制待 S-9 | ⛔ 不得由 P10／AON GPIO 直接驅動未上電 U202 |
| `PORT` | → GND | 固定 UFP／sink-only **[凍]** |
| `VBUS_DET` | 經 **855–920 kΩ** 接 system VBUS | 此 pin 不是直接接 VBUS |
| `CC1`／`CC2` | 各一顆 5.1 kΩ Rd 下拉（**DNP，退路**） | TUSB320LI 內部已提供 Rd；DNP 僅作純電阻退路 |

`ADDR` 的受控事實為：NC=GPIO mode、L=I²C 0x47、H=I²C 0x67。舊 0x60／0x61 敘述不適用。

**S-9 必須在原理圖建立前一次關閉**：VBUS→VDD 接法、GPIO 或 I²C mode、I²C 位址（若用）、完整的
OUT/ID/INT/polling 接收策略，以及每條 AON-facing 線的 VBUS=0 fail-safe isolation。隔離器／bus switch 本身
也不得由 AON 向 VBUS 反灌。需在 VBUS=0／5 V、AON=0／3.3 V 四象限量測雙向漏電與邏輯狀態。

在 S-9 關閉前不得把 U202 畫成已凍結模式，不得把 P10 直接連到 `EN_N`，也不得宣稱 source-current detection
或拔線零電池負載已通過。

### 3.5 BQ25628E 關鍵接法

| 腳位 | 接法 | 必辦／禁止 |
| --- | --- | --- |
| `CE`（active-low 充電致能） | ← 擴充器 **P05**，外部**下拉** | 🔴 資料手冊明文要求**不得浮空**；下拉 = 預設充電開啟（韌體未開機也能充電） |
| `ILIM` | → `R201` 5.6 kΩ → GND；並聯 `R204` 1.2 kΩ + `C204` 330 nF 串聯支路 | 🔴 見 §3.2；缺 RC 即阻塞 |
| `/INT` | → 擴充器 P06，上拉至 `3V3_AON` | open-drain，併入 `EXP_INT` |
| `STAT` | → 擴充器 P07，上拉至 `3V3_AON` | open-drain |
| `TS` | NTC 分壓 | ⚠ 與 BQ27427 `BIN` 的 NTC 共用或分立未定（U7），待目標電芯 NTC 曲線凍結 |
| `QON` | ← 隔離網 `QON_BTN`；與 GPIO1 網只共用機械致動 | 見 §3.6／S-10 |
| `SW`（Pin 16） | → **2.2 µH**、`ISAT` ≥ 2 A 電感；47 nF bootstrap capacitor 接 `SW`–`BTST` | Pin 名是 `SW`，不是 `LSW`；紋波 38 % **[算]** |
| `CSYS` | **2 × 22 µF** **[算]** | 最壞降額後 22.0 µF ≥ 20 µF 需求 |

### 3.6 BATFET `QON` 與 Power 鍵隔離（S-10）

2026-09-07（Codex）：已实现SW201=EP21SD1ABE侧按工程候选，R528=10k/0402连接3V3_AON与GPIO1。
规格别名QON_BTN在实际KiCad中沿用BQ_QON。端子1/3与4/6为两独立常开接点；不得把信号直接合网。
局部电路/布线和反向网络测试通过，精确3D、微电流可靠性与实物行为仍未通过，见[库件记录](lib/review/EP21SD1ABE-A-stage.md)。

**[凍]** 出廠 ship mode 只能由 BQ25628E `QON` 或 VBUS 解除。可共用機械致動器，但必須有兩個電氣網：

| 網路 | 接法 | 硬門 |
| --- | --- | --- |
| `KEY_POWER_MCU` | GPIO1，上拉至 `3V3_AON`；接按鍵一刀至 GND | deep-sleep active-low wake |
| `QON_BTN` | BQ25628E `QON`；接按鍵另一刀至 GND | ship mode 中不依賴 AON；不得接 AON pull-up |

首選是雙刀 momentary switch。若機構料號不提供雙刀，需提出可在 AON=0 工作的隔離 FET／等效電路並重新審查。
⛔ 兩網同名或直接短接是阻塞缺陷，不再列為可接受 ERC 例外。

### 3.7 本頁必須避免的錯誤

| # | 禁止 | 後果 |
| --- | --- | --- |
| E2-1 | ⛔ 省略 `R201`（`ILIM`） | 輸入限流退為 `IINDPM` POR 3.2 A，違反 PRD 硬體默認並構成安全問題 |
| E2-2 | ⛔ `CE` 浮空 | 資料手冊明文禁止；充電行為不定 |
| E2-3 | ⛔ TUSB320LI `VDD` 接 `3V3_AON` | 違反 VBUS-only；拔線後增加電池負載 |
| E2-4 | ⛔ AON GPIO／I²C pull-up 直接接未上電 U202 | 經 I/O 反灌 VBUS domain；拔線零負載失效 |
| E2-5 | ⛔ ESD 陣列接在 CC 電阻之後 | 保護失效 |
| E2-6 | ⛔ `QON_BTN` 與 `KEY_POWER_MCU` 共網 | ship mode 跨域漏電／閾值不確定；違反 S-10 |
| E2-7 | ⛔ 省略 ILIM 的 1.2 kΩ + 330 nF 串聯 RC 支路 | 計算低端 <400 mA，違反 SLUSFA4C §8.3.3.3 |

---

## 4. 第 3 頁：電池／燃料計／RTC

### 4.1 器件

| 位號 | 器件 | 封裝 | 位址 |
| --- | --- | --- | --- |
| `U301` | BQ27427YZFR | **YZF0009 DSBGA-9（1.62×1.58 mm、3×3、P0.5）** | I²C **0x55**（固定） |
| `U302` | RV-3028-C7 family；`SUPPLIER-CONFIRMED-ORDERABLE-P/N: TBD`，不是可採購料號 | **C7 SON-8（3.2×1.5×0.8 mm、P0.9，無 EP／NC）** | I²C **0x52**（固定） |
| `C301` | approved rechargeable supercapacitor／LIC（`VBACKUP`）；coin battery 均排除 | exact part／package 未凍結 | 見 §4.4 |
| `J301` | 電池連接器（≥3 線，防反鎖扣）；3,500–5,000 mAh target／3,500 mAh hard floor | — | exact cell 未凍結 |

`U302` 的 BOM／library freeze 還要求 supplier quote／specification ID、exact orderable suffix、reel／packaging
及對應 controlled datasheet；family name／placeholder 不足以放行。

2026-08-13 A-stage checkpoint 已接入 U302、C302、R303–R305 与 TP14。当前 C301 尚未选型，因此采用官方
Application Manual Rev. 1.4 §7.1 的 **no-backup-source** 接法：U302.6 `VBACKUP` 经 `R304=10 kΩ` 接 GND；
U302.8 `EVI` 经 `R303=10 kΩ` 上拉 `3V3_AON`；U302.2 `INT` 原经R305上拉至GPIO2/TP14；2026-09-08改为共享EXP_INT/GPIO4，R305 DNP、R502唯一已装100k上拉，TP14为共享IRQ；
U302.7 VDD 以 `C302=100 nF` 去耦。批准 C301 后才允许把 R304 改 DNP。该边界避免以未冻结 footprint 虚构
后备电容，但不关闭 24 h 保时、EEPROM、精确料号或 B-stage。

2026-08-13 A-stage fuel-gauge checkpoint 已接入 U301、C303/C304、R301/R302/R306/R307 与 TP4。
J301/harness 尚未冻结，故入口止于 `TP4` 与 `R306=0 Ω/0805`（MB1）；下游 `BAT_PACKP` 只经 U301.C3
`BAT`→内建 7 mΩ sense→U301.C2 `SRX` 到 `PACK_BAT`，没有另画绕过 sense 的高流支路。C303=1 µF
只对 BAT 本地去耦，C304=2.2 µF 只接 VDD；R301/R302=1 MΩ 保持 DNP。该切片不是 J301、目标电芯、
NTC、F0 电流/热或不同身份 B-stage 签核。

### 4.2 BQ27427 接法

正確 YZF0009 球位：A1=`GPOUT`、A2=`SDA`、A3=`SCL`、B1=`BIN`、B2=`VSS`、B3=`VDD`、
C1=`VSS`、C2=`SRX`、C3=`BAT`。**器件沒有 `REGIN`。**

| 球位／腳位 | 接法 | 必辦／禁止 |
| --- | --- | --- |
| C3 `BAT` | PACK+ 星點的 battery-side **載流端**；另以最短 Kelvin 幾何取樣；1 µF 至 VSS 靠近器件 | ⛔ 不得把 BAT 畫成只載微安的旁路 sense 線 |
| C2 `SRX` | 接 BQ25628E `BAT`／system-side battery rail | 全部充放電電流由 BAT→內建 7 mΩ sense→SRX；禁止 PACK+→charger/load 旁路 |
| B3 `VDD` | 2.2 µF 去耦至 VSS | ⛔ **1.8 V regulator output，不得接 `3V3_AON` 或供電其他器件** |
| A1 `GPOUT` | → 擴充器 **P04**（平時 input／released；外部上拉至 `3V3_AON`） | BQ27427 端為 open-drain。TCA9535 output 是 push-pull；喚醒時僅可短暫 output-low ≥`tSHUP`，隨即回 input，禁止 output-high |
| B1 `BIN` | 当前 embedded-battery A-stage 以 `R307=10 kΩ` 接 VSS | TI 推荐的未使用/embedded battery 默认终接；目标电芯 NTC／battery-insertion contract 与充电器 `TS` 共用或分立仍待 U7 冻结，冻结后必须重审，不得直接短路至 VSS/VCC |
| A2／A3 `SDA`／`SCL` | I²C 匯流排 | 見 §4.3 |
| B2／C1 `VSS` | GND | 兩顆球都必須顯式出現在 symbol 並接地 |

**載流門**：SLUSEB5B 給 `ISRX` 長期 RMS 2.0 A、10% duty peak RMS 3.5 A（−40…+70 °C）。精確電芯、音訊、
刷新與充電併載定案後，最壞 RMS／峰值必須低於此界；BAT/SRX breakout、過孔與銅寬要由板廠 stackup 計算，
並以雙向充放電壓降／溫升實測關門。只做 continuity 或只把 `BAT` 畫成 Kelvin 細線都不合格。

**深睡模式：SLEEP（不用 SHUTDOWN）**，依 **D1 決策**。理由見 [key-calculations.md](key-calculations.md) §8.4：
SLUSEB5B 未明文記載 SHUTDOWN 喚醒後學習參數是否保留，但架構事實（資料記憶體為揮發性 RAM、SHUTDOWN 停用
內部 1.8 V LDO）足以推論**不保留**。若推論成立，D2 的真實代價是「每次喚醒都需重下載化學檔案與全部
data memory 參數」，遠大於原記錄的「失去深睡期間追蹤」。

⚠ 此推論**未經驗證**，狀態為「數據手冊未載，WP9 台架驗證」（未關閉項 U11）。

### 4.3 🔴 BQ27427 I²C 浮空防護

`3V3_AON` 關閉（ship mode）時，I²C 上拉消失，但 BQ27427 由 `BAT` 直供仍在工作，其 I²C 腳將浮空。

| 位號 | 值 | 裝件 | 說明 |
| --- | --- | --- | --- |
| `R301`／`R302` | 1 MΩ | **DNP（選項 P1）** | `SDA`／`SCL` 各一顆下拉 |

裝件則深睡增加 **+6.6 µA** **[算]**，會顯著吃掉 D1 餘裕 → **預設 DNP**，待 WP9 ship mode 實測後決定
（未關閉項 U9）。

### 4.4 🔴 超級電容選型準則（新冲突二的結論）

[power-tree.md](power-tree.md) §5 的深睡元件表**漏了超級電容漏電這一行**。涓流充電器充飽後，漏電由
`3V3_AON` 持續補償，因此它是**常態深睡負載**。

TUSB320LI 修正為 VBUS-only 後，固定已知項 + 超級電容 1–5 µA 的深睡計算包絡為
**36.45–40.45 µA [算]**，對 50 µA 暫餘 **9.55–13.55 µA**。這仍未含 IMU、負載開關與板級漏電，
所以不構成 D1 或整板深睡通過；超級電容漏電仍是關鍵選型參數。

| # | 準則 | 值 | 理由 |
| --- | --- | --- | --- |
| S1 | 25 °C、實際施加電壓下漏電 | **≤5 µA** | 10 µA 級只餘 4.55 µA，在 IMU 與開關漏電未實測前不可接受 |
| S2 | 額定電壓 | **≥3.3 V** | 保留篩選門；實際最大充電電壓仍需核對，typ二極體壓降不能當保證裕量 |
| S3 | 有效容量（含容差、溫度、老化） | 滿足自洽條件 | 標稱值不等於壽命末期有效值 |
| S4 | 元件工作溫度 | 至少 −20…+60 °C（2026-09-11 使用者決定放寬；原值 −40…+85 °C） | 元件能力。放寬係為採用 RTC 後備候選 CPH3225A（原廠目錄 −20…+60 °C）。**後果**：低於 −20 °C 或高於 +60 °C 時 RTC 後備不保證；Rev A 整機仍受 N16R8 baseline +65 °C 限制 |
| S5 | 滿充時間 | 可納入產線節拍 | 實際初態/調理及達指定V_ready時間待驗；3 kΩ/100mF約15min到95%僅零初壓EDLC線性例，不是保證且不得套用LIC |
| S6 | 類型 | 只允許經批准的可充電 supercapacitor／LIC | **[凍]** 一次性與可充電 coin battery 均排除；精確 part／package 仍阻塞 |

⚠ 容量本身**不凍結**：容量與漏電互相牽制（漏電越大需要越大容量，容量越大漏電通常越大），
[key-calculations.md](key-calculations.md) §6以LSM180nA指定条件重算的例值為8.32…474.97mF；
舊60nA/2.77…469mF不是後備LSM依據。例值仍假設1.87V窗口，實際V_ready、全程負載及有效容量須由資料/實測閉合（U6）。

### 4.5 🔴 RV-3028-C7 EEPROM 出廠預設會使後備功能完全失效

兩個關鍵設定都在 **EEPROM 37h**，出廠預設為**停用** **[手]**：

| 欄位 | 出廠預設 | 本設計需要 |
| --- | --- | --- |
| `TCE`（涓流充電使能） | **停用** | **啟用** |
| `TCR`（串聯電阻） | 00 = 3 kΩ | 00 = 3 kΩ（維持） |
| `BSM`（後備切換模式） | **00 = 切換停用** | **11 = LSM** |
| `FEDE` | 1 | 維持 1 |

> 🔴 **產線／bring-up 必辦**：出廠或首次上電必須寫入 EEPROM 37h。
> 若略過，超級電容既不會充電、也不會在主電池斷開時接手，**24 小時保時直接失效且無任何硬體徵兆**。

⚠ 順序約束 **[手]**：讀寫 EEPROM 前必須先把 `BSM` 設為 00 或 10（停用切換），寫完再設回 11。

**維持既定後備切換模式 LSM（`BSM`=11）**，不重選DSM：舊條件模型提示DSM切換點接近AON下衝時有非必要切換風險，並非已量得的下衝或必然誤切換。實際V_ready、LSM切入與後續保持範圍仍待資格驗證，見[key-calculations.md](key-calculations.md) §6.7。

**未用腳硬門**：Pin 8 `EVI` 不得浮空，裝 10 kΩ 上拉至 RTC `VDD`；Pin 1 `CLKOUT` 可留 no-connect，但
出廠 EEPROM 35h 預設會輸出 32.768 kHz，必須把 `CLKOE`=0 且 `CLKF`=0（或 `FD`=111）寫入並讀回，否則
不是「未使用」。EEPROM 35h 與 37h 都進入產線 programming/verify 清單。

### 4.6 電池連接器

| 項 | 值 |
| --- | --- |
| 線數 | **≥3**（`BAT+`、`BAT−`、`NTC`） **[凍]** |
| 型式 | 防反插 + **鎖扣** **[凍]** |
| 熱插拔 | ⛔ 不支援（內部可維修更換，非熱插拔） **[凍]** |

⚠ **電池更換必然觸發燃料計重初始化**：拔除電池包會使 BQ27427 完全失電並遺失 RAM。
更換後必須重新執行化學檔案配置與學習循環——這不是可選售後步驟，而是燃料計恢復精度的必要條件。
→ 必須寫入 WP8 首次上電／調試作業指導與售後維修流程。

### 4.7 本頁必須避免的錯誤

| # | 禁止 | 後果 |
| --- | --- | --- |
| E3-1 | ⛔ 用 BQ27427 `VDD` 供電其他器件 | 資料手冊明文禁止；1.8 V 調節器過載 |
| E3-2 | ⛔ 略過 EEPROM 37h 寫入 | 24 h 保時直接失效，無硬體徵兆 |
| E3-3 | ⛔ 用 2.7 V 額定超級電容 | 不符S2；無法以typ二極體壓降證明不過壓，存在壽命/漏電風險 |
| E3-4 | ⛔ 選漏電 10 µA 級超級電容 | 深睡餘裕降到 2.85 µA，IMU 未實測前不可接受 |
| E3-5 | ⛔ 電池連接器無鎖扣或可反插 | 反接損壞；運輸振動脫落 |

---

## 5. 第 4 頁：`3V3_AON` 與功能域開關

### 5.1 器件

| 位號 | 器件 | 封裝 |
| --- | --- | --- |
| `U401` | TPS63802 | **DLA0010A 10-Pin VSON-HR（3.0×2.0 mm，0.5 mm pitch），無中央 EP** |
| `L401` | 0.47 µH XFL4015 family／body-envelope reference candidate；exact suffix／orderable MPN 未凍結 | **4.0×4.0×1.5 mm family body envelope**；land pattern 未凍結 |
| `U402`–`U405` | 負載開關 ×4 | 見 §5.5 |

### 5.2 TPS63802 逐腳接法

| # | 腳位 | 接法 | 必辦／禁止 |
| --- | --- | --- | --- |
| 1 | `EN` | ← `VSYS_RAW`（經電阻） | ⛔ **不得浮空**；⚠ 啟動需 `VIN > 1.8 V` **[手]** |
| 2 | `MODE` | → **GND**（power save） | ⛔ **不得浮空**；🔴 見 §5.4 保留跳線 |
| 3 | `AGND` | → GND | — |
| 4 | `FB` | ← 分壓中點 | 見 §5.3 |
| 5 | `PG` | 100 kΩ 上拉至 TPS63802 本地 `3V3_AON_SRC` → 擴充器 **P14** | open-drain，必須上拉；MB2 斷開時仍可直接觀察轉換器 PG |
| 6 | `VOUT` | → `3V3_AON_SRC` → `R509/MB2` → 系統 `3V3_AON` | MB2 必須為可拆換 0 Ω/0805，兩端保持可探測 |
| 7 | `L2` | → `L401` | ⛔ **不得與 L1 對調** |
| 8 | `GND` | → GND（功率地） | — |
| 9 | `L1` | → `L401` | ⛔ **不得與 L2 對調** |
| 10 | `VIN` | ← `VSYS_RAW` | — |

2026-08-13 MB2 A-stage contract：`R509.1=3V3_AON_SRC`、`R509.2=3V3_AON`；源側只包含
U401.6、C402.1、C403.1、R401.1、R403.1 與 R509.1，所有常供負載都在 R509.2 下游。負載側使用 KiCad
官方 `PWR_FLAG` 明確表示電力經已安裝的 passive 0 Ω 傳入；這是 ERC 對 removable breakpoint 的必要宣告，
不得用來掩飾實際未連通或未供電的 rail。R509 exact MPN、電流／熱額定、替換分流時的壓降與不同身份 B-stage
仍未凍結。

### 5.3 FB 分壓與電容

| 位號 | 值 | 精度 | 說明 |
| --- | --- | --- | --- |
| `R401` | 560 kΩ | **±0.5 %** | 上臂 |
| `R402` | 100 kΩ | **±0.5 %** | 下臂；⛔ 資料手冊硬上限 **R2 ≤ 100 kΩ** **[手]** |
| `C401` | **22 µF** | X5R/X7R ≥6.3 V | `CI`（採 E2 決策，非 10 µF） |
| `C402` | **22 µF** | X5R/X7R ≥6.3 V | `CO`（單顆，`VOUT` ≤3.6 V 允許） |

**PWM 規範條件下的 VOUT 算術窗口 [算]：3.2394…3.4177 V**
（含 `VFB` ±1 %、分壓 ±0.5 %、`IFB` max 100 nA）。`VFB` ±1 % **只規範 PWM mode**，不得外推到
尚未判定模式的 automatic PWM/PFM 工作點；該窗口不是 automatic/PFM 資格證據。

**分壓靜態電流 [算]：5.00 µA** — 這是 R2 ≤ 100 kΩ 限制下的**數學下限**，不可通過提高阻值降低。
它是 PRD 凍結的同步升降壓拓樸的架構成本，已計入 D1 決策。

### 5.4 🔴 `MODE` 與 1.06 A 的正確邊界

`IPWM/PFM`=1.06 A 的完整定義是**進入 PFM 的峰值電感電流**，不是輸出負載切換點。舊「所有正常狀態都在
PFM」結論撤回。`MODE`=LOW 只表示 automatic PWM/PFM；HIGH 才表示 forced PWM。

| 必辦 | 說明 |
| --- | --- |
| 🔴 `MODE` 選擇 | 原理圖保留受控 LOW／HIGH 選擇；復位與深睡必須硬體保證 LOW |
| 🔴 模式／紋波台架 | LOW 時掃 VIN 3.0–5.0 V、負載 1 mA–2 A，以 SW／電感電流波形記錄實際轉換；HIGH 做同條件對照 |
| ⚠ 活動態控制 | P15 與 L3 預留衝突；在量測與資源決策前不凍結 MCU 控制 |

3.2394…3.4177 V 只適用資料手冊 PWM accuracy 條件；到 3.0／3.6 V 的 0.2394／0.1823 V 距離**不是 PFM
紋波預算**。兩種 MODE 都必須直接證明 `VOUT` 全時域在 3.0–3.6 V。

### 5.5 電感選型（C2 決策）

**C2 決策**：選 **±20 % 或更緊**容差的 0.47 µH，使有效值 0.376–0.564 µH 完整落入資料手冊建議工作條件
窗口（MIN 0.37／NOM 0.47／MAX 0.57 µH）。

理由：資料手冊同時給出「有效值 MIN 0.37」與「電感有效值可能變動 +20 %／−30 %」。標稱 0.47 µH 在 −30 %
時為 0.329 µH，**低於 0.37 µH 下限**——兩個約束若相乘則算術上無解。C2 通過限定容差消除該矛盾，
代價是排除 −30 % 容差料號、供應商池收窄。

| 驗算 **[算]** | 結果 |
| --- | --- |
| IPEAK @ VIN=3.0 V 壓力點、L=0.376 µH、1.00 A 負載（不是已知最壞 rail bound） | 1.4812 A |
| 對 `IPK` MIN 4 A 的裕度 | **2.70×** ✅ |
| 對 Isat 5.4 A 的裕度 | **3.04×** ✅ |

⚠ **未關閉項 U2**：TPS63802 推薦表中的 `XFL4015-471ME` 名稱只作 reference。exact suffix／可訂購 MPN、
容差、溫度與 DC bias 降額、Isat 定義及 supplier-controlled land pattern 均未取得；全部關閉前不得把它寫成
合格／凍結料號。**這是 C2 決策能否落到實料的前提。**

### 5.6 四個功能域負載開關

| 位號 | 輸出軌 | 使能來源 | 預設 | 去處 |
| --- | --- | --- | --- | --- |
| `U402` | `3V3_SD` | 擴充器 **P00**；`R604=100 kΩ` 下拉 | 關 | `R514/MB3` → microSD；`TP5` 在 MB 下游 |
| `U403` | `3V3_TOUCH` | 擴充器 **P01**；`R605=100 kΩ` 下拉 | 關 | `R515/MB4` → 轉接板；`TP6` 在 MB 下游 |
| `U404` | `3V3_EPD_LOGIC` | 擴充器 **P02**；`R606=100 kΩ` 下拉 | 關 | `R516/MB5` → 轉接板；`TP7` 在 MB 下游 |
| `U405` | `VSYS_AUDIO` | 擴充器 **P03**（下拉）；当前 `R507=100 kΩ` 保證 default-off | 關 | `R508/MB6` → MAX98357A |

`U402`–`U405` 均已建立 **TPS22916CYFPT** A-stage engineering candidate；精確身份尚未經不同身份 B-stage
或採購/F0 凍結。共同選型條件：

| 條件 | 值 | 理由 |
| --- | --- | --- |
| 關斷漏電 | **≤0.5 µA @25 °C** | 四顆合計須 <1 µA **[估]**，否則吃掉 D1 餘裕 |
| 使能電平 | 3.3 V 邏輯相容 | 由 TCA9535 驅動 |
| 輸出端防反灌 | 需要 | 轉接板側電容可能反灌 |
| TPS22916CYFPT 共同邊界 | 1–5.5 V、2 A、`ISD` max 100 nA、reverse leakage max 300 nA、true reverse-current blocking；RDS(on)、dropout、熱與瞬態仍須 WP3／台架覆蓋 | 三路 0.5 A 需求在額定內，但不等於系統資格；音訊域仍須以受控 `VSYS_RAW` min/max／峰值驗證 |

四路精確 pin contract 均為 A1=`VOUT`、A2=`VIN`、B1=`GND`、B2=`ON`。U402/U403/U404 分別使用
`3V3_SD_SW/3V3_TOUCH_SW/3V3_EPD_LOGIC_SW`、共同 VIN=`3V3_AON`、EN=`EN_3V3_SD/EN_3V3_TOUCH/EN_3V3_EPD_LOGIC`；
`C508/C509/C511=1 µF` 必須靠近 VIN/GND，`R514/R515/R516=0 Ω/0805` 同時是 MB3/MB4/MB5，TP5/TP6/TP7
在其下游。U405 使用 A1=`VSYS_AUDIO_SW`、A2=`VSYS_RAW`、B2=`EN_VSYS_AUDIO`；`C507=1 µF`、MB6/TP8
保持既有契約。TI `SLVSDO5F`
要求 CIN 靠近 VIN 並使 VIN/VOUT/GND 銅短而寬。當前原理圖／PCB 只構成 A-stage candidate；F0、WP3 與
不同身份 B-stage 未關閉。

### 5.7 本頁必須避免的錯誤

| # | 禁止 | 後果 |
| --- | --- | --- |
| E4-1 | ⛔ `EN` 或 `MODE` 浮空 | 資料手冊明文禁止；行為不定 |
| E4-2 | ⛔ `L1`／`L2` 對調 | 開關節點錯接，整板無法上電 |
| E4-3 | ⛔ `R402` > 100 kΩ | 違反資料手冊硬上限 |
| E4-4 | ⛔ `CO` 用 0.47 µH + 10 µF 組合 | 資料手冊 Table 10-1 明文不允許（僅限 `CO`，`CI` 不受此限） |
| E4-5 | ⛔ `PG` 無上拉 | open-drain 永遠讀為低，誤判電源未就緒 |
| E4-6 | ⛔ 負載開關預設上拉（開啟） | 深睡時功能域未關斷 |

---

## 6. 第 5 頁：ESP32-S3／儲存／音訊／IMU

### 6.1 器件

| 位號 | 器件 | 封裝 | 位址 |
| --- | --- | --- | --- |
| `U501` | **ESP32-S3-WROOM-1-N16R8** **[凍]** | **41-pad 模組（Pad 40 GND、Pad 41 EPAD/GND）** | —；baseline ambient **−40…+65 °C** |
| `J501` | microSD 插座（板緣，使用者可插拔） | — | — |
| `U502` | MAX98357AETE+T | **TQFN-16 + EP（3×3 mm）** | — |
| `U503` | LSM6DSO32XTR | **LGA-14L（2.5×3.0×0.86 mm max）** | I²C **0x6B** |

U501 的 N16R8 module pads 28／29／30（IO35／36／37）被 Octal PSRAM 佔用，必須在專案 symbol 標 DNU。
模組真正 strapping GPIO 是 0／3／45／46；GPIO19／20 是 USB D−／D+，不是 strapping pins。

🔴 **溫度邊界**：WROOM-1 v1.8 把 N16R8（Octal R8）列為模組外立即環境 **−40…+65 °C**，不是 +85 °C。
只有啟用 PSRAM ECC 才可把上限提高到 +85 °C，代價是可用 PSRAM 減少 1/16；ECC 尚未成為固件／構建契約，
故 Rev A baseline 必須以 +65 °C 作元件／整機環境上限並做 enclosure hot-spot 實測。

### 6.2 ESP32-S3 GPIO 分配（依 [gpio-budget.md](gpio-budget.md) §6，M3 已決策）

RTC 池22/22、非RTC池11/11，合计33/33；GPIO2已由独立RTC改作VBUS，GPIO4共享RTC/扩展通知，仍零备用。

| GPIO | 訊號 | 狀態 | 關鍵約束 |
| --- | --- | --- | --- |
| 0 | BOOT strap + 復原焊盤 | **[矽]** | 外部上拉；⛔ 禁掛大電容 |
| 1 | `KEY_POWER_MCU` | **[凍]** | 上拉至 `3V3_AON`；與 `QON_BTN` 電氣隔離 |
| 2 | `VBUS_VALID_AON` | **[2026-09-07批准改配]** | U501.pad38；比较器经AON缓冲的高有效VBUS感知，不在低有效EXT1群 |
| 3 | `EPD_LE` | **[保]** | 🔴 strapping 且無內部上下拉 → **必須**外加 10 kΩ **下拉** |
| 4 | `EXP_INT`（含RTC） | **[已批准合并]** | RTC与核心/适配器开漏共同通知；聚合 `KEY_FN`／`TOUCH_INT`／`IMU_INT1`／`SD_CD`／`CHG_INT`；OD active-low |
| 5–10 | SDMMC `CLK`／`CMD`／`D0`–`D3` | **[凍]** | `CMD`／`D0`–`D3` 需上拉 |
| 11–13 | I²S `BCLK`／`LRCLK`／`DIN` | **[凍]** | `DIN` = MCU 出、放大器入 |
| 14–15 | `I2C_SCL`／`I2C_SDA` | **[凍]** | 核心板獨佔上拉 |
| 16–18 | `EPD_CKH`／`STV`／`CKV` | **[保]** | `CKH` 約 20 MHz 級，必須直連且遠離 strapping |
| 19–20 | USB `D−`／`D+` | **[矽]** | ⛔ 不可改派 |
| 21 | `EPD_D7` | **[保]** | 8-bit 資料第 8 位被迫落在 RTC 池 |
| 38–42 | `EPD_D0`–`D4` | **[保]** | GPIO39–42 為原 JTAG，已釋放 |
| 43–44 | `UART0_TXD`／`RXD` | **[矽]** | → 調試焊盤 |
| 45 | `EPD_STH`（預算佔位） | **[保／阻塞]** | VDD_SPI strap；所需 reset level 依 exact module／chip／eFuse／board configuration。contract 關閉前禁止外部 pull、adapter loading、connector mapping 與 placement |
| 46 | `EPD_OE` | **[保]** | boot+ROM print strap；維持低／禁止上拉，以保留 ROM print／boot 診斷 |
| 47–48 | `EPD_D5`／`D6` | **[保]** | — |

### 6.3 microSD

| 項 | 值 |
| --- | --- |
| 介面 | **SDMMC 4-bit** **[凍]**（⛔ 不得降為 1-bit／SDSPI） |
| 電源 | `3V3_SD`（`U402` 開關） |
| 卡偵測 | `SD_CD` → 擴充器 **P13**，上拉至 `3V3_AON` |
| 上拉 | `CMD`／`D0`–`D3` 各 10 kΩ 至 `3V3_SD` |

### 6.4 MAX98357A

| 腳位 | 接法 | 說明 |
| --- | --- | --- |
| `VDD` | ← `VSYS_AUDIO`（`U405`） | **[凍]** 由 `VSYS_RAW` 直供，⛔ 無 5 V 升壓 |
| `DIN`／`BCLK`／`LRCLK` | ← GPIO13／11／12 | I²S |
| `SD_MODE`（Pin 4） | **10 kΩ 上拉至 `VSYS_AUDIO`** | 🔴 見下 |
| `GAIN_SLOT`（Pin 2） | **三焊位可換件** | EVT 保留全部增益檔 |
| `NC`（Pins 5／6／12／13） | 明確 no-connect markers | ⛔ 不得與相鄰 GND 合併 |
| EP（KiCad 候選 synthetic Pad 17） | 接 solid GND plane | EP 內部未連接，但資料手冊要求作散熱接地；不是資料手冊第 17 pin |
| 輸出 Pins 9／10 | `OUTP`／`OUTN` → `J502` | 8 Ω／≥1 W 單聲道 **[凍]** |

2026-09-08，Codex：J502=JST SM02B-GHS-TB工程接口已提升，pin1→OUTP/SPK_P，pin2→OUTN/SPK_N；
兩MP為no-net機械焊盤，兩路BTL都不是地。ERC僅關閉兩SPK孤立標籤，完整总成／線束／M0／声學資格仍待驗。
詳見[J502工程記錄](lib/review/J502-GH-A-stage.md)。

🔴 `SD_MODE` **必須上拉至 `VSYS_AUDIO`，不得上拉至 `3V3_AON`**：
`SD_MODE` 的絕對最大值相對於 `VDD`。若上拉至 `3V3_AON` 而 `VSYS_AUDIO` 已關斷，則
`SD_MODE` > `VDD` 違反絕對最大值。上拉至 `VSYS_AUDIO` 使該違反天然不可能發生。

⚠ 最終增益檔屬 WP9 聲學資格輸出（未關閉項 U10）。⛔ 不得在此宣稱任何聲壓或失真達標。

### 6.5 LSM6DSO32XTR

2026-09-07 当前U503使用项目符号 `LSM6DSO32XTR_I2C_MODE1`：实际CS/SA0高、SDx/SCx接GND，
按ST DS13607 Table18把pins1/2/3建模为input。通用多模式符号保留；其他引脚类型、几何和物理网络不变。
变体不适用于SPI或sensor-hub Mode2；完整边界见[Mode1记录](lib/review/LSM6DSO32XTR-I2C-MODE1-A-stage.md)。

| Pin／腳位 | 接法 | 必辦／禁止 |
| --- | --- | --- |
| 1 `SDO/SA0` | → **Vdd_IO（高）** | 位址移至 **0x6B**，避開 BQ25628E 0x6A |
| 2 `SDx`／3 `SCx` | Mode 1 不用 sensor hub，兩腳各接 GND（或依最終審查改接 Vdd_IO） | ⛔ 不是主 I²C SDA/SCL，不得浮空 |
| 4 `INT1` | → 擴充器 **P12**，**100 kΩ 下拉** | 上電須 LOW／浮空；見下 |
| 5 `Vdd_IO`／8 `Vdd` | → `3V3_AON`，各自去耦 | 兩個電源 pin 不得在 symbol 中隱藏合併 |
| 6／7 `GND` | → GND | 兩腳都顯式接地 |
| 9 `INT2` | 不使用，no-connect | 依資料手冊允許保持未連接 |
| 10／11 `NC` | 保留實體 solder pads，但電氣 no-connect | ⛔ 不得接地或合併 |
| 12 `CS` | → Vdd_IO | 選 I²C／I3C；低為 SPI |
| 13 `SCL`／14 `SDA` | → 主 I²C bus | 這兩腳才是主介面 clock/data |

器件沒有 `OCS`，也沒有第二顆 `SDO/SA0`。`INT1/INT2` 的 output type 可程式，reset 時 `INT1` 是帶內部
pull-down 的輸入；symbol 不應無條件把它描述成固定 push-pull output。

🔴 **I3C 危害**：LSM6DSO32X 若在上電瞬間 `INT1` 被拉至 `Vdd_IO`，會選入 **I3C-only 模式，I²C 不可用**。
→ `IMU_INT1` 網路 ⛔ **禁止任何上拉至 `Vdd_IO`**。因 TCA9535 P 埠無內部上下拉，該網路會浮空，
故**必須**外加 **100 kΩ 下拉**保證上電為低。IMU INT 為推挽輸出，可正常克服此下拉。

⚠ **位址陷阱**：0x6B 是 BQ25628E 的**舊**位址（TI 在修訂中從 0x6B 改為 0x6A）。
依過期文件開發的韌體會在 0x6B 上與 IMU 衝突。此項必須寫入韌體註記。

### 6.6 調試／恢復焊盤（六網 Tag-Connect）

| 網路 | 來源 |
| --- | --- |
| `UART0_TX` | GPIO43 |
| `UART0_RX` | GPIO44 |
| `EN` | 模組 `EN` |
| `GPIO0` | GPIO0 |
| `3V3` | `3V3_AON` |
| `GND` | GND |

**[凍]** 僅供 EVT／維修／治具，⛔ 必須與天線區、開關節點、音訊、IMU、顯示 FPC 隔離。

2026-08-13 已实现 J503 A-stage pin contract：1=`CHIP_PU`、2=`3V3_AON`、3=`UART0_RX`、4=`GND`、
5=`UART0_TX`、6=`GPIO0`。其中 programmer `ESP_TXD` 接目标 `UART0_RX`，programmer `ESP_RXD` 接目标
`UART0_TX`；不得按相同名称直连而把方向接反。符号采用 KiCad 10 官方
`Connector_Generic:Conn_02x03_Odd_Even`，footprint 采用官方 TC2030-IDC-NL；不同身份 B-stage 与实物治具
方向仍未关闭。

### 6.7 本頁必須避免的錯誤

| # | 禁止 | 後果 |
| --- | --- | --- |
| E5-1 | ⛔ `IMU_INT1` 上拉至 `Vdd_IO` | IMU 進 I3C-only 模式，I²C 永久不可用 |
| E5-2 | ⛔ `SA0` 接地 | 位址 0x6A 與 BQ25628E 衝突 |
| E5-3 | ⛔ `SD_MODE` 上拉至 `3V3_AON` | `VSYS_AUDIO` 關斷時違反絕對最大值 |
| E5-4a | ⛔ 在 GPIO45 reset-strap contract 關閉前加任何 pull、adapter loading 或 connector mapping | VDD_SPI reset selection 未受控，可能破壞 flash／PSRAM 啟動 |
| E5-4b | ⛔ GPIO46 加上拉 | 影響 ROM print／boot 診斷，破壞產線可觀測性 |
| E5-5 | ⛔ GPIO0 掛大電容 | 復位時序破壞，無法進下載模式 |
| E5-6 | ⛔ GPIO3（`EPD_LE`）無下拉 | strapping 浮空，開機行為不定 |
| E5-7 | ⛔ SDMMC 降為 1-bit | 違反 PRD 凍結決策 |

---

## 7. 第 6 頁：I/O 擴充器與板間連接器

### 7.1 TCA9535 完整分配（位址 **0x20**）

⚠ **P 埠無內部上下拉**（設為輸入時高阻抗，漏電 ±1 µA max）→ 所有經擴充器的輸入**必須**外加上下拉。

| 埠 | 訊號 | 方向 | 外部電阻 | 說明 |
| --- | --- | --- | --- | --- |
| P00 | `EN_3V3_SD` | O | 下拉 | 預設關閉 |
| P01 | `EN_3V3_TOUCH` | O | 下拉 | 送轉接板 |
| P02 | `EN_3V3_EPD_LOGIC` | O | 下拉 | 送轉接板 |
| P03 | `EN_VSYS_AUDIO` | O | 下拉 | 預設關閉 |
| P04 | `FUEL_GPOUT` | **I（預設 released）／短暫 O-low** | 上拉 `3V3_AON` | TCA9535 是 push-pull output；平時 input，喚醒脈衝只驅低後立即回 input，禁止驅高 |
| P05 | `CHG_CE` | O | **下拉** | 🔴 不得浮空；下拉 = 預設充電開啟 |
| P06 | `CHG_INT` | I | 上拉 `3V3_AON` | OD，併入 `EXP_INT` |
| P07 | `CHG_STAT` | I | 上拉 `3V3_AON` | OD |
| P10 | BQ_PG | I | R600=10kΩ／1%上拉AON | U201.3低有效输入源合格状态，不是TPS PG；不直接连U202 |
| P11 | `KEY_FN` | I | 上拉 `3V3_AON` | **[M3]** 併入 `EXP_INT` |
| P12 | `IMU_INT1` | I | **下拉 100 kΩ** | **[M3]** 🔴 I3C 危害，見 §6.5 |
| P13 | `SD_CD` | I | 上拉 `3V3_AON` | 併入 `EXP_INT` |
| P14 | `PG_3V3_MAIN` | I | 上拉 `3V3_AON` | TPS63802 `PG` 為 OD |
| P15 | 備用／L3 預留 | — | **100 kΩ 下拉** | ⚠ 見 §7.3 |
| P16 | CC_OUT1_AON | I | R602=10kΩ上拉AON | U204.6开漏输出，不能配置推挽输出 |
| P17 | CC_OUT2_AON | I | R603=10kΩ上拉AON | U204.4开漏输出，原100k下拉已重配 |

🔴 **§7.3 备用及输入端口必须有确定终接**：
仅P15未分配并保持100kΩ下拉（L3预留）；P10为BQ_PG、R600改10kΩ／1% AON上拉，原专用GND叶支/via按批准移除。
P16/P17为CC输入并各有10kΩ AON上拉，不再算备用，也不保留100k下拉。P10配置输入/非反相，读port1 bit0并处理共享INT；PG电气与掉电资格见[BQ_PG记录](lib/review/BQ_PG-P10-A-stage.md)。
（此處偏離資料手冊約 10 kΩ 建議的說明僅針對 P15 預留下拉：採100 kΩ以降低誤設輸出高時的電阻電流；不適用於P10及P16/P17已裝的10 kΩ上拉，實際漏電仍須計入。）

⚠ **P15 資源衝突**：P15 同時是 L3 快充切換（§3.3）與 MCU 控制 `MODE`（§5.4）的候選。
兩者只能取一，需在 EVT 前明確。

### 7.2 板間連接器函數群

| 群 | 訊號 | 類型 | 腳數 | 直連要求 |
| --- | --- | --- | --- | --- |
| G1 顯示資料 | `EPD_D0`–`D7` | 高速數位（約 20 MHz 級） | **8** | ✅ 必須直連 |
| G2 顯示時序 | `CKH`、`CKV`、`STV`、`STH`、`LE`、`OE` | 高速／中速數位 | **6** | ✅ 必須直連 |
| G3 管理匯流排 | `I2C_SCL`、`I2C_SDA` | 低速 OD | **2** | ✅ |
| G4 中斷 | `EXP_INT`（wired-OR，含 `TOUCH_INT`） | 低速 OD active-low | **1** | ✅ |
| G5 低壓電源 | `3V3_EPD_LOGIC`、`3V3_TOUCH`、`VSYS_FL_IN`、`EPD_HV_IN` | 電源 | **4**（各需足夠腳數） | ✅ |
| G6 地 | `GND` | 地回流 | 依準則 | ✅ |
| G7 高壓／VCOM | ±HV、VCOM | **高壓** | **0** | ⛔ **禁止過連接器** |

G1／G2 共 14 支為 **[保]** 保留信號，WP1 定案後回填。若 WP1 選 SPI／TCON 候選，約 8 支釋放。
連接器只凍結 `>=40 contacts` envelope；exact contact count／numbering／order／MPN 在 WP1 受控面板資料與
機構輸入齊備前不得凍結。`VSYS_FL_IN` 是核心 unswitched input；adapter 擁有 load switch、`VSYS_FL_SW`
與 switched-rail test point。

### 7.3 I²C 上拉歸屬

🔴 **核心板單獨擁有 I²C 上拉。⛔ 轉接板禁止再掛 I²C 上拉電阻。**
理由：上拉並聯會使等效阻值下降、上升緣過快，且總阻值隨插上哪塊轉接板而變，無法一致驗證。

| 網路 | 上拉域 | 擁有者 |
| --- | --- | --- |
| `I2C_SCL`／`I2C_SDA` | `3V3_AON` | 核心板 |
| `EXP_INT`（wired-OR） | `3V3_AON` | 核心板 |
| RTC共享`EXP_INT` | `3V3_AON` | 核心板R502；R305 DNP，不另装第二上拉 |
| `KEY_POWER_MCU` | `3V3_AON` | 核心板 |

⛔ **禁止**把 I²C 上拉接到任何可被關閉的電源域。

**阻值**：上界 `RPU` ≤ **29.2 kΩ** **[算]**（器件級約束），實用範圍收窄至約 **2.2–10 kΩ**。
精確值取決於匯流排總電容（含 FPC 長度，屬 WP1）→ bring-up 實測上升緣確定（未關閉項 U8）。

**`EXP_INT` 阻值選 100 kΩ**（偏離資料手冊建議值，理由見 [key-calculations.md](key-calculations.md) §7.2）：
`EXP_INT` 是低速 wired-OR 中斷，不需快速上升緣，100 kΩ 可降低深睡電流。

---

## 8. ERC 驗收條件與預期例外

### 8.1 驗收命令

```bash
KICAD_CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
"$KICAD_CLI" sch erc --exit-code-violations PANDA-STD-CORE-EVT.kicad_sch
```

### 8.2 預期 ERC 例外（必須逐條書面說明，不得無理由抑制）

| # | 預期告警 | 理由 |
| --- | --- | --- |
| X1 | `KEY_POWER_MCU` 與 `QON_BTN` 鄰近／機械聯動 | 兩網必須電氣隔離；若 ERC 顯示共網，屬缺陷而非例外 |
| X2 | `PG`、`CHG_INT`、`CHG_STAT`、BQ27427 `FUEL_GPOUT` 與 `EXP_INT` 的器件端為 OD 且有上拉 | open-drain 有意設計；TCA9535 P04 本身不是 OD |
| X3 | `EXP_INT` 多驅動 | wired-OR 有意設計（核心板 + 轉接板兩顆擴充器 INT） |
| X4 | `FUEL_GPOUT` 接到 TCA9535 P04 | P04 預設 input／released；只允許 deliberate output-low wake pulse，之後回 input，禁止 output-high |
| X5 | 板間連接器 **[保]** 腳位未連接 | WP1 未定案，14 支保留信號按設計留空 |
| X6 | DNP 元件未連接（`R202`／`Q201`／`R203`／`R301`／`R302`／CC Rd） | 有意 DNP 預留 |
| X7 | BQ27427 `VDD` 僅接去耦電容 | 資料手冊明文禁止供電其他器件 |

### 8.3 ⛔ 不接受的抑制方式

- 全域關閉某類 ERC 檢查
- 無書面理由的 net class 例外
- 為消除告警而改動 **[凍]** 決策

---

## 9. 本頁規格產生的未關閉項

| # | 未關閉項 | 阻擋來源 | 解除條件 |
| --- | --- | --- | --- |
| S-1 | 負載開關 ×4 精確料號 | 未選型 | 依 §5.6 條件選型並確認漏電 ≤0.5 µA |
| S-2 | 超級電容精確料號／容量 | 未選型 | 依 §4.4 S1–S6 準則選型（U6） |
| S-3 | XFL4015 reference candidate 的 exact suffix／orderable MPN、容差、降額、Isat 定義與 land pattern | supplier-controlled data 未取得 | 全部取得並複核（U2）；在此之前不是凍結料號或封裝 |
| S-4 | NTC 共用或分立（`TS` vs `BIN`） | 目標電芯 NTC 曲線未凍結 | 電芯定案（U7） |
| S-5 | I²C 上拉精確阻值 | 匯流排總電容取決於 FPC（WP1） | bring-up 實測（U8） |
| S-6 | P15 歸屬（L3 快充 vs MCU `MODE`） | 二者取一未決 | EVT 前明確 |
| S-7 | G1／G2 實際訊號數（現以 14 保留） | WP1 未定案 | WP1 |
| S-8 | 板廠層疊書面簽核 | 未找到真實回簽；只有待回填模板 | 阻塞 WP6A 完成門與 WP7A 走線 |
| S-9 | TUSB320LI VBUS-derived VDD + mode/address + AON-off 隔離 | VBUS-only 與常供 I/O 跨域；直接連線會反灌 | GUI 前一次選定供電、mode、位址／輸出策略、fail-safe 隔離，並定義四象限漏電測試 |
| S-10 | `QON_BTN`／`KEY_POWER_MCU` 隔離 | EP21SD1ABE工程候选已布线；微电流/机构/实物资格未完成 | 两网不同net name且负控已验证；精确3D/M0待完成；WP9 覆蓋 ship/deep-sleep/長按/卡鍵 |
| S-11 | N16R8 溫度策略 | baseline 只到 +65 °C；ECC 尚未成固件契約 | Rev A 以 +65 °C 關機構／熱門；若要求 +85 °C，先凍結 ECC + PSRAM 容量代價並重驗 |
| S-12 | GPIO45 VDD_SPI reset strap | exact module／chip／eFuse／board configuration 未受控 | placement 前凍結所需 reset level；此前禁止外部 pull、adapter loading 與 connector mapping |

---

## 10. 邊界聲明

本文件是**原理圖規格**，不是已繪製的原理圖，也不是已驗證的設計。

**不宣稱**下列任一項已通過資格門：`3V3_AON` 紋波／效率／暫態／熱／深睡電流、充電安全性、
500 mA 或 1 A 充電電流、24 小時 RTC 保時、聲壓或音訊失真、BQ27427 SHUTDOWN 行為、
觸控喚醒、EPD 顯示任何光學指標。

不含任何認證聲明。「認證就緒」不等於「已認證」。
不含任何未實測的續航、聲學或效能承諾。所有 **[估]** 值只用於建立選型條件，
⛔ **不得**作為規格或採購依據。

顯示側全部訊號為 **[保]** 保留狀態，WP1 未交付任何通過文件門的顯示路線。
本規格的顯示介面僅是**連接器邊界與保留腳位**，不構成任何顯示候選已選定的陳述。

截至 2026-08-13，已建立并由 KiCad 10.0.5 解析的受控 `.kicad_sch` engineering candidate；当前
104-footprint J503 debug/recovery checkpoint 的 ERC=34（21 `pin_not_connected`、6 `isolated_pin_label`、
4 `power_pin_not_driven`、2 `pin_not_driven`、1 `pin_to_pin`）。相对 91-footprint 基线，J503 接通 U501.36/37
后 `pin_not_connected` 从 23 降为 21，其余类型不变；MB2 后唯一
`pin_to_pin` 为 U503.1 与负载侧 `#FLG0101`，取代原先 U503.1 与 U401.6 的直接 rail 提示。U301、R509 与新增
测试点与 J503/UART reference slices=0；RTC reference slice 仍只有 U302.6 `VBACKUP` 的 1 条可解释
`power_pin_not_driven`：当前用 R304 passive shunt 接 GND，不用 PWR_FLAG 隐藏无后备源事实。它仍不是完整
ERC／WP4／WP7A 放行；原理圖建立与
验收步骤、工程命名及 CLI／来源复核命令继续以 drawing runbook 与实际 EDA source 为准，不得用本规格取代原理图。
