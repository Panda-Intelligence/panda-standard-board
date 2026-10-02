# Split-C1 全量国产化设计记录

当前要求：Core-C1 和 Display-C1 两块 PCB 的所有已装配位号均采用中国大陆厂家器件，不保留进口料例外。当前只有设计文件，没有真实样板。这里的国产身份指厂家身份；电气、固件、供料及实物 EVT 分别验证。

**尚未完成，不能按全国产 BOM 下单。** 当前系统 BOM 共 156 个已装配位号：152 个国产厂家，4 个进口厂家。Core 有 118 个 SMT 位号及板外 TH301；Display 有 37 个 SMT 位号。DNP 和已移除的旧集成电路不计入。屏幕、电池包、线束、天线和外壳选型仍需各自冻结。

本轮对 91 个位号执行受控替换（Core 61、Display 30），另新增 Core C516 本地输出旁路。每项替换同时修改原理图、PCB、精确 MPN/厂家/C 码及可重建脚本；不通过只改厂家字段声明国产化。

## 已应用替换

| 板 | 位号 | 新厂家 / 精确 MPN | C 码 |
| --- | --- | --- | --- |
| Core-C1 | R201 | FH (Fenghua Advanced) / `RS-03K5601FT` | C99891 |
| Core-C1 | R204 | FH (Fenghua Advanced) / `RS-03K1201FT` | C118396 |
| Core-C1 | R303, R510, R511, R512, R513, R523, R524, R525, R526, R527, R528, R600 | FH (Fenghua Advanced) / `RC-02K1002FT` | C140215 |
| Core-C1 | R501, R502, R507, R604, R605, R606, R607, R608, R609, R610, R611, R612 | FH (Fenghua Advanced) / `RC-02K1003FT` | C140219 |
| Core-C1 | R508, R509, R514, R515, R516 | FH (Fenghua Advanced) / `RS-05000FT` | C132364 |
| Core-C1 | R517, R518, R519, R520, R521, R522 | FH (Fenghua Advanced) / `RS-03000FT` | C136582 |
| Core-C1 | R529, R530 | FH (Fenghua Advanced) / `RC-02K22R0FT` | C324769 |
| Core-C1 | R613, R614 | FH (Fenghua Advanced) / `RC-02K2201FT` | C140192 |
| Core-C1 | R615 | FH (Fenghua Advanced) / `RS-03K5231FT` | C140082 |
| Core-C1 | R616 | FH (Fenghua Advanced) / `RS-03K3012FT` | C321843 |
| Display-C1 | C4, C5, C6, C7, C8, C9 | FH (Fenghua Advanced) / `0805B475K250NT` | C37818 |
| Display-C1 | C10 | FH (Fenghua Advanced) / `0805B105K250NT` | C89190 |
| Display-C1 | C11, C12, C13 | FH (Fenghua Advanced) / `0603B104K250NT` | C694249 |
| Display-C1 | R1, R2, R3, R4, R5 | FH (Fenghua Advanced) / `RC-02K22R0FT` | C324769 |
| Display-C1 | R6 | FH (Fenghua Advanced) / `RC-02K1000FT` | C140217 |
| Display-C1 | R7, R8, R9, R10, R11, R12 | FH (Fenghua Advanced) / `RC-02K1003FT` | C140219 |
| Display-C1 | R13 | FH (Fenghua Advanced) / `RS-03L2R20FT` | C322118 |
| Display-C1 | R14 | FH (Fenghua Advanced) / `RC-02K1002FT` | C140215 |
| Core-C1 | U402, U403, U404, U405 | SGMICRO / `SGM2578SDYG/TR` | 未确认，待精确供料接收 |
| Display-C1 | D1, D2, D3 | JSCJ / `MBR0530` | C77336 |
| Core-C1 | J601 | HCTL / `HC-PBB40C-60DS-0.4V-1.5-02` | C19089250 |
| Display-C1 | J1 | HCTL / `HC-PBB40C-60DP-0.4V-02` | C19089235 |
| Core-C1 | TH301 | Nanjing Shiheng Elec / `MF52D-103F3435-100` | C394023 |
| Core-C1 | J302 | HCTL / `HC-1.0-3PWT` | C2845362 |
| Core-C1 | J502 | HCTL / `HC-1.0-2PWT` | C2845361 |
| Core-C1 | J803, J804 | XKB Connection / `X05A10H06G`，原厂 A2 p2 | C528032 |
| Core-C1 | L401 | Sunlord / `MWSA0402S-R47MT` | C6331050 |
| Core-C1 | L402 | Sunlord / `MWSA0402S-1R0MTB01` | 未确认，必须为 B01 |
| Display-C1 | L1 | Sunlord / `SWPA3012S470MT` | C83420 |
| Core-C1 | D202 | SGMICRO / `SGM05HU1ALXUGY2G/TR` | C55274065，公开库存0 |
| Core-C1 | SW201, SW202 | XKB Connection / `TS-1186E-B-B` | C2885153 |
| Core-C1 | J201 | MUP / `U20405-01`，原厂 Rev4 | C20624794 |
| Core-C1 | D201 | LRC / `LRC8804FDT1G` | C2856698 |
| Core-C1 | J301 | HCTL / `HC-HY-2AWT` | C2845705 |
| Display-C1 | J2 | XKB Connection / `X05A10L24G` | C2880917 |

