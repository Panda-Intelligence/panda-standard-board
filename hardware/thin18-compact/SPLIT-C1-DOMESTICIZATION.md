# Split-C1 全量国产化设计记录
2026-10-02。当前只有Core-C1／Display-C1两块PCB设计，没有实物样板。所有已装配BOM位号使用中国大陆厂家身份；这项身份审计与电气、固件、实际供料及EVT分别验证。

**155个已装配系统位号全部为大陆厂家，0进口、0未知。** Core118个（116SMT、板上手焊C301、板外TH301），Display37SMT。R303、R304已移除；DNP不计入。当前实施94个位号、39组受控替换，另有C516本地输出旁路。完整身份／原厂来源和ECO见split-c1-domestic-policy.json、split-c1-domestic-eco.json、split-c1-domestic-audit.json。

## 已实施国产ECO
| 板 | 位号 | 当前厂家／精确MPN | 精确C码 |
|---|---|---|---|
| Core-C1 | R201 | FH (Fenghua Advanced) / RS-03K5601FT | C99891 |
| Core-C1 | R204 | FH (Fenghua Advanced) / RS-03K1201FT | C118396 |
| Core-C1 | R510, R511, R512, R513, R523, R524, R525, R526, R527, R528, R600 | FH (Fenghua Advanced) / RC-02K1002FT | C140215 |
| Core-C1 | R501, R502, R507, R604, R605, R606, R607, R608, R609, R610, R611, R612 | FH (Fenghua Advanced) / RC-02K1003FT | C140219 |
| Core-C1 | R508, R509, R514, R515, R516 | FH (Fenghua Advanced) / RS-05000FT | C132364 |
| Core-C1 | R517, R518, R519, R520, R521, R522 | FH (Fenghua Advanced) / RS-03000FT | C136582 |
| Core-C1 | R529, R530 | FH (Fenghua Advanced) / RC-02K22R0FT | C324769 |
| Core-C1 | R613, R614 | FH (Fenghua Advanced) / RC-02K2201FT | C140192 |
| Core-C1 | R615 | FH (Fenghua Advanced) / RS-03K5231FT | C140082 |
| Core-C1 | R616 | FH (Fenghua Advanced) / RS-03K3012FT | C321843 |
| Display-C1 | C4, C5, C6, C7, C8, C9 | FH (Fenghua Advanced) / 0805B475K250NT | C37818 |
| Display-C1 | C10 | FH (Fenghua Advanced) / 0805B105K250NT | C89190 |
| Display-C1 | C11, C12, C13 | FH (Fenghua Advanced) / 0603B104K250NT | C694249 |
| Display-C1 | R1, R2, R3, R4, R5 | FH (Fenghua Advanced) / RC-02K22R0FT | C324769 |
| Display-C1 | R6 | FH (Fenghua Advanced) / RC-02K1000FT | C140217 |
| Display-C1 | R7, R8, R9, R10, R11, R12 | FH (Fenghua Advanced) / RC-02K1003FT | C140219 |
| Display-C1 | R13 | FH (Fenghua Advanced) / RS-03L2R20FT | C322118 |
| Display-C1 | R14 | FH (Fenghua Advanced) / RC-02K1002FT | C140215 |
| Core-C1 | U402, U403, U404, U405 | SGMICRO / SGM2578SDYG/TR | 未确认 |
| Display-C1 | D1, D2, D3 | JSCJ / MBR0530 | C77336 |
| Core-C1 | J601 | HCTL / HC-PBB40C-60DS-0.4V-1.5-02 | C19089250 |
| Display-C1 | J1 | HCTL / HC-PBB40C-60DP-0.4V-02 | C19089235 |
| Core-C1 | TH301 | Nanjing Shiheng Elec / MF52D-103F3435-100 | C394023 |
| Core-C1 | J302 | HCTL / HC-1.0-3PWT | C2845362 |
| Core-C1 | J502 | HCTL / HC-1.0-2PWT | C2845361 |
| Core-C1 | L401 | Sunlord / MWSA0402S-R47MT | C6331050 |
| Core-C1 | L402 | Sunlord / MWSA0402S-1R0MT | C408332 |
| Display-C1 | L1 | Sunlord / SWPA3012S470MT | C83420 |
| Core-C1 | J803, J804 | XKB Connection / X05A10H06G | C528032 |
| Core-C1 | J201 | MUP / U20405-01 | C20624794 |
| Core-C1 | SW201, SW202 | XKB Connection / TS-1186E-B-B | C2885153 |
| Core-C1 | D202 | SGMICRO / SGM05HU1ALXUGY2G/TR | C55274065 |
| Display-C1 | J2 | XKB Connection / X05A10L24G | C2880917 |
| Core-C1 | D201 | LRC / LRC8804FDT1G | C2856698 |
| Core-C1 | J301 | HCTL / HC-HY-2AWT | C2845705 |
| Core-C1 | J501 | XUNPU / TF-122-CCP9 | C41347844 |
| Display-C1 | Q1 | JSMSEMI / NX3008NBK,215-JSM | C53113911 |
| Core-C1 | U302 | WAVE / SD3078 | C916255 |
| Core-C1 | C301 | KAMCAP / SE-5R5-D105VYH | C118887 |

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
- L402：本轮明确从 B01 改为 MWSA0402S-1R0MT/C408332。1uH±20%、DCR27mΩ最大、Isat Max/Typ 5.6/7A、Irms Max/Typ 5.4/6A；保留原表标题，不推定保证下限。原厂焊盘与 B01 相同。5.5V、D=0.5、Lmin0.8uH、1.38MHz、3A平均算例为3.623A峰值/3.022Arms；历史13.5V算例含20%峰值筛选为5.435A，13.5V不是允许的USB输入。反向升压在首板 bring-up 中必须保持关闭，固件尚未实现该约束；OCP/饱和/热及既有0.2mm铜图仍未验证。完整算例和限制见 split-c1-candidate-review.json。
- Display L1：Sunlord SWPA3012S470MT，47uH±20%、DCR1.885Ω最大，原厂 Isat Max/Typ 0.27/0.35A、Irms Max/Typ 0.35/0.40A（表头不是保证下限）。原厂焊盘0.8×2.7mm、中心距2.3mm、高度最大1.2mm；较旧料增高0.2mm，已登记机械输入。EPD升压峰值、RESE最坏角、纹波、效率及热测试仍需资格确认；精确C码C83420已确认；实际供料/装配接收未确认。
- Display U1–U3 的 MPN/铜图未更换，本来已是中微爱芯 AIP74LVC2G17GC363.TR；将错误的 TI SN74AUP2G17 数据手册链接改为原厂 B032EN/A5。LVC 的静态/关断泄漏和输入非轨电压额外耗电应按原厂最坏值预算，不能引用 AUP 低功耗规格。

