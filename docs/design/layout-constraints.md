# Panda 標準電子書板：WP7A Layout 約束

工作包：WP6A 輸出 → WP7A 輸入
日期：2026-08-11（最後更新：2026-09-09，執行者：Codex）
板號：`PANDA-STD-CORE-EVT`（修訂 `A`）

2026-09-09 新增 [62.2 × 99.0 mm coupon99 独立工程版本](coupon99-layout-status.md)，
已按用户授权整组重排并完成布线；下文 110.2 mm、旧坐标及旧铜对象统计仅描述保留基线，
不再表示它是唯一可 review 外形。缩板没有关闭 F0/M0 或实物资格门。

本文件是**暫定 Layout 設計意圖**，不是 WP6A 已通過或約束已凍結的證據。`wp6a-pre-layout-review.md` 已於
2026-08-11 撤回通過判定；板廠、機構、原理圖、ERC 與獨立複核到位後必須重審本文件。

---

## 0. 2026-09-09 J501 merged current controlled candidate

本節覆蓋下列所有標為「正式 checkpoint」或「current candidate」但帶有 Fix25 之前歷史 hash／座標／
`0/0/0` 的切片描述；那些切片仍只可作局部工程證據，**不是**目前 J501 merged PCB 的 DRC、parity、ERC 或
製造狀態。

| 項目 | 當前受控值 |
| --- | --- |
| 權威 PCB | `eda/core/PANDA-STD-CORE-EVT/Quilter_PANDA-STD-CORE-EVT.kicad_pcb_Placement_1/PANDA-STD-CORE-EVT-quilter-j501-merged.kicad_pcb` |
| PCB SHA-256 | `d96aef03000e560f7408079990fc9af17437914758e2f50310fa858d3e46a0d6` |
| 外形 | Edge.Cuts 端點 `62.20 × 110.20 mm`；4.26 吋參考 `62.37 × 105.33 mm`，長邊仍多 `4.87 mm`，不是 M0 freeze。 |
| 結構 | 155 footprints、2128 segments、381 vias、1 個 GND 銅區與 2 個封裝內 keepout zone；Fix25新增J601/J302/R615/R616/C301及419铜对象，旧150封装几何/2090铜和SD/USB/BQ/J502保持。 |
| 本轮 DRC | 2026-09-09完整候选独立检查及正式目录saved/refill复验均為 `0 violations / 0 unconnected / 0 schematic parity`。详见[ERC16检查点](erc16-layout-status.md)。 |
| ERC | 原16条真实闭合，active entries=0；四类历史ignored checks不变。逐项见[erc-status.md](erc-status.md)。 |
| 已關閉的局部問題 | Fix 1–17 已关闭当时报告的 clearance/dangling 项并补齐 project-local library tables。2026-09-07 Fix 18 另删除九段 DRC 未识别的 I²S 近重叠盲支线／被包含段；不能把 DRC=0 推广为全板无冗余铜。 |
| candidate process envelope | KiCad project 目前以 0.15 mm min track、0.40 mm min via、0.20 mm min through-hole、0.05 mm min mask web 記錄**候選**幾何；它使既有 exact-footprint/fine escape 可被 DRC 量測，不是 F0 量產能力或阻焊良率批准。 |
| 未關閉的 layout/DFM | 本地ERC/PCB几何门已清零，但J301电池电源接口及实物线束未完成；I²S BCLK/LRCLK/DIN铜段总和108.660/111.585/102.060mm及8/6/6vias须EVT/SI/EMI实测。F0/M0/WP3/WP4、精確BOM和实物原型不因DRC0关闭；历史31个器件模型缺口之外，新增J601/C301也缺实体模型，完整装配包络未验。 |

## Fix 24：J502 两路BTL输出（2026-09-08，Codex）

已批准并提升的J502位于(34,4)F/90°，pin1=P、pin2=N，两MP no-net；14段／4标准0.60/0.30mm过孔，
0.30mm源逃线与0.50mm主线。完整旧对象保持、SD/USB/参考地及真实负控通过。
几何口径与未验总成边界见[J502记录](lib/review/J502-GH-A-stage.md)，不是音频／制造放行。

## Fix 23: BQ_PG / P10 routing (历史检查点，2026-09-08, Codex)

PG uses32 segments and7 ordinary0.60/0.30mm vias across F/B/In2, with no In1 signal track or via-in-pad.
The summed track length is84.189690mm, not an endpoint propagation length. Existing placements and unrelated copper
remain fixed; only the approved P10/R600 termination and dedicated old ground via changed. See the linked BQ_PG record
for independent topology, negative controls and electrical qualification limits. 中文说明：临时锁和非目标序列化差异已恢复，规则未放宽。

## Fix 22：SD 单层与匹配（历史检查点，2026-09-08，Codex）

六路267段全F.Cu、零SD via，实际pad中心参考长度均在CLK±1.27mm；267段与29pad的1µm外逼近
铜幅均落在保存的In1 GND内。D3曾贴地平面边界的问题已在新候选向内移0.2mm修复，未改地平面规则。
六路均超50.8mm理想长度偏好；此结果不是SI、50Ω或4-bit SD台架资格。批准范围及精确长度见[SD检查点](sd-layout-status.md)。

## Fix 21：底边USB／共享IRQ（历史检查点，2026-09-08，Codex）

新增底边J201=USB4105-15-A-120及CC、失电隔离、VBUS监控、ESD和阻尼电路，共149封装/1566segments/311vias。
RTC与扩展器共用GPIO4；GPIO2经比较器/缓冲器监控VBUS；R305 DNP，R502为唯一已装核心IRQ上拉。
P16/P17接收隔离后的CC GPIO状态。正式saved/refill DRC、未连接、parity均0/0/0，ERC22→19。
USB两插向的中心参考平面路径差为−0.321863/−0.321905mm，各6via且层序相同；不含过孔竖直延迟，
不以曾被纠正的“<0.001mm”脚本结果宣称精度。最长未选镜像接点支路3.5025mm，ESD/DNP支路另列。
当时R517–R519为USB让位并重布相关SD网；其余旧器件位置保持。当时SD全六路未满足同层/≤1.27mm目标；最新结果见Fix22。
3D完整分类为6缺引用文件、25真实器件未配置模型、21非装配测点/治具、97可解析模型；不能沿用旧“缺5个”作为完整统计。
USB总源500mA门、3ms实测、C210有效容量、ROM/ESD/EMI及F0/M0等仍未关闭。
详情见[USB2/S-9工程记录](lib/review/USB2-S9-A-stage.md)和[剩余ERC](erc-status.md)。

### Fix 18：I²S 盲支线清理（2026-09-07）

| 网络 | 原铜段长度总和 mm | 当前铜段长度总和 mm | segments 前→后 | vias |
| --- | ---: | ---: | --- | ---: |
| I2S_BCLK | 139.484848 | 108.659848 | 50→45 | 8 |
| I2S_LRCLK | 139.035028 | 111.585028 | 41→39 | 6 |
| I2S_DIN | 131.510060 | 102.060060 | 35→33 | 6 |

删除 U501 三网各两条向东重叠盲支线、U502 BCLK 端两条向西盲支线，以及 BCLK 一条完全被同层铜包含的
0.3 mm 段；现有有效 pad escape、器件、过孔、原理图、规则、板框及非目标铜保持。累计减少 87.725 mm
是逐线段累加值，包含重叠铜；不能据此宣称独占铜长度或端到端传播路径缩短相同数值。
U501→U502 主路径未重新布线，换层和参考平面的风险保持开放。

