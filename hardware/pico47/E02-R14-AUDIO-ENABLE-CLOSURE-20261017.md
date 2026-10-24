# Pico47 E0.2 r14-audio-enable — 四层布线续作

2026-10-17 续作更新：当前具名检查点为
[r15-fl-pwm](E02-R15-FL-PWM-CLOSURE-20261017.md)，Core22/Display3。
以下保留r14历史验证记录。

2026-10-17，执行者：Codex。**仍有26个原生未连接项，禁止制造及面板/电池上电。**

当前具名检查点：
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261017-r14-audio-enable/engineering-candidate`。
继承关系为 r12 → r13-vcom → r14-audio-enable；旧包完整保留。

| 板 | 未连接项 | DRC错误 | 警告 | Parity | ERC |
| --- | ---: | ---: | ---: | ---: | ---: |
| Core | 23 | 0 | 0 | 0 | 0 |
| Display | 3 | 0 | 0 | 0 | 0 |

## 本次闭合及范围

Core 的 EN_VSYS_AUDIO 原生连接了 U601.7、U405.B2、R507.1，未连接项从24降到23。
音频新主线约100.034 mm，整个网络铜长约104.805 mm，共8个过孔。
新孔为普通0.45/0.25 mm通孔；没有新增孔中盘工艺。

采用方案替换37项铜并增加312项铜，仅涉及 EN_VSYS_AUDIO、
EN_3V3_EPD_LOGIC、EN_3V3_SD、3V3_TOUCH、VSYS_RAW 五网。
其中两个电源网络仅调整所选原有0.15 mm分支，替换段保持0.15 mm；
3V3_TOUCH全网铜长增加约2.049 mm，VSYS_RAW增加约0.996 mm。
这不是载流能力或瞬态验证结论；相关工程门槛继续保持未完成。

独立原生逐项审计确认其它10,797项走线/过孔相同。
Display原生板和两板规则文件未变；器件、焊盘、位置、外形及四层堆叠未变。
无In1信号线。Core原有219组焊盘保持并因音频连接合并为218组；
Display保持93组。全部237个地焊盘与8个指定地目标连接完整。
GPIO2直控、Display四控制线、负PMIC隔离EP、C804指定回流保持。

## 验证证据

受控铜替换、带 `--require-complete-ground` 的完整捕获、
`build_pico47.py --routing-checkpoint` 源码重建及独立完整地再捕获均通过，
重现23/3及错误/警告/parity/ERC全零。
三只音频焊盘在首次捕获和重建后均按原生物理身份确认同组。
重建会改变UUID，跨重建验证使用 reference/pad/position/net/layers身份。

外部包旁保存准确铜意图、独立铜审计、往返验证和299文件SHA复制验证。
本轮没有源码逻辑修改，没有把旧源码测试结果当成新布线验收。

| 原生板 | SHA-256 |
| --- | --- |
| Core | `6a95d16ca6452d38fa0560f450bb989568a17d497ad49b76da7b5a8a86461f79` |
| Display | `33ac2acda088d20cb73e29c9d58f9d5ca17567bb463ecd11958c12749332acd9` |

## 后续操作

从上述具名包继续四层布线；不要采用较新mtime的不完整试验。
继续使用 `capture_pico47_checkpoint.py --require-complete-ground`，
并保持原生组、原规则和源绑定重建。
独立检查器会向候选写入netlist，应在新副本上运行，勿修改已发布包。

Display仍有SDA/VP/VPOS，Core仍有23项未连接；完整布线目标未达成。
C810移位范围问题尚未获答复，本轮未移动任何器件。
时序/电流、精确电池与完整屏幕堆叠、≤7mm成品及实物EVT仍未验证。
所有生成CAD、报告和试验均留在忽略目录或外部交付目录；未提交或推送。
