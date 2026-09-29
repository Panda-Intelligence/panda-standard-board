# Panda 標準電子書板：電源樹與供電狀態表

日期：2026-08-10（USB／IRQ 同步：2026-09-08，Codex）
狀態：電源樹設計意圖；TUSB320LI 改回 VBUS-only 邊界、QON 隔離與 BQ27427 載流門已明列；仍非原理圖
適用板號：`PANDA-STD-CORE-EVT`

本文件記錄核心板電源樹設計意圖、軌擁有權、四種供電狀態與負載預算。它不是 KiCad 原理圖或 WP6A 凍結證據，
也**不凍結**生產 BOM、最終輸出電流、精確料號或採購決定。狀態名稱與 `design.md` §4 一致。

當前USB/IRQ工程候選及未完成資格見[USB2 S-9 A-stage](lib/review/USB2-S9-A-stage.md)；本頁深睡差量與
[key-calculations.md](key-calculations.md) §4.5使用同一指定穩態預算，不把CAD連通當作實物功耗或喚醒通過。

---

## 1. 電源樹

```text
USB-C VBUS (5 V) ─┬───────────────────────────────────→ BQ25628E VBUS
                   ├─→ TPS70933 → 3V3_USB_CC → TUSB320LI / AUP2G07 / TPS3700
                   └─→ VBUS_DET / VBUS分壓 / R209泄放（繞過BQ限流，須計入總源負載）

1S Li-Po PACK+ → BQ27427 BAT(C3) → [內建 7 mΩ high-side sense] → SRX(C2) → BQ25628E BAT
1S Li-Po PACK− ───────────────────────────────────────────────────→ GND

BQ25628E SYS ─→ VSYS_RAW
                  ├─→ TPS63802 ─→ 3V3_AON ─┬─→ ESP32-S3-WROOM-1-N16R8
                  │   (buck-boost)          ├─→ RV-3028-C7 (RTC)
                  │                         ├─→ TCA9535 #1／LSM6DSO32X
                  │                         ├─→ I²C／INT pull-up domain（連到 BQ27427，但不為其供電；
                  │                         │   CC輸出經AUP2G07隔離；TUSB不在I²C匯流排）
                  │                         ├─→ AUP1G17 VBUS監控buffer與CC接收端上拉
                  │                         ├─→ [LS] 3V3_SD ─→ microSD
                  │                         ├─→ [LS] 3V3_TOUCH ──→ connector
                  │                         └─→ [LS] 3V3_EPD_LOGIC → connector
                  ├─→ [LS] VSYS_AUDIO ─→ MAX98357A ─→ 8 Ω speaker
                  ├─→ VSYS_FL_IN ───────→ connector → [adapter LS] VSYS_FL_SW → LM3630A
                  └─→ EPD_HV_IN ───────→ connector → EPD PMIC (adapter) → ±HV／VCOM

[LS] = independently switchable branch；核心板只切換 SD／touch／EPD logic／audio。`VSYS_FL_IN` 在核心板不切換，
前光 load switch／driver／`VSYS_FL_SW` 全由 adapter 擁有。
```

BQ27427 沒有 `REGIN`，也不是 `3V3_AON` 負載；B3 `VDD` 是自身 1.8 V regulator output。`BAT` 不是只接一條
高阻 Kelvin sense 的旁路腳：PACK+ 必須以星點／短寬銅接到 `BAT`，全部充放電電流只可經器件內建 sense path
由 `SRX` 進出系統；禁止另有 PACK+→charger／load 的旁路。長期 RMS 2 A、10% duty peak RMS 3.5 A（−40–70 °C）
是 SLUSEB5B 的器件邊界，精確電芯／音訊／刷新峰值定案後仍須重算與實測。

**高壓隔離邊界**：核心板只把 `EPD_HV_IN`（低壓輸入域）送出去；±HV 與 VCOM 完全由轉接板產生與擁有，
不經板間連接器回流。與 [README.md](README.md) §3.1 一致。

---

## 2. 軌清單與擁有權