### Fix 19：ERC模型与SCL清理（2026-09-07）

当前U503采用固定 `LSM6DSO32XTR_I2C_MODE1`，pins1/2/3按实际模式设为input；通用符号保留。
新增GND参考及已装R508/MB6下游VSYS_AUDIO供电声明，ERC28→25且其余条目原文不变。
PCB只删除SCL三段冗余铜，所有9个相关焊盘和7个过孔保持；SCL由54→51segments，铜段中心线长度总和
164.169449337→162.519449337mm。1.65mm减少值不是端到端传播路径缩短量。候选及正式独立DRC/refill/parity均0/0/0。
新模型与供电声明已通过三个ERC反向控制，细节见[erc-status.md](erc-status.md)。

`fp-lib-table` 和 `sym-lib-table` 現已位於該 J501 project directory，且分別以
`${KIPRJMOD}/../../../../lib/panda-standard.pretty`、`${KIPRJMOD}/../../../../lib/panda-standard.kicad_sym` 指向受控
project-local library；MAX98357A exact-copper footprint 以 `${KIPRJMOD}/../MAX98357A_T1633_4.pretty` 指向同層受控資產。
這些 library assets 必須與 PCB/SCH/DRU 一起進版本控制，否則 DRC/ERC 結果不可復現。

**4.26 吋長邊壓縮可行性**：2026-08-18 對 `U501 + J501 + R517–R527 + C512/C513` 作 `−4.87 mm` Y 向剛體測試。
在目標 `105.33 mm` 長邊內，U501 會與 U201/L402/U302/C501/C502/C510/J503/R510–R513 等既有固定區碰撞，J501 亦會與
R512/R513 碰撞。因此不得把板框縮短或只移 J501；需要 M0 驅動的整組 floorplan 重排與後續全網重佈，現有
`62.20 × 110.20 mm` 仍是唯一受控 candidate 外形。

---

## 1. 層疊設計意圖（暫定；待板廠書面回簽）

| 層 | 功能 | 重要約束 |
| --- | --- | --- |
| L1 | 元件面、關鍵信號 | TPS63802 + 被動元件、ESP32-S3 模組、BGA/LGA 器件 |
| L2 | **連續地參考** | 🔴 任何斷口都必須有書面理由；地過孔圍欄 |
| L3 | 電源/低速信號 | 電源平面 + `VSYS_RAW`/`3V3_AON` 主幹；保持關鍵回流路徑連續 |
| L4 | 次要信號、底部元件 | 六網調試焊盤在此側 |

待板廠提供：各層銅厚、介質厚度、Dk／玻纖樣式，以及 **50 Ω ±10% 單端／90 Ω differential** 的可製造
線寬與間距。回簽前本文件只保留阻抗目標，不給 CAD 線寬。

---

## 2. 天線禁入設計意圖（B4；待 41-pad footprint 與機構聯合批准）

| 約束 | 說明 |
| --- | --- |
| ESP32-S3-WROOM-1 天線投影區 | **全層禁銅**（L1–L4 全部） |
| 天線距板邊 | 天線優先伸出板邊；若無法伸出，板邊清空且環境淨空 ≥15 mm |
| 禁入物件 | 電池、前光金屬/導光板、顯示 FPC、外殼金屬結構 **不得侵入** |
| 驗收 | 每層 DRC keepout 無違反 |

---

## 3. 電源樹 Layout 約束（B3）

### 3.1 TPS63802 核心升降壓

| 約束 | 值 | 理由 |
| --- | --- | --- |
| `L401` 距 L1/L2 腳 | ≤5 mm | 輸入/輸出功率回路最短；XFL4015 family reference body envelope 為 4.0×4.0×1.5 mm，exact suffix／land pattern 未凍結；另一 reference 為 2.0×1.6×1.2 mm |
| `CI`/`CO` 電容中心距目標腳 | **≤2 mm** | 2026-08-11 核定的可驗收門；量測為電容封裝中心到 U401 對應 pad 中心的直線距離。 |
| `CI`/`CO` 熱端 pad 距目標腳 | 記錄實測值，越短越好 | `C401.1(VSYS_RAW)`→VIN；`C402.1`/`C403.1(3V3_AON_SRC)`→VOUT。 |
| `CI`/`CO` 冷端 pad | 就近 via 下沉 `In1.Cu` GND 平面 | 不以表層長走線回 Pad 8；回流由 GND 平面承擔。 |
| 反饋分壓 `R401`/`R402` | 遠離 SW 節點，靠近 `FB` 腳 | 避免開關噪聲耦合到 FB |
| SW 節點（L1↔L2↔電感） | **最短、無分支、無不必要過孔；目前四段 F.Cu 均為 0.30 mm** | 0.20 mm 已於 2026-08-12 加寬；獨立把四段全改為 0.50 mm 的試驗產生 21 組 clearance violation（按 DRC 報告條目計，未按銅物件去重）。0.30 mm 已驗證 DRC 0/0；0.30–0.50 mm 間未逐級掃寬，不能宣稱 0.30 mm 是幾何上限。載流、溫升與銅厚仍須 F0 複核。 |
| Pad 8 `GND` | 按 DLA0010A 的加長周邊 pad 與回流要求接地 | TPS63802 **沒有中央 EP**；不得建立虛構熱焊盤／EP via array |
| U401↔L401 走廊 | 禁止放置被動件 | X 76.550–78.400、Y 39.150–40.850 保留給 SW。 |

#### 3.1.1 2026-08-11 受控實作實測

| 電容 | 位置與 hot-pad | center→目標 pad | hot→目標 pad | cold→GND via | 結果 |
| --- | --- | ---: | ---: | ---: | --- |
| C401 | `(75.90,38.30)/180°`；pad1 `(76.65,38.30)`→VIN | 0.752 mm | 0.846 mm | 0.550 mm | 已落板 |
| C402 | `(77.02,42.80)/0°`；pad1 `(76.27,42.80)`→VOUT | 1.988 mm | 1.803 mm | 0.550 mm | 已落板；距 2 mm 門僅 0.012 mm，沒有位置公差餘量，M0/F0 後須重驗。 |
| C403 | `(75.12,42.65)/270°`；pad1 `(75.12,41.90)`→VOUT | 1.958 mm | 1.387 mm | 1.124 mm（最近既有 GND via） | 已落板；曾試放的專屬 GND via 與 In2 3V3 僅 0.1485 mm，已撤回，不能把 1.124 mm 誤讀為該專屬 via。 |

在 BQ floorplan 回填前，此 checkpoint 曾為 `0 violations/4 unconnected`；回填初期曾為 `0 violations/18 unconnected`，新增的 14 項是 BQ25628E 必要元件的待佈線網路。該 2026-08-11 受控 candidate 已完成 BQ25628E 的 GND/VBUS/REGN/PMID/BAT/ILIM/CBOOT、SW、SYS local bank 與跨區 `VSYS_RAW` 主幹，并已加入 U501 的 3V3/GND power seed、reset／strap seed、U503 IMU、U502 audio island、U402–U405 四路 load switch、U601 I/O-expander、U302 RTC、U301 fuel-gauge、R509/MB2、核心觀測測試點與 J503 底面調試／恢復接口。KiCad 10.0.5 普通 DRC 為 `0 violations/0 unconnected/0 schematic parity`；ERC=34，J503/UART reference slices=0。唯一 `pin_to_pin` 由基線的 U503.1↔U401.6 改為 U503.1↔負載側官方 PWR_FLAG，反映 MB2 passive 斷點後的 ERC 電力宣告；RTC reference slice 仍只有 U302.6 `VBACKUP` 的 1 条可解释 `power_pin_not_driven`。各 checkpoint 都沒有 TPS63802 未接項。這只表示該 104-footprint core/IO candidate 的已存在網路全部連通；`C_0603_POWER_SEED` 缺 `F.CrtYd`、L401 仍是 M0 envelope、U503/U402–U405/U301 使用严格限定的 local clearance rules，J301/J502/C301 尚未选定，F0/DFM 與獨立 B-stage 尚未簽核，因此不是整板完成或製造放行。