完整逐项原身份、规格/封装评估及原厂来源见 [split-c1-domestic-eco.json](split-c1-domestic-eco.json)。设计中已装配 BOM 身份与逐项审查政策见 [split-c1-domestic-policy.json](split-c1-domestic-policy.json)，结果见 [split-c1-domestic-audit.json](split-c1-domestic-audit.json)。

## 与原器件存在差异的资格项

- U402–U405：选用 SGM2578SDYG/TR，主动高电平、QOD、2A；独立 WLCSP 封装采用原厂 0.5mm 球距、0.22mm 圆焊盘、最大 0.93mm 本体和 0.493mm 高度，符号引脚 A1=OUT、A2=IN、B1=GND、B2=ON。Jan.2026 Rev.A.2 第9页明确 ON 高/低均有 RCB，但首页仍有“when disabled”概述冲突；装配前需原厂确认该具体 SD 版本的 enabled-state RCB，首板测开启/关闭反灌、爬升及外设时序。典型参数不能代替最坏值资格。
- 增加 C516：FH 0603B105K250NT / C59302，1uF、25V、X7R、±10%、0603，直接接 U403 的 3V3_TOUCH_SW 输出和 GND。底面中心(37.9,15.9)位于 Display 投影之外；供电接现有输出过孔，地回流新增 0.4/0.2mm 过孔(36.25,19.225)。已有 SD 和音频输出电容保留；Display 输出负载电容位于匹配子板，线缆/断开子板工况必须测。
- 0Ω电阻：FH 原厂跨接电阻规范 I12.0 对 F 等级 0603/0805 的额定电流分别为 3A/4A（70°C），最大阻值10mΩ；2A时上界40mW。高温降额、充放电峰值及焊接温升仍测，不能按旧厂家的0Ω电阻阻值等级推断。
- Display R13：风华 RS-03L2R20FT 为2.2Ω±1%、100mW，TCR250ppm/°C高于旧料100ppm/°C。60°C温差的附加变化约1.5%/33mΩ；需重核 RESE 电流限制最坏角。
- Display C4–C9：4.7uF/25V/0805 的 X5R 改为 X7R，厂家最大高度1.45mm；C11–C13 最大高度0.9mm。有效直流偏压容量、EPD纹波/刷新、热循环及装配高度待验证。
- Display D1–D3：JSCJ MBR0530 的原厂推荐焊盘0.94×0.91mm、中心距3.3mm，pin1为阴极；独立封装已应用。0.5A时 VF 最大0.55V，旧 onsemi 为0.43V；最大反漏也不同。EPD升压效率、纹波、调节范围及温升待测。
- J601/J1：整对更换 HCTL DS1.5/DP，60针0.4mm间距、名义1.5mm配合高。逐一核对原厂图中 DS 0.2×0.7mm、行中心±1.54mm；DP 0.23×0.66mm、行中心±1.355mm及四支撑焊盘。当前几何相符，保留网线和60针映射，移除不适用的 Hirose 3D 模型。额定0.3A/触点、最大接触电阻90mΩ、30次插拔；两件均须用准确HCTL型号，不混用Hirose。实际插接、pin1及接触/支撑资格未通过。
- TH301：时恒 MF52D-103F3435-100 / C394023，R25=10kΩ±1%、B25/85=3435K±1%；完成品−20..105°C、100mm AWG30导线、环氧头最大4mm、静止空气 τ≤7s、δ≥2mW/°C。旧 Semitec 为600mm AWG26线、3±0.5mm头。新R-T表给0°C=27.513kΩ、45°C=4.923kΩ；同R25/B不代表全曲线相同。保持温控保护，J302接线、绝缘、包体间隙、热贴合及低/高温充电阈值按新曲线验证。TH301仅板外手工件，不进入机器CPL。
- J302/J502：HCTL HC-1.0 PWT 原厂第18页，信号焊盘0.7×1.75mm、支撑1.0×2.55mm，行中心相距3.70mm；独立封装已应用。J302 的 NTC 支路过孔和地线已受控调整，温控不旁路。两件按3.2mm保守高度预算，需匹配 HC-1.0-3Y/2Y 壳和端子；旧 JST 线束不沿用。J502 为浮地 BTL 喇叭输出，两端均不得接地；2.5W/4Ω算例为0.791Arms/1.118Apeak，1A连接器额定值仍需核对连续音频温升条件。
- J803/J804：XKB X05A10H06G 原厂 A2（2026-01-15，ECN-P-2026011502）第2页，6针双触点、0.5mm间距、0.3mm FPC、0.5A/50V。信号焊盘0.3×0.8mm、支撑0.4×0.8mm，支撑中心x=±2.3mm，两行相距2.5mm；原厂钢网建议0.25×0.65mm、厚0.1mm须另与装配厂确认，不能将普通焊盘大小当成已批准钢网。原厂pin1在左，PCB整件旋转180°并向−Y移动2.5mm，保持全部原信号焊盘世界坐标与网名；入口改向−Y。H804孔移至(3,33)，保留1.6mm孔径和原3.2mm直径安装包络；SDA绕开J804支撑焊盘。闭合高最大1.1mm、开启锁扣名义1.55mm；FT01C排线折弯、安装柱、锁扣工具空间与实际A2供料版本未冻结，不能据CAD检查宣布插接合格。
- L401：Sunlord MWSA0402S-R47MT / C6331050，0.47uH±20%，DCR14mΩ最大；2025-05-29原厂表的 Isat Max/Typ 为7.6/9.5A，Irms Max/Typ 为6.65/7.5A。保留原表标题，不当作保证下限；饱和与温升判据需确认。原厂焊盘1.5×2.5mm、中心距3.7mm、本体最大4.75×4.45×2.0mm已应用。SGM62125算例（Vin1.9V、Vout3.3V、2A输出、效率80%、2MHz、Lmin0.376uH）得到5.23A峰值及1.2倍6.28A筛选目标；效率/频率是假设，不能代替低温、限流及热最坏角验证。
- L402：精确B01变体 MWSA0402S-1R0MTB01，1uH±20%、DCR27mΩ最大，原厂 Isat Max/Typ 8/9A、Irms Max/Typ 5.4/6A；普通1R0MT不等效。按SGM41513典型应用将旧2.2uH受控改为1uH，采用同系列原厂焊盘，中心移至(40.675,6.65)、旋转270°；C402/R306和相关电源/电池走线受控调整，C201补齐Courtyard。VBUS13.5V、D=0.5、1.38MHz、Lmin0.8uH、3A平均算例为3.057App、4.529A峰值、3.13Arms、0.265W绕组损耗（不含磁芯损耗）。充电+SYS、反向升压、OCP、铜图压降及温升仍需闭环；原0.2mm电源支路不能因DRC为0就宣称通过3A载流。
- Display L1：Sunlord SWPA3012S470MT，47uH±20%、DCR1.885Ω最大，原厂 Isat Max/Typ 0.27/0.35A、Irms Max/Typ 0.35/0.40A（表头不是保证下限）。原厂焊盘0.8×2.7mm、中心距2.3mm、高度最大1.2mm；较旧料增高0.2mm，已登记机械输入。EPD升压峰值、RESE最坏角、纹波、效率及热测试仍需资格确认；精确C码C83420已确认；实际供料/装配接收未确认。
- Display U1–U3 的 MPN/铜图未更换，本来已是中微爱芯 AIP74LVC2G17GC363.TR；将错误的 TI SN74AUP2G17 数据手册链接改为原厂 B032EN/A5。LVC 的静态/关断泄漏和输入非轨电压额外耗电应按原厂最坏值预算，不能引用 AUP 低功耗规格。