| 軌 | 電壓 | 來源 | 可否關斷 | 控制 | 擁有者 | 負載 |
| --- | --- | --- | --- | --- | --- | --- |
| `VBUS` | 5 V | USB-C | 由主機／線纜 | — | 核心板 | BQ25628E VBUS、TUSB320LI `VDD` 與 `VBUS_DET` 電阻網路 |
| `VSYS_RAW` | **未凍結的 NVDC SYS 範圍**（見 §3） | BQ25628E SYS | 否（BATFET／shutdown 除外） | I²C／QON | 核心板 | 下游全部 |
| `3V3_AON` | 3.3 V | TPS63802 | 否（EN 恆致能） | EN 綁定 | 核心板 | MCU 與常供域 |
| `3V3_SD` | 3.3 V | `3V3_AON` 負載開關 | **是** | 擴充器 P00 | 核心板 | microSD |
| `3V3_TOUCH` | 3.3 V | `3V3_AON` 負載開關 | **是** | 擴充器 P01 | 核心板 | 觸控控制器（轉接板） |
| `3V3_EPD_LOGIC` | 3.3 V | `3V3_AON` 負載開關 | **是** | 擴充器 P02 | 核心板 | EPD 邏輯（轉接板） |
| `VSYS_AUDIO` | = `VSYS_RAW` | `VSYS_RAW` 負載開關 | **是** | 擴充器 P03 | 核心板 | MAX98357A |
| `VSYS_FL_IN` | 跟隨 `VSYS_RAW`；核心板不切換 | `VSYS_RAW` 直通板間連接器 | **核心板否** | — | 核心板只輸出 unswitched input | adapter 前光 load switch 輸入 |
| `VSYS_FL_SW` | 由 adapter switch 後的前光軌 | `VSYS_FL_IN` 經 adapter load switch | **是** | adapter 控制器／driver | **adapter** | LM3630A VIN；switched-rail test point 亦由 adapter 擁有 |
| `EPD_HV_IN` | = `VSYS_RAW` | `VSYS_RAW` | 由轉接板 PMIC 自身 | 轉接板 | 核心板供 | EPD PMIC VIN |
| `±HV`、`VCOM` | 面板決定 | 轉接板 PMIC | — | 轉接板 | **轉接板** | 面板 |

### 2.1 TPS63802 EN 恆致能的理由

`3V3_AON` 是常供域，關閉它等於整機斷電，且 MCU 自身無法再把它開回來。故 `EN` 直接綁 `VSYS_RAW`
（經上拉，不浮空）。整機真正的斷電由 BQ25628E BATFET ship mode 完成，不由 TPS63802 EN 完成。

資料手冊要求 `EN` 與 `MODE` **都不得浮空**。

### 2.2 TPS63802 關鍵接法（EVT 設計要求；未經原理圖／台架凍結）

| 腳 | 網路 | 接法 | 依據 |
| --- | --- | --- | --- |
| 1 `EN` | `VSYS_RAW` 經上拉 | 恆致能，禁止浮空 | 資料手冊 SLVSEU9D |
| 2 `MODE` | 復位／深睡必須 LOW；活動態 LOW／HIGH 需可受控對照 | 禁止浮空；1.06 A 是峰值電感電流條件，不能由輸出負載預判模式 | 同上 |
| 5 `PG` | 上拉至 `3V3_AON` → 擴充器 P14 | **open-drain，必須外部上拉** | 同上 |
| 4 `FB` | 分壓回授 | 阻值於 WP4 定 | 同上 |
| 7 `L2`／9 `L1` | 0.47 µH | 不得對調；電感料號尚未凍結 | 同上 |
| 6 `VOUT` | ≥22 µF | | 同上 |
| 10 `VIN` | 10 µF | | 同上 |

`MODE` 若在深睡為 HIGH（forced PWM）會破壞靜態電流預算，故深睡 LOW 是必要條件。除此之外，
`IPWM/PFM`=1.06 A 描述的是**進入 PFM 的峰值電感電流**，不是輸出負載切換點；舊「所有正常負載均為 PFM」
結論已撤回。活動態是否 LOW 或 HIGH 尚未凍結，EVT 必須保留受控選擇並以 SW／電感電流波形掃描後決策。

---

## 3. `VSYS_RAW` NVDC 邊界與 TPS63802 工作點

`VSYS_RAW` 是 BQ25628E 的 NVDC `SYS`，不是固定 3.0–4.5 V 電源。其瞬時與穩態上下界依賴已程式化的
`VSYSMIN`、電芯 `VBAT`、USB／battery-only 模式、充電與 system load、DPM／thermal regulation、BATFET 與
路徑 dropout。這些 charger／cell inputs 尚未受控，因此本階段**不凍結數值上下界**。