#### 3.1.2 2026-08-13 MB2／觀測點 checkpoint

| 項目 | 受控實作／驗收證據 |
| --- | --- |
| MB2 器件 | `R509=0 Ω/0805`，`(83.50,38.50)/90°/F.Cu`；pad1=`3V3_AON_SRC`、pad2=`3V3_AON`，兩端可探測。 |
| 源側集合 | 只有 `U401.6/C402.1/C403.1/R401.1/R403.1/R509.1`；由 `(76.60,41.70)` 經 0.80 mm In2/F.Cu 主段接 R509.1。 |
| 負載側集合 | R509.2 經 0.80 mm F.Cu/In2.Cu 接回 `(82.00,36.30)` 的系統 trunk；TP3 明確位於負載側。source/load copper shared nodes=`[]`。 |
| 電源／信號 TP | TP1/TP2/TP3/TP16/TP18=`VBUS_USB/VSYS_RAW/3V3_AON/PG_3V3_MAIN/CHIP_PU`；均為 F.Cu D1.5 mm pad。TP1 是 charger-side candidate，不凍結未來 J201 connector-side exact VBUS。 |
| GND TP | TPG1–TPG6 分散於板面，最小中心距 23.005 mm；每點使用獨立 0.60/0.30 mm through-via 下沉 In1.Cu GND。 |
| MB2 歷史 checkpoint 結構 | 103 footprints、526 segments + 160 vias、1 zone；DRC/unconnected/parity=`0/0/0`；当前结构见 §3.1.3。 |

 MB2、TP 與 GND pad 的當前可達性只屬歷史暫定 110 × 60 mm engineering candidate；2026-08-13 J501 merged 緊湊候選已改為縱向 `62.20 × 110.20 mm`。寬邊接近 4.26 吋面板參考 `62.37 × 105.33 mm`，但長邊仍多 `4.87 mm`，尚未完成整組卡座／模組／扇出重排與 M0 凍結。先前嘗試只移動 J501 以得到 `62.20 × 106.35 mm`，造成 J501 與 R521/R522/C512/C513 相對焊盤碰撞，已明确撤回；禁止再作單一卡座位移。R509 exact MPN／額定、
fixture pin map、探針淨空、單／雙面接觸策略及外殼可達性仍受 F0/M0/WP9/B-stage 阻塞。

2026-08-13 J501 merged candidate 另以 `In2.Cu` 0.30 mm 短段把 `U201.9 VSYS_RAW` via `(44.675,70.7)` 接到 `C208.1=(40.3,70.95)` 的 0.60/0.30 mm via-in-pad；此為候選級連通修正，需 F0 與板廠確認 via-in-pad、阻焊／鋼網與 35 µm/18 µm 銅厚口徑，不能視為製造豁免。

2026-08-13 J501 merged candidate 再以 R514.2 pad 内 0.60/0.30 mm through via 与 `In2.Cu` 0.20 mm 走廊接通远端 `3V3_SD` 至 `C513.1=(55.425,89.4)`；走廊为 `(8.1,13.7875)→(8.1,19.1)→(60.0,19.1)→(60.0,89.4)→(55.425,89.4)`。临时 clone 与目标 DRC 均无新增 `shorting_items`/`tracks_crossing`，但 via-in-pad、In2 载流与板厂工艺仍属 F0 门项。

#### 3.1.3 2026-08-13 J503 底面調試／恢復 checkpoint

| 項目 | 受控實作／驗收證據 |
| --- | --- |
| 器件／位置 | `J503=Connector:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical`，`(40.00,26.50)/90°/B.Cu`；排除 BOM/CPL。 |
| 針序 | 1=`CHIP_PU`、2=`3V3_AON`、3=`UART0_RX`、4=`GND`、5=`UART0_TX`、6=`GPIO0`；U501.36/37 分别为 RX/TX。 |
| 接點／孔 | 六個 0.7874 mm B.Cu+B.Mask contact pads；三個 0.9906 mm NPTH 定位孔，中心 `(38.984,23.960)`、`(41.016,23.960)`、`(40.000,29.040)`。 |
| 走線 | J503 新增 20 segments + 8 顆 0.60/0.30 mm through-via；六網均連通；`GPIO0` 不新增電容。 |
| 天線/開關節點隔離 | 最近定位孔 `(38.984,23.960)` 距天線 keepout 區（0–48 × 0–21）邊緣 2.96 mm、距 U501 pad 區（X 15.25–32.75）6.23 mm、距 TPS63802 SW 節點（X≈76–79）>35 mm；§6「距天線 ≥5 mm」按天線物理投影（模組 X 15–33、南向伸出）量測為 ≥5.98 mm，B.Cu 底面接觸墊不進入全層 keepout。 |
| 原廠機械約束 | Tag-Connect Rev B SHA-256=`46073f8d…ceb`；中央陰影 keepout 無 via，六條同網扇出只由各 contact pad 向外離開。DRU 另要求 J503 contact pad 至 footprint 外異網銅 ≥0.508 mm；正式 DRC=0，故意插入不接觸任何 pad 的異網銅負控準確命中 1 條該規則（actual 0.2113 mm）。 |
| 正式結構 | 104 footprints、546 segments + 168 vias（14 × 0.40/0.20 mm、154 × 0.60/0.30 mm）、1 zone；DRC/unconnected/parity=`0/0/0`，ERC=34，J503/UART slice=0。 |

J503 的 bottom-side mating-face、Pin 1 治具視圖、探針行程／retention、板框／外殼可達性與實物下載／恢復仍受
M0、不同身份 B-stage 與 WP9 阻塞。这个 checkpoint 不是治具、機構或製造簽核。

### 3.2 BQ25628E 充電 buck／BQ27427 高側載流

| 約束 | 值 |
| --- | --- |
| `SW`（Pin 16）電感 | `L402` 以受控 2.2 µH envelope 置於 `(42.00,38.00)/180°`；Pin 1=`BQ_SW`、Pin 2=`VSYS_RAW` 已由原理圖 parity 證實。依 TI SLUSFA4C §11.1 item 5，SW 由 U201/CBOOT 側兩個 through-via 下沉 `In2.Cu`，以 0.80 mm 銅線接至 L402.1 側兩個 0.60/0.30 mm through-via。普通 DRC 已連通；F0/B-stage 仍須核定實際 via、銅厚、電流、熱與 EMI。 |
| `CBOOT`（C201） | TI SLUSFA4C §11.1 明確要求置於 IC 反面，並分別以 via 接 `BTST` 與 `SW`；目前 `(45.00,42.55)/B.Cu`。`BTST` 自 U201.1 的真實窄上側 land 出口 `(42.95,41.40)` 至 `(43.40,40.70)` F–B via；`SW` 自 U201.16 經 `(44.50,43.45)` F–B via 接 C201.2。兩端已以 0.15 mm copper DRC 驗證。C201 與 J503 是僅有的 B.Cu 元件（J503 見 §3.1.3），雙面貼裝成本/流程、via/mask 與高 dv/dt 回路須由 F0/B-stage 一併核實。 |
| `CPMID`／`CREGN`／`CVBUS`／`CBAT` | `C203`=10 µF PMID、`C205`=4.7 µF REGN、`C202`=1 µF VBUS、`C206`=**10 µF** BAT 已回填至 PCB。`C206` 為避開 SYS escape 移至 `(38.70,46.20)/180°`，BAT 以 0.15 mm F.Cu QFN escape、0.50 mm B.Cu 主段和兩個 through-via 接回 C206.1。`U201.18→C202.1`、`U201.2→C205.1`、`U201.17→C203.1`、`U201.8→C206.1` 及六個去耦地端的 local-via 回流已 DRC 驗證。PMID/BAT 的 0.15 mm QFN escape 沒有降低 0.200 mm clearance；F0/B-stage 仍須確認製程與電流能力。 |
| `CSYS` 電容 ×2 | `C207/C208`=22 µF（滿足原理圖 `2 × 22 µF` 契約）；兩個正端以 0.50 mm F.Cu 接至 `L402.2`，負端各自 local-via 回 In1.Cu GND。`U201.9 SYS` 以 0.15 mm F.Cu escape 到 `(39.00,43.575)` via，再以 0.80 mm `In2.Cu` 接入兩個 CSYS 正端／L402.2，並延伸至 TPS63802 區既有 `(72.30,38.50)` `VSYS_RAW` via。當前 KiCad 暫定 stackup 的 In2.Cu 僅 18 µm；0.80 mm 不是脫離銅厚的通用門，F0 必須重新計算約 129 mm 混合層路徑的壓降、電流與溫升。**2026-08-13 Quilter（CircuitHub 4-Layer with power plane）輸出全層 35 µm（1 oz）**——若 EVT 在 CircuitHub 製造，129 mm 路徑按 35 µm 重算（壓降約減半）；若仍用 18 µm 內層板廠，維持原口徑。 |
| `RILIM` | `ILIM` 腳 → GND 走線越短越好；1.2 kΩ + 330 nF 串聯 RC 支路與 RILIM 並聯並就近放置 |
| BQ27427 BAT→SRX | 当前 `TP4/R306(MB1)`→`BAT_PACKP`→U301.C3 BAT→內建 7 mΩ sense→U301.C2 SRX→`PACK_BAT`/charger BAT；禁止任何高流旁路。BAT→C303 hot=1.872672 mm，VDD→C304 hot=1.963899 mm；最终 breakout／via／銅寬仍按 RMS 2 A、10% duty peak RMS 3.5 A 與板廠 stackup 核算。 |

2026-08-12 歷史 BQ power-seed checkpoint：`C202/C203/C205/C206/C207/C208/L402` 由 KiCad 10.0.5 `pcbnew` API 依專案 footprint library 及當時 schematic netlist 匯入。六個去耦 GND local-via 回流、VBUS/REGN/PMID/BAT/CBOOT、CSYS-L402、ILIM、SW 與 local/remote `VSYS_RAW` 均已接入；當時普通 DRC=`0 violations/0 unconnected`，PCB SHA-256=`6c0dbff7f4e1f2e036ade2d84c96db03a41e5a3736fe9b0cf7e834d7d42a439e`。`REGN` 自 U201.2 以 0.15 mm F.Cu escape 至 `(42.60,40.70)`，再經 B.Cu 避開 ILIM path；`ILIM` 自 U201.4 以 0.15 mm F.Cu escape 至 `(41.35,40.75)`，經 B.Cu 於 `(42.00,45.55)` 回到 R201。當時 schematic-parity 報告尚有 53 條歸屬 `U501` 的 `net_conflict` 記錄；這是報告條目數，不是未接腳或物理 pad 數（U501 共 41 pads），同一 pad 可出現在多條衝突記錄中。BQ parity 為零。這是歷史切片的電氣連通證據，不是當前檔案 hash、整板完成、製造 DRC pass、F0 stack-up 確認或 WP4/B-stage 簽核。

2026-08-13 U301 fuel-gauge checkpoint：U301=`(33.00,49.50)/180°/F.Cu`，C303/C304=
`(30.15,48.90)/(30.15,50.10)`，R306/MB1=`(29.50,45.50)`，TP4=`(26.00,45.50)`。
`BAT_CONN_P`/`BAT_PACKP` 主段 0.80 mm，U301.C2 `SRX` 到既有 `PACK_BAT` 主段包含 0.80 mm 铜，
无 BAT→SRX 旁路；C303/C304 cold pad 各有 0.870 mm local GND via。正式 schematic/PCB/DRU SHA-256
分别为 `364234d2…3df`/`f79ce105…b84`/`6e53da17…1b1`；DRC=`0/0/0`，ERC=36 且 U301 slice=0。
该历史 fuel-gauge checkpoint 为 91 footprints、508 segments + 150 vias、1 zone；原 83 footprints 和 601 个既有 copper objects
全部保持。U301 中央 VSS escape 的 0.15 mm local rule 移除后恰有 GND track→B1 `FUEL_BIN` 的 1 条
clearance error（actual 0.1561 mm）；全局仍为 0.20 mm，
该规则不是 F0 waiver。R307=10 kΩ 对应 embedded-battery `BIN` 默认终接；目标电芯 NTC/J301/harness
冻结后必须复核，不能把本 checkpoint 当作电池总成签核。

### 3.3 ESP32-S3-WROOM-1-N16R8 电源、reset 与 strap（A-stage seed）

| 约束 | 当前实现 |
| --- | --- |
| `3V3_AON` 入口 | U501 pad 2 先以 0.635 mm F.Cu 接 C502 100 nF，再接 C501 22 µF 与 `(13.15,27.20)` 0.60/0.30 mm through-via；按 Espressif ≥25 mil 建議取值，尚不構成 exact stackup/thermal 合規判定。 |
| 高频旁路 | `C502=(12.90,23.65)/180°`，hot pad `(13.38,23.65)` 到 U501.2 `(15.25,23.76)` 为 **1.8732 mm**；先于 bulk capacitor 落点。 |
| Bulk capacitor | `C501=(12.20,25.40)/180°`，hot pad `(13.15,25.40)` 到 U501.2 为 **2.6645 mm**；它是 bulk，不套用 TPS63802 CI/CO 的 2 mm 門，高頻回路由 1.8732 mm 的 C502 承擔；精確 MPN、電壓與 DC-bias 後有效電容待 BOM review。 |
| 内层主干 | 0.80 mm `In2.Cu` 从 U501 入口绕过 pad 41 thermal array，经 `(12.00,33.50)→(78.50,33.50)→(82.00,36.30)` 到 MB2 負載側；R509/MB2 再以 0.80 mm F.Cu/In2.Cu 接 TPS63802 `(76.60,41.70)` 的 `3V3_AON_SRC` star。 |
| GND 回流 | C501/C502 与 U501 pads 1/40 各有独立短 F.Cu stub + local through-via；pad 41 使用官方 footprint 导热阵列接 GND。 |
| 天线区 | 所有新增电容、入口铜线与 vias 均位于 footprint all-layer keepout 的 Y=21 mm 下缘之外；M0 仍须冻结模组相对板边/外壳位置。 |

