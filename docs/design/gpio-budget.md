# Panda 標準電子書板：GPIO 預算與衝突分析

日期：2026-08-10（USB／IRQ／BQ_PG 同步：2026-09-08，Codex）
狀態：WP2 容量基線 + 已提升 USB／IRQ／BQ_PG 工程候選；MCU 仍 33/33。顯示側以**最大候選**保留，板間腳位與 GPIO45 reset-strap contract 未凍結
適用板號：`PANDA-STD-CORE-EVT`

本文件凍結核心板 MCU 腳位預算。**不凍結**板間連接器腳位順序與編號（屬 WP1／WP4 輸入，見
[unfrozen-inputs.md](unfrozen-inputs.md)）。

2026-09-08 當前覆蓋：正式 CAD 為149封裝／1766段／306via，saved/refill DRC0/0/0、ERC18 report entries；
這不關閉製造、SI、台架或軟體門。依據見[USB2 S-9 A-stage](lib/review/USB2-S9-A-stage.md)與[BQ_PG記錄](lib/review/BQ_PG-P10-A-stage.md)。

---

## 1. 可用 GPIO 池（實測自官方文件）

模組：ESP32-S3-WROOM-1-N16R8（16 MB flash + 8 MB Octal PSRAM）

| 項目 | 數量 | 依據 |
| --- | --- | --- |
| 模組引出腳位總數 | 41 | WROOM-1 規格書 v1.8 §2 引腳定義 |
| 模組引出 GPIO 數 | 36 | 同上；GPIO0–21、GPIO35–48 |
| 模組**未引出**的 GPIO | GPIO33、GPIO34 | 同上；模組未 bonding，晶片端存在但模組不可用 |
| N16R8 被 Octal PSRAM 佔用 | GPIO35、GPIO36、GPIO37 | WROOM-1 規格書 v1.8 表 3 註腳：「IO35、IO36、IO37 連接至 Octal SPI PSRAM，不可用」 |
| **實際可用 GPIO** | **33** | GPIO0–21（22）+ GPIO38–48（11） |
| 其中 RTC-capable | **22** | GPIO0–GPIO21 → RTC_GPIO0–21（晶片規格書 v2.2 表 2-3／2-4，晶片腳位 5–27） |
| 其中非 RTC | **11** | GPIO38–48 |
| input-only 腳位 | **0** | ESP32-S3 無 input-only 腳位（與 classic ESP32 不同） |

來源：
- ESP32-S3 系列晶片規格書 v2.2，<https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf>，擷取日期 2026-08-10
- ESP32-S3-WROOM-1／1U 規格書 v1.8，<https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf>，擷取日期 2026-08-10
- ESP32-S3 硬體設計指南（Release master），<https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/esp-hardware-design-guidelines-en-master-esp32s3.pdf>，擷取日期 2026-08-10

GPIO26–GPIO32 為封裝內 flash／PSRAM 的 SPI0/1，模組本就未引出，不計入池內。

---

## 2. 特殊腳位約束清單

| 腳位 | 特殊身份 | 復位時預設 | 設計約束 |
| --- | --- | --- | --- |
| GPIO0 | Strapping：boot mode | 弱上拉 | 硬體設計指南建議外部上拉；**禁止**掛大容值電容（會誤入下載模式） |
| GPIO3 | Strapping：JTAG 訊號源選擇 | 浮空（無內部上下拉） | 若使用必須外加確定性上下拉；否則復位取值不定 |
| GPIO19 | USB Serial/JTAG D− | — | 晶片固定，**不可**軟體改派 |
| GPIO20 | USB Serial/JTAG D+ | — | 同上；上電時 USB_D+ 會浮高 |
| GPIO43 | UART0 TXD | — | 燒錄／log 契約腳位 |
| GPIO44 | UART0 RXD | — | 同上 |
| GPIO45 | Strapping：VDD_SPI 電壓選擇 | 弱下拉 | 所需 reset level 必須依 exact module／chip、eFuse 與 board configuration 的受控 contract 決定；**不能**由 N16R8 容量名稱推導為固定 LOW。contract 關閉前禁止任何外部 pull、adapter loading 或 schematic placement |
| GPIO46 | Strapping：boot mode + ROM print | 弱下拉 | 與 GPIO45 是不同問題；外部上拉會影響 ROM print／boot 診斷，故本設計維持低／不加上拉並保留產線 ROM log |
| GPIO39–42 | 預設 JTAG（MTCK/MTDO/MTDI/MTMS） | — | 本設計用 USB Serial/JTAG，故此 4 腳釋放為一般 GPIO |
| GPIO47、GPIO48 | SPICLK_P/N_DIFF | — | 非 R16V 版本為 3.3 V，可作一般 GPIO |
| GPIO15、GPIO16 | XTAL_32K_P/N | — | 本設計用外部 RTC（RV-3028-C7），不接 32 kHz 晶振，可作一般 GPIO |

