# E0.2 R49 前光升压供电修正

2026-11-06，执行者：Claude。基线为 R48（由 git 中 `v0.1.1`／R26 经 `build_pico47_single.py --revision R48` 回放，语义与铜指纹均与 R48 增量绑定值一致）。

## 问题

两板合并为 Single 后，前光升压电路的输入网络 `VSYS_FL_IN` 只连接 L905.1、R920.1、C920.1 三个无源焊盘，没有任何电源。原两板方案中该电源经板间连接器来自主板系统轨（`thin18-compact/C3-INTEGRATION.md`："VSYS_FL_IN derived from the battery/system rail"），合板删除连接器时随之断开。DRC／ERC 均不报告此类问题。在 R48 及以前，U905（SGM37601）没有输入电压，前光不能工作。

## 修正

`VSYS_FL_IN` 并入系统轨 `VSYS_RAW`（SGM41513 SYS 输出），与 U905 的 2.7–5.5 V 输入范围相符。

| 项目 | 内容 |
| --- | --- |
| 原理图 | 三处全局标签 `VSYS_FL_IN` 改为 `VSYS_RAW` |
| 焊盘 | L905.1、R920.1、C920.1 改入 `VSYS_RAW` |
| 原有铜 | 18 段原 `VSYS_FL_IN` 走线／过孔改名，几何不变 |
| 新增铜 | 14 段 0.40 mm 走线（F.Cu／In2.Cu／B.Cu）＋4 颗 0.40/0.20 mm 过孔，全长 29.16 mm，接入最近的宽 `VSYS_RAW` 铜；In1 不走线，不新增焊盘内过孔 |
| 其余 | 器件、位姿、焊盘、其他网络的铜、区、规则与 R48 相同 |

按 In2 0.5 oz 估算，这段连接铜约 0.07 Ω；前光输入电流按约 0.15 A 估算时压降约 10 mV。估算未计过孔和温升，不代替实测。

增量见 `r25_router/single_r49_frontlight_supply_delta.json`，起点与终点的原生语义指纹和铜指纹都在其中绑定。

## 重建与检查

```sh
python3 build_pico47_single_r49.py --output <.work 下新目录>   # 使用 KiCad 自带 Python
```

脚本先回放 R48，校验 R48 指纹，再套用 R49 并校验目标指纹，然后运行原生 DRC（`--refill-zones --all-track-errors --schematic-parity`）与 ERC，执行 `inspect_single` 全部检查并导出下单包。

本次重建结果：DRC 错误／告警／未连接／原理图一致性／ERC 均为 0；焊盘内过孔清单 46 颗、待供 SMT 21 项、BT301 后装，与 R48 相同。BOM／CPL 各 226 行，其中背面 6 颗（需双面贴片）。独立扫描的焊盘内过孔与 `REQUIRED-VIA-IN-PAD.csv` 一致，另有 TP8、TPG2 两个裸测试点上的 5 颗过孔，这两个焊盘不上锡、不在清单内。

在没有图形会话的 SSH 环境中，构建脚本调用的 `wx.App` 无法创建；本次用 `.work` 下的空 `wx` 替身运行，未修改构建代码。

## 状态

`manufacturing_release`、`supplier_process_accepted` 及两项 EVT 资格保持 false。前光的实际亮度、调光与升压效率仍需按 EVT 规程在样机上验证。

## 2026-11-08 采购元数据增量

在上述 R49 基线下，按“保守首件”策略应用了 [R49 SMT 目录元数据整理](E02-R49-SMT-CATALOG-CLEANUP-20261108.md)：14 个位号只更新精确国产 MPN 的 LCSC 属性，其中 8 个原始待供位号获得当前精确目录编号，原始待供 21 项变为当前构建清单 13 项；没有跨 MPN 替代，也没有电气、封装、位置或铜修改。下单时以新构建生成的 `PENDING-SUPPLY.csv` 为准，实时库存、J201、TH801、关键 IC 与精密分压仍须人工复核。此增量不关闭制造放行或任何实际 EVT 资格。

## 打样下单清单

设计侧问题已修完；以下事项必须由下单人完成，CAD 无法代替。

1. **板厂文件**：用 `build_pico47_single_r49.py` 新生成的 `orderpack/Single/JLCPCB_Single_Gerber_4L_Green_ENIG.zip`、`BOM_JLCPCB_Single.csv`、`CPL_JLCPCB_Single.csv`，不要用 R48 或更早的下单包。
2. **板子参数**：4 层，0.8 mm，绿油，沉金，单片出货。叠层以 `Single-job.gbrjob` 为准（外层到 In1/In2 介质 0.1 mm，芯板 0.495 mm）；下单时选与之对应的嘉立创 0.8 mm 四层叠层，并请板厂确认。0.16 mm 射频线按该叠层约为 50 Ω。
3. **过孔工艺**：必须选择“树脂塞孔 + 电镀封顶”（IPC-4761 Type VII），并取得板厂按 `REQUIRED-VIA-IN-PAD.csv` 46 颗逐孔的书面 CAM 确认；不能用普通塞油或盖油。
4. **贴片**：双面贴片（背面 6 颗：C537、C538、C543、C815、R710、R731）。
5. **物料**（原始 R49 `PENDING-SUPPLY.csv` 21 项；2026-11-08 采购元数据 ECO 后以下单包新生成的 13 项清单为准）：2026-11-06 在立创商城检索到下列型号完全一致的候选编号，**下单前须在实时页面再次核对厂家、型号、规格与库存**：

   | 位号 | 型号 | 候选 LCSC |
   | --- | --- | --- |
   | C807、C809、C810、C812 | FH 0805B105K500NT | C215803 |
   | C808、C811 | FH 0805B473K500NT | C1745 |
   | R805 | FH RC-02K7501FT | C140131（阻值、精度、封装须对照规格书） |

   原始 2026-11-06 对照中其余 14 个位号没有检索到型号完全一致的编号，须按精确型号采购后客供：R801–R804（0.1% 薄膜电阻）、R806、TH801、J201、U402–U405（WLCSP，不能手焊）、U810、U902（WLCSP）、U905。2026-11-08 ECO 已为 R806 绑定精确编号 `C324808`；当前仍待供的 13 项和各项禁止替代规则见 [采购元数据整理](E02-R49-SMT-CATALOG-CLEANUP-20261108.md)。检索到的近似型号（不同阻值、封装、后缀或系列）一律不得替代。
6. **BT301**：CR1216 焊片组件贴片后手工装焊，不得过回流焊。
7. **上电前**：按 [EVT 规程](E02-EVT-ELECTRICAL-VERIFICATION-PROTOCOL-20261104.md) 0 节，先限流、先不接面板、先不接真实电池。