| 情境 | 必須帶入的 NVDC 依賴 | TPS63802／下游處理 |
| --- | --- | --- |
| battery-only | `VBAT`、`VSYSMIN`、BATFET／sense／connector dropout、system load | 用受控最小／最大 `SYS` 判定 buck／boost、啟動、2 A 降額與 load-step |
| USB + battery | VBUS 能力、IINDPM／VINDPM、charge current、`VSYSMIN`、`VBAT`、system load、thermal/DPM | 掃插入／拔出與 DPM 轉換；不得以「約 4.5–5 V」代替 |
| battery absent／protection cut | charger configuration、VBUS 與 system load | 驗證啟動、掉電、反灌與 brownout |

### 3.1 TPS63802 輸入條件 gate

資料手冊 VIN 1.3–5.5 V、啟動 VIN >1.8 V，以及 3.3 V 輸出 2 A 能力需 VI≥2.3 V，都是待比對條件，
**不是已通過結論**。WP3 必須先以 BQ25628E／電芯受控配置導出的 `VSYS_RAW` min/max 做官方模型模擬，或以
原廠 EVM／受控 bench fallback 量測；沒有該結論不得 schematic placement、WP4 pass 或 Layout release。

### 3.2 boost 模式的電池峰值電流放大（WP3 必算）

當受控測得／計算的 `VSYS_RAW` 低於 3.3 V 輸出目標時，TPS63802 進入 boost，輸入電流大於輸出電流：

```
I_in ≈ I_out × (V_out / V_in) / η
```

以下 V_in=3.0 V、η≈90% 只是一個**壓力測試情境**，不是已凍結的 `VSYS_RAW` 下界；須由受控 NVDC 輸入取代：

```
I_in ≈ I_out × (3.3 / 3.0) / 0.90 ≈ I_out × 1.22
```

→ 低電量時 `3V3_AON` 的負載階躍會被放大約 1.22 倍反映到 `VSYS_RAW` 與電池。ESP32-S3 Wi-Fi TX 疊加
SD 寫入的最壞階躍必須以此係數換算後才與 BQ25628E SYS 能力、電池放電能力比對。

**buck/boost 交越點（約 3.3 V）落在 1S 放電曲線中段**，是裝置最常駐的工作區。`design.md` 已要求仿真
覆蓋交越點，本文件確認其為最高優先台架項，而非次要邊界。

### 3.3 N16R8 熱邊界

ESP32-S3-WROOM-1-N16R8 的模組外立即環境 baseline 為 **−40…+65 °C**。充電、Wi-Fi、刷新與音訊併發造成的
外殼內 hot spot 必須以 +65 °C 關門；不得拿 ESP32-S3 晶片結溫或其他 WROOM 變體的 +85 °C 取代。PSRAM ECC
放寬到 +85 °C 的路線尚未凍結，且會損失 1/16 可用 PSRAM。

---

## 4. 供電狀態表

狀態定義與 `design.md` §4 一致（四種）。

| 狀態 | `VSYS_RAW` | `3V3_AON` | `3V3_SD` | `3V3_TOUCH` | `3V3_EPD_LOGIC` | `VSYS_AUDIO` | `VSYS_FL_IN`／`VSYS_FL_SW` | EPD ±HV／VCOM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **工廠運輸／長期倉儲** | **SYS 下游關**（BATFET ship mode；BQ27427 仍在 battery side） | 關 | 關 | 關 | 關 | 關 | 關／關 | 關 |
| **深睡眠**（使用者「關機」） | 開，值依 NVDC 狀態 | 開 | 關 | 關（基線）／保留（見 §4.2） | 關 | 關 | 有輸入／adapter 關 | 關 |
| **閱讀待機** | 開，值依 NVDC 狀態 | 開 | 依需求 | 開 | 依候選 | 關 | 有輸入／依使用者設定 | 關 |
| **螢幕刷新** | 開，值依 NVDC 狀態 | 開 | 依需求 | 開 | 開 | 關（除同時播放） | 有輸入／adapter 可獨立控制 | **開**（嚴格按面板／PMIC 時序） |

### 4.1 進入／退出方式與允許喚醒源

