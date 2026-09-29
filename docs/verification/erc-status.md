# 标准板 ERC 当前状态

日期：2026-09-09；执行者：Codex。

J501 merged 权威工程当前 ERC 为 **0 active report entries**，本轮显示/外置NTC/RTC真实电路关闭原16项。
独立候选复查及正式目录保存/重填的PCB DRC、未连接、schematic parity均0/0/0；这不代表实物资格或制造放行。
项目既有四类ignored checks（single_global_label、four_way_junction、simulation_model_issue、footprint_filter）未修改，
不把active ERC0说成所有规则类别均启用。完整本轮证据见[ERC16工程检查点](erc16-layout-status.md)。

## J502 前轮已修复（历史18→16）

J502.1→SPK_P/U502.9、J502.2→SPK_N/U502.10真实接通，两机械MP焊盘保持no-net。
仅消除SPK_P `65020112-0502-4502-8502-000000000112` 与SPK_N `65020114-0502-4502-8502-000000000114` 两条isolated_pin_label。
其余16条完整报告与旧源一致；没有新增NC/flag或忽略规则。详见[J502工程记录](lib/review/J502-GH-A-stage.md)。

## BQ_PG 前轮已修复（历史19→18）

U201.3 → U601.13/P10/R600.1 已真实接通，R600改10k/1%上拉至3V3_AON，保持原位置；原专用地via按批准删除。
唯一减少isolated_pin_label对象 `2a6b2b49-9f0a-4908-ac42-6b27f3dc0a07`，其余18条逐项不变。
三种实际副本负控分别拒绝断PG、错并PG_3V3_MAIN、恢复错误下拉；PG专属电气/固件/台架资格仍开放。
详见[BQ_PG/P10记录](lib/review/BQ_PG-P10-A-stage.md)。

## USB 前轮已修复（历史22→19）

真实J201接口、数据线与VBUS输入声明关闭U501.pad13/14未接及U201.pad18未驱动，剩余19条与正式基线原文一致。
GPIO2是改配而非额外关闭一个正式遗留；中间释放脚的第23条不计入净改善。八个当前原理图负控及J201内/外孔距负控通过。
细节见[USB2/S-9记录](lib/review/USB2-S9-A-stage.md)。

## Power/QON 前轮已修复

SW201双刀常开接点与R528真实上拉/走线关闭U501.39未接、U201.7未驱动、BQ_QON孤立标签三项；没有新增flag/NC/ignore。
两信号精确网络契约与三种断线/短接负控通过，见[开关记录](lib/review/EP21SD1ABE-A-stage.md)。

## 前轮已修复（历史28→25）

| 原报告 | 修复 | 证据与边界 |
| --- | --- | --- |
| U502.7 VDD power_pin_not_driven | `#FLG0103` 声明 VSYS_AUDIO 经 U405 和已安装 R508=0Ω/MB6 供电 | 真实网络和R508两侧网名保持；flag不代表常开或实测带载通过。 |
| J501.6 VSS power_pin_not_driven | `#FLG0104` 声明全板 GND 参考 | ERC按网报告，标记在J501不意味着J501局部断地；没有改变其标准库pin类型。 |
| U503.1 bidirectional↔power_out | 当前U503采用 `LSM6DSO32XTR_I2C_MODE1` | CS/SA0接Vdd_IO、SDx/SCx接GND；依据ST的Mode1引脚定义，pins1/2/3为input，其他类型保持，通用符号保留。 |

反向控制：移除audio声明后ERC26，仅恢复U502.7；移除GND声明后ERC26，仅恢复J501.6；恢复通用U503模型且保留
两声明后ERC28，新增U503.1/.2/.3三项pin_to_pin。恢复正向候选后ERC25，剩余25项与原报告原文一致。

## 原16项本轮闭合归属

| 功能／对象 | 原报告数 | 本轮真实实现／未验边界 |
| --- | ---: | --- |
| 显示接口：U501 IO16/17/18/21/38/39/40/41/42/47/48 | 11 pin_not_connected | 接J601真实低压显示接口，全部14显示网及电源/控制布线通过；面板、配对件与机械实物仍未验。 |
| GPIO45 | 1 pin_not_connected | 指定N16R8模块条件下接EPD_STH/J601.23；没有烧写或读回实物eFuse，启动资格仍开放。 |
| 电池温度：BQ_TS、BQ_TS_BIAS | 1 pin_not_driven + 2 isolated_pin_label | J302外置103JT-025-600AY NTC、R615=5.23k/R616=30.1k真实网络；配置读回、贴附与热响应未验。 |
| RTC_VBACKUP / U302.6 | 1 power_pin_not_driven | R304 DNP、C301=KW-5R5C684-R，依赖RV-3028内部trickle配置及预充；24h保持和漏电老化仍未验。 |

原报告分类合计：12 pin_not_connected、2 isolated_pin_label、1 power_pin_not_driven、1 pin_not_driven、0 pin_to_pin；本轮关闭后active合计0。
其中同一个未完成网络可能产生不同类别的报告；16是报告条目数，不是16个独立硬件故障。喇叭／线束／机械声学资格仍开放，不能由ERC减少推断通过。

## 当前源身份与复现

- SCH SHA-256：`b6e499f2a8917dc10115c5d25f54f65a86ac5f6a43d3d447a5a67dc88ba40fbc`。
- PCB SHA-256：`d96aef03000e560f7408079990fc9af17437914758e2f50310fa858d3e46a0d6`（Fix25，SD/USB/BQ/J502及旧铜保持，ERC16→0）。
- 项目symbol library SHA-256：`40412b7ff0d3518c8c520f12b428d5cbe551f387b8c7b6449ffe8fe44d9d591f`。
- KiCad10.0.5，在实际权威project目录执行 `kicad-cli sch erc --format json --severity-all --output <erc.json> <board>.kicad_sch`，
  并独立执行 `pcb drc --severity-all --schematic-parity --refill-zones --exit-code-violations`；ERC不能用进程exit0代替条目审计。
- 完整逐条UUID表和复现代码在Trellis任务 `09-07-panda-remaining-erc-layout`（此前Power/QON及模型修正记录保留） 的research/implementation-evidence/verification记录。

## 依据

- [KiCad10：power pins and power flags](https://docs.kicad.org/10.0/en/eeschema/eeschema.html#power-pins-and-power-flags)。
- [ST LSM6DSO32X，DS13607 Rev1，Table18](https://www.st.com/resource/en/datasheet/lsm6dso32x.pdf)。
- [Mode1 A-stage记录](lib/review/LSM6DSO32XTR-I2C-MODE1-A-stage.md)。
- [RTC无后备源记录](lib/review/RV-3028-C7-A-stage.md)。