| Reset RC | `R510=(12.80,28.20)/0°`、`C510=(10.50,29.50)/180°`；R510=10 kΩ 上拉、C510=1 µF 到 GND。U501.3 的短 F.Cu escape 经 `(14.25,25.03)` 与 `(13.90,28.20)` 两颗 0.60/0.30 mm through-via 在 B.Cu 绕开相邻 pads。 |
| GPIO0 strap | `R511=(35.00,34.80)/270°`，10 kΩ 上拉；signal pad 到 U501.27 中心距 **4.3219 mm**，上拉端以 `(35.00,33.50)` via 接既有 In2.Cu `3V3_AON`。未加会提高 GPIO0 reset 电平的电容。 |
| GPIO3／GPIO46 strap | `R512=(17.00,42.40)/270°`、`R513=(19.20,42.40)/270°`，各 10 kΩ pulldown；signal-pad→目标脚中心距分别 **1.6401 mm**／**1.8780 mm**，各用独立 local GND via。 |
| GPIO45 | U501 pad 26 仍完全无外部 pull、adapter loading、connector mapping 或铜线；必须等待 exact module／eFuse／board reset-level contract。 |

2026-08-12 U501 reset/strap 歷史 checkpoint：當時 schematic
SHA-256=`f8fccba61cb3b401440884b12fc3c564c2749ee32010847d695a6969c88aae85`，PCB
SHA-256=`23a1a52effd13d6f82cf89ff1f6bf21b8b8e4376f62c476e6505a2a34ba5c836`。該 checkpoint 的受控輸出為
ERC=45、普通 DRC=`0 violations/0 unconnected`、schematic-parity=33；剩餘 parity 全部為 U501 尚未分配功能腳的
`net_conflict`，無 asset/field mismatch。先前文字中的 ERC=50／parity=37 是未歸檔暫態數字，已移出驗收鏈，
不再用來宣稱改善幅度。新增五顆 passives 與所有新增銅均位於 Y>21 mm 的天線 keepout 外。
C501/C502/C510/R510–R513 是 generic KiCad placement envelopes，精确 BOM、F0 电流/热核算、M0 与不同身份
B-stage 均未关闭。

### 3.4 LSM6DSO32XTR IMU（A-stage engineering candidate）

| 约束 | 当前实现／边界 |
| --- | --- |
| 器件位置 | `U503=(62.00,23.00)/0°`，远离 U501 天线 keepout、TPS/BQ 开关区和预留音频区；最终位置仍由 M0/整机振动与应力评估决定。 |
| Vdd_IO 去耦 | `C503=(61.00,25.80)/270°`；hot pad→U503.5 为 **1.49 mm**、center→pad 为 **1.95 mm**，cold pad→专属 GND via 为 **0.72 mm**。 |
| Vdd 去耦 | `C504=(64.80,24.30)/0°`；hot pad→U503.8 为 **1.28 mm**、center→pad 为 **1.73 mm**，cold pad→专属 GND via 为 **0.72 mm**。 |
| INT1 reset level | `R501=(58.40,25.00)/270°`，100 kΩ pulldown；INT1 局部铜总长约 **2.727 mm**。U601 P12 consumer 已接入，网表成员为 `R501.1/U503.4/U601.15`，既有硬件下拉保留。 |
| Mode 1 straps | SA0→3V3_AON（7-bit 0x6B）；SDx/SCx→GND；CS→3V3_AON；INT2/pins 10/11 各保持独立 NC。 |
| I²C topology | U503.13/14 分别接 U501 GPIO14/GPIO15 与 U201 SCL/SDA。2026-08-23 整板当前值：SCL=54 segments/7 vias/164.169 mm，SDA=39 segments/7 vias/189.409 mm，均使用 F.Cu/B.Cu；pull-up 值、总线电容、分支拓扑与 timing 尚未关闭。 |
| LGA 内部间距 | 全局 clearance 维持 0.20 mm；`PANDA-STD-CORE-EVT.kicad_dru` 只对 U503 内部对象设 0.15 mm。删除该规则的相同工程 negative control 恰有 12 个 U503 内部 pad clearance errors（0.150/0.175 mm）。这是 generic footprint 与全局规则冲突的显式 F0/DFM/B-stage 门，不是制造豁免。 |
| 方向标识 | 官方 candidate 有 Pin-1 marker；X/Y/Z 朝向尚未写入丝印／装配层，因此 M0/assembly gate 未关闭。 |

2026-08-12 歷史受控 checkpoint：schematic SHA-256=`81be91793a76218a04f05b115dffcf379ea045a18a7e8eb04be2cd6eee5da543`，
PCB SHA-256=`7796d4a14e9bee42f708b02edda0a099ffb2c85fc5d1ab1eb54b7e6f13e50837`，局部规则
SHA-256=`9c5865b886cc9b001432178d7459cb2711a4e9d4af4812836727021b00fa9700`。KiCad 10.0.5 普通 DRC=`0/0`；
schematic parity=31 且全部为 U501 尚未分配功能脚；ERC=41，包含 U503.1 bidirectional→3V3_AON 的 1 个
`pin_to_pin` 电气类型审查项。此切片是受控工程候选；它不关闭 `schematic-spec.md` 的 WP3 总门，也不构成
ST exact land pattern、F0、M0 或不同身份 B-stage 签核。

### 3.5 MAX98357A 音频岛（A-stage engineering candidate）

| 约束 | 当前实现／边界 |
| --- | --- |
| 器件与 footprint | `U502=(99.00,36.50)/0°`，F.Cu；使用 project-local `MAX98357A_T1633_4:MAX98357AETE_T_TQFN16`。铜焊盘按 ADI `90-0031 Rev C`／`T1633+4`，不是 KiCad generic `T1633-5`／`90-0032`。 |
| 高频去耦 | `C505=100 nF (99.50,40.00)/270°`；hot-pad→最近 U502 VDD pad **1.614 mm**，cold-pad→local GND via **1.000 mm**。 |
| Bulk 去耦 | `C506=10 µF (102.00,40.00)/270°`；hot-pad→最近 U502 VDD pad **2.599 mm**，cold-pad→local GND via **1.000 mm**。它是 bulk，不套用 TPS63802 CI/CO 的 2 mm 門，高頻回路由 1.614 mm 的 C505 承擔；精确 MPN、电压与 DC-bias 未冻结。 |
| `VSYS_AUDIO` local island | U502 pads 7/8 以 0.30 mm、最长 0.875 mm 的 fine-pitch escape 合并到 0.50 mm 主段；C505/C506 与 `R503=10 kΩ` 接该 island。0.30 mm 例外仅限 U502 perimeter pad escape；上游现由 U405→R508/MB6 接入，见 §3.6。 |
| SD/Gain | R503 只上拉 `SD_MODE` 到 `VSYS_AUDIO`。R504=0 Ω→GND 已安装（12 dB baseline）；R505=100 kΩ→GND、R506=0 Ω→VSYS_AUDIO 均 DNP。 |
| EP/GND | Synthetic pad17 与 GND pins 3/11/15 在 F.Cu 短接；外置 GND via 位于 `(102.00,36.25)`。没有 via-in-pad；EP paste/mask/钢网仍由 F0/B-stage 审核。 |
| I²S | U501 GPIO11/12/13（pads 19/20/21）分别接 BCLK/LRCLK/DIN。2026-09-07 当前值均为 0.20 mm F.Cu/B.Cu 混合走线：BCLK=45 segments/8 vias/108.660 mm，LRCLK=39/6/111.585 mm，DIN=33/6/102.060 mm；长度口径为铜段中心线总和，见 §0。B.Cu 相邻 In2 power 而非连续 GND，参考质量与多次换层风险保持开放；必须在 M0/F0 后重布或以 EVT/SI/EMI 复核关闭。 |
| GPIO45 | U501 pad26 仍无 net；最近 track/via 中心线距离 **2.163 mm**。 |
| Speaker output | Fix24正式源已将U502 pads9/10接至JST GH SM02B-GHS-TB `J502`，pin1=P、pin2=N、两机械焊盘no-net，其他元件／铜／规则保持。属于2026-09-08已批准工程例外；8 Ω ≥1 W 总成、线束／插拔、声孔／声腔与 M0 仍未验收，不以接口接通代替。 |