| 狀態 | 進入方式 | 允許喚醒／退出 | 誤觸發防護 |
| --- | --- | --- | --- |
| 工廠運輸／長期倉儲 | 韌體經 I²C 設 BQ25628E 進 ship mode（僅工廠治具授權） | ① `QON` 拉低達 `tSM_EXIT`；② 插入 USB（VBUS） | 需治具授權；非使用者可達路徑。`QON` 有內部上拉，預設高 |
| 深睡眠 | `esp_deep_sleep_start()`；進入前關閉所有可關斷軌、確認 BQ25628E ADC 關閉 | 低有效EXT1：`KEY_POWER_MCU`(GPIO1)、共享`EXP_INT`(GPIO4)；USB插入喚醒仍為待實作／驗證目標 | Fix21（2026-09-08，Codex）：GPIO2為高有效VBUS狀態，不加入此低有效EXT1群；USB喚醒接入方式依software-gate-plan另驗。CC域有限漏電／半掉電仍未關閉；共享IRQ須逐一讀清全部來源 |
| 閱讀待機 | 由深睡喚醒或刷新完成後降階 | — | — |
| 螢幕刷新 | 韌體按面板時序開 `3V3_EPD_LOGIC` → EPD PMIC 上電序 | — | 下電序必須反向且完整放電；順序以 WP1 面板／PMIC 資料為唯一凍結依據 |

### 4.2 觸控深睡保留域

PRD 已確認：觸控喚醒**只預留不強制**。故：
- **基線**：深睡時 `3V3_TOUCH` 關斷，`TOUCH_INT` 不作喚醒源
- **保留**：`3V3_TOUCH` 為獨立負載開關，可在深睡保留；`TOUCH_INT` 經轉接板擴充器併入 `EXP_INT`
- **啟用條件**：該具體總成通過 25°C 整板 ≤50 µA、誤喚醒與恢復時序資格

⚠ **反灌約束**：`3V3_TOUCH` 關斷時，觸控控制器的 I²C／INT／RST 腳位不得經上拉把電流灌回未上電的
控制器。核心板 I²C 上拉在 `3V3_AON`（常供），因此關斷觸控電源時該控制器成為未上電節點掛在已上拉匯流排上。
→ **轉接板必須處理**：或用 I²C 隔離／切換，或選擇明確容許此條件的控制器，或改為保留觸控電源不關斷。
此項屬轉接板設計約束，列入 [interfaces-and-connectors.md](interfaces-and-connectors.md) 的轉接板規則。

---

## 5. 深睡眠靜態電流預算

門檻（PRD §162）：**25°C 整板 ≤35 µA typ、≤50 µA 上限**。此為候選門，非產品承諾。

| 元件 | 狀態 | typ | max | 依據 |
| --- | --- | --- | --- | --- |
| ESP32-S3 | Deep-sleep，RTC memory + RTC 週邊上電 | **8.0 µA** | — | 晶片規格書 v2.2 表 5-10 |
| TPS63802 | power save（`MODE`=LOW），輕載 | **11 µA** | — | 資料手冊 SLVSEU9D Iq |
| BQ27427 | SLEEP mode | **9.0 µA** | — | SLUSEB5B §5：`ISLP` |
| BQ25628E | battery-only、BATFET 開、**ADC 關** | **1.5 µA** | 3 µA | SLUSFA4C：`IQ_BAT` |
| TUSB320LI | VBUS-only，拔線後無主動电池供電 | 不作整接口0漏電保證 | — | 隔離／監控的有限漏電在下一行另計，半掉電另測 |
| USB隔離／VBUS監控差量 | VBUS=0、AON有效、CC rail穩定放電 | **3.8µA工程預算，非typ** | 非全狀態max | AUP2G07保守2.4 + AUP1G17輸入0.5 + ICC0.9；條件及假設見key-calculations §4.5 |
| TCA9535 #1 | standby，`fSCL`=0 | **0.9 µA** | 4 µA | **SCPS201E**（高／低輸入包絡 typ 均 0.9 µA） |
| RV-3028-C7 | timekeeping | **0.045 µA** | 0.060 µA | 資料手冊：`IDDO` 45 nA typ／60 nA max @3 V |
| LSM6DSO32X | power-down | **待實測** | — | 需以實際 ODR／量程複核；PRD 記錄加速度計超低功耗檔約 4.4 µA，**非 power-down 值** |
| `3V3_AON` FB 分壓 | 560 kΩ + 100 kΩ | **5.00 µA [算]** | — | `R2≤100 kΩ` 下的數學下限 |
| RTC 後備元件漏電 | 涓流充飽，由 AON 補償 | **1–5 µA [估]** | — | 精確料號未選；≤5 µA 是選型門 |
| I²C／INT 上拉 | 匯流排空閒為高 | 理想電阻壓差≈0 | — | 不代表接收器無漏電；共享IRQ僅R502裝件、R305 DNP，I²C阻值待定 |
| 關斷 switched branches 漏電 | 四路均为 `TPS22916CYFPT` A-stage candidate | **typ 未規範；待整板實測** | **每路 `ISD` max 0.100 µA @25 °C；四路器件级合计 0.400 µA** | reverse leakage 每路 max 300 nA；总和只是 datasheet arithmetic，不含 PCB/下游反灌；前光開關位於 adapter，不計為核心開關 |
| **合計（舊固定項 + USB差量 + RTC漏電估算）** | | **≈40.25–44.25µA混合工程包絡** | 非整板max | 不含IMU／開關／板漏及全部實際狀態驗證；RTC後備尚未實現 |

