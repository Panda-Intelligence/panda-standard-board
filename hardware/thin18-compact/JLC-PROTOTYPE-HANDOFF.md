# Split-C1 嘉立创原型打样交接

本包是 Core-C1 + Display-C1 两块 PCB 的台架 EVT 原型资料。当前没有实板。不要把旧 Murphy 串口板作为本版本样板，也不要依据本包进行量产放行。

**全国产要求尚未完成：当前156个已装配系统位号中仍有4个进口料，禁止按本BOM提交装配申请或下单。** 本包供设计/CAM审核。已完成91个位号受控替换，另增U403输出旁路C516；详见 [SPLIT-C1-DOMESTICIZATION.md](SPLIT-C1-DOMESTICIZATION.md)。

## 提交范围和当前状态

| 项目 | Core-C1 | Display-C1 |
| --- | --- | --- |
| 成品板外形 | 96 × 68 mm，USB 直板边 | 45 × 36 mm |
| FR-4 / 铜层 | 0.8 mm，4 层 | 0.8 mm，2 层 |
| 外铜 / 内铜 | 1 oz / 0.5 oz | 1 oz / 无 |
| 表面 / 阻焊 | ENIG 沉金、绿油 | ENIG 沉金、绿油 |
| SMT | 双面，118 个坐标 | 双面，37 个坐标 |
| 标准裸板工艺下单 | 独立标准DFM通过，完整下单门禁仍未通过 | 制造数据可提交 |
| PCBA | 全国产及供料未完成；装配申请/订单未放行 | 全国产及供料未完成；装配申请/订单未放行 |

待全国产设计及CAM条件闭环后，裸板下单仅上传各板目录内的 *Gerber-Drill.zip。当前生成文件只能供工程审核。总交接 ZIP 含审核资料，不是 Gerber 上传文件。两块板各自下单，勿把旧 c4d20 集成板作为第三块成品板。

## Core USB 制造问题已修正

J201已替换为国产MUP U20405-01/C20624794，采用原厂Rev4无定位柱顶装16针图，保持所有USB/CC/VBUS/GND逻辑针序。独立焊盘为0.25×0.80mm、间距0.4mm；壳脚铜盘1.2×2.0/2.1mm、槽0.6×1.4/1.5mm。原中沉开槽和J201三个历史DRC例外已删除，板边恢复为直线。两板独立0.2mm铜到板边DFM均为零；打包器不再放过旧16项USB间距错误或任何新DFM失败。

Core 的0.20mm钻孔/0.40mm过孔需选择小过孔工艺；保留0.8mm板厚。MUP图壳脚名义0.6mm，并不证明焊料/公差在Display投影处无干涉。顶装接口安装高按3.46mm保守预算，原厂最大安装高度、外壳口和插头空间仍须冻结。5A接触额定不能替代现有窄VBUS/GND铜图的3A载流/温升资格；新增USB数据过孔需首板信号验证。

## SMT 供料和工艺确认

拟采用 Standard 双面装配，U902 包含0.4mm间距WLCSP，U402–U405的国产SGM2578SD为0.5mm间距、0.22mm圆焊盘；使用ENIG。厂商需接受全部实际封装和双面工艺。Economy 的单面/封装能力不适合整套 BOM。当前 Standard 页面要求板或拼板至少 70 × 70 mm，因此需由装配厂生成并确认载板、工艺边、定位孔及基准点。

建议工程讨论尺寸：Core 单板四周 5 mm 工艺边约 106 × 78 mm；Display 2 × 2、间隔 2 mm、四周 5 mm 工艺边约 102 × 84 mm。这些是载板建议，不是已生成/已批准的拼板 Gerber。Core 的 USB/ESP32 天线、Display 的 FPC 口附近不得随意放连接桥。最终分板方向、元件悬挑、底面器件支撑与两个回流面的顺序需装配厂确认。

本包 CPL 是原单板坐标，不能混用为上述载板坐标。由装配厂拼板时保持其单板 BOM/CPL 路径；若改为客户拼板，必须按每个实例变换和重编号重新生成 BOM/CPL，再核对数量及旋转。