2026-08-12 歷史受控 checkpoint：schematic SHA-256=
`61b2444d0fe85c781cf0fb38dc360505d609abddd6902eddd6232f67d6a17800`，PCB SHA-256=
`e1b7a7027f12654fab4f5f3552ac54df18b92e784d01d6e62f3aa36f34beb696`。普通 DRC=`0/0`；parity=28，
全部为既有 U501 尚未分配功能脚。`PANDA-STD-CORE-EVT.kicad_dru` 没有 U502 特例，全局 0.20 mm 未改变。
这是 U405 应用前的历史 U502 checkpoint；当前 U405 A-stage 上游见 §3.6。J502、SPK EMI、声学、F0、M0、
WP3 与不同身份 B-stage 仍阻塞。

### 3.6 四個功能域負載開關

| 約束 | 說明 |
| --- | --- |
| 使能信號 | 來自 TCA9535 P00–P03，低速，可繞線 |
| 輸出連接 | `3V3_SD` → microSD 插座；`3V3_TOUCH`/`3V3_EPD_LOGIC` → 板間連接器 |
| 隔離 | 輸出端防反灌，板間側可能有電容反灌 |

`U402`–`U405` 均已建立 TPS22916CYFPT A-stage engineering candidate；以下先保留 U405 歷史 checkpoint，
再記錄 2026-08-13 三路 3V3 switched-rail 增量：

| U405 約束 | 当前实现／量化证据 |
| --- | --- |
| 器件／方向 | `U405=(105.00,44.50)/0°`，F.Cu；A1=`VSYS_AUDIO_SW`、A2=`VSYS_RAW`、B1=`GND`、B2=`EN_VSYS_AUDIO`；project-local `panda-standard:TPS22916CYFPT_YFP0004`。 |
| VIN 去耦 | `C507=1 µF (107.00,45.30)/270°`；A2→C507 hot pad **1.814 mm**，cold pad→专属 GND via `(107.00,47.20)` **1.125 mm**。精确 MPN／电压／DC-bias 尚未冻结。 |
| 默认关断 | `R507=100 kΩ (105.20,47.60)/270°`；U405 B2→R507.1 为 **2.390 mm**；R507.2 以专属 via `(105.20,49.00)` 回 In1.Cu GND。U601 P03 已接入 `EN_VSYS_AUDIO`；上电配置前仍由 R507 保持关断。 |
| MB6／TP8 | `R508=0 Ω/0805 (102.60,44.30)/180°` 实作 MB6；U405 A1→R508.1 **1.2875 mm**，两端保持可探测。`TP8=(98.00,45.75)` 位于 R508 下游 `VSYS_AUDIO`。 |
| 电源铜 | U405 fine-pitch pad 仅用 0.15 mm 极短 escape；`VSYS_AUDIO_SW/VSYS_AUDIO` 主段 0.50 mm。`VSYS_RAW` 以 0.80 mm B.Cu 走廊跨区，源端 `(69.80,35.00)/(70.80,35.00)` 与音频端 `(108.80,46.20)/(108.80,47.00)` 各两颗 0.60/0.30 mm through-via。B.Cu 與 In1.Cu 並不相鄰，不能宣稱直接參考；混合 F/B/In2 路徑的壓降、熱與平面耦合待 F0。 |
| GND 回流 | U405 B1→local GND via `(103.80,46.00)` **1.6401 mm**；C507 与 R507 各有独立 local via。没有 via-in-pad，In1.Cu GND zone／Edge.Cuts 未改。 |
| YFP0004 内部间距 | TI example land 为 0.23 mm、pitch 0.40 mm，相邻内部铜间距 0.17 mm。全局 clearance 仍为 0.20 mm；`.kicad_dru` 只在 `A.memberOfFootprint('U405') && B.memberOfFootprint('U405')` 时允许 0.15 mm。 |
| 规则反例 | 移除 U405 local rule 时恰出现 4 个 U405 内部 0.17 mm clearance errors；保留规则但在 A2 外放置实际间距 0.17 mm 的 GND 铜时，全局 0.20 mm 仍产生 clearance error。该规则不是整板 waiver，也不是 F0 回签。 |

2026-08-12 歷史受控 U405 checkpoint：schematic SHA-256=
`fd2d6924022edb9d7711ee04ca3138145936312594270390d877f29b86e240e2`，PCB SHA-256=
`adaf5997d39c4cfc64e61b8e946aabaf0efefb91a785761259d1e3cbf9797af1`，DRU SHA-256=
`bc3fae1a67268bdc4b81345fc5303337e2b3312a3b806181fc55eba63533bf72`。普通 DRC=`0 violations/0 unconnected`；
parity=28 且全是既有 U501；ERC=41，與 U405 加入前的语义基线完全一致。这里的 39 个 footprints／296 个
copper objects 是 **U405 應用前**的歷史基線；應用後的 2026-08-12 歷史 candidate 為 44 footprints、243 segments +
78 vias = 321 copper objects。Edge.Cuts、zone 与 `SPK_P/SPK_N` 经结构审计均未改变。该结果只关闭 U405 A-stage
engineering candidate；F0、M0、WP3、精确被动件与不同身份 B-stage 仍阻塞。U601 P03 consumer 已于
2026-08-13 的 65-footprint candidate 接入，不再列为此节点缺项。

| U402–U404 約束 | 当前实现／量化证据 |
| --- | --- |
| 器件／方向 | U402/U404/U403 分別置於 `(92.00,7.00)/(92.00,13.00)/(92.00,19.00)`、均为 `180°`/F.Cu；共用 project-local `panda-standard:TPS22916CYFPT_YFP0004`。 |
| 网络契约 | A2=`3V3_AON`、B1=`GND`；A1 分別为 `3V3_SD_SW/3V3_EPD_LOGIC_SW/3V3_TOUCH_SW`；B2 分別为 `EN_3V3_SD/EN_3V3_EPD_LOGIC/EN_3V3_TOUCH`。 |
| VIN 去耦 | C508/C511/C509 分別置於 `(90.20,7.00)/(90.20,13.00)/(90.20,19.00)`、`90°`；中心→U 均 **1.800 mm**、hot pad→VIN 均 **1.700 mm**、cold pad→各自 local GND via 均 **1.513 mm**。 |
| 默认关断 | U601 P00/P02/P01 分别驱动三路 enable；既有 R604/R606/R605=100 kΩ pulldown 保留，配置前 default-off。 |
| MB／TP | R514/MB3=`(95.00,7.00)`→TP5=`(99.00,7.00)`；R516/MB5=`(95.00,13.00)`→TP7=`(99.00,13.00)`；R515/MB4=`(95.00,19.00)`→TP6=`(99.00,19.00)`。输出止于 MB/TP，待 M0 冻结 J501/J601 后再延伸。 |
| 电源铜／回流 | WLCSP pad 使用 0.15 mm 极短 escape，3V3_AON 与 MB 主段 0.50 mm；每路两颗 local GND via，无 via-in-pad。当前 provisional stackup 的压降、热、铜厚与过孔能力仍由 F0 复核。 |
| YFP0004 规则 | 全局 clearance 仍为 0.20 mm；`.kicad_dru` 分别把 U402/U403/U404/U405 的 footprint-internal gap 限域为 0.15 mm。删除整个 DRU 的负控产生 28 条 clearance errors（四颗 TPS22916 与 U503 均被捕获），不构成板厂 waiver。 |

