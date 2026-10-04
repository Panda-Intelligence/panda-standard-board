> **Current hardware-finish checkpoint (2026-10-04):** use the freshly regenerated
> Split-C1 package, not an older ZIP. Default-off charger authorization and direct
> GPIO2 shutdown are implemented. Population is now **162 mainland system refs**
> (Core125/123SMT + C301/TH301; Display37/37SMT). New Q907/Q908/R930-R933 reuse
> reviewed exact catalog identities; the same7 older SMT supply gaps remain.
> Read [hardware finish](SPLIT-C1-HARDWARE-FINISH.md) for TP19 FORCE-LOW access and
> incompatible old firmware. Earlier156-ref and missing-hardware-gate descriptions
> below are historical; real source-bound generated audits override old counts.

# Split-C1 精确供料待确认清单

> Current Split-C1 power-integrity ECO: the saved main-derived board now adds
> U906 SGM809B-TXN3LG/TR, reuses R201/R204 for REGN-derived PSEL and moves C204
> to supervisor bypass. Expected current BOM: 156 mainland refs (Core119,
> Display37), Core117 SMT + 2 manual/offboard, Display37 SMT. Seven SMT refs
> remain unmapped (U902,U905,U402-U405,U906). Older observations below retain
> their dates; use [the current power contract](SPLIT-C1-POWER-INTEGRITY.md),
> regenerated audits and the handoff for the current source. No actual stock,
> assembly acceptance or physical EVT result is asserted.

2026-10-02。一套=Core-C1+Display-C1两板，批量N未给定。此文件未发送给供方；没有回执、采购、预留或装配接收。

| 位号 | 数量/套 | 精确身份 | 仍缺什么 |
|---|---:|---|---|
| Core U902 | 1 | SGMICRO SGM62125AXG/TR，A版WLCSP-15 | 精确C码／客供接收、库存、批次／MSL和料带头尾；不得用非A版或别的封装 |
| Core U905 | 1 | SGMICRO SGM37601YTRL20G/TR，TQFN-20 | 精确20脚C码／客供接收、交期和包装；24脚型号不能代用 |
| Core U402–U405 | 4 | SGMICRO SGM2578SDYG/TR，WLCSP0.9×0.9 | 世强精确SD商品页显示3940颗、约3–4工作日、未预留；精确C码／嘉立创接收仍缺。请确认RevA.2 p9的ON高／低RCB与首页disabled概述冲突；AAD/C5151451仅关闭态RCB不能代用 |
| Core U302 | 1 | WAVE SD3078 / C916255 | 精确SOP8宽208mil版本，Rev4.4／批次、MSL3、料带及实际可用量；公开4674未预留 |
| Core C301 | 1 | KAMCAP SE-5R5-D105VYH3C / C2894294 | 精确现行20mm水平封装CAD已实施，盒装目录身份确认；当前库存数量无法核实，实际批次／数量及独立后装接收待确认，不寄SMT仓；需漏电上限／RTC低压容量、负极标记及0.8mm板手焊工艺 |
| Display Q1 | 1 | JSMSEMI NX3008NBK,215-JSM / C53113911 | 公开2306未预留；确认实际批次与1G/2D/3S，按已修改符号／焊盘装配；首板验证样件极性、GDR/RESE及温升 |
| Core D202 | 1 | SGMICRO SGM05HU1ALXUGY2G/TR / C55274065 | 精确身份已确认但公开库存0；可用库存／交期、7inch/8mm tape/2mm pitch及手料头尾；1阴极VBUS、2阳极GND |
| Core L402 | 1 | Sunlord MWSA0402S-1R0MT / C408332 | 显式MT改型，非B01别名；公开19754未预留，3000/reel，实际批次／损耗和装配接收 |
| Core J501 | 1 | XUNPU TF-122-CCP9 / C41347844 | 公开36未预留，1000/reel；RevA/实际批次及CD、定位柱；卡口／行程尺寸3D图 |

本次8个位号的精确渠道、MSL／料带和未发送申请资料见SPLIT-C1-SUPPLY-REQUEST.md及split-c1-supply-plan.json。六个无C码SMT位号的逐位号封装和引脚网络见split-c1-smt-consignment.json。N套需求U902=N、U905=N、SGM2578SD=4N，损耗／头尾另计。先让装配厂接收精确MPN/封装并分配C码，随后创建Parts Manager记录；不得给空白／未接受料号发货。收货后核对My Parts可用量并绑定准确6个位号。不能用目录相似名称补码，也不能默默不贴。

所有其他精确映射见split-c1-sourcing-evidence.json。目录身份验证与实际库存／订单接收分别记录；没有查询到不代表停产。全国产身份审计通过仍不代表SMT供料已齐。

RTC24h以完整节点≤2µA、预充实测≥3.15V、末端≥2.3V为原型预算目标；厂家RTC最大电流及电容漏电上限缺失。请求常温／批准冷／热／老化参数，不能把0.8µA典型值作为最坏值保证。JLCPCB公开客供条款排除超级电容；C301采用独立采购、PCBA回板后客户／独立后装工位手焊、实际正端装到PCB+、引脚剪到Core背面≤0.5mm；1F电容不经过回流。18H=82H启用本节点充电，禁止一次性电池。

主电池完整最大输入54×36×5.5mm、名义1100mAh／最小900mAh；电芯、PCM器件、HCTL HC-HY-2Y／HC-HY-T、AWG26线束均需精确大陆厂家身份和完整极性／最大图。连续1.5A／峰值3A三秒是采购筛选目标，既有0.2mm铜支路未完成该电流等级资格。独立时恒TH301不与未知包内NTC并联。

外壳112×75×21mm为两板空间预算，所需厚度20.5mm，不是冻结尺寸。主电池区Core[1,11,37,65]，Display投影[38,30,83,66]；H804不能穿入电池。C301最大直径19.2／整体高6.5mm需实体、引脚、FPC／工具、接口／喇叭／天线／支撑建模；见SPLIT-C1-PACK-INPUTS.md。

卡口TF-122-CCP9入口朝Core+X，原厂压入／锁定／弹出1.30／2.30／5.00mm，各±0.30mm；壳体须有凹入访问／取卡路径。全部实板EVT仍NOT_RUN。当前6个SMT映射、零库存供料、实际PCBA接收与壳体／整包冻结仍未完成。