所有 strapping 腳位在復位時被 latch，之後才可改作一般用途（晶片規格書 v2.2 §2.4）。

### 2.1 EXT1 喚醒的全域約束（關鍵）

ESP-IDF 睡眠模式文件：使用**多個** IO 作 EXT1 喚醒時，所有喚醒 IO 必須**共用同一喚醒電位**。

→ 當前 EXT1 物理輸入為 `KEY_POWER_MCU`（GPIO1）與 `EXP_INT`（GPIO4），均 **active-low**，上拉至
`3V3_AON`；RTC 與核心／適配器中斷源共享後者。`VBUS_VALID_AON`（GPIO2）為高有效電壓狀態，不加入此低有效 EXT1 群。

來源：ESP-IDF 穩定版《Sleep Modes》，<https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/system/sleep_modes.html>，擷取日期 2026-08-10

---

## 3. 訊號分組

**歷史預算（2026-08-10／11）**：§3–§5 保留最初 35 腳需求、−2 缺口與 M3 取捨；当前 USB 差量見 §5.1，實際分配以 §6／§7 為準。

### Group A：必須直連 MCU（矽層固定或時序關鍵）

| 訊號 | 數量 | 必須直連的理由 |
| --- | --- | --- |
| USB_D−／USB_D+ | 2 | 晶片固定 GPIO19／GPIO20 |
| UART0_TXD／RXD | 2 | 燒錄與 log 契約 |
| BOOT／下載 strap | 1 | GPIO0，復位時序 |
| I2C_SCL／SDA | 2 | 擴充器本身掛在此匯流排上，不可自我遞迴 |
| SDMMC CLK／CMD／D0–D3 | 6 | 高速同步匯流排，PRD 已凍結 4-bit |
| I2S BCLK／LRCLK／DIN | 3 | 音訊連續時序 |
| EPD 資料 + 時序（最大候選） | 14 | 見 §3.1 |
| **小計** | **30** | |

#### 3.1 顯示側直接訊號數：以最大候選保留

WP1 未交付精確面板料號，因此顯示側**只凍結函數群與訊號類上限**，不凍結腳位對應。預算以候選中
**直接訊號數最大者**保留。

| 候選類型 | 直接訊號估算 | 依據 |
| --- | --- | --- |
| ED047TC1 類（8-bit 並列 + 外部時序） | **14**：D0–D7（8）+ CKH、STV、CKV、STH、LE（5）+ OE（1） | 本倉庫 `m5papers3` 板級設定實測（見下） |
| Good Display SPI／內建 TCON 類 | 約 **6**（估算，待 WP1 證實） | SPI 4 線 + RST + BUSY 之類；**標記為估算** |

`m5papers3`（ED047TC1）板級設定實測值：`kEpdDataPins{6,14,7,12,9,11,8,10}`、`kEpdCkh=16`、
`kEpdStv=17`、`kEpdCkv=18`、`kEpdSth=13`、`kEpdLe=15`，另 OE=GPIO45、DCDC_EN=GPIO46。
→ 顯示本身佔 15 個直接 GPIO（含 DCDC_EN）。本預算把 DCDC_EN 移至擴充器，故直接訊號記為 14。

**保留 14**（ED047TC1 路線）。此為**保留值**，非確認值；WP1 定案後回填實際值。

### Group B：必須直連且必須 RTC-capable（深睡喚醒）

