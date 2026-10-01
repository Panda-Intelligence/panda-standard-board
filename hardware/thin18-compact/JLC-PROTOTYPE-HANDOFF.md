# Split-C1 嘉立创原型打样交接

本包是 Core-C1 + Display-C1 两块 PCB 的台架 EVT 原型资料。当前没有实板。不要把旧 Murphy 串口板作为本版本样板，也不要依据本包进行量产放行。

**全国产要求尚未完成：当前156个已装配系统位号中仍有18个进口料，禁止按本BOM提交装配申请或下单。** 本包供设计/CAM审核。已完成77个位号受控替换，另增U403输出旁路C516；详见 [SPLIT-C1-DOMESTICIZATION.md](SPLIT-C1-DOMESTICIZATION.md)。

## 提交范围和当前状态

| 项目 | Core-C1 | Display-C1 |
| --- | --- | --- |
| 成品板外形 | 96 × 68 mm，USB 边缘开槽 | 45 × 36 mm |
| FR-4 / 铜层 | 0.8 mm，4 层 | 0.8 mm，2 层 |
| 外铜 / 内铜 | 1 oz / 0.5 oz | 1 oz / 无 |
| 表面 / 阻焊 | ENIG 沉金、绿油 | ENIG 沉金、绿油 |
| SMT | 双面，118 个坐标 | 双面，37 个坐标 |
| 标准裸板工艺下单 | **待 CAM 确认 USB 开槽边距** | 制造数据可提交 |
| PCBA | 全国产及供料未完成；装配申请/订单未放行 | 全国产及供料未完成；装配申请/订单未放行 |

待全国产设计及CAM条件闭环后，裸板下单仅上传各板目录内的 *Gerber-Drill.zip。当前生成文件只能供工程审核。总交接 ZIP 含审核资料，不是 Gerber 上传文件。两块板各自下单，勿把旧 c4d20 集成板作为第三块成品板。

## Core 必须先取得的 CAM 确认

J201 为 GCT USB4500-03-0-A，0.8 mm mid-mount。真实 CAD 有 9.24 mm 宽的开槽及角部避让，不是直边无开槽。现有原厂模式焊盘距开槽水平边只有 0.02 mm，低于嘉立创标准 0.2 mm 铣边铜距。本包独立 DFM 将旧 edge_clearance=0 的例外提升至 0.2 mm，明确输出 16 项 J201 焊盘问题；不会把它们当作通过。

CAM 需明确接受此 0.02 mm 距离、槽边/角部刀具半径及公差，确认焊盘不被铣削、不会露铜影响焊接。如果拒绝，应做受控连接器/焊盘/槽形 ECO 后重新生成全套资料，不能让 CAM 随意移动铜、缩小接触焊盘或取消装配开槽。Core 标准工艺放行状态因此仍为 false。

Core 的 0.20 mm 钻孔 / 0.40 mm 过孔需选择嘉立创小过孔规格；不能把普通过孔自动放大。0.8 mm 名义板厚须按其公差复核 USB4500 的安装面，不能改成 1.6 mm 默认板。

## SMT 供料和工艺确认

拟采用 Standard 双面装配，U902 包含0.4mm间距WLCSP，U402–U405的国产SGM2578SD为0.5mm间距、0.22mm圆焊盘；使用ENIG。厂商需接受全部实际封装和双面工艺。Economy 的单面/封装能力不适合整套 BOM。当前 Standard 页面要求板或拼板至少 70 × 70 mm，因此需由装配厂生成并确认载板、工艺边、定位孔及基准点。

建议工程讨论尺寸：Core 单板四周 5 mm 工艺边约 106 × 78 mm；Display 2 × 2、间隔 2 mm、四周 5 mm 工艺边约 102 × 84 mm。这些是载板建议，不是已生成/已批准的拼板 Gerber。Core 的 USB/ESP32 天线、Display 的 FPC 口附近不得随意放连接桥。最终分板方向、元件悬挑、底面器件支撑与两个回流面的顺序需装配厂确认。

本包 CPL 是原单板坐标，不能混用为上述载板坐标。由装配厂拼板时保持其单板 BOM/CPL 路径；若改为客户拼板，必须按每个实例变换和重编号重新生成 BOM/CPL，再核对数量及旋转。

| 原 7 个待供料位号 | 当前精确身份 | 状态 |
| --- | --- | --- |
| Core C301 | Seiko CPH3225A / C6048128 | 已有精确 C 码，库存/包装/装配接收待确认 |
| Core C506、C513 | HRE CGA0603X7R106K100JT / C22399626 | 受控 ECO：10uF、10V、X7R、±10%、0603；实际库存待确认 |
| Core L402 | Coilcraft XGL4015-222MEC | 精确厂家身份，JLC 料号或客供接收待确认 |
| Core U902 | SGMICRO SGM62125AXG/TR | A 版 WLCSP-15，JLC 料号或客供接收待确认 |
| Core U905 | SGMICRO SGM37601YTRL20G/TR | TQFN-20，不能换成 24 引脚型号；供料接收待确认 |
| Display L1 | Taiyo Yuden LSXNE3030KKT470MN | 旧名 NRH3010T470MN；JLC 料号或客供接收待确认 |

当前8个尚无精确C码的SMT位号（Core L402、U902、U905、U402–U405；Display L1）不能被默默不贴：会影响关键电源/显示功能。先让 JLC 接收精确 MPN/封装并分配料号，再创建 Parts Manager 客供记录；收货后核对 My Parts 的可用数量、损耗及料带头尾。本包没有询价回执、库存预留、采购或付款记录。

