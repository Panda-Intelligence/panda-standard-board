# Split-C1 全量国产化设计记录

当前要求：Core-C1 和 Display-C1 两块 PCB 的所有已装配位号均采用中国大陆厂家器件，不保留进口料例外。当前只有设计文件，没有真实样板。这里的国产身份指厂家身份；电气、固件、供料及实物 EVT 分别验证。

**尚未完成，不能按全国产 BOM 下单。** 当前系统 BOM 共 156 个已装配位号：138 个国产厂家，18 个进口厂家。Core 有 118 个 SMT 位号及板外 TH301；Display 有 37 个 SMT 位号。DNP 和已移除的旧集成电路不计入。屏幕、电池包、线束、天线和外壳选型仍需各自冻结。

本轮对 77 个位号执行受控替换（Core 49、Display 28），另新增 Core C516 本地输出旁路。每项替换同时修改原理图、PCB、精确 MPN/厂家/C 码及可重建脚本；不通过只改厂家字段声明国产化。

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

完整逐项原身份、规格/封装评估及原厂来源见 [split-c1-domestic-eco.json](split-c1-domestic-eco.json)。实际已装配 BOM 身份与逐项审查政策见 [split-c1-domestic-policy.json](split-c1-domestic-policy.json)，结果见 [split-c1-domestic-audit.json](split-c1-domestic-audit.json)。

## 与原器件存在差异的资格项

- U402–U405：选用 SGM2578SDYG/TR，主动高电平、QOD、2A；独立 WLCSP 封装采用原厂 0.5mm 球距、0.22mm 圆焊盘、最大 0.93mm 本体和 0.493mm 高度，符号引脚 A1=OUT、A2=IN、B1=GND、B2=ON。Jan.2026 Rev.A.2 第9页明确 ON 高/低均有 RCB，但首页仍有“when disabled”概述冲突；装配前需原厂确认该具体 SD 版本的 enabled-state RCB，首板测开启/关闭反灌、爬升及外设时序。典型参数不能代替最坏值资格。
- 增加 C516：FH 0603B105K250NT / C59302，1uF、25V、X7R、±10%、0603，直接接 U403 的 3V3_TOUCH_SW 输出和 GND。底面中心(37.9,15.9)位于 Display 投影之外；供电接现有输出过孔，地回流新增 0.4/0.2mm 过孔(36.25,19.225)。已有 SD 和音频输出电容保留；Display 输出负载电容位于匹配子板，线缆/断开子板工况必须测。
- 0Ω电阻：FH 原厂跨接电阻规范 I12.0 对 F 等级 0603/0805 的额定电流分别为 3A/4A（70°C），最大阻值10mΩ；2A时上界40mW。高温降额、充放电峰值及焊接温升仍测，不能按旧厂家的0Ω电阻阻值等级推断。
- Display R13：风华 RS-03L2R20FT 为2.2Ω±1%、100mW，TCR250ppm/°C高于旧料100ppm/°C。60°C温差的附加变化约1.5%/33mΩ；需重核 RESE 电流限制最坏角。
- Display C4–C9：4.7uF/25V/0805 的 X5R 改为 X7R，厂家最大高度1.45mm；C11–C13 最大高度0.9mm。有效直流偏压容量、EPD纹波/刷新、热循环及装配高度待验证。
- Display D1–D3：JSCJ MBR0530 的原厂推荐焊盘0.94×0.91mm、中心距3.3mm，pin1为阴极；独立封装已应用。0.5A时 VF 最大0.55V，旧 onsemi 为0.43V；最大反漏也不同。EPD升压效率、纹波、调节范围及温升待测。
- J601/J1：整对更换 HCTL DS1.5/DP，60针0.4mm间距、名义1.5mm配合高。逐一核对原厂图中 DS 0.2×0.7mm、行中心±1.54mm；DP 0.23×0.66mm、行中心±1.355mm及四支撑焊盘。当前几何相符，保留网线和60针映射，移除不适用的 Hirose 3D 模型。额定0.3A/触点、最大接触电阻90mΩ、30次插拔；两件均须用准确HCTL型号，不混用Hirose。实际插接、pin1及接触/支撑资格未通过。
- TH301：时恒 MF52D-103F3435-100 / C394023，R25=10kΩ±1%、B25/85=3435K±1%；完成品−20..105°C、100mm AWG30导线、环氧头最大4mm、静止空气 τ≤7s、δ≥2mW/°C。旧 Semitec 为600mm AWG26线、3±0.5mm头。新R-T表给0°C=27.513kΩ、45°C=4.923kΩ；同R25/B不代表全曲线相同。保持温控保护，J302接线、绝缘、包体间隙、热贴合及低/高温充电阈值按新曲线验证。TH301仅板外手工件，不进入机器CPL。
- Display U1–U3 的 MPN/铜图未更换，本来已是中微爱芯 AIP74LVC2G17GC363.TR；将错误的 TI SN74AUP2G17 数据手册链接改为原厂 B032EN/A5。LVC 的静态/关断泄漏和输入非轨电压额外耗电应按原厂最坏值预算，不能引用 AUP 低功耗规格。

以上均为工程候选资格，不是制造或 EVT 放行。受控新引脚、焊盘和 C516 已纳入当前/重建 CAD 检查；原有 DRC 规则与例外未放宽。

## 剩余进口位号及工作