- J201：MUP U20405-01/C20624794，原厂Rev4无定位柱顶装16针。0.4mm间距、0.25×0.80mm独立焊盘、y=-6.55mm行；壳脚铜盘1.2×2.0/2.1mm、槽0.6×1.4/1.5mm。完整重接USB/CC/VBUS/GND，保留16针逻辑；删除中沉槽、旧GCT模型及三条J201历史例外，恢复直板边。两板0.2mm板边标准DFM为零。5A为VBUS触点总额定，0.2mm板上支路仍需3A载流审查；新增数据过孔需USB全速验证。官方安装高3.26mm与图3.20mm不同，暂按3.46mm保守预算，尚无5.95mm整机证明。原厂1200/盘、24mm带宽/12mm步距、192mm头尾；实际供料与装配接收待确认。

- SW201/SW202：XKB TS-1186E-B-B/C2885153，A1（2025-06-06）无定位柱侧按160gf、行程0.20mm、50mA/12VDC。板上高度为侧视图1.50±0.10mm；目录H3.55是顶视图含按钮方向深度，不能当作Z高度。原厂两焊盘0.6×1.6mm、内距4.3mm/外距5.5mm、中心x=±2.45mm，pin1左/pin2右；整件原PCB位置与−90°旋转保持。原四焊盘铜线移除，按键/地线重新接通，C504仅移0.25mm以留Courtyard。无定位柱变体不钻孔。外壳按钮开口、作用力、超行程、寿命和实际供料仍待确认。