| 原 7 个待供料位号 | 当前精确身份 | 状态 |
| --- | --- | --- |
| Core C301 | Seiko CPH3225A / C6048128 | 已有精确 C 码，库存/包装/装配接收待确认 |
| Core C506、C513 | HRE CGA0603X7R106K100JT / C22399626 | 受控 ECO：10uF、10V、X7R、±10%、0603；实际库存待确认 |
| Core L402 | Sunlord MWSA0402S-1R0MT / C408332 | 受控 MT 改型；公开库存19754，未预留，实际供料接收待确认 |
| Core U902 | SGMICRO SGM62125AXG/TR | A 版 WLCSP-15，JLC 料号或客供接收待确认 |
| Core U905 | SGMICRO SGM37601YTRL20G/TR | TQFN-20，不能换成 24 引脚型号；供料接收待确认 |
| Display L1 | Sunlord SWPA3012S470MT / C83420 | 公开库存2173，未预留；包装/装配接收待确认 |

当前6个尚无精确C码的SMT位号（Core U902、U905、U402–U405）不能被默默不贴：会影响关键电源/显示功能。先让 JLC 接收精确 MPN/封装并分配料号，再创建 Parts Manager 客供记录；收货后核对 My Parts 的可用数量、损耗及料带头尾。本包没有询价回执、库存预留、采购或付款记录。

D202已替換為SGM05HU1ALXUGY2G/TR，採用單向陰極/陽極符號和原廠焊盤；舊TI C48260已撤銷，精確C55274065已確認，公開庫存0；客供接收待確認。USB僅5V sink/no PD，整板ESD仍待首板驗證。

旧进口L402/L1路径已撤销；L1已映射C83420，实际库存/包装仍须接收确认；L402已通过受控 ECO 改为 MT/C408332，不沿用旧厂家或 B01 采购路径。C301仍进口，不能按全国产采购。U402–U405需取得精确SGM2578SDYG/TR供料及enabled-state RCB确认；不能用非SD或不同封装代替。Core/Display SMT C码覆盖为112/118和37/37；全部原7项供料及新4个负载开关仍待实际库存/料带/接收确认。

TH301 是板外时恒MF52D-103F3435-100 / C394023热敏电阻，R25=10k±1%、B25/85=3435K±1%、100mm AWG30线和4mm-max环氧头；曲线、温控阈值、线束终端及热固定待确认；已从机器贴装 BOM 移出，完整系统 BOM 和 sourcing 表仍保留它。电池、连接线、TH301 固定与屏幕/FPC/板间插接为后装，不经过 SMT 回流。

## 封装、极性及装配预览

国产HCTL J601/J1作为配对更换：Core HC-PBB40C-60DS-0.4V-1.5-02/C19089250，Display HC-PBB40C-60DP-0.4V-02/C19089235。原厂焊盘/脚号匹配现有铜图，保持60针逻辑和1.5mm名义插接变换；移除旧Hirose3D模型。不得混用不同厂家的插座/插头。

J302/J502采用HCTL原厂独立焊盘，配套线束必须重选；NTC不旁路，BTL喇叭两端不接地。J803/J804采用XKB X05A10H06G A2 p2，整件旋转180°保持全部针序和铜图信号位置；入口改向−Y。H804改为(3,33)，排线折弯、锁扣开启空间、孔柱及实际供料版本仍待冻结。详见国产化记录。

新增底面C516为FH 0603B105K250NT/C59302，直接为U403的3V3_TOUCH_SW输出提供1uF旁路。SGM WLCSP、JSCJ二极管独立封装及所有国产件的资格差异见国产化记录；当前CAD通过并不表示反灌、爬升、偏压容量或热测试已通过。

L401/L402 已采用 Sunlord MWSA0402S 原厂1.5×2.5mm焊盘、中心距3.7mm、高度最大2.0mm。L402本轮明确选择1R0MT/C408332，保持SGM41513典型应用的1uH；相关电源布局调整及计算条件见国产化记录。DRC不等于载流/稳定性/热资格。

C301 使用独立有极性封装：pin 1 = 正端 RTC_VBACKUP，pin 2 = GND。原厂底面端子 1 × 1 mm，本次工程推导的焊盘为 1.3 × 1.3 mm、中心 x=±1.1 mm；它不是厂家推荐焊盘，须在工程装配审核中接受，并在首板检查焊接。不要通过 SII 字样方向猜极性；以器件正端对准 pin 1，图中 + 位于 pin 1。C301 原厂限制最多两次回流，温度以电容顶部实测为准。

Display L1已改为Sunlord SWPA3012S470MT，焊盘0.8×2.7mm、中心距2.3mm、高度最大1.2mm，移除旧Taiyo轮廓与模型。Display 丝印位号增至 1 mm 高、0.15 mm 笔画。部分标准封装轮廓线为 0.12 mm，要求 CAM 在不覆盖焊盘的前提下按其丝印工艺修正/裁剪。