| 訊號 | 數量 | 理由 |
| --- | --- | --- |
| KEY_POWER | 1 | 深睡唯一保證喚醒路徑 |
| RTC_INT（RV-3028-C7） | 1 | 定時喚醒 |
| KEY_FN | 1 | 第二鍵喚醒 |
| TOUCH_INT | 1 | 觸控喚醒（PRD 標為選配） |
| IMU_INT1（LSM6DSO32X） | 1 | 動作喚醒（PRD v1 不含 IMU 驅動工作） |
| **小計** | **5** | |

### Group C：可掛 I/O 擴充器（慢速、非喚醒關鍵）

電源致能、power-good、重置、卡偵測、充電狀態等。詳見 §6 擴充器分配表。這些訊號**不佔** MCU GPIO。

---

## 4. 歷史衝突一：GPIO 預算不足（ED047TC1 路線）

### 4.1 缺口計算

```
Group A（必須直連）                        30
Group B（必須直連且 RTC-capable）           5
                                        ----
需求合計                                  35
可用 GPIO                                 33
                                        ----
缺口                                      -2
```

RTC 池另有獨立壓力：

```
RTC-capable 總數                          22
已被固定佔用（GPIO0、19、20）               -3
                                        ----
可自由分配的 RTC 腳位                       19
非 RTC 池可用                              11 − 2（UART0）= 9
Group A 非固定訊號                         30 − 5（USB×2、UART×2、GPIO0）= 25
  其中最多可推到非 RTC 池                    9
  被迫佔用 RTC 腳位                        16
                                        ----
RTC 池剩餘                                19 − 16 = 3
Group B 需求                              5
                                        ----
RTC 池缺口                                -2
```

兩種算法缺口一致：**−2**。

### 4.2 結論

**ED047TC1 類 8-bit 並列候選，在 PRD 已凍結的完整核心板功能集下，GPIO 不足 2 支。**
此缺口**不能**用擴充器搬移 Group A／Group B 訊號解決，因為：
- 顯示資料與關鍵時序不得經低速 I²C 擴充器（PRD 明文約束）
- I²C 本身、USB、UART0、SDMMC、I2S 皆為矽層或匯流排層固定

必須由使用者在 §5 選項中決策。

---

## 5. 歷史緩解選項與當前差量

| 選項 | 作法 | 釋放 | 代價／風險 |
| --- | --- | --- | --- |
| **M1** | KEY_FN 併到 GPIO0（active-low，沿用 LilyGo BOOT 鍵先例） | 1 | 復位瞬間按住 Fn 會進下載模式；與復原焊盤共用網路 |
| **M2** | 不安裝 KEY_FN（PRD 已許可的單鍵退路，DNP + 外殼不開孔） | 1 | 失去第二鍵 |
| **M3** | KEY_FN + TOUCH_INT + IMU_INT1 聚合到擴充器，以單一 active-low open-drain INT 佔 1 支 RTC 腳位 | 2 | 喚醒後需一次 I²C 讀取判斷來源；擴充器靜態電流計入深睡預算；喚醒延遲增加 |
| **M4** | 僅 ED047TC1 路線把 TOUCH_INT 移到擴充器（不聚合） | 1 | 該轉接板永久失去觸控深睡喚醒；`design.md` §10 偏好 RTC-capable INT，屬路線專屬偏離，需簽核 |
| **M5** | SDMMC 降為 1-bit／SDSPI | 3 | **PRD 已凍結 4-bit，需使用者明確批准**；讀寫頻寬下降。不建議 |
| **M6** | ED047TC1 另做獨立 EVT 主板 | 不適用 | `implement.md` §7 既有退路；增加一塊板的成本與週期 |
| **M7** | WP1 選 SPI／內建 TCON 候選 | 約 8 | 缺口消失且留餘裕；但顯示選型由 WP1／WP11 決定，非 WP2 可裁決 |

### 5.1 建議

**✅ 已決策（2026-08-11 用戶確認）：採 M3。** 恰好補足 −2，保留雙鍵與觸控喚醒，不動 PRD 已凍結的 4-bit SDMMC，且與本倉庫
`lilygo-t5s3-pro` 把 TPS65185 控制訊號放在 PCA9535 的先例一致。