- D202：聖邦微 SGM05HU1ALXUGY2G/TR，原廠August2024 Rev.A；5.5V單向保護，pin1陰極接VBUS、pin2陽極接GND。採用原廠0.25×0.50mm焊盤、0.65mm中心距與独立K/A符號，移除TI模型；原走線端點仍在新焊盤內。現有USB2/5V sink/no PD基線保持，不開放9/12V輸入。漏電最大1uA@5V高於舊料100nA；100pF典型/130pF最大僅適用VBUS。12.1V最大鉗位@43A8/20us與SGM41513關閉轉換器時22V绝对最大值不能替代整板ESD、分壓支路與運行中充電器瞬態驗證。資料p5通用bidirectional文字與p1單向圖衝突，按p1明確極性實施。精確C碼C55274065已確認，公開庫存0；供料接收未確認，原C48260已撤销。

以上均为工程候选资格，不是制造或 EVT 放行。受控新引脚、焊盘和 C516 已纳入当前/重建 CAD 检查；原有 DRC 规则与例外未放宽。

## 剩余进口位号及工作

| 板 | 位号 | 功能 | 待完成 |
| --- | --- | --- | --- |
| Core-C1 | C301 | RTC backup EDLC | Select an exact mainland low-leakage backup part together with RTC U302; obtain polarity/land/height drawings and recalculate backup duration. Current 11mF EDLC is foreign and remains a release blocker. |
| Core-C1 | J501 | MicroSD socket with detect | Select exact mainland microSD socket with detect switch, reviewed sales drawing and pin map. Recheck outline/card insertion window, support lands, ESD, power and native routing before changing CAD. |
| Core-C1 | U302 | Integrated-crystal RTC | SD3900 Rev2.4 primary obtained: integrated crystal10pad3225,max0.78mm,VDD2.7..5.5V,VBAT1.8..3.6V,backup0.8uA typical (maximum absent),100kHz I2C at3.3V. Joint C301/driver redesign still required for user-confirmed >=24h isolated RTC backup. Native EVI is unused, R304 is DNP; preserve shared EXP_INT and use100kHz at3.3V. No RV3028-compatible pin/register/drop-in claim; select exact backup assembly/grade and review charging policy/lands/supply before ECO. See C4D8-RTC-DECISION.md. |
| Display-C1 | Q1 | EPD boost N-MOSFET | Retain30V VDS requirement. CJ3400 lower RDS is not sufficient: qualify its gate charge versus the display controller driver/switching loss and check SOT23 pin map/land. No direct replacement approved. |

这些位号都是阻止全国产打样的待改项，不是获准保留的例外。候选及原厂依据详见政策 JSON 的 remaining_redesigns。未检索到精确 C 码不等于停产；候选不能从典型电流、相似名字或同值同封装直接替换。

## 供料及下单状态