BOM/CPL 必须在嘉立创预览中复核底面视图与旋转约定，尤其 J601/J1 的 plug/socket、U301/U402–405/U902/U905 pin 1、D/Q 极性和 C301 正端。Assembly-Bottom.svg 已镜像为底面观察视图；CPL Bottom 行仍遵循 KiCad 导出的约定，不应再整体镜像坐标。

## 验证证据与收到样板后的范围

生成器要求当前 CAD 与从不可变基线重建结果一致，两板 DRC/open/parity/ERC 全部为 0，60 针逻辑与插接变换一致，并检查生产文件源哈希、Gerber ZIP CRC、机器 BOM/CPL 位号完全相等。两板独立嘉立创 DFM 零违规结果在 prototype-status.json 中公开；SHA256SUMS 覆盖交接包内文件。

全量国产化审计绑定完整系统BOM、CPL、CAD与政策/替换证据的哈希；未知或变更的厂家/MPN/封装/C码必须重审。`audit_split_c1_domestic.py --require-complete`当前按预期在3个进口位号处失败。工程资料可复核，但不能据此提交全国产装配或声明可下单。收到样板后执行现有 Q04–Q14：限流上电、各电源轨/峰值、I2C 设备、显示刷新、前光、反灌/保护、RTC、温度、实测续航及板间/FPC 插接。记录样板 ID、仪器、原始波形和电流；所有现有未测结果继续 NOT_RUN。

RTC 斷電保持目標已由使用者確認為至少24小時，獨立於整機閱讀續航。Q14將在USB、主電池和調試供電斷開、無信號反灌的狀態下驗證24h時間有效性、末端電壓及常溫/批准冷熱條件；R304備援短接電阻保持DNP。國產RTC/備援方案尚未選定，不能把典型耗電換算當成已通過；詳見C4D8-RTC-DECISION.md。

XTEINK X4 Pro 的 5.95 mm / 1100 mAh 仅是参照。当前双板、1.5 mm HCTL 名义间隙、屏幕与器件叠层尚未证明能实现该外壳厚度，电池包最大尺寸、保护板/线尾及膨胀余量也未冻结。首轮可在外部限流电源和夹具上完成板级 EVT，再由实测电流及真实屏幕/电池决定最终外壳；不要给本包添加虚假的 EVT 通过结果。

## 可复现与原始来源

在安装 KiCad 的机器、仓库根目录运行：

```sh
python3 hardware/thin18-compact/release_split_c1.py
```

输出 hardware/thin18-compact/production/Panda-Split-C1-JLC-Prototype.zip。生成文件不提交 git；审核源 CAD、脚本和本说明在 PR 中。

- 嘉立创 PCB：https://jlcpcb.com/capabilities/Capabilities
- 嘉立创装配：https://jlcpcb.com/capabilities/pcb-assembly-capabilities
- MUP USB原厂Rev4图：https://atta.szlcsc.com/upload/public/pdf/source/20240223/861C7C148AA03685D8854DCE43F31033.pdf
- Sunlord MWSA原厂2025图：https://atta.szlcsc.com/upload/public/pdf/source/20250613/CEE4AE5EC9F7EB97495A767C9ECB8960.pdf
- Seiko 图：https://www.sii.co.jp/en/me/datasheets/chip-capacitor/cph3225a/
- Sunlord SWPA原厂2024图：https://atta.szlcsc.com/upload/public/pdf/source/20241120/5FB31A17AAA509171003FB8365AF70A5.pdf
- HCTL线对板原厂图：https://www.hctldz.com/static/upload/2025/10/17/202510178492.pdf
- XKB 6针原厂A2图：https://atta.szlcsc.com/upload/public/pdf/source/20260407/3BDDFDA54F9DA860D59B5DD75ED63F9A.pdf
- HRE 精确 C 码：https://jlcpcb.com/partdetail/HRE-CGA0603X7R106K100JT/C22399626
侧按键 SW201/SW202 为 XKB TS-1186E-B-B/C2885153 原厂 A1 无定位柱型，两个0.6×1.6mm焊盘；不要按旧ALPS四焊盘或有柱A变体采购。侧视图板上高1.50±0.10mm，目录3.55为顶视按钮深度；按钮开口/行程/供料仍需确认。原厂图：https://atta.szlcsc.com/upload/public/pdf/source/20260728/758CDD32F102D63D6B0CBF7CD2FCF600.pdf