- J201：MUP U20405-01/C20624794，原厂Rev4无定位柱顶装16针。0.4mm间距、0.25×0.80mm独立焊盘、y=-6.55mm行；壳脚铜盘1.2×2.0/2.1mm、槽0.6×1.4/1.5mm。完整重接USB/CC/VBUS/GND，保留16针逻辑；删除中沉槽、旧GCT模型及三条J201历史例外，恢复直板边。两板0.2mm板边标准DFM为零。5A为VBUS触点总额定，0.2mm板上支路仍需3A载流审查；新增数据过孔需USB全速验证。官方安装高3.26mm与图3.20mm不同，暂按3.46mm保守预算，尚无5.95mm整机证明。原厂1200/盘、24mm带宽/12mm步距、192mm头尾；实际供料与装配接收待确认。

- SW201/SW202：XKB TS-1186E-B-B/C2885153，A1（2025-06-06）无定位柱侧按160gf、行程0.20mm、50mA/12VDC。板上高度为侧视图1.50±0.10mm；目录H3.55是顶视图含按钮方向深度，不能当作Z高度。原厂两焊盘0.6×1.6mm、内距4.3mm/外距5.5mm、中心x=±2.45mm，pin1左/pin2右；整件原PCB位置与−90°旋转保持。原四焊盘铜线移除，按键/地线重新接通，C504仅移0.25mm以留Courtyard。无定位柱变体不钻孔。外壳按钮开口、作用力、超行程、寿命和实际供料仍待确认。