上述进口C301/L402/L1的供料研究属于历史记录，不构成当前全国产采购许可。U402–U405需取得精确SGM2578SDYG/TR供料及enabled-state RCB确认；不能用非SD或不同封装代替。Core/Display SMT C码覆盖为111/118和36/37；全部原7项供料及新4个负载开关仍待实际库存/料带/接收确认。

TH301 是板外时恒MF52D-103F3435-100 / C394023热敏电阻，R25=10k±1%、B25/85=3435K±1%、100mm AWG30线和4mm-max环氧头；曲线、温控阈值、线束终端及热固定待确认；已从机器贴装 BOM 移出，完整系统 BOM 和 sourcing 表仍保留它。电池、连接线、TH301 固定与屏幕/FPC/板间插接为后装，不经过 SMT 回流。

## 封装、极性及装配预览

国产HCTL J601/J1作为配对更换：Core HC-PBB40C-60DS-0.4V-1.5-02/C19089250，Display HC-PBB40C-60DP-0.4V-02/C19089235。原厂焊盘/脚号匹配现有铜图，保持60针逻辑和1.5mm名义插接变换；移除旧Hirose3D模型。不得混用不同厂家的插座/插头。

新增底面C516为FH 0603B105K250NT/C59302，直接为U403的3V3_TOUCH_SW输出提供1uF旁路。SGM WLCSP、JSCJ二极管独立封装及所有国产件的资格差异见国产化记录；当前CAD通过并不表示反灌、爬升、偏压容量或热测试已通过。

L402 已按 Coilcraft 图修正为 0.98 × 3.4 mm 焊盘，中心距 2.37 mm；原 1.2 × 1.2 mm 待确认封装不再用于原型铜图。

C301 使用独立有极性封装：pin 1 = 正端 RTC_VBACKUP，pin 2 = GND。原厂底面端子 1 × 1 mm，本次工程推导的焊盘为 1.3 × 1.3 mm、中心 x=±1.1 mm；它不是厂家推荐焊盘，须在工程装配审核中接受，并在首板检查焊接。不要通过 SII 字样方向猜极性；以器件正端对准 pin 1，图中 + 位于 pin 1。C301 原厂限制最多两次回流，温度以电容顶部实测为准。

Display L1 原厂旧型号对应关系与目录焊盘尺寸支持现有 0.8 × 2.7 mm、中心距 2.2 mm 封装；本轮不改变电感铜图。Display 丝印位号增至 1 mm 高、0.15 mm 笔画。部分标准封装轮廓线为 0.12 mm，要求 CAM 在不覆盖焊盘的前提下按其丝印工艺修正/裁剪。

BOM/CPL 必须在嘉立创预览中复核底面视图与旋转约定，尤其 J601/J1 的 plug/socket、U301/U402–405/U902/U905 pin 1、D/Q 极性和 C301 正端。Assembly-Bottom.svg 已镜像为底面观察视图；CPL Bottom 行仍遵循 KiCad 导出的约定，不应再整体镜像坐标。

## 验证证据与收到样板后的范围

生成器要求当前 CAD 与从不可变基线重建结果一致，两板 DRC/open/parity/ERC 全部为 0，60 针逻辑与插接变换一致，并检查生产文件源哈希、Gerber ZIP CRC、机器 BOM/CPL 位号完全相等。独立嘉立创 DFM 及已知 USB 例外在 prototype-status.json 中公开；SHA256SUMS 覆盖交接包内文件。

全量国产化审计绑定完整系统BOM、CPL、CAD与政策/替换证据的哈希；未知或变更的厂家/MPN/封装/C码必须重审。`audit_split_c1_domestic.py --require-complete`当前按预期在18个进口位号处失败。工程资料可复核，但不能据此提交全国产装配或声明可下单。收到样板后执行现有 Q04–Q14：限流上电、各电源轨/峰值、I2C 设备、显示刷新、前光、反灌/保护、RTC、温度、实测续航及板间/FPC 插接。记录样板 ID、仪器、原始波形和电流；所有现有未测结果继续 NOT_RUN。

XTEINK X4 Pro 的 5.95 mm / 1100 mAh 仅是参照。当前双板、1.5 mm HCTL 名义间隙、屏幕与器件叠层尚未证明能实现该外壳厚度，电池包最大尺寸、保护板/线尾及膨胀余量也未冻结。首轮可在外部限流电源和夹具上完成板级 EVT，再由实测电流及真实屏幕/电池决定最终外壳；不要给本包添加虚假的 EVT 通过结果。

## 可复现与原始来源

在安装 KiCad 的机器、仓库根目录运行：

```sh
python3 hardware/thin18-compact/release_split_c1.py
```

输出 hardware/thin18-compact/production/Panda-Split-C1-JLC-Prototype.zip。生成文件不提交 git；审核源 CAD、脚本和本说明在 PR 中。

- 嘉立创 PCB：https://jlcpcb.com/capabilities/Capabilities
- 嘉立创装配：https://jlcpcb.com/capabilities/pcb-assembly-capabilities
- GCT 图：https://gct.co/files/drawings/usb4500.pdf
- Coilcraft 图：https://www.coilcraft.com/getattachment/049b0399-3b2b-4f77-b39d-70c5352a0fe3/xgl4015d.gif?lang=en-US
- Seiko 图：https://www.sii.co.jp/en/me/datasheets/chip-capacitor/cph3225a/
- Taiyo 旧名对应：https://ds.yuden.co.jp/TYCOMPAS/or/detail?pn=LSXNE3030KKT470MN&u=M
- Taiyo 目录焊盘尺寸：https://www.yuden.co.jp/productdata/catalog/wound04_e.pdf （本次搜索缓存可读，当前文件端点返回 404；保留来源与访问限制）
- HRE 精确 C 码：https://jlcpcb.com/partdetail/HRE-CGA0603X7R106K100JT/C22399626