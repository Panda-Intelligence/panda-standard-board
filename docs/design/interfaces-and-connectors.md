# Panda 標準電子書板：接口與連接器計畫

日期：2026-08-10（J502工程接口批准同步：2026-09-08，Codex）
狀態：WP2 凍結函數群、訊號類上限與 `>=40 contacts` envelope；**板間連接器 exact count／order／MPN 未凍結**（待 WP1 受控面板資料 + 機構輸入）
適用板號：`PANDA-STD-CORE-EVT`、`PANDA-STD-ADP-<精確面板料號>-EVT`

歷史USB/IRQ工程候選已提升（149封裝／1566段／311via，DRC 0/0/0、ERC 19），共同依據為
[USB2 S-9 A-stage](lib/review/USB2-S9-A-stage.md)。這不關閉F0/M0、SI/ESD、ROM或整機台架資格。
當前正式工程以 [布局狀態](layout-constraints.md) 與 [ERC狀態](erc-status.md) 為準；J502工程接口已完成CAD提升，仍非總成資格通過。

---

## 1. 凍結邊界宣告

| 項目 | 本文件是否凍結 |
| --- | --- |
| 函數群（哪些功能必須過連接器） | ✅ 凍結 |
| 每群訊號類上限（數量上界） | ✅ 凍結 |
| 電源／地／訊號的類別劃分與電流類別 | ✅ 凍結 |
| 連接器選型準則 | ✅ 凍結 |
| **板間連接器腳位順序、編號、實際腳數** | ❌ **不凍結** |
| 板間連接器精確料號 | ❌ 不凍結；不覆蓋下述已選USB工程候選 |
| FPC 長度、層數、阻抗結構 | ❌ 不凍結 |

**不凍結腳位的理由**：WP1 尚未交付 ED047TC1／Good Display 4.0／4.7 的精確料號、原生 FPC 定義、
TCON 有無與高壓需求。腳位順序取決於這些輸入（差分／高速訊號的相鄰關係、地回流分配、HV 隔離間距）。
提前凍結會導致 WP4 返工。詳見 [unfrozen-inputs.md](unfrozen-inputs.md)。

---

## 2. 外部接口（核心板，已凍結）

| 接口 | 型式 | 訊號 | 狀態 |
| --- | --- | --- | --- |
| USB-C | GCT USB4105-15-A-120（現件）→ 薄型候選 GCT **USB4500-03-0-A**（mid-mount，0.8 mm offset；USB4505 為 1.0 mm offset 不匹配） | VBUS/GND/D±/CC1/CC2；SBU不用，SH共同地 | 功能已定；thin12 已落圖精確廠商焊盤，底邊重布未完成；外殼／F0/M0實物資格未凍結 |
| microSD | 使用者可直插卡座，板邊 | `CLK`、`CMD`、`D0–D3`、`CD`、`3V3_SD`、`GND` | 函數凍結 |
| 喇叭 | JST GH SM02B-GHS-TB側插2-pin工程接口，8 Ω／≥1 W | `SPK_P`、`SPK_N` | 接口與走線已提升；完整音頻總成／線束／M0未驗收 |
| 電池 | **≥3-pin**（含 NTC） | `BAT+`、`BAT−`、`NTC` | PRD 已凍結至少三線；精確 NTC 曲線／料號待電芯定案 |
| 使用者按鍵 | Power 首選雙刀 momentary + Fn 單刀（Fn 可 DNP） | `KEY_POWER_MCU`、隔離的 `QON_BTN`、`KEY_FN` | S-10；Power 兩網只共用機械致動 |
| 調試／恢復焊盤 | 六網彈簧針／Tag-Connect 兼容，**無外露連接器** | `UART0_TX`、`UART0_RX`、`EN`、`GPIO0`、`3V3`、`GND` | 已凍結（PRD） |
| 板間連接器 | 待選型 | 見 §3 | **腳位未凍結** |

### 2.1 USB-C（sink-only）