- D202：聖邦微 SGM05HU1ALXUGY2G/TR，原廠August2024 Rev.A；5.5V單向保護，pin1陰極接VBUS、pin2陽極接GND。採用原廠0.25×0.50mm焊盤、0.65mm中心距與独立K/A符號，移除TI模型；原走線端點仍在新焊盤內。現有USB2/5V sink/no PD基線保持，不開放9/12V輸入。漏電最大1uA@5V高於舊料100nA；100pF典型/130pF最大僅適用VBUS。12.1V最大鉗位@43A8/20us與SGM41513關閉轉換器時22V绝对最大值不能替代整板ESD、分壓支路與運行中充電器瞬態驗證。資料p5通用bidirectional文字與p1單向圖衝突，按p1明確極性實施。精確C碼C55274065已確認，公開庫存0；供料接收未確認，原C48260已撤销。

以上均为工程候选资格，不是制造或 EVT 放行。受控新引脚、焊盘和 C516 已纳入当前/重建 CAD 检查；原有 DRC 规则与例外未放宽。


## 最后3个进口位号已完成设计替换
| 板／位号 | 国产精确选择 | 已完成 |
|---|---|---|
| Core U302 | WAVE SD3078 / C916255 | 1SCL/2F32K/3VDD/4NC/5VBAT/6GND/7INT/8SDA新符号、208milSOP8工程焊盘及重布线 |
| Core C301 | KAMCAP SE-5R5-D105VYH / C118887 | 1F水平通孔超级电容；工程槽孔／极性、备援走线；SMT后手焊 |
| Display Q1 | JSMSEMI NX3008NBK,215-JSM / C53113911 | 1G/2D/3S、原厂0.8×0.6mm焊盘、源漏网络及局部重布线 |

U302/C301详见C4D8-RTC-DECISION.md与SPLIT-C1-RTC-FIRMWARE.md。原型要求RTC断电有效时间≥24h；总节点≤2µA、实测起点≥3.15V、终点≥2.3V是待验证工程目标。条件估算室温66.11h／−25°C老化角33.06h，不是保证值；RTC最大电流／电容漏电缺少限值。一次性电池不允许装到充电节点。驱动未集成，实板Q04–Q14全部NOT_RUN。

Q1原厂V1.0 p1功能图明确1G/2D/3S，p5提供推荐焊盘；实际样件极性／GDR／RESE／效率／温升在样板后验证。30V，Rds最大0.6Ω@2.5V/200mA、Qg最大0.87nC@4.5V/15V/1A，仅构成原型选型筛选；测试条件不同不能直接用参考MOS的Qg数值证明动态合格。

## 供料仍有6个SMT映射缺口
Core精确C码110/116，Display37/37。U902、U905、U402–U405共6个SMT仍无确认的精确C码／客供接收；逐位号CAD封装和网表已整理为split-c1-smt-consignment.json。不能用相似型号补码、不能不贴，未检索到不代表停产。

SD3078公开4674／Q1公开2306未预留；C301/C118887与D202/C55274065库存观察0。全部物料的实际库存、批次／MSL、头尾／损耗及PCBA接收仍需闭环；没有报价、采购、预留、供应商消息或订单。assembly_request_ready／assembly_order_ready=false。

裸板Gerber／钻孔可以作为当前两板工程审核资料。标准DFM、DRC与全国产身份通过不代表整机或PCBA下单条件全部满足。电池完整最大输入54×36×5.5mm、外壳112×75×20mm仍是工程预算；未选完整国产电池包／冻结外壳。

## 复现
python3 hardware/thin18-compact/release_split_c1.py
python3 hardware/thin18-compact/audit_split_c1_domestic.py --require-complete

第二条现在应通过155/155身份审计，但不会批准实际供料或EVT。当前与不可变基线重建的两板DRC/open/parity/ERC必须全0；60针逻辑／插接变换不变；焊盘和负向控制拒绝错误引脚、槽孔或SKU。生产文件绑定源哈希及ZIP CRC；生成ZIP、PDF、PNG、生产CSV和临时脚本不提交git。