2026-08-13 正式 switched-rail checkpoint：schematic SHA-256=
`0403ec43fb5634f0413d7fb41fe013167057108a5e21eb1cb406f76a1eabc20f`，PCB SHA-256=
`bfe40f3e3fa2b10fe698f369debc5144975a9d21f93de3b7e3bacc63488e628f`，DRU SHA-256=
`fb34d9176ae0fceae5689fcd0ac5993d118c555531dd26e42ada2acaeaef8b2d`。KiCad 10.0.5 DRC=
`0 violations/0 unconnected/0 schematic parity`；ERC=36，新增 slice=0；77 footprints、421 segments + 131 vias。
原 65 个 footprint 的位置/角度/层、486 个既有铜对象 UUID、Edge.Cuts 与 In1.Cu GND zone 均保持。该结果只
关闭三路 A-stage engineering candidate；M0/F0/WP3、连接器、精确被动件与不同身份 B-stage 仍阻塞。

### 3.7 RV-3028-C7 RTC（A-stage engineering candidate）

| 约束 | 当前实现／量化证据 |
| --- | --- |
| 器件／方向 | `U302=(53.50,35.00)/0°/F.Cu`；KiCad 官方 C7 SON-8，8 个功能 pads，无 EP／NC。 |
| VDD 去耦 | `C302=100 nF (56.20,33.60)/0°`；U302.7→hot pad=`1.8350 mm`；VSS→专属 GND via `(55.00,36.35)`=`0.8500 mm`。 |
| 无后备源边界 | C301 未获准，故 `R304=10 kΩ (56.20,35.45)` 将 VBACKUP 接 GND；U302.6→R304.1=`1.5400 mm`。批准 C301 后才改 R304 DNP。 |
| 未用 EVI／CLKOUT | `R303=10 kΩ (52.00,30.50)` 把 EVI 上拉 `3V3_AON`；CLKOUT no-connect，EEPROM 35h 禁用／读回仍是产线门。 |
| RTC_INT | `R305=100 kΩ (50.80,32.50)` 上拉；`TP14=(47.00,35.50)`；以 F/B/F 铜线和两颗 vias 接 U501 pad38/GPIO2。 |
| I²C | U302.3/4 以短 F.Cu escape + B.Cu 接入现有 SCL/SDA 主干；地址固定 `0x52`，不沿用 PCF85063A 的 0x51。 |
| 回流几何 | C302/R304 共用正交 T 形 GND 路径到 `(58.00,36.50)` via；C302 cold route=`3.4258 mm`，无三段锐角聚合／copper sliver。 |
| 保留审计 | 原 77 footprints 均保持；只把 U501 pad38 从自动未连接网接入 RTC_INT。原 552 个 copper objects、Edge.Cuts 与 In1.Cu GND zone 身份均保留。 |

2026-08-13 正式 RTC checkpoint：schematic SHA-256=
`a43e1892eb6a7156c7436ee42f11a11c453b48a49e72a567d894e7cb899f6417`，PCB SHA-256=
`b9c8dfb23bacbab97aef6b67dc525fbe4c0fff3aa84d500ac1615c7c67f15888`，DRU SHA-256=
`fb34d9176ae0fceae5689fcd0ac5993d118c555531dd26e42ada2acaeaef8b2d`。KiCad 10.0.5 DRC=
`0 violations/0 unconnected/0 schematic parity`；ERC=36（23/6/4/2/1），RTC slice 仅上述 VBACKUP warning；
83 footprints、461 segments + 140 vias、1 zone。两次从相同 77-footprint 基线独立生成的 PCB 语义指纹一致；
四层 SVG、top/bottom 3D、RTC close-up 与 schematic PDF 均已检查。该结果只关闭 RTC A-stage engineering
candidate；exact suffix、C301／24 h 保时、EEPROM、F0/M0/WP3 与不同身份 B-stage 仍阻塞。

---

## 4. 板間連接器機械邊界（B1，提案；尚未批准）

本节保留早期分组/机械提案，不覆盖当前工程接点表：Fix25已选60pin DF40C-60DS-0.4V(58)，
准确针序/位置见[ERC16检查点](erc16-layout-status.md)与任务接口文档；配对高度、板框及M0仍未冻结。

| 項 | 值 |
| --- | --- |
| 信號數上界 | G1(8) + G2(6) + G3(2) + G4(1) + G5(4) + G6(地) = 21 信號 + 地 |
| 連接器尺寸 | 早期21+脚估算已由60pin工程封装替代；配对禁入区、对接高度与板框仍待M0，不能称为机械frozen |
| 高壓禁止 | ⛔ **G7 高壓/VCOM 腳數為 0**，任何正負高壓網路絕不過此連接器 |
| 對接高度 | 視機構圖確定 |

---

## 5. 關鍵器件 Layout 優先級與位置

| 優先級 | 器件 | 約束 |
| --- | --- | --- |
| 1（先鎖定） | ESP32-S3-WROOM-1 天線端 | 板邊，天線朝外，全層 keepout |
| 2 | USB-C 插座 `J201` | 板邊可插拔；ESD 陣列在連接器旁 |
| 3 | microSD 插座 `J501` | 側邊可插拔 |
| 4 | 板間連接器 `J601` | EVT候选B面(51.2,86)、0°，pad1(45.4,84.46)；配对总成/M0待验 |
| 5 | 電池連接器 `J301` | 內部，防反鎖扣 |
| 6 | TPS63802 `U401` + 電感/電容 | L1 核心電源區，遠離天線 |
| 7 | 調試焊盤 `J503` | 已以 TC2030-IDC-NL A-stage 置於 `(40.00,26.50)/B.Cu`；最終治具／外殼可達性仍待 M0/WP9 |
| 8 | BQ25628E `U201` | 靠近 USB-C 和電池連接器 |
| 9 | MAX98357A `U502` + 喇叭連接器 `J502` | 音訊域，有聲孔/聲腔配合 |
| 10 | LSM6DSO32X `U503` | A-stage candidate 位于 `(62.00,23.00)/0°`；远离喇叭/板边应力，X/Y/Z 朝向标识与 M0 仍待关闭。 |
| 11 | RV-3028-C7 `U302` + 超級電容 `C301` | C301=KW-5R5C684-R已落B面(12,49.5)/90°，R304 DNP；内部trickle配置、预充、24h与漏电老化待实测 |
| 12 | BQ27427 `U301` | 電池路徑附近；BAT/SRX 之間不得有繞過 integrated sense 的 PACK+→system 支路 |
| 13 | TCA9535 `U601` | 接近 I²C 匯流排中心 |
| 14 | 其餘被動元件/電阻 | 按電源/信號就近原則 |