### 5.1 判定

USB加入前的歷史固定項35.445µA，加本批指定穩態3.8µA及RTC後備漏電估算1–5µA，為40.245–44.245µA，
四捨五入 **40.25–44.25µA**；對50µA的名義餘量約5.75–9.75µA。這混合typ、估算與部分保守器件預算，
不是整板max，也不是35µA typ或50µA門通過。IMU、switched-branch、板漏／溫度與實際DC狀態仍待驗證；
RTC後備尚未實作。舊36.45–40.45µA只作歷史值，不再漏掉USB隔離／監控差量。

**風險評級：緊，未通過。** 以下為降風險選項：

| 選項 | 節省 | 代價 |
| --- | --- | --- |
| TPS631000 取代 TPS63802（PRD 已列備選，8 µA typ） | 約 3 µA | 官方 PSpice 模型受加密限制，WP3 仿真證據較弱 |
| BQ27427 深睡進 SHUTDOWN（0.6 µA）而非 SLEEP（9 µA） | 約 8.4 µA | 失去深睡期間的荷電狀態追蹤；若重評，TCA9535 P04 平時必須 input／released，只可短暫 push-pull output-low 喚醒後立即回 input，禁止 output-high。**會影響電量計精度，需產品決策** | ❌ **未採用（2026-08-11）**：採 D1，保持 SLEEP 模式 |
| 四路统一低漏电负载开关 | U402–U405 已以 TPS22916CYFPT 收敛；器件级 `ISD` max 合计 0.400 µA @25 °C | 仍需 B-stage、温度／反灌与整板实测，不能直接从预算中扣除 |

BQ27427 的 SLEEP vs SHUTDOWN 是**產品決策**（電量精度 vs 待機電流）。✅ **2026-08-11 已決策：採 D1，保持 SLEEP 模式**。

### 5.2 韌體契約（深睡達標的必要條件）

| 契約 | 理由 |
| --- | --- |
| BQ25628E ADC 必須關閉 | ADC 開啟時 `IQ_BAT_ADC` = **260 µA**，單項即超標 5 倍 |
| TUSB320LI的AON-facing I/O在VBUS=0須隔離 | 防止直接反灌；隔離／監控有限漏電仍計入預算，不能稱零電池負載 |
| TPS63802 `MODE` 在復位／深睡必須為 LOW | 活動態策略未凍結；1.06 A 不得當輸出負載邊界 |
| 進入深睡前關閉核心 `3V3_SD`／`3V3_TOUCH`／`3V3_EPD_LOGIC`／`VSYS_AUDIO`，並命令 adapter 關閉 `VSYS_FL_SW` | `VSYS_FL_IN` 仍是 unswitched input；前光關斷由 adapter 負責 |
| 本板EXT1群同為active-low | GPIO1/4；GPIO2是高有效VBUS狀態，其USB插入喚醒接入方式另驗 |

此表是硬體與韌體的交界契約，任何一項未滿足，深睡實測必然不合格。列入 WP9 台架前置檢查。

---

## 6. 各狀態負載預算

⚠ 標記說明：**[手]** = 官方資料手冊值 · **[算]** = 由資料手冊值推算 · **[估]** = 估算，未經實測，
**不得**當作承諾。

### 6.1 螢幕刷新（最壞情境）

| 負載 | 軌 | typ | peak | 標記 |
| --- | --- | --- | --- | --- |
| ESP32-S3（含 Wi-Fi TX） | `3V3_AON` | — | **≥500 mA 供電能力要求** | **[手]** 硬體設計指南：單電源 3.3 V、≥500 mA |
| microSD 寫入 | `3V3_SD` | **[估] 100 mA** | **[估] 200 mA** | **[估]** 卡片相依，無官方統一值；**必須實測** |
| EPD 邏輯 | `3V3_EPD_LOGIC` | **待 WP1** | **待 WP1** | 面板相依 |
| EPD PMIC（TPS65185 類） | `EPD_HV_IN` | **待 WP1** | LDO1／LDO2 各 120 mA @±15 V | **[手]** SLVSAQ8G（TPS65185）；TPS651851 為 200 mA 但需 VIN ≥ 3.6 V |
| 前光（LM3630A 類，拓撲待 WP1） | adapter `VSYS_FL_SW`（input=`VSYS_FL_IN`） | **待 WP1** | 依 LED 串壓、電流、效率與 NVDC input | 核心只輸出 unswitched input；adapter 擁有 switch／driver／測試點 |
| 音訊（MAX98357A） | `VSYS_AUDIO` | 見 §6.2 | 見 §6.2 | |

**核心板供電能力凍結依據**：TPS63802 在 VI ≥ 2.3 V 時 2 A 輸出，涵蓋 `3V3_AON` 上的 MCU（≥500 mA）
+ SD + EPD 邏輯 + 觸控。前光、音訊、EPD 高壓皆**不在** `3V3_AON` 上，符合 `design.md` §4.1 的
「大電流脈衝不得無條件加到 `3V3_AON`」約束。

### 6.2 音訊負載（`VSYS_AUDIO`，直供 `VSYS_RAW`）

MAX98357A 資料手冊值 **[手]**：
- 單電源 2.5–5.5 V
- 8 Ω + 68 µH 負載：THD+N=1% 時 **1.4 W**；THD+N=10% 時 **1.8 W**
- 效率 92%（RL=8 Ω、POUT=1 W）
- 3.2 W @4 Ω @5 V

本設計為 8 Ω／≥1 W EVT 喇叭、`VSYS_RAW` 經核心 audio switch 直供。功放實際 VDD 是受 NVDC
`VSYSMIN`／`VBAT`／USB 模式／負載／dropout 影響的 `SYS`，不是固定「3.0–4.2 V 電池」。

**[算] 壓力情境（非 rail bounds）**：以 V_supply=3.7 V、8 Ω、Class-D 理想滿幅估算：
```
P_out(max) ≈ V²/(2×R) = 3.7²/(2×8) ≈ 0.86 W
I_peak ≈ V/R = 3.7/8 ≈ 0.46 A
```
以 V_supply=3.0 V 壓力點：`P_out ≈ 0.56 W`、`I_peak ≈ 0.375 A`

⚠ **結論（必須報告）**：0.56–0.86 W 只是 3.0／3.7 V 情境計算，**不是** `VSYS_RAW` 保證範圍或
整機輸出資格。正式音訊 gate 必須使用受控 charger／cell configuration 下量得的 `VSYS_RAW` min/max、load-switch
dropout 與 system coexistence 重算並實測；情境值仍
低於資料手冊 5 V／4 Ω 條件下的 3.2 W，也低於 8 Ω／1.4 W。`design.md` §6 的 65 dBA @30 cm 目標
能否達成，取決於實際喇叭靈敏度與聲腔，**本文件不作任何聲學承諾**。

`design.md` 已預先寫明退路：「若實測聲壓不足，才在受控新板版本中增加 5 V 升壓」。本文件補充硬體側
量化依據：直供拓樸的功率上限受 1S 電壓平方限制，且低電量時再降約 35%。此數字應在 WP1／WP3 選喇叭時
與靈敏度規格一併評估。

**峰值電流對電源樹的影響**：`I_peak ≈ 0.46 A` 從 `VSYS_RAW` 抽取，不經 `3V3_AON`，故不影響 MCU 軌。
但會反映到 BQ25628E SYS 與電池，需與 §3.2 的 boost 放大係數一併計入最壞總峰值。

### 6.3 深睡眠

見§5，加入USB差量後的混合工程包絡 **≈40.25–44.25µA**；不是整板max，50µA門仍未通過。

### 6.4 工廠運輸／長期倉儲（ship mode）

BQ25628E BATFET 只切斷 `SYS` 下游；BQ27427 位於 PACK+ 與 charger `BAT` 之間，仍由電池供電。因此不得把
charger 的 `IQ_BAT_SHIP` 寫成整包電池電流。

| battery-side 項目 | typ／max 輸入 | 當前狀態 |
| --- | --- | --- |
| BQ25628E ship mode | 0.15 µA typ／0.5 µA max **[手]** | 只是一個加總項 |
| BQ27427 | SLEEP 9 µA typ，或 deliberate SHUTDOWN 0.6 µA typ **[手]**；相應 max 尚未轉錄 | ship 前模式、學習資料保留與喚醒策略未決；不能假定 0 |
| Battery-side leakage | 保護板、connector／PCB 污染、BQ27427 I²C 浮空或下拉等 | 尚未定量，必須量測 |

受控計算形式為 `I_ship_pack = I_BQ25628E_ship + I_BQ27427_selected_mode + ΣI_battery_side_leakage`。
在 BQ27427 mode、max current、I²C released／floating／SHUTDOWN 決策與 battery-side leakage 未關閉前，**不給
passing total**。WP3/WP4 必須留下 mode 決策；WP9 以 PACK+ 實測 ship 進入、保持、QON／VBUS 退出與 I²C 恢復。
BQ25628E shutdown mode 的 0.1 µA typ／0.2 µA max 也只代表 charger 自身，不能替代整包計算。

---

## 7. 電池與充電

| 項目 | 值 | 狀態 |
| --- | --- | --- |
| 電芯 | 1S Li-Po | 已凍結（PRD） |
| 電芯容量 | **3,500–5,000 mAh 設計目標；3,500 mAh 硬下限；精確電芯未凍結** | 最新受控產品邊界；待機構／供應／熱資格 |
| 充電電流 | **未凍結** | 需依電芯規格與 `TS` 熱敏設定；BQ25628E 經 I²C 設定 |
| `TS` 熱敏 | 建議 103AT-2 10 kΩ NTC | **[手]** SLUSFA4C 建議值；分壓阻值待電芯溫度窗定案 |
| `CE`（充電致能） | 外部**下拉** = 預設充電開啟 | 已凍結。資料手冊要求不得浮空 |
| `STAT` | open-drain，10 kΩ 上拉 | 已凍結 **[手]** |
| `QON` | 內部上拉；與 MCU power-key 網路**電氣隔離**，只共用機械致動 | 隔離拓樸／精確按鍵料號未凍結 |

### 7.1 `QON` 與 Power 鍵隔離門

Power 鍵可共用**機械致動器**，但 `KEY_POWER_MCU`（GPIO1、上拉至 `3V3_AON`）與 `QON_BTN`（BQ25628E
內部上拉、ship mode 仍有效）不得直接短成同一電氣網路。首選設計意圖是雙刀 momentary switch：一刀只把
`KEY_POWER_MCU` 拉到 GND，另一刀只把 `QON_BTN` 拉到 GND；若改用 FET／其他隔離，必須在 AON=0 與 VBUS
有／無兩種條件下仍能可靠退出 ship mode。

BQ25628E 的時序功能保持：ship mode 中 `QON` 拉低達 `tSM_EXIT` 可退出；非 ship mode 長按可觸發硬體復位。
產品必須同時保留**實體 Power 按鍵重啟**（隔離的 `QON_BTN`）與 **VBUS 插入退出 ship mode** 兩條路徑。
但在精確按鍵／隔離料號、漏電、閾值、按壓時序與故障測試完成前，不宣稱長按復位路徑已合格。

**原理圖門**：兩網必須使用不同 net name；直接共網屬阻塞缺陷。WP9 必測短按／長按、deep-sleep wake、ship
退出、VBUS 有／無、AON=0 漏電、卡鍵與單刀失效。

---

## 8. 未凍結項目