当前 SMT 精确 C 码：Core 111/118，Display 37/37。未确认7个均在Core：L402、U902、U905、U402–U405。D202的C55274065为零库存预购目录身份，不等于实际供料；L1精确C83420公开库存观察2173件，未预留。手工 TH301 的 C394023 单列，不充当 SMT 覆盖率。原7个供料事项的库存、包装和装配接收仍未完成；旧进口 L402/L1 供料路径已撤销，改为精确 Sunlord 身份；仍进口 C301 不构成当前全国产采购许可。所有库存观察均不等于预留。

SGM2578SD 的精确供料、原厂 RCB 文字确认及全国产剩余4项解决前，assembly_request_ready 和 assembly_order_ready 均为 false。可以生成工程审核资料、Gerber/BOM/CPL 供设计/CAM复核；不能把资料生成成功称作全国产可下单。MUP顶装USB已消除旧槽边例外，两板独立标准DFM均通过；电池/外壳最终尺寸、供料与没有实板的EVT继续保留。

## 复现与检查

```sh
python3 hardware/thin18-compact/release_split_c1.py
python3 hardware/thin18-compact/audit_split_c1_domestic.py --require-complete
```

第二条在4个进口位号未解决时按预期失败。审计读取 KiCad 已装配完整系统 BOM 和机器 CPL，并验证源哈希；任何未审查的厂家/MPN/封装/C码变化均阻止完成状态。两板DNP不计入，但手工TH301不允许漏审。打样包携带相同审计、政策、替换证据和说明，其哈希与CAD及导出文件绑定。生成ZIP、PDF、预览、生产CSV及临时脚本不提交git。

2026-10-02 本轮补齐：D201 改用 LRC8804FDT1G/C2856698；J301 改用 HCTL HC-HY-2AWT/C2845705；Display J2 改用 XKB X05A10L24G/C2880917。原理图、原厂焊盘、PCB 走线和可重建 ECO 同步修改。

- D201：原厂 Rev.B 的 VRWM 是 5 V。当前非 PD 的 USB 5 V 受电端，CC 接 5.1kΩ±5% Rd；以 5.5 V 源电压和 8kΩ 保守最小 Rp 计算，正常 CC 最大约 2.205 V。USB DP/DM 适用该低电容保护器，VBUS 保留独立 5.5 V D202。没有声明 CC 短接 VBUS 或违规高压故障已验证。pin3/pin8 的原厂 GND 焊盘尺寸不同，不能套成对称焊盘。
- J301：原厂 p22 为 HY **2.0 mm** 系列、3 A。信号焊盘 1.2×3.8 mm，支撑 1.2×3.7 mm，信号/支撑行中心相隔 7.6 mm；整件移至 (62,12)、旋转 90°。pin1 BAT+ / pin2 GND，支撑无网络，独立 NTC 保持 J302。新主逃线 1.2 mm，接既有铜图处仍有 0.2 mm 短颈和过孔，不能声明整条电源路径通过 3 A。原厂高度 5.2 mm，按一般公差暂预算 5.5 mm。
- J2：原厂 A1、24×0.5 mm、下接触、0.3 mm FPC、闭合高 1.0±0.1 mm。信号焊盘 0.30×0.65 mm，支撑 0.30×0.76 mm、中心 x=±6.635 mm。入口保持局部 +Y，板上 contact1 在局部 −X，24 根逻辑网不变；原厂未标 terminal1，这个号码是屏幕接口约定。MOSI/地线绕开新的支撑焊盘，实物插接仍未测试。

公开目录在 2026-10-02 观察到：L1=C83420/2173 件，D201=C2856698/2464 件，J301=C2845705/2050 件，J2=C2880917/3736 件；D202=C55274065 只有预购目录、库存 0。全部未预留，也未获得装配接收。精确 SGM2578SDYG/TR、SGM62125AXG/TR、SGM37601YTRL20G/TR 和 MWSA0402S-1R0MTB01 查询未找到匹配：不等于停产。普通 MWSA0402S-1R0MT/C408332、停产 SGM2578YG/TR/C403706、仅关闭态 RCB 的 SGM2578AADYG/TR/C5151451 均不能静默代用。

两板旁置电池的外壳工程预算为 **112×75×19 mm**，电池包完整最大输入 **54×36×5.5 mm**，不是选定电池或释放壳体尺寸。完整规格与受控 OpenSCAD 空间模型见 [SPLIT-C1-PACK-INPUTS.md](SPLIT-C1-PACK-INPUTS.md)。24 h 仍仅为 RTC 断电保持要求，实板 EVT 均为 NOT_RUN。