---

## 6. 特殊網類規則

| 網類 | 走線規則 | 間距 |
| --- | --- | --- |
| USB D+/D− | **90 Ω differential**；pair skew ≤0.5 mm | 精確線寬／間距待板廠 stackup 回簽 |
| SDMMC CLK/CMD/D0–D3 | **50 Ω ±10% single-ended**；CMD/D0–D3 各自與 CLK 長度差 ≤50 mil（1.27 mm）；不得跨層 | 精確線寬待 stackup |
| I²S BCLK/LRCLK/DIN | 当前 U501→U502 使用 0.20 mm F.Cu/B.Cu 混合走线；BCLK/LRCLK/DIN 为 45/39/33 segments、8/6/6 vias。B.Cu 相邻 In2 power 而非连续 GND，参考品质弱；M0/F0 后重布或做 EVT/SI/EMI 复核 | 全局 ≥0.20 mm；当前铜段长度总和 108.660/111.585/102.060 mm，多次换层与串扰风险保持显式开放 |
| I²C SCL/SDA | 既有器件网络保持，Fix25新增至J601的0.20mm分支并通过原生连通；旧51/39段与7/7via统计只是新增接口前历史切片。最终路径、层转换与支线须在pull-up值、总线电容、速率及M0冻结后复核 | 全局 ≥0.20 mm；U503/U301 局部规则不适用于外部 I²C 铜线 |
| SW 節點（L1↔L2↔L401） | 最短、無分支；四段 F.Cu 實作 0.30 mm | 0.30 mm 已在現有 DLA/L401 幾何下驗證 DRC 0/0；0.50 mm 全段試驗會產生 21 組 clearance violation，兩者之間未逐級掃寬，因此不宣稱幾何上限；F0 仍核算載流/溫升 |
| `3V3_AON` 主幹 | ≥0.5 mm（目標 ≥1 mm）；当前 MB2 源／負載接入主段均為 0.80 mm | R509 兩側必須維持 `3V3_AON_SRC`／`3V3_AON` 不同網名，禁止銅旁路 |
| `VSYS_RAW` 主幹 | ≥0.8 mm 只適用於當前候選幾何，不是脫離銅厚的通用門；In2.Cu 暫定 18 µm、外層 35 µm | 約 129 mm 混合層主幹的峰值壓降、溫升與銅厚由 F0 重算 |
| `VSYS_AUDIO` | 主段 ≥0.5 mm；只允许 U502 0.5 mm pitch pads 7/8 各用 0.30 mm、≤0.875 mm 的封装逃线，随后立即合并到 0.50 mm；U405 YFP pads 只用 0.15 mm 极短 escape，随后立即进入 0.50 mm | U405 已是 A-stage candidate；WP3 声学峰值／压降／热与 F0/B-stage 尚未冻结 |
| EPD 數據 D0–D7 | 直連，不過擴展器；当前8路pad中心平面路径22.798195–32.159193mm，最大差9.360998mm≤10mm；不含via-Z/时延资格 | 新信号0.15mm，换层via实际0.40/0.20mm；无In1信号 |
| 调試焊盤 6 網 | 隔離：距天線 ≥5 mm，距 SW 節點 ≥3 mm | — |

**阻抗邊界**：以上是 pre-stackup 設計目標，不能生成可製造線寬。只有板廠回簽唯一 stackup ID 與 geometry 後，
才可把線寬／間距寫入 KiCad net class。

### 6.1 顯式 DFM／組裝跟蹤項

- 當前有 **66 顆 0.40/0.20 mm through-via**（另有315顆0.60/0.30mm，共381；Fix25原生逐层读回）；以 1.6 mm 板厚計，前者為 8:1 深徑比。部分板廠只保證 6:1，F0
  必須書面確認 finished drill、鍍銅與量產能力，否則放大鑽孔或重佈。
- 当前B.Cu共12个封装：C201/C301/C514/C515/D202/J302/J503/J601/R529/R530/R615/R616（C514/C515为DNP、J503为非装配治具触点，C301是后装THT）；`C201` 反面位置符合所引用的 BQ25628E layout guidance，`J503` 為無腿 tag-connect 接觸墊（排除 BOM/CPL）。雙面貼裝成本、
  二次回流與治具流程，仍由 F0/組裝報價決定。
- `C402` 的 2 mm 中心距門只剩 12 µm 餘量；M0 移位、封裝更新或 grid round-off 後都必須重新量測。

---

## 7. WP7A 開始前的必要條件

| # | 條件 | 狀態 |
| --- | --- | --- |
| 1 | WP6A 通過 | **❌ 未通過；舊結論已撤回** |
| 2 | 板廠 **Phase F0** stackup／工藝能力書面回簽 | **未取得；只有 unsigned template**；post-layout board-specific DFM 屬 WP8，不是此門 |
| 3 | 機構 **Phase M0** 板框／孔位／固定器件 envelope 批准 | **未取得；只有 unapproved template**；post-layout STEP collision 屬後續門 |
| 4 | KiCad 原理圖完成並通過 ERC | **2026-09-09工程ERC门通过：active0**，旧34/16报告均为历史；J301未落图及NTC/RTC/面板实物资格不在ERC0结论内 |
| 5 | Project symbols／footprints 由不同身份逐項複核 | **A-stage 記錄已建立；不同身份 B-stage 未執行** |
| 6 | TUSB320LI S-9（VBUS VDD、mode/address、AON-off isolation）與 QON S-10 關閉 | **未關閉** |
| 7 | N16R8 熱邊界以 +65 °C ambient baseline 進 enclosure 熱規格 | **未驗證**；不得按通用 +85 °C 模組處理 |

WP7A 必須等待條件 1–6 各自有可追溯證據；symbol／footprint 子門不能替代其他條件。
## Fix 20（历史checkpoint）：Power/QON 侧按工程候选（2026-09-07，Codex）

新增 SW201=C&K EP21SD1ABE 双刀常开侧按开关和 R528=10k/0402 上拉。SW201 位于(48.50,51.00)/90°，
端子1/3为KEY_POWER_MCU/GND，4/6为BQ_QON/GND；两颗无编号支撑PTH无net，六孔均Ø1.09mm。
R528位于(25.40,74.00)，连接3V3_AON与GPIO1。已完成实际走线和保存GND重填，只有FUEL_GPOUT及BQ_ILIM两条旧段作局部绕线。
当时120 footprints、1218 segments、249 vias；saved/refill DRC、未连接、parity均0/0/0，ERC25→22，未新增flag/NC/ignore。
断开两个接点及直接短接信号的三种负控均被网络成员契约拒绝。安装高度10.29mm，右侧未按外伸5.15mm。
详细孔位、哈希、复现与边界见[EP21SD1ABE A-stage记录](lib/review/EP21SD1ABE-A-stage.md)。
该型号仍是工程候选：没有精确3D；微电流接点寿命、M0整机适配、盖孔工艺及真实ship/deep-sleep行为尚未资格验证。

### Fix21 SD实际路径与未关闭门

用相同端点/串阻两侧中心线及pad中心连接、串阻pad-gap代理口径复算，CLK/CMD/D0/D1/D2/D3依次为
48.978860/35.821458/25.553302/25.540776/16.890022/17.612039mm，路径via数2/4/0/2/2/2。
这不是传播延迟；五路相对CLK差仍超过1.27mm，且CLK本轮也使用换层。未放宽原同层/匹配目标，后续需专项收敛。
