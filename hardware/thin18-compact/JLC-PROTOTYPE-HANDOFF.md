> **Current hardware-finish checkpoint (2026-10-04):** use the freshly regenerated
> Split-C1 package, not an older ZIP. Default-off charger authorization and direct
> GPIO2 shutdown are implemented. Population is now **162 mainland system refs**
> (Core125/123SMT + C301/TH301; Display37/37SMT). New Q907/Q908/R930-R933 reuse
> reviewed exact catalog identities; the same7 older SMT supply gaps remain.
> Read [hardware finish](SPLIT-C1-HARDWARE-FINISH.md) for TP19 FORCE-LOW access and
> incompatible old firmware. Earlier156-ref and missing-hardware-gate descriptions
> below are historical; real source-bound generated audits override old counts.

> 2026-10-04 control follow-up: native CAD is unchanged from the PG/PSEL ECO.
> The package includes host-tested control logic evidence, NOT a flashed product
> firmware. R607 still pulls nCE low before MCU initialization, so autonomous
> charging is not excluded; do not connect an unqualified cell based on CAD-clean
> status. A permanently failed I2C bus can leave frontlight outputs enabled.
> Read CONTROL-FIRMWARE-README.md and split-c1-control-verification.json.

# Thin7 thickness gate — current PCB must be redesigned

> Current Split-C1 power-integrity ECO: the saved main-derived board now adds
> U906 SGM809B-TXN3LG/TR, reuses R201/R204 for REGN-derived PSEL and moves C204
> to supervisor bypass. Expected current BOM: 156 mainland refs (Core119,
> Display37), Core117 SMT + 2 manual/offboard, Display37 SMT. Seven SMT refs
> remain unmapped (U902,U905,U402-U405,U906). Older observations below retain
> their dates; use [the current power contract](SPLIT-C1-POWER-INTEGRITY.md),
> regenerated audits and the handoff for the current source. No actual stock,
> assembly acceptance or physical EVT result is asserted.


User requires about 7 mm whole-device thickness. The routed Split-C1 CAD
and earlier 21 mm study do not meet it. Read thin7/THIN7-REDESIGN.md before
any fabrication; its blank outline templates are not fabrication inputs.
Previously generated packages are superseded for this product requirement.

# Split-C1 嘉立创原型打样交接
2026-10-02。Core-C1+Display-C1两板，没有真实样板；本包是台架EVT原型资料，不是量产放行。

**全国产BOM身份已完成：155个已装配位号，155大陆厂家／0进口／0未知。** 最后U302/C301/Q1已实施符号、封装、引脚、走线和可重建ECO。实际供料仍未齐：Core U902、U905、U402–U405六个SMT没有精确C码／客供接收；C301、D202库存观察0；装配申请／订单状态仍false。

| 项目 | Core-C1 | Display-C1 |
|---|---|---|
| 成品板 |96×68mm，USB直板边|45×36mm|
| FR4／铜层 |0.8mm／4层|0.8mm／2层|
| 外铜／内铜 |1oz／0.5oz|1oz／无|
| 表面／阻焊 |ENIG／绿油|ENIG／绿油|
| SMT坐标 |116个，双面|37个，双面|
| 手工后装 |回板后独立后装C301水平超级电容；板外TH301|屏幕／排线／板间插接|
| 原生检查 |DRC/open/parity/ERC均0，重建相同|DRC/open/parity/ERC均0，重建相同|
| 标准裸板DFM |0.2mm铜到板边无违规|0.2mm铜到板边无违规|
| PCBA供料及接收 |未完成，6个SMT映射缺口|映射37/37，实际供料／接收未完成|

裸板CAM使用各板目录内Gerber-Drill.zip，总审核包不是Gerber上传文件。只下单两块成品板，旧c4d20集成板不是第三块。当前文件可审核裸板制造数据，完整PCBA和整机尚未释放。

## 工艺与拼板
Core0.20mm钻孔／0.40mm过孔需小孔工艺，保留0.8mm板厚；新C301为镀通槽1.8×1.4mm。Core J201是MUP U20405-01/C20624794原厂Rev4顶装16针，无旧中沉开槽／历史USB间距豁免；焊盘／壳脚槽按原厂图。既有0.2mm电源支路／过孔尚未获得3A载流资格，连接器触点额定不能替代整个电源路径验证。

拟用Standard双面装配、ENIG；Core U902为0.4mm WLCSP，U402–U405为0.5mm、0.22mm圆焊盘WLCSP。需厂商确认封装、双面顺序及载板／工艺边／定位孔／基准点。工程讨论Core四周5mm边约106×78mm；Display2×2、2mm间隔、5mm边约102×84mm。没有批准的拼板Gerber；接口口部不得随意连接桥。

CPL是原单板坐标，不是上述载板坐标。装配厂拼板时按其单板BOM/CPL路径；客户拼板须按每个实例变换和重编号重新生成，再核对数量／旋转。底面坐标遵循KiCad约定，Assembly-Bottom.svg已镜像为观察视图，不再整体镜像CPL。

## 六个SMT缺项与实际供料
| 位号 | 精确型号 | 数量／套 | 接收状态 |
|---|---|---:|---|
| U902 |SGM62125AXG/TR，A版WLCSP-15|1|精确C码／客供接收缺失|
| U905 |SGM37601YTRL20G/TR，TQFN-20|1|精确C码／客供接收缺失；不能用24脚|
| U402–U405 |SGM2578SDYG/TR，全时RCB/QOD版本|4|世强精确现货3940未预留；精确C码／客供接收缺失，原厂RCB文字差异待确认|