| 板 | 位号 | 功能 | 待完成 |
| --- | --- | --- | --- |
| Core-C1 | C301 | RTC backup EDLC | Select an exact mainland low-leakage backup part together with RTC U302; obtain polarity/land/height drawings and recalculate backup duration. Current 11mF EDLC is foreign and remains a release blocker. |
| Core-C1 | D201 | USB D+/D-/CC ESD | Reviewed candidates have 5.0V VRWM; this cannot be assumed adequate on CC at the USB supply high corner. Select suitable VRWM/clamp and review pin map, pad geometry and signal capacitance, or split CC and USB protection. |
| Core-C1 | D202 | VBUS ESD | Select exact mainland VBUS protection with verified standoff/clamping/polarity and package; review USB maximum voltage and protected-node absolute maximum. Do not copy a similar part-number ID. |
| Core-C1 | J201 | Mid-mount USB-C | Obtain exact mainland connector drawing for 0.8mm mid-mount board, all contacts/shell pads and cutout. Redesign copper/cutout as required and resolve the existing 0.02mm edge-clearance CAM blocker. |
| Core-C1 | J301 | Battery power connector | Select exact mainland battery connector and mating harness with current rating for peak/charge current; original DF58 is 3A. Do not downgrade to the 1A HC-1.0 NTC/speaker series; check polarity, height and pad map. |
| Core-C1 | J302 | External NTC connector | Use a custom mainland footprint and reroute three signals/supports: HCTL signal lands 0.7x1.75mm/supports 1.1x1.75mm and row offset differ from current JST lands. Freeze matching harness termination and TH301 tip/100mm lead clearance. |
| Core-C1 | J501 | MicroSD socket with detect | Select exact mainland microSD socket with detect switch, reviewed sales drawing and pin map. Recheck outline/card insertion window, support lands, ESD, power and native routing before changing CAD. |
| Core-C1 | J502 | Speaker connector | Use custom HCTL lands and reroute pads/supports; confirm 1A contact rating against speaker peak current and select matching mainland cable. Current JST geometry is not a drop-in match. |
| Core-C1 | J803, J804 | Touch/frontlight six-pin FPC | Obtain exact mainland 6-pin 0.5mm connector drawings and mating FPC/contact side. Preserve pin-1, signal assignment, locking/entry clearance and maximum height; replace footprint and reroute if lands differ. |
| Core-C1 | L401 | AON buck-boost 0.47uH | Review exact recommended land/body dimensions and the SGM62125 peak/ripple/thermal corner. Candidate DCR21mohm max differs from incumbent 8.36mohm max; do not infer equal efficiency/current heating or a JLC ID. |
| Core-C1 | L402 | Charger inductor 2.2uH | Candidate minimum saturation2.4A and maximum DCR83.5mohm are materially different from incumbent saturation4.9A and DCR36mohm. Recalculate charger peak/ripple/loss or choose a stronger exact mainland part, then apply manufacturer land pattern. |
| Core-C1 | SW201, SW202 | Side-actuated buttons | Select exact mainland switch with matched actuation direction, force/travel, land/peg drawing and enclosure datum. Update footprint/copper and button mechanism before approval. |
| Core-C1 | U302 | Integrated-crystal RTC | Treat as subsystem redesign: SD3078 VDD2.7..5.5V/VBAT2.3..3.6V and typical0.8uA backup differ from RV3028 low-voltage/45nA. New footprint/pin map/driver and backup C301/current/accuracy budget are required; no equivalent selected yet. |
| Display-C1 | J2 | 24-pin panel FPC | Confirm exact original manufacturer land drawing, bottom-contact side, 0.3mm FPC, latch and height for an orderable mainland variant. Catalog-only dimensional claims are insufficient; then replace footprint/routing and recheck panel mating. |
| Display-C1 | L1 | EPD boost 47uH | SWPA3010 minimum saturation0.22A does not meet the incumbent0.25A rating merely because typical is0.35A. Verify the taller3012 exact ratings/land/height and boost current corners or choose another exact mainland inductor. |
| Display-C1 | Q1 | EPD boost N-MOSFET | Retain30V VDS requirement. CJ3400 lower RDS is not sufficient: qualify its gate charge versus the display controller driver/switching loss and check SOT23 pin map/land. No direct replacement approved. |

这些位号都是阻止全国产打样的待改项，不是获准保留的例外。候选及原厂依据详见政策 JSON 的 remaining_redesigns。未检索到精确 C 码不等于停产；候选不能从典型电流、相似名字或同值同封装直接替换。

## 供料及下单状态

当前 SMT 精确 C 码：Core 111/118，Display 36/37。未确认8个：Core L402、U902、U905、U402–U405；Display L1。手工 TH301 的 C394023 单列，不充当 SMT 覆盖率。原7个供料事项的库存、包装和装配接收仍未完成；进口 C301/L402/L1 的原供料路径不构成当前全国产采购许可。所有库存观察均不等于预留。

SGM2578SD 的精确供料、原厂 RCB 文字确认及全国产剩余18项解决前，assembly_request_ready 和 assembly_order_ready 均为 false。可以生成工程审核资料、Gerber/BOM/CPL 供设计/CAM复核；不能把资料生成成功称作全国产可下单。Core USB槽边0.02mm的CAM问题、电池/外壳最终尺寸和没有实板的EVT也继续保留。

## 复现与检查

```sh
python3 hardware/thin18-compact/release_split_c1.py
python3 hardware/thin18-compact/audit_split_c1_domestic.py --require-complete
```

第二条在18个进口位号未解决时按预期失败。审计读取 KiCad 已装配完整系统 BOM 和机器 CPL，并验证源哈希；任何未审查的厂家/MPN/封装/C码变化均阻止完成状态。两板DNP不计入，但手工TH301不允许漏审。打样包携带相同审计、政策、替换证据和说明，其哈希与CAD及导出文件绑定。生成ZIP、PDF、预览、生产CSV及临时脚本不提交git。