2026-10-02 本轮补齐：D201 改用 LRC8804FDT1G/C2856698；J301 改用 HCTL HC-HY-2AWT/C2845705；Display J2 改用 XKB X05A10L24G/C2880917。原理图、原厂焊盘、PCB 走线和可重建 ECO 同步修改。

- D201：原厂 Rev.B 的 VRWM 是 5 V。当前非 PD 的 USB 5 V 受电端，CC 接 5.1kΩ±5% Rd；以 5.5 V 源电压和 8kΩ 保守最小 Rp 计算，正常 CC 最大约 2.205 V。USB DP/DM 适用该低电容保护器，VBUS 保留独立 5.5 V D202。没有声明 CC 短接 VBUS 或违规高压故障已验证。pin3/pin8 的原厂 GND 焊盘尺寸不同，不能套成对称焊盘。
- J301：原厂 p22 为 HY **2.0 mm** 系列、3 A。信号焊盘 1.2×3.8 mm，支撑 1.2×3.7 mm，信号/支撑行中心相隔 7.6 mm；整件移至 (62,12)、旋转 90°。pin1 BAT+ / pin2 GND，支撑无网络，独立 NTC 保持 J302。新主逃线 1.2 mm，接既有铜图处仍有 0.2 mm 短颈和过孔，不能声明整条电源路径通过 3 A。原厂高度 5.2 mm，按一般公差暂预算 5.5 mm。
- J2：原厂 A1、24×0.5 mm、下接触、0.3 mm FPC、闭合高 1.0±0.1 mm。信号焊盘 0.30×0.65 mm，支撑 0.30×0.76 mm、中心 x=±6.635 mm。入口保持局部 +Y，板上 contact1 在局部 −X，24 根逻辑网不变；原厂未标 terminal1，这个号码是屏幕接口约定。MOSI/地线绕开新的支撑焊盘，实物插接仍未测试。

公开目录在 2026-10-02 观察到：L1=C83420/2173 件，D201=C2856698/2464 件，J301=C2845705/2050 件，J2=C2880917/3736 件；D202=C55274065 只有预购目录、库存 0。全部未预留，也未获得装配接收。精确 SGM2578SDYG/TR、SGM62125AXG/TR、SGM37601YTRL20G/TR 和 MWSA0402S-1R0MTB01 查询未找到匹配：不等于停产。普通 MT 已经显式电气复核并作为当前 L402/C408332；停产 SGM2578YG/TR/C403706、仅关闭态 RCB 的 SGM2578AADYG/TR/C5151451 仍不能静默代用。

两板旁置电池的外壳工程预算为 **112×75×19 mm**，电池包完整最大输入 **54×36×5.5 mm**，不是选定电池或释放壳体尺寸。完整规格与受控 OpenSCAD 空间模型见 [SPLIT-C1-PACK-INPUTS.md](SPLIT-C1-PACK-INPUTS.md)。24 h 仍仅为 RTC 断电保持要求，实板 EVT 均为 NOT_RUN。

2026-10-02 后续 ECO：J501 已应用 XUNPU TF-122-CCP9/C41347844，原厂 RevA 信号/检测焊盘0.60×1.60mm，两个1.00mm定位孔、孔距8.00mm；检测触点插卡时闭合到接地壳体。整件改为(81.75,17.315)、90°，入口朝 Core +X；25条新增局部线段/6个过孔，旧卡座支路受控撤销或截短，孔距规则不放宽。9=CD、10/SH=壳体地是工程编号，并非原厂额外编号触点。原C585350采购身份撤销。公开目录仅36件，未预留。卡片行程、壳体开口/压入和取卡工具空间仍须确认，不能只按静态包络制作外壳。

L402当前 MT/C408332 已有明确改型依据，不是 B01 别名。Core 精确 SMT C码112/118、Display37/37；当前6个缺口为U902、U905、U402–U405。RTC/备援和显示Q1三个位号仍阻止全国产 BOM。新的候选审查与原厂哈希见 [split-c1-candidate-review.json](split-c1-candidate-review.json)。

当前剩余事项已整理为可给供方逐项答复的 [SPLIT-C1-PROCUREMENT-QUESTIONS.md](SPLIT-C1-PROCUREMENT-QUESTIONS.md)，含精确6个SMT位号、零库存D202、RTC等级/备援、MOS引脚与完整电池/卡口尺寸；目前没有供方回执。