| 項目 | 決定 | 依據 |
| --- | --- | --- |
| 角色 | UFP（sink）only，不做 DFP／OTG | PRD |
| CC 邏輯 | TUSB320LI GPIO模式；ADDR NC、PORT/EN_N=GND；TPS70933由VBUS供3V3_USB_CC；OUT1/2經AUP2G07至TCA P16/P17 | 見 [i2c-address-map.md](i2c-address-map.md) §5.3 |
| `VBUS_DET` | R205=887kΩ±1%；878.13–895.87kΩ落在855–920kΩ範圍 | **[手/算]** SLLSEP2D |
| AON 跨域 | 本地CC只上拉3V3_USB_CC，buffer輸出才上拉AON；VBUS=0無主動CC電池供電，但有限漏電仍計入指定穩態3.8µA工程預算 | 四象限／半掉電／ramp未測，不承諾零負載 |
| 資料對 | GPIO19/20經R530/R529=22Ω接D−/D+；MCU側C515/C514對地默認DNP；D201保護D±和CC | 實際調試容值未凍結 |
| 差分目標 | **90 Ω differential**；pair skew ≤0.5 mm | 統一 pre-stackup 設計目標；精確線寬／間距待板廠回簽 |
| ESD／電容 | D202=TPD1E10B06DPYR保護VBUS；直接VBUS C202+C209=2µF nominal，CC rail 2.5µF另計 | 不採無條件≥10µF；見下方inrush／釋放預算 |
| 直接VBUS監控 | TPS3700 + 105k/10k + 1nF → AUP1G17 → GPIO2，高表示有效 | 4.75/4.35V端點僅有指定公差下靜態餘量；3ms／ROM／失電待測 |
| 溫度等級 | 選 **TUSB320LI**（−40–85 °C） | **[手]** SLLSEP2D §6.3 |

⚠ `USB_D+` 上電時會浮高（硬體設計指南），佈局須確認不影響鄰近網路。

**2026-09-08 電容／源端預算**：C202/C209各1µF直接接VBUS；C210=2.2µF、C211/C212/C213各0.1µF在CC rail，
六顆合計4.5µF nominal，統一+20%為5.4µF，按5.5V保守電荷29.7µC。這不是整機inrush保證：C215/TVS寄生、
PMID/SYS經BQ內部啟動路徑及實際插拔仍須納入。C214由AON供電，不重複併入CC rail。C210須由exact MPN證明
在3.3V、全容差／溫度／DC-bias後有效 **≥1.5µF**，不能憑2.2µF名義值關閉TPS709穩定性門。

R209=1k±1%、≥0.1W；5.5V/990Ω為5.5556mA、30.5556mW，是繞過BQ限流的USB負載。
默認500mA總門須在J201量測，含全部旁路和啟動負載；僅BQ支路限流合格不構成總源通過。

當前PCB：J201在F面(28,106.525)；R529/R530在B面(40.10/38.83,92)/270°，C514/C515在B面
(41.90/37.03,92.51)/0°/180°；D202在B面(31.6,100.8)/180°，VBUS 0.50mm短支路2.212409mm，
獨立GND 0.50mm支路0.924264mm，不借C510復位RC回流。USB初次提升時正／反插完整平面參考路徑skew為
−0.321863／−0.321905mm（含1.02mm電阻pad-gap代理、不計via垂直長度），符合≤0.5mm幾何目標，**不是SI或90Ω資格**。
後續SD走廊重布的現行結果以 [布局狀態](layout-constraints.md) 為準，不沿用上述歷史路徑值。

### 2.2 microSD（4-bit SDMMC，已凍結）

| 項目 | 決定 | 依據 |
| --- | --- | --- |
| 模式 | 4-bit SDMMC | PRD 已凍結 |
| 腳位 | GPIO5（CLK）、6（CMD）、7–10（D0–D3） | 見 gpio-budget.md §6.1 |
| 主機能力 | ESP32-S3 有一個 SD/MMC host，**不能作 slave** | **[手]** 硬體設計指南 |
| 腳位彈性 | 「SDIO 介面可由軟體配置到任意空閒 GPIO」 | 同上 |
| 上拉 | `CMD`、`D0–D3` 需上拉 | 同上 |
| 串聯電阻 | 預留 | 同上 |
| 電源 | `3V3_SD` 獨立可關斷 | PRD |
| 卡偵測 | `SD_CD` → 擴充器 P13，併入 `EXP_INT` | 本文件 |