| 項目 | 阻擋來源 | 解除條件 |
| --- | --- | --- |
| 電感／電容精確料號、`FB` 分壓阻值 | 需 WP3 仿真 | WP3 |
| TPS63802 vs TPS631000 最終選擇 | 需 WP3 + WP9 深睡實測 | WP9 |
| TPS63802 `MODE` 是否需 MCU 可控 | WP3 紋波結果 | WP3；EVT 以 0 Ω 跳線保留 |
| 精確電芯（保持 3,500–5,000 mAh target／3,500 mAh hard floor）、充電電流、`TS` 分壓 | 電芯未選定 | 電芯定案 |
| microSD 峰值電流 | 無官方統一值 | WP9 實測 |
| EPD 邏輯與 PMIC 實際負載 | WP1 | WP1 |
| 前光 LED 串數／電流／串壓 | WP1 | WP1 |
| 喇叭靈敏度與聲腔 → 65 dBA 可行性 | 喇叭未選定 | WP9 聲學實測 |
| IMU power-down 電流 | 需實測 | WP9 |
| 負載開關漏電 | U402–U405=`TPS22916CYFPT` A-stage；每路 `ISD` max 100 nA，typ 未规范 | 四路 B-stage/F0/WP3 + WP9 温度／反灌／整板實測 |
| BQ27427 深睡 SLEEP vs SHUTDOWN | ✅ **已決策 D1：SLEEP，保持荷電追蹤** | — |
| TUSB320LI VBUS-derived VDD、mode/address、AON-off 隔離 | S-9 尚未關閉 | 原理圖前以 fail-safe／反灌證據關閉 S-9 |
| QON／Power 雙網隔離拓樸與精確按鍵 | 機構／料號未定 | 原理圖前關閉隔離門，WP9 實測 |
| EPD 高壓上下電時序 | WP1 面板／PMIC 資料 | WP1 |

---

## 9. 來源清單

| 元件 | 文件號／版本 | URL | 擷取日期 |
| --- | --- | --- | --- |
| ESP32-S3 晶片 | v2.2 | <https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf> | 2026-08-10 |
| ESP32-S3 硬體設計指南 | Release master | <https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/esp-hardware-design-guidelines-en-master-esp32s3.pdf> | 2026-08-10 |
| TPS63802 | SLVSEU9D | <https://www.ti.com/lit/ds/symlink/tps63802.pdf> | 2026-08-10 |
| TPS22916 | SLVSDO5F | <https://www.ti.com/lit/ds/symlink/tps22916.pdf> | 2026-08-12 |
| BQ25628E | SLUSFA4C | <https://www.ti.com/lit/ds/symlink/bq25628e.pdf> | 2026-08-10 |
| BQ27427 | SLUSEB5B | <https://www.ti.com/lit/ds/symlink/bq27427.pdf> | 2026-08-10 |
| RV-3028-C7 | Rev. 1.4 | <https://www.microcrystal.com/fileadmin/Media/Products/RTC/App.Manual/RV-3028-C7_App-Manual.pdf> | 2026-08-10 |
| TCA9535 | **SCPS201E** | <https://www.ti.com/lit/ds/symlink/tca9535.pdf> | 2026-08-10 更正 2026-08-11（WP4 發現誤記） |
| TUSB320LI | SLLSEP2D | <https://www.ti.com/lit/ds/symlink/tusb320li.pdf> | 2026-08-11 更正 |
| MAX98357A | 19-6779 Rev 16 | <https://www.analog.com/media/en/technical-documentation/data-sheets/MAX98357A-MAX98357B.pdf> | 2026-08-10 |
| LM3630A | SNVS974B | <https://www.ti.com/lit/ds/symlink/lm3630a.pdf> | 2026-08-10 |
| TPS65185 | SLVSAQ8G | <https://www.ti.com/lit/ds/symlink/tps65185.pdf> | 2026-08-10 |

---

## 10. 邊界聲明

本文件為電源樹與狀態規劃，不是原理圖，不構成任何認證聲明。所有 **[估]** 與 **[算]** 值未經實測，
不得作為續航、聲壓、效率或深睡電流承諾。深睡預算 §5 仍缺 IMU、四路負載開關的板級温度／反灌证据與整板實測，
**本文件不宣稱通過 50 µA 門**。