**但必須明示：採 M3 後 33/33 全滿，零備用腳位。** 對 EVT 而言這是實質風險：bring-up 期間沒有
飛線腳位、沒有臨時偵錯腳位、沒有後續加訊號的餘地。因此建議 **M3 + M6 併行**，或在 WP11 顯示決策中
把「GPIO 餘裕」列為正式評分項（M7）。

**M5 不建議**，且未經使用者批准不得執行。

**2026-09-08 當前差量**：RTC 與擴展中斷共享 GPIO4，釋放 GPIO2 作專用 VBUS 感知，一減一增，仍為
33/33、零備用（直接時序／狀態群 31 + 物理喚醒輸入 2）。RTC 定時喚醒保留，但不能再從 GPIO2 的 EXT1 bit
辨別 RTC；須讀取 RTC 與實際存在的各 TCA 並清源。顯示 14 腳保留、GPIO45 阻塞與 SD 四位功能均不變。

### 5.2 對 WP1／WP11 的正式輸入

> GPIO 預算是顯示選型的**硬約束**，不只是佈線細節。8-bit 並列候選使核心板 GPIO 歸零且需強制採用
> I/O 擴充器聚合中斷；SPI／內建 TCON 候選可留約 8 支餘裕。此結論須進入 WP11 決策矩陣。

---

## 6. 建議分配表（採 M3）

圖例：**[矽]** 矽層固定 · **[凍]** PRD／WP0 已凍結 · **[保]** 保留給最大顯示候選，WP1 定案後回填 ·
**[M3 已決策]** §5 選項 M3，2026-08-11 用戶確認（見 §5 決策段）

### 6.1 RTC-capable 池（GPIO0–21）

| GPIO | 訊號 | 方向 | 狀態 | 備註 |
| --- | --- | --- | --- | --- |
| 0 | BOOT／下載 strap + 復原焊盤 | I | **[矽]** | 外部上拉；禁掛大電容 |
| 1 | `KEY_POWER_MCU` | I | **[凍]** | active-low，上拉至 `3V3_AON`；只與 QON 共用機械致動，**禁止電氣共網** |
| 2 | VBUS_VALID_AON | I | **[2026-09-08 已批准改配]** | U501.pad38；TPS3700→AUP1G17 高有效 VBUS 感知，AON 緩衝輸出及 100k 下拉；非獨立 RTC EXT1 |
| 3 | EPD_LE | O | **[保]** | strapping 腳位、無內部上下拉 → **必須**外加 10 kΩ 下拉；LE 空閒為低，與下拉一致 |
| 4 | EXP_INT（RTC／擴展共享） | I | **[2026-09-08 已批准合併]** | U302、U601 與已接入適配器 TCA 的 open-drain wired-OR；R502=100k 為唯一已裝核心上拉，R305 DNP |
| 5 | SDMMC_CLK | O | **[凍]** | |
| 6 | SDMMC_CMD | I/O | **[凍]** | 需上拉 |
| 7 | SDMMC_D0 | I/O | **[凍]** | 需上拉 |
| 8 | SDMMC_D1 | I/O | **[凍]** | 需上拉 |
| 9 | SDMMC_D2 | I/O | **[凍]** | 需上拉 |
| 10 | SDMMC_D3 | I/O | **[凍]** | 需上拉 |
| 11 | I2S_BCLK | O | **[凍]** | |
| 12 | I2S_LRCLK | O | **[凍]** | |
| 13 | I2S_DIN | O | **[凍]** | MAX98357A DIN（MCU 出、放大器入） |
| 14 | I2C_SCL | O/OD | **[凍]** | |
| 15 | I2C_SDA | I/O/OD | **[凍]** | |
| 16 | EPD_CKH | O | **[保]** | 高速（約 20 MHz 級），必須直連且遠離 strapping 腳位 |
| 17 | EPD_STV | O | **[保]** | |
| 18 | EPD_CKV | O | **[保]** | |
| 19 | USB_D− | I/O | **[矽]** | 不可改派 |
| 20 | USB_D+ | I/O | **[矽]** | 不可改派；上電浮高 |
| 21 | EPD_D7 | O | **[保]** | 8-bit 資料的第 8 位被迫落在 RTC 池 |

RTC 池使用 22/22。

### 6.2 非 RTC 池（GPIO38–48）

| GPIO | 訊號 | 方向 | 狀態 | 備註 |
| --- | --- | --- | --- | --- |
| 38 | EPD_D0 | O | **[保]** | |
| 39 | EPD_D1 | O | **[保]** | 原 JTAG MTCK，已釋放 |
| 40 | EPD_D2 | O | **[保]** | 原 JTAG MTDO |
| 41 | EPD_D3 | O | **[保]** | 原 JTAG MTDI |
| 42 | EPD_D4 | O | **[保]** | 原 JTAG MTMS |
| 43 | UART0_TXD | O | **[矽]** | |
| 44 | UART0_RXD | I | **[矽]** | |
| 45 | EPD_STH（預算佔位） | O | **[保／阻塞]** | VDD_SPI strap；所需 reset level 尚未受控。exact module／chip／eFuse／board contract 關閉前禁止外部 pull、adapter loading、connector mapping 與 schematic placement |
| 46 | EPD_OE | O | **[保]** | boot+ROM print strap；維持低／禁止上拉，以保留 ROM print 與產線診斷 |
| 47 | EPD_D5 | O | **[保]** | |
| 48 | EPD_D6 | O | **[保]** | |

非 RTC 池使用 11/11。

### 6.3 佔用總結

| 池 | 已用 | 總數 | 備用 |
| --- | --- | --- | --- |
| RTC-capable | 22 | 22 | **0** |
| 非 RTC | 11 | 11 | **0** |
| **合計** | **33** | **33** | **0** |

**歷史 M3 附記**：TCA9535 本來必裝，M3 本身只是使用既有擴充器；這不表示本批 USB 零新增器件或電流。
當前 CC 固定 GPIO 模式，EN_N／PORT 接地，無 P10 隔離控制；P10 已作 BQ_PG 輸入及10k AON上拉，仍不得直連 U202。
USB 隔離／監控的指定穩態新增 3.8µA 工程預算另計，半掉電／過渡仍須實測。
**MCU GPIO 零備用**是 ED047TC1 路線的必然結果，已在 §5.1 標為風險。若 WP1 選 SPI／TCON 候選，`EPD_D0–D7`、
`CKH/STV/CKV/STH/LE/OE` 共 14 支中約 8 支釋放，備用回到約 8 支。

---

## 7. 核心板 I/O 擴充器分配（TCA9535，位址 0x20）

選型理由：16 位、open-drain active-low INT 輸出、8 組硬體位址、standby 電流 0.9 µA typ／4 µA max
（VCC=3.6 V、輸入接地）。KiCad 官方庫已有 TCA9535 符號需複核（見
[symbol-footprint-workload.md](symbol-footprint-workload.md)）。

來源：TCA9535 資料手冊，文件號 **SCPS201E**（2026-08-11 更正，WP4 發現誤記），<https://www.ti.com/lit/ds/symlink/tca9535.pdf>，擷取日期 2026-08-10

**P 埠無內部上下拉**（設為輸入時為高阻抗，漏電流 ±1 µA max）。所有經擴充器的輸入訊號必須外加上下拉。

