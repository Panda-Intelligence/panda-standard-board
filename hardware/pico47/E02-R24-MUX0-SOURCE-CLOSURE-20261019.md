# Pico47 E0.2 r24-mux0-source — MUX0 四层布线闭合

2026-10-19，执行者：Codex。**Core 仍有 16 个原生未连接项，不可制造、充电或给面板/电池上电。**

当前具名检查点：
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261019-r24-mux0-source/engineering-candidate`。
继承 r12 至 r23，旧包完整保留。全程后台 CLI/nice 10，没有窗口激活、Git 提交或推送。

| 板 | 未连接项 | DRC 错误 | 警告 | Parity | ERC |
| --- | ---: | ---: | ---: | ---: | ---: |
| Core | 16 | 0 | 0 | 0 | 0 |
| Display | 0 | 0 | 0 | 0 | 0 |

## 接点与修改范围

P47_MUX0 接通 U501.10 与 U710.4，原生物理焊盘组独立核对通过。当前该网总铜长
21.988657 mm、4 个过孔。协调 GPIO0、I2C_SDA、KEY_POWER_MCU、P47_BUS_OE_N、
P47_D3_SRC、P47_D8_SRC、P47_MUX1、P47_MUX2、P47_XSTL_SRC；全部原网络恢复，
包括 SDA 的 13 个实际焊盘，以及 GPIO0、D8、XSTL 的完整分支。

精确源绑定事务移除 300 个原铜对象、增加 705 个铜对象；保留的 14,474 个原对象逐项相同。
其他网络的 12,296 个轨迹/过孔完全不变。7 个原过孔随审阅的信号引出迁移或接点清理移除，
新增 12 个 0.4/0.2 mm 过孔。器件、焊盘、位置、板框、库、原理图和规则不变；
四层、无 In1 信号走线。电源与地的原轨迹、过孔、平面定义，以及 GPIO2 关断链、USB 和射频铜保持；
地填充按原规则重算，完整地连接复核通过。

原生首轮已复现 16 opens、零错误与全部旧焊盘组，但有 9 条尾线/单层过孔警告，故事务回退。
单层过孔逐个核对全部层的铜环接触支路；多支路先添加明确的同层接续，再移除无换层作用的过孔。
每一步均检查原生连通组、16 opens 和零错误。尾线整体删除曾被连接守卫拒绝；最终仅删除
确认的自由尾线，缩短仍承担中途接点的原线段端部。没有把单层过孔或 dangling 警告当作可盲删接点。

## 本地证据

从原 r23 回放清理后的精确铜意图，完整地捕获、干净源码重建及独立完整地再捕获，均复现
Core 16 / Display 0，双板 DRC 错误/警告、Parity、ERC 全零。Core 原 212 组、Display 原 90 组
全部保留，Core 因新 MUX0 闭合合并为 211 组。独立按物理身份检查 30 个 Core 网络与
15 个 Display 网络的全部焊盘连接。

237 个地焊盘、8 个指定地目标、完整 GPIO2/互连/R813/PMIC EN 链、C804 规定返流过孔及负 PMIC EP
隔离均保持。重建与再捕获的全部 15,179 个 Core、5,985 个 Display 铜对象与首次捕获逐项相同，
原生语义指纹相同。原 r23 的 305 文件 SHA 清单仍逐项匹配；新 r24 包逐项核实 306 个文件。

| 原生板 | SHA-256 |
| --- | --- |
| Core | `0dcaaa46e4bddd20ddf02cf16503aba0c758f3bd85debe383d200352d06101c8` |
| Display | `27273daadceaa9e01d8ebb8571f7a2fec7f27928b05eef3ae22a4ab3e7416409` |

本地证据在 `.work/pico47-fourlayer-resume-20261017/`：`mux0-complete-ground-capture`、
`mux0-source-rebuild`、`mux0-roundtrip-proof`、`MUX0-ROUNDTRIP-AUDIT.json`、
`MUX0-INDEPENDENT-COPPER-AUDIT-r24.json` 和逐接点/尾线审阅。外部包含精确
`MUX0-NATIVE-INTENT.json`、独立审计与 SHA 清单。未改产品代码，没有冒称重跑历史单元测试、CI 或实物 EVT。

## 继续与限制

仍需完成 P47_D1_SRC、SDMMC_CLK、P47_MUX3、P47_MUX5、P47_D10_SRC、P47_D11_SRC、
P47_D14_SRC、P47_XLE_SRC、SDMMC_D2、SDMMC_D1、SDMMC_D0、UART0_RX、UART0_TX、
P47_D0_SRC、P47_D7_SRC、P47_D6_SRC。完整四层目标要求两板真实 opens 均为零。

后续意图必须绑定 r24 的新 Core SHA；不要直接应用旧 r23 意图。继续使用
`capture_pico47_checkpoint.py --require-complete-ground`、干净源码重建与独立再捕获。
独立 inspector 只能在新副本写 netlist，不能修改本具名包。

数字时序、SI/PI、电流、模拟反馈、精确 2050 mAh LCO 电池、全屏堆叠、含正公差的 ≤7 mm 成品、
CAM/SMT 与实物 EVT 门槛仍未完成。`manufacturing_release=false`，
`physical_qualification_complete=false`。生成 CAD/报告/试验保持忽略或外部存储；保留 packaging/、
其他工作树和用户修改。