**統一佈線目標（列入 WP7A）**：
- `CMD`、`D0–D3` 各自與 `CLK` 的長度差絕對值 **≤50 mil（1.27 mm）**；不得再使用 ±5 mm 版本
- 單端阻抗目標 **50 Ω ±10%**
- **不得跨層**，並有完整連續地參考平面
- `CLK` 周圍鋪地銅；總長度盡量短

上述是板廠 stackup 前的唯一**設計目標**。在介質／銅厚／Dk 未回簽前，不給可製造線寬／間距，也不得把
CAD 預設線寬寫成受控阻抗解。

### 2.3 調試／恢復焊盤（已凍結）

六網：`UART0_TX`（GPIO43）、`UART0_RX`（GPIO44）、`EN`（CHIP_PU）、`GPIO0`、`3V3`、`GND`。

2026-08-13 A-stage 已在 PCB 底面放置 `J503=TC2030-IDC-NL`，中心 `(40.00,26.50)`、90°。针序按
Espressif ESP-Prog program interface 的目标板方向固定：1=`CHIP_PU`、2=`3V3_AON`、
3=`UART0_RX`（接 programmer `ESP_TXD`）、4=`GND`、5=`UART0_TX`（接 programmer `ESP_RXD`）、
6=`GPIO0`。该针序已通过 schematic/PCB parity 与 XML netlist，但底面 mating-face／Pin 1 治具方向仍须
M0 + 不同身份 B-stage + WP9 实物下载共同关闭。

| 約束 | 內容 |
| --- | --- |
| 外露性 | **無外露連接器**，僅底面焊盤 |
| 用途 | EVT、返修、產線治具；不是使用者端口 |
| 隔離 | 須與天線、開關電源節點、音訊／IMU、顯示 FPC 隔離 |
| `EN` 電路 | RC 延遲，硬體設計指南建議 R=10 kΩ、C=1 µF |
| `GPIO0` | 禁掛大容值電容（見 gpio-budget.md §2） |
| 驗證 | 須完成治具下載／恢復驗證（WP9） |

---

### 2.4 J502 喇叭工程接口（2026-09-08，Codex）