| 埠 | 訊號 | 方向 | 外部電阻 | 說明 |
| --- | --- | --- | --- | --- |
| P00 | EN_3V3_SD | O | 下拉 | 預設關閉 SD 電源 |
| P01 | EN_3V3_TOUCH | O | 下拉 | 送轉接板 |
| P02 | EN_3V3_EPD_LOGIC | O | 下拉 | 送轉接板；核心板擁有此軌 |
| P03 | EN_VSYS_AUDIO | O | 下拉 | 音訊負載開關，預設關閉 |
| P04 | FUEL_GPOUT | **I（預設 released）／短暫 O-low** | 上拉至 `3V3_AON` | TCA9535 output 是 push-pull，不是 open-drain。平時保持 input，由 BQ27427 open-drain GPOUT 驅動；喚醒時只可刻意 output-low ≥`tSHUP`，隨即回 input，**禁止 output-high** |
| P05 | CHG_CE | O | **下拉** | BQ25628E active-low 充電致能；資料手冊要求不得浮空。下拉 = 預設充電開啟（韌體未開機也能充電） |
| P06 | CHG_INT | I | 上拉至 `3V3_AON` | open-drain，併入 EXP_INT |
| P07 | CHG_STAT | I | 上拉至 `3V3_AON` | open-drain 充電狀態 |
| P10 | BQ_PG | I（保持輸入） | R600=10 kΩ／1%上拉3V3_AON | U201.3開漏、低有效輸入源合格狀態；不是充滿或TPS PG，不直接連U202 |
| P11 | KEY_FN | I | 上拉至 `3V3_AON` | **[M3 已決策]**；併入 EXP_INT |
| P12 | IMU_INT1 | I | **下拉 100 kΩ** | **[M3 已決策]**；併入 EXP_INT。⚠ 見 §7.1 |
| P13 | SD_CD | I | 上拉至 `3V3_AON` | 卡偵測，併入 EXP_INT |
| P14 | PG_3V3_MAIN | I | 上拉至 `3V3_AON` | TPS63802 PG 為 open-drain |
| P15 | 備用／L3 預留 | I（預設） | 100 kΩ 下拉 | 精確用途未決；不得浮空 |
| P16 | CC_OUT1_AON | I | R602=10k 上拉 3V3_AON | U204.6 非反相開漏輸出；無舊 100k 下拉，禁止配置推挽輸出 |
| P17 | CC_OUT2_AON | I | R603=10k 上拉 3V3_AON | U204.4 非反相開漏輸出；無舊 100k 下拉，禁止配置推挽輸出 |

`TOUCH_INT` 不佔核心板擴充器：由轉接板側擴充器擁有，其 INT 與核心板擴充器 INT **同一條 open-drain
線 wired-OR** 併入 `EXP_INT`（見 [interfaces-and-connectors.md](interfaces-and-connectors.md)）。

RTC U302.INT 亦直接加入此共享 `EXP_INT`；核心擁有唯一已裝上拉，適配器不得另加 IRQ 上拉。
擴充器未固定分配 **1/16（P15）**，仍為既有 L3 預留。P10是BQ_PG、P16/P17是CC輸入，均不計作備用。

BQ_PG host contract: keep configuration0x07 bit0=1 and polarity0x05 bit0=0; read input0x01 bit0 while AON is valid.
PG transitions can assert shared EXP_INT, so process the whole port1 snapshot and other TCA/RTC sources before sleeping.
中文說明：不把P10配置為推挽輸出；AON失效時不能把不可讀狀態當有效低。PG專屬VOL/漏電和實物中斷資格仍待驗，見[BQ_PG記錄](lib/review/BQ_PG-P10-A-stage.md)。

### 7.1 ⚠ LSM6DSO32X I3C 危害

LSM6DSO32X 若在上電瞬間 INT1 被拉至 Vdd_IO，會選入 **I3C-only 模式**，I²C 不可用。

→ `IMU_INT1` 網路**禁止**任何上拉至 `Vdd_IO`。因 TCA9535 P 埠無內部上下拉，此網路會浮空，故
**必須**外加 100 kΩ 下拉以保證上電為低。IMU INT 本身為推挽輸出，可正常克服此下拉。

來源：LSM6DSO32X 資料手冊，文件號 DS13607 Rev 1，<https://www.st.com/resource/en/datasheet/lsm6dso32x.pdf>，擷取日期 2026-08-10

---

## 8. 逐項複核清單

### 8.1 Strapping 檢查

| 檢查 | 結果 |
| --- | --- |
| GPIO0 是否掛大容值電容 | 否。僅外部上拉 + 復原焊盤 |
| GPIO3 是否有確定性復位電位 | 是。外加 10 kΩ 下拉（EPD_LE 空閒為低） |
| GPIO45 reset strap contract 是否已受控 | **否，阻塞。** 所需 VDD_SPI reset level 依 exact module／chip／eFuse／board configuration；關閉前禁止外部 pull、adapter loading、connector mapping 與 placement |
| GPIO46 復位是否維持低／無上拉 | 是。EPD_OE 空閒為低；轉接板禁止上拉，以保留 ROM print／boot 診斷 |
| 其餘 strapping 腳位是否被指派為空閒為高的訊號 | 無；GPIO45 因 contract 未關閉不在此宣稱通過 |

### 8.2 PSRAM／flash 檢查

| 檢查 | 結果 |
| --- | --- |
| GPIO35／36／37 是否被指派 | **否**。N16R8 Octal PSRAM 佔用，已排除出池 |
| GPIO33／34 是否被指派 | **否**。模組未引出 |
| GPIO26–32 是否被指派 | **否**。封裝內 flash／PSRAM，模組未引出 |

### 8.3 USB 衝突檢查

| 檢查 | 結果 |
| --- | --- |
| GPIO19／20 是否被其他功能佔用 | 否，只用於 USB 物理路徑；應用 CDC/MSC 與 ROM Serial/JTAG 依 PHY 模式分別驗證 |
| 是否預留串聯電阻與 DNP 電容 | R530/R529=22Ω；MCU 側 C515/C514 默認 DNP，實際调試容值未凍結 |
| 差分目標 | 90 Ω differential、pair skew ≤0.5 mm；精確線寬／間距待 F0 stackup |
| USB_D+ 上電浮高是否影響其他網路 | D±只用於USB；ROM pull-up、重新連接與鄰網影響仍待實測 |
| 直接 VBUS 監控 | GPIO2 高有效；四象限、半掉電、3ms 拔除釋放與 ROM 行為仍待台架，不以 DRC 代替 |

### 8.4 RTC-capable／喚醒檢查

| 檢查 | 結果 |
| --- | --- |
| 所有 EXT1 喚醒源是否共用同一電位 | **是，全部 active-low**（KEY_POWER_MCU、含RTC的EXP_INT） |
| 喚醒源是否全在 GPIO0–21 | 是，物理GPIO僅1／4；GPIO2已改VBUS狀態，不再是RTC EXT1來源 |
| 深睡唯一保證喚醒路徑是否存在 | 是。`KEY_POWER_MCU`→GPIO1；另由隔離的第二接點驅動 QON，兩網禁止直通 |
| 是否有 active-high 喚醒源混入 | 無 |

### 8.5 input-only 檢查

ESP32-S3 無 input-only 腳位，此類衝突不存在。作為輸入使用的 GPIO0／1／2／4／6–10／44 皆為雙向腳位。

### 8.6 ADC 可用性（附帶結論）

GPIO1–10（ADC1 通道）已全部佔用 → **核心板無可用 MCU ADC**。電池電壓與電流由 BQ27427 燃料計經
I²C 提供，BQ25628E 亦有內建 ADC，故功能上不缺。ADC2 通道與 Wi-Fi 衝突，本設計本就不採用。

此結論須記錄：任何後續需要 MCU ADC 的需求都會觸發 §5 的重新決策。

---

## 9. 未凍結項目

| 項目 | 阻擋來源 | 解除條件 |
| --- | --- | --- |
| 板間連接器腳位順序與編號 | WP1 未交付精確面板料號／FPC／TCON | WP1 定案後於 WP4 凍結 |
| `EPD_D0–D7`、`CKH/STV/CKV/STH/LE/OE` 的實際存在與數量 | 同上 | 同上；現以 ED047TC1 類 14 支保留 |
| 顯示路線 M6／M7 是否採用 | WP1／WP11 未定；M3 已採用 | 顯示定案後重算；不得改動 4-bit SDMMC |
| SPI／TCON 候選的直接訊號數（估算 6） | WP1 | WP1 交付後以實際值取代估算 |
| GPIO45 VDD_SPI reset level／pull／adapter loading contract | exact module／chip／eFuse／board configuration 未受控 | 原理圖 placement 前取得並審查受控 contract |
| TCA9535 於深睡的實測靜態電流 | 需樣板實測 | WP9 台架量測（資料手冊值見 §7） |

---

## 10. 邊界聲明

本文件為腳位預算與衝突分析，**不是**原理圖、不是網表、不構成任何認證聲明。所有標為「估算」者未經
實測；所有標為 **[保]** 者為保留值，WP1 定案後必須回填並重新執行 §8 全部檢查。