本次8个位号的未发送采购／客供资料见SPLIT-C1-SUPPLY-REQUEST.md，精确5组接收模板及包装在split-c1-supply-plan.json；公开库存不能代替回执。逐位号封装／网络见split-c1-smt-consignment.json。N套需求N／N／4N，损耗／头尾另按接收规则。先确认精确型号和分配C码，再创建Parts Manager客供记录；收货后核对My Parts可用数量并绑定六个位号。不能用AAD关闭态RCB或相似非A／不同封装补码，不能默默不贴。

U302=SD3078/C916255公开4674、Q1=NX3008NBK,215-JSM/C53113911公开2306，均未预留。C301现行H3C/C2894294目录与图纸已确认，当前库存数量无法核实；D202=C55274065库存观察0。实际料带／批次／MSL／损耗／接收仍待确认，完整列表见SPLIT-C1-PROCUREMENT-QUESTIONS.md。没有采购、付款、预留、供方消息或报价回执。

## 极性与后装
Core J601/J1为配套HCTL HC-PBB40C-60DS-0.4V-1.5-02／HC-PBB40C-60DP-0.4V-02，60针／1.5mm名义间隙；不得混厂家。两板pin1、35/36电源／地／保留NC、插接姿态和底面旋转均须在装配预览复核。J302为NTC，J502浮地BTL喇叭两端不接地；HCTL新线束不沿用旧JST。XKB FPC实际A2／A1版本和锁扣／工具空间待核对。

U302引脚1SCL/2F32K/3VDD/4NC/5VBAT/6GND/7INT/8SDA，宽208mil SOP8、MSL3；工程焊盘2.0×0.7mm／1.27mm脚距／7.3mm行距。F32K、NC无连接，INT共享EXP_INT。驱动必须迁移为0x32／3.3V100kHz，详见SPLIT-C1-RTC-FIRMWARE.md；本仓库未集成产品固件。

C301精确KAMCAP SE-5R5-D105VYH3C/C2894294，1F0/+30%／5.5V水平通孔；旧H/C118887及VYV3C不代用。原厂p4最大直径19.2／整体高6.5mm，20±0.5mm脚距、扁脚宽1.0±0.1／厚0.2±0.05mm；20mm工程焊盘2.4×2.0／镀通槽1.8×1.4mm。负极标记端必须接pad2 GND，正端接PCB+／pad1。独立采购并在PCBA回板后后装，不寄SMT客供仓。原厂260°C／≤5秒以1.6mm板为依据，Core0.8mm需验证手焊工艺；不回流。本体离板暂留0.2mm，后脚剪到Core B下≤0.5mm并检查毛刺、绝缘、1.5mm板间隙。C301不在SMT BOM/CPL中，在完整BOM／sourcing表保留。

JLCPCB现行客供条款排除超级电容，不把C301寄入SMT仓。当前凯美官网H3C后缀为20mm脚距，与本板旧H型19±0.5mm不一致；须取得精确旧型号签认图／批次，或另做明确改型及CAD复核，不能同名代用。国内工厂例外接收尚未核实，默认仍为独立后装。

TH301为板外时恒MF52D-103F3435-100/C394023，10k±1%／B3435K±1%、100mmAWG30、头部最大4mm。手工接J302并固定在主电池；R-T曲线、热贴合／绝缘和充电阈值待验证。整包、喇叭／天线、屏幕／FPC及插接件后装，不回流。

Display Q1=JSM NX3008NBK,215-JSM，原厂1G/2D/3S；pad1 GDR、pad2 BOOST_SW、pad3 RESE。原厂推荐焊盘0.8×0.6mm、双脚1.9mm间距、两行2.02mm。实物样件极性／GDR波形／RESE限流／温升在首板验证。不会因为同名MOS就套用旧2S/3D。

## 原型与机械边界
RTC目标是移除USB／主电池／调试电源后保持有效时间≥24h。可充电电容每次主电启动18H=82H；禁止原电池。完整备援电流≤2µA、预充实测≥3.15V、末端≥2.3V是工程目标；−25°C容量／老化条件估算33.06h，不是实测或保证值。缺RTC最大电流／电容漏电上限，Q14常温／批准冷／热／寿命验证仍NOT_RUN；R303/R304已移除。

双板侧置主电池完整最大输入54×36×5.5mm，1100mAh名义／900mAh最小目标；无精确国产整包选择。外壳112×75×21mm是空间预算，H3C整体最大6.5mm使所需厚度20.5mm；引脚、FPC、USB／卡口、工具、天线／喇叭、支持柱需实体建模。X4 Pro5.95mm／1100mAh仍仅为参考。

所有Q04–Q14在真实样板之后执行，目前NOT_RUN。先分别检查两板，再断电插接测配对；注册样板／PCB和BOM哈希、仪器及原始数据。完整当前／不可变基线重建0检查、60针核对、BOM/CPL集合相同、源哈希／Gerber及总ZIP CRC保存在生成包内。全国产身份通过不会把供料或物理验证自动设为通过。

## 重建
在仓库根目录运行python3 hardware/thin18-compact/release_split_c1.py。
输出production/Panda-Split-C1-JLC-Prototype.zip，生成ZIP／PDF／PNG／生产CSV不提交git。