已批准在最終音頻總成定案前建立可修改的J502及兩條BTL走線；不是聲學或M0豁免。
板端JST **SM02B-GHS-TB（LF/SN）**，配合 **GHR-02V-S** 膠殼、兩個 **SSHL-002T-P0.2** 接點及AWG26線材。
來源：[JST GH目錄](https://www.jst-mfg.com/product/pdf/eng/eGH.pdf)，2026-09-08核對第2–3頁。

| 接點 | 板端网络 | 線束端 |
| --- | --- | --- |
| 1 | U502.9 OUTP／SPK_P | 喇叭正端 |
| 2 | U502.10 OUTN／SPK_N | 喇叭負端 |
| 兩機械固定焊盤 | no-net；均需焊接 | 無線束接點 |

兩輸出都不是GND；線束按接點編號驗證，不按鏡像視圖左右猜極性。1A額定以AWG26為條件，不能當功放故障限流保證。
正式位置(34,4.0)mm／F面90°，線束伸出朝+X；組合本體參考高度4.35mm，不是含公差的最大高度或完整插拔包絡。
實際布線／完整saved-refill DRC與獨立檢查已通過，見[J502記錄](lib/review/J502-GH-A-stage.md)。線長、彎曲／解鎖空間、精確喇叭、声腔與連續播放／熱／EMI資格保持待驗。

## 3. 板間連接器：函數群與訊號類上限

### 3.1 函數群（凍結）

| 群 | 內容 | 訊號類 | 數量上限 | 是否過連接器 |
| --- | --- | --- | --- | --- |
| G1 顯示資料 | `EPD_D0–D7` | 高速數位（約 20 MHz 級） | **8** | ✅ 必須直連 |
| G2 顯示時序 | `CKH`、`CKV`、`STV`、`STH`、`LE`、`OE` | 高速／中速數位 | **6** | ✅ 必須直連 |
| G3 管理匯流排 | `I2C_SCL`、`I2C_SDA` | 低速 open-drain | **2** | ✅ |
| G4 中斷 | `EXP_INT`（RTC + 核心／適配器TCA共享，含TOUCH_INT） | 低速 open-drain active-low | **1** | ✅ |
| G5 低壓電源 | `3V3_EPD_LOGIC`、`3V3_TOUCH`、`VSYS_FL_IN`、`EPD_HV_IN` | 電源 | **4**（各需足夠腳數，見 §3.3） | ✅ |
| G6 地 | `GND` | 地回流 | **見 §3.3** | ✅ |
| G7 高壓／VCOM | ±HV、VCOM | **高壓** | **0** | ❌ **禁止過連接器** |

**G7 = 0 是硬邊界。** 與 [README.md](README.md) §3.1 及 power-tree.md §1 一致。

### 3.2 訊號類上限依據

G1＋G2 = 14，取自 ED047TC1 類候選（最大直接訊號數）。見 gpio-budget.md §3.1。
若 WP1 選 SPI／TCON 候選，G1＋G2 降至約 6（**估算**），連接器可縮小但**不重新擴大**。

→ **連接器選型必須按 14 個顯示直接訊號的上限選**，避免 WP1 定案後需換連接器。

### 3.3 電源與地腳數準則（凍結準則，不凍結腳數）

| 軌 | 電流類別 | 腳數準則 |
| --- | --- | --- |
| `EPD_HV_IN` | 最大（PMIC 升壓輸入） | 按 PMIC 峰值輸入電流 + 降額，**待 WP1** |
| `VSYS_FL_IN` | 中（未開關的前光輸入；精確負載待 WP1） | ≥1，按 adapter load switch／driver 受控最大輸入電流 |
| `3V3_EPD_LOGIC` | 中，待 WP1 | ≥1 |
| `3V3_TOUCH` | 小（觸控控制器 mA 級） | 1 |
| `GND` | 必須同時滿足電源回流與高速訊號回流 | **每個高速訊號群相鄰須有地**；總地腳數 ≥ 電源腳數，且 G1／G2 兩側與中間須插入地腳 |

`VSYS_FL_IN` 由核心板 unswitched 傳出；adapter 擁有前光 load switch／driver、switched rail `VSYS_FL_SW`
及其測試點。核心板不得宣稱能直接關斷或量測 switched frontlight rail。

地腳分配是 20 MHz 級並列匯流排訊號完整性的必要條件，不是可省項。實際插入位置、exact contact count、
numbering、order 與 MPN 只有在 WP1 受控面板資料及機構輸入齊備後，才可於 WP4 凍結。

### 3.4 估算腳數（僅供選型，非凍結）

```
G1 顯示資料         8
G2 顯示時序         6
G3 I²C              2
G4 中斷             1
G5 電源             4–8（依 §3.3 降額）
G6 地               8–12（依 §3.3 交錯）
                  -----
估算合計           29–37
```

→ **只凍結 `>=40 contacts` envelope**。exact contact count／numbering／order／MPN 待 WP1 受控面板資料與
機構輸入，不能在本階段或僅憑估算凍結。

---

## 4. 連接器選型準則（凍結）

`design.md` §3 已要求驗證額定電流、接觸電阻、插拔壽命、防呆、裝配高度、探測可達性與候選最大訊號數。
本文件補上量化準則：

| 準則 | 要求 | 理由 |
| --- | --- | --- |
| 接點包絡 | `>=40 contacts`；不是 exact count | §3.4 上限 + 餘裕；exact count／order／MPN 仍阻塞 |
| 額定電流 | 單腳額定 ≥ `EPD_HV_IN` 峰值 ÷ 腳數 × 2（降額 50%） | 保守降額 |
| 接觸電阻 | 越低越好；須列入 `EPD_HV_IN` 壓降計算 | PMIC 輸入壓降影響升壓效率 |
| 插拔壽命 | ≥ EVT 預期插拔次數 × 安全係數 | EVT 每塊核心板會配 5 套轉接板反覆插拔 |
| 防呆 | **必須**有機械防呆 | 反插會把 `EPD_HV_IN` 接到訊號腳，破壞面板與 MCU |
| 裝配高度 | 待機構 | 未凍結 |
| 探測可達性 | 插合後關鍵訊號仍可探測（見 [test-points.md](test-points.md)） | bring-up 必要 |
| 高速適用性 | 須有廠商提供的高速特性資料或至少完整機械／電氣規格 | 20 MHz 級並列匯流排 |

**EVT 連接器是驗證工具，不構成 DVT 量產器件承諾**（`design.md` §3）。

---

## 5. 轉接板側設計規則（凍結）

這些規則對**所有**顯示候選轉接板生效，與具體面板無關。

| # | 規則 | 理由 |
| --- | --- | --- |
| R1 | **禁止**在 `I2C_SCL`／`I2C_SDA` 上加上拉電阻 | 上拉由核心板單獨擁有（i2c-address-map.md §5.1） |
| R2 | GPIO45／`EPD_STH` 在受控 reset-strap contract 關閉前，**禁止任何外部 pull、adapter loading 或 connector mapping** | GPIO45 選擇 VDD_SPI；所需 reset level 依 exact module／chip／eFuse／board configuration，不能由 N16R8 名稱推導 |
| R3 | **禁止**在 `EPD_OE`（GPIO46）加上拉 | GPIO46 是獨立的 boot + ROM print strapping concern；上拉會影響 ROM log／產線診斷 |
| R4 | ±HV 與 VCOM **不得**接到板間連接器任何腳位 | 高壓隔離邊界 |
| R5 | 轉接板擴充器（若有）用 **0x21**，INT只可open-drain加入RTC／核心共享EXP_INT；禁止推挽與額外IRQ上拉 | 核心R502唯一裝配上拉，R305 DNP |
| R6 | `3V3_TOUCH` 關斷時，觸控控制器不得經 I²C／INT／RST 反灌 | 見 power-tree.md §4.2 |
| R7 | 高壓區域須與低壓區域有明確間距，HV 測試點只在轉接板受控區 | `design.md` §3；見 test-points.md |
| R8 | EPD 上下電時序以該候選面板／PMIC 官方資料為唯一凍結依據 | PRD；現有 TPS65185 PDF 僅交叉審查 |

### 5.1 R2／R3 的重要性

GPIO45／GPIO46 是**唯二**被暫列為顯示訊號的 strapping 腳位，但兩者風險不同：
- GPIO45 控制 VDD_SPI 選擇；所需 reset level 尚未依 exact module／chip／eFuse／board configuration 受控，故目前不得接入 adapter
- GPIO46 的外部上拉會影響 ROM print／boot 診斷，故保持低／無上拉

這是**跨板耦合的復位期風險**，必須寫進每份轉接板的原理圖檢查清單。GPIO45 contract 未關閉前，
不能把「禁止上拉」誤寫成「允許下拉／允許低態 adapter loading」。

---

## 6. 天線與機構邊界（來源：硬體設計指南）

| 約束 | 內容 |
| --- | --- |
| 模組天線位置 | 置於底板**之外**，饋點靠板邊 |
| 若無法置於板外 | 天線兩側與下方挖空（**不是**中央開孔），附近密集地過孔 |
| 外殼內淨空 | 所有方向 **≥15 mm** |
| 驗證 | 成品必須做吞吐量／距離測試 |

天線淨空與 §2.3 的調試焊盤隔離要求會共同約束核心板外形，屬 WP7A 輸入。本文件只記錄約束，不定外形。

---

## 7. 未凍結項目

| 項目 | 阻擋來源 | 解除條件 |
| --- | --- | --- |
| 板間連接器腳位順序與編號 | WP1 | WP4 |
| 連接器 exact contact count／order／MPN | WP1 受控面板資料 + 機構 | 輸入齊備後於 WP4 凍結 |
| G1／G2 實際訊號數（現以 14 保留） | WP1 | WP1 |
| `EPD_HV_IN`／`3V3_EPD_LOGIC` 電流 → 電源腳數 | WP1 | WP1 |
| USB4105-15-A-120 的安裝／配合資格 | 本批已選工程候選，非16/24接點待選 | 板厚、1.20mm焊尾、pin-in-paste／外殼開口與M0/F0實物驗證 |
| 電池連接器是否含 NTC 腳 | 電芯定案 | 電芯選定 |
| FPC 長度／層數／阻抗結構 | WP1 + 機構 | WP1 |
| 核心板外形與天線開孔 | 機構 + WP0 層疊簽核 | WP7A |

---

## 8. 邊界聲明

本文件為接口與連接器規劃，不是原理圖、不是連接器腳位表，不構成任何認證聲明。§3.4 腳數為選型用估算。
天線淨空與吞吐量須實測，本文件不作 RF 性能承諾。
