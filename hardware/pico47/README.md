# Current Continuation: E0.2 R49 — 前光升压供电修正（2026-11-06）

`hardware/pico47/v0.1.2/` 是 R49 的完整 KiCad 工程（PCB＋带连线的可读原理图＋本地库），可直接打开或打包导入；原理图由 `readable_schematic.py` 生成，网表与 R49 完全相同。嘉立创EDA专业版的 KiCad 导入文档注明支持 10.0 以下版本，本工程为 KiCad 10 格式，导入前须实测。

2026-11-06，Claude。先读 [R49 前光升压供电修正](E02-R49-FRONTLIGHT-SUPPLY-20261106.md)。R48 及以前前光升压输入 `VSYS_FL_IN` 没有电源；R49 把它并入 `VSYS_RAW`，其余与 R48 相同。用 `build_pico47_single_r49.py --output <.work 下新目录>` 从 R26 经 R48 回放重建并导出下单包；`manufacturing_release` 仍为 false。

# Historical Continuation: E0.2 R48 — XSTL背面清零、CKV局部内层与顶层桥接及四网协调（2026-11-03）

2026-11-03，Codex。先读 [R48 XSTL背面清零、CKV局部内层与顶层桥接及四网协调](E02-R48-XSTL-AND-CKV-BRIDGES-20261103.md) 及 2026-11-04 发布的权威总览与三份专项工程规范：
- [七组待闭合硬件实证项状态总览](E02-SEVEN-QUALIFICATION-EVIDENCE-OVERVIEW-20261104.md)
- [DFM 制造工艺、装配公差与高速时序工程规范](E02-DFM-ASSEMBLY-AND-TIMING-SPECIFICATION-20261104.md)
- [EVT 电气测试与温度标定规程](E02-EVT-ELECTRICAL-VERIFICATION-PROTOCOL-20261104.md)
- [46 孔盘中孔 (POFV / IPC-4761 Type VII) 板厂 CAM 专项制造规范](E02-POFV-46-VIA-CAM-MANUFACTURING-PACKAGE-20261104.md)

联合调整`P47_XSTL`、`P47_CKV`、`UART0_RX`与`3V3_EPD_LOGIC`四个网络：清理`3V3_EPD_LOGIC` 156段冗余并联阶梯环路及3颗冗余过孔（保留`0.35 mm` In2主干），将`P47_XSTL`仅存3段B面桥线改为5段In2桥并移除旧换层孔`(51.425,84.650)`mm（`P47_XSTL`背面0段）；将`P47_CKV`西中段`(34.000,104.075) → (34.525,104.925)`mm改入In2层、中段`(34.525,104.925) → (44.900,106.450)`mm改为F面连续走线并移除2颗旧换层孔`(41.150,104.925)`与`(43.425,104.975)`mm（`UART0_RX`过孔南移至`41.000,106.500`mm）、东侧In2折点微调至`x=47.700`mm消除避铜切口，并将东侧B面走线对齐至`SD_REFERENCE_GND`下方。全部265件／908盘身份、字段、位姿、其余网络铜与过孔、19区／规则／图纸／库、CPL226／完整46孔／21项与BT301清单保持。全板为10475轨（−151）、996孔（−6）、19区。`P47_XSTL_SRC`（0.544301mm²）、`P47_XLE_SRC`（2.719541mm²，背面0段）、`P47_XCL_SRC`（3.196081mm² In2）、`P47_XSTL`（2.395350mm² 5段In2桥，背面0段）与`P47_CKV`（0.553152mm² 全7段In2）铜边+0.25mm连续走廊均由实际连通`U501.57`的In1地100%零缺口覆盖。`P47_XSTL`主路径总导体缩短0.136mm、过孔9→8、铜阻估算+12.86mΩ；`P47_CKV`主路径总导体缩短0.985mm、过孔9→7、铜阻估算+6.12mΩ，未声称时序或噪声通过。

默认R48，候选 `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261103-r48/engineering-candidate`；510个不同本地测试互补通过（geometry 406 pass/104 skip，KiCad 491 pass/19 skip），原502 IDs保留。背面时钟缺口由420／608点、26.399309mm²（5网）降至385／574点、24.386846mm²（4网，净减2.012463mm²），但`P47_CKV`、`P47_XCL`、`P47_XCL_SRC`及`R731`支路仍待继续处理。四项物理资格全部false；板厂46孔TypeVII书面CAM、21项及BT301核验、真实2050mAh电池／全屏／壳体含正公差≤7.0mm实测与EVT签核仍待证据。不制造、充电或面板上电，保持单候选串行核验与中间CAD清理，历史R47及其它包不改。

# Historical Continuation: E0.2 R47 — XLE源端内层桥段与五网局部协调（2026-11-03）

2026-11-03，Codex。先读 [R47 XLE源端内层桥段与五网局部协调](E02-R47-XLE-INNER-BRIDGE-20261103.md)。联合调整`P47_XLE_SRC`、`EN_VSYS_AUDIO`、`P47_XCL_SRC`、`P47_D2_SRC`与`HW_ARM_GPIO`局部In2走线，将`P47_XLE_SRC`两段B面桥线改为三段In2走线并移除已废弃过渡孔`(51.825,101.275)`mm（−1孔）。全部265件／908盘身份、字段、位姿、F面／其余网络铜与过孔、19区／规则／图纸／库、CPL226／完整46孔／21项与BT301清单保持。全板为10626轨（+19）、1002孔（−1）、19区。`P47_XSTL_SRC`（0.544301mm²）、`P47_XLE_SRC`（2.719541mm²，背面0段）与`P47_XCL_SRC`（3.196081mm² In2）铜边+0.25mm连续走廊均由实际连通`U501.57`的In1地100%零缺口覆盖。`P47_XLE_SRC`主路径平面长度保持13.758mm、换层导体缩短0.2525mm、过孔3→2、铜阻估算+10.61mΩ；`P47_XCL_SRC`平面+3.373mm、铜阻估算+22.15mΩ，未声称时序或噪声通过。

默认R47，候选 `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261103-r47/engineering-candidate`；500个不同本地测试互补通过（geometry 402 pass/98 skip，KiCad 481 pass/19 skip），原498 IDs保留。背面时钟缺口由438／629点、27.743521mm²降至420／608点、26.399309mm²（净减1.344213mm²），但`P47_CKV`、`P47_XCL`、`P47_XCL_SRC`及`R731`支路仍待继续处理。四项物理资格全部false；板厂46孔TypeVII书面CAM、21项及BT301核验、真实2050mAh电池／全屏／壳体含正公差≤7.0mm实测与EVT签核仍待证据。不制造、充电或面板上电，保持单候选串行核验与中间CAD清理，历史R46及其它包不改。

# Historical Continuation: E0.2 R46 — XSTL源端内层桥段（2026-11-03）

2026-11-03后续：[R731迁位与供电连接可行性审查](E02-R731-RELOCATION-FEASIBILITY-20261103.md)记录了未采用的局部迁位／两件对换试验。C527正面电源盘兼作U501.20及两颗总线开关供电组的连接点，不能当普通电容引线删除。正式PCB和默认构建仍为R46。

2026-11-03，Codex。先读 [R46主桥段、连续参考与路径取舍](E02-R46-XSTL-INNER-BRIDGE-20261103.md)。仅把XSTL_SRC四段B桥迁成四段In2线，使用原两孔并裁掉25µm悬空尾段，所有部件／焊盘／位姿、F面／其它网铜／过孔、19区／规则／图纸／库、CPL226／完整46孔／21项与BT301清单保持。新0.544301mm²铜边参考走廊由实际连通In1地完整覆盖；主模型平面长度增加0.401mm、换层导体缩短0.2525mm、铜阻估算增加约7.14mΩ，未声称时序或噪声通过。

默认R46，候选 `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261103-r46/engineering-candidate`；498个不同本地测试互补通过，原491 IDs保留。背面仍438／629点和27.743522mm²参考缺口，CKV及R731支路还需继续处理。四项物理资格全部false；板厂46孔TypeVII书面CAM、21项及BT301核验、真实2050mAh电池／全屏／壳体含正公差≤7.0mm实测与EVT签核仍待证据。不制造、充电或面板上电，保持单候选串行核验与中间CAD清理，历史R45及其它包不改。

# Historical Continuation: E0.2 R45 — 背面时钟局部参考地（2026-11-03）

2026-11-03，Codex。先读 [R45局部参考地及连续走廊检查](E02-R45-REAR-CLOCK-GROUND-20261103.md)。只新增三块有界In2 GND区，全部R44器件／焊盘／字段／位姿、10607轨／1003孔、原16区和规则／图纸／库／CPL226／全46孔／21项供料／BT301保持。三区经实际U501.57连接的原生填铜验收：背面时钟缺口495→442／633点，连续铜边外扩0.25mm走廊缺地31.247640→27.996008mm²，减少3.251632mm²。参考仍不完整，时序／阻抗／实际噪声稳定性仍未资格化，不能用较远In1替代相邻In2的缺口。

默认R45从不可变R26回放；历史R44保留。491个不同本地用例互补通过，保留原484 IDs；新增小孔、侧边缺口、孤岛及删线负例。当前候选为 `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261103-r45/engineering-candidate`。四项物理资格仍为false，46孔TypeVII书面CAM、21项SMT与BT301来料、真实2050mAh电池及全屏／壳体含正公差≤7.0mm实测与EVT签核均待证据；不制造、充电或面板上电。保持单候选串行核验与清理，生成CAD及报告留在Git外。

# Historical Continuation: E0.2 R44 — TH801封装与名义温度曲线修正（2026-11-03）

执行者：Codex。先读 [R44 TH801原厂型号、0402及名义3380修正](E02-R44-THERMISTOR-IDENTITY-20261103.md)。原`CMFA103F3950HANT`按原厂尺寸代码为0603/B3950，和既有0402焊盘及历史PMIC参考3380不匹配；改用FH官方目录确认的`CMKD103F3380HANT`（0402、10kΩ±1%、B25/50=3380K±3%）。仅同步PCB／原理图／本地库／构造器及物料注册的一项MPN，全部265件位姿、908盘ID／形状／针网、10607轨1003孔16区和原规则保持。CPL226／全46孔工艺／BT301保持，21待供料仅TH801料号变化，不新增LCSC或收货记录。

默认R44；两次完整R26重建、默认入口与历史R43均为原生／ERC0/0/0/0/0，三个R44独立原生审计通过。484个不同本地用例互补覆盖（geometry402 pass/82 skip、KiCad465 pass/19 skip，旧475 IDs全保）。温度守卫核精确0402料号、7.5k/36k及实际TS／VREF／参考地连接；B公差±3%比Murata参考件±1%更宽，完整R–T、实际温度精度和来料仍未资格。资格报告四项false保持，并追加温度曲线的第七组待实证记录。

候选 `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261103-r44/engineering-candidate`，PCB SHA `590e5f8388b9e82c6f9303dde3c70931f26e620a295c269a70d314ae5f2c4939`，增量SHA `9c7f1cf13a8d101e7f582e5dfb81322aa3c491c905c8de517daab0a1fe4e5311`。实际PMIC版本、全曲线／噪声稳定性／泵纹波、真实2050mAh包与全屏／背高／正公差≤7mm、46孔TypeVII CAM／21项与BT301供料／EVT仍待证据，禁止制造、充电及面板上电；完整中间回放核后清理，仅保单个正式native候选及小验收记录。

# Historical Continuation: E0.2 R43 — C808 / C811 双电荷泵飞跨电容网络（`P47_VGH_DRV`、`P47_PUMP_POS`、`P47_PUMP_NEG`）几何收敛与全 8 网守卫（2026-11-02）

执行者：Codex。先读 [R43 C808 / C811 双电荷泵飞跨电容网络几何收敛与全 8 网守卫](E02-R43-C808-C811-FLYING-CAP-LAYOUT-20261102.md)。相对 R42 保持 **零器件迁位**（全部 265 件 908 盘位姿、身份、UUID、值、字段与针网 100% 不变，CPL 226 项逐字节恒等），且**仅改动 `P47_VGH_DRV`、`P47_PUMP_POS`、`P47_PUMP_NEG` 三条飞跨电容网络**（其余全板铜轨、过孔与 16 个覆铜区完全保持）：
- `P47_VGH_DRV`（`U810.36 <-> C808.2`）：消除 108 段 `25 µm` 阶梯碎线、1 条 `35.4 µm` 悬空短桩、2 条 `1.7 µm` 重复线段及 `In2.Cu` 上 `274.9 µm` 非端点重合圆头搭接，走线段数由 `119 -> 9` 段（`-110` 段 / `-92.4%`），全网铜长 `6.857 -> 6.812 mm`（`-0.046 mm`），`2` 孔不变（`F.Cu + In2.Cu`），串联铜阻 `0.0353 -> 0.0350 Ω`；
- `P47_PUMP_POS`（`C808.1 <-> D803.3`）：消除 28 段 `25 µm` 阶梯碎线及 `79.1 µm` 非端点重合圆头搭接，走线段数由 `38 -> 10` 段（`-28` 段 / `-73.7%`），全网铜长 `15.854 -> 15.777 mm`（`-0.077 mm`），`0` 孔（`F.Cu` 同层直连，距 `L801.1` 焊盘净空 `>= 175 µm`），串联铜阻 `0.0511 -> 0.0508 Ω`；
- `P47_PUMP_NEG`（`C811.1 <-> D804.3`）：消除 18 段 `25 µm` 阶梯碎线与 4 处非端点重合圆头搭接，并将原 `0.15 / 0.16 mm` 混合细线统一拓宽至 `0.20 mm`，走线段数由 `27 -> 7` 段（`-20` 段 / `-74.1%`），全网铜长 `12.303 -> 12.164 mm`（`-0.139 mm`），`2` 孔不变（`B.Cu + F.Cu`），串联铜阻 `0.0338 -> 0.0320 Ω`（`-5.5%`）；
- 三条飞跨电容网络合计走线段数由 `184 -> 26` 段（净减 `158` 段），其余 5 条电荷泵网络（`P47_VEE_BASE` `30.266 mm / 2 孔`、`P47_VEE_DRV` `7.253 mm / 2 孔`、`P47_VGL` `51.515 mm / 7 孔`、`P47_VGH_BASE` `24.605 mm / 3 孔`、`P47_VGH` `51.792 mm / 6 孔`）100% 保持原样。

默认 R43；两次独立完整 R26→R43 重建、默认入口及历史 R42 回归均通过，原生／ERC **0/0/0/0/0**，全板 `265` 件 `908` 盘、`10607` 轨 `1003` 孔 `16` 区。`inspect_pmic_charge_pump_storage` 守卫现完整锁定正负双侧全部 **6 颗电荷泵电容**（`C810`、`C811`、`C812`、`C807`、`C808`、`C809`）、全部 **8 条电荷泵网络**及全部 **24 颗过孔** `>= 50 µm` SMD 盘边净空，并保持 185 地 52 关键链、7 对 PMIC 连续铜参考地走廊、66 件源位姿 0 冲突、背面 6 件 SMT 禁布净空、完整 46 孔 POFV 工艺签名、226 SMT/CPL、BT301 后装及 21 项待供料。470 个不同本地源用例互补全覆盖（geometry 396 pass/74 skip，KiCad 451 pass/19 skip）。

工程候选为 `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r43/engineering-candidate`，默认 PCB SHA-256 `92f6fe61767f79146c79e0bcba254d54c464b0c1f8f2391cced6807feb173abc`，源增量 SHA-256 `14d01b10f96da7e7666af7c2d0f70fc533a4817c0c2e1f59a645b8578ef369e0`。电荷泵瞬态／纹波与 PMIC 真实噪声稳定性、供应商最大包络、实际电池全屏与正公差 ≤7mm、板厂 46 孔 CAM 确认／21 项供料建档／EVT 仍待实证，`manufacturing_release=false`。

2026-11-03，Codex：[四项资格状态与待闭合证据](E02-QUALIFICATION-STATUS-20261103.md)统一导出制造、板厂工艺、真实噪声／稳定性及泵瞬态／纹波四项`false`。报告绑定实际R43 PCB与46孔／21项SMT／BT301精确清单，不能由零DRC或几何守卫上调为通过。本轮完整重建与独立全板对照保持R43全部铜、身份、位姿及原生检查全零，475个不同本地用例互补通过。历史预CAM位号分组已按真实46孔清单勘误；实际板厂书面CAM、来料、真实电池全屏含正公差≤7.0mm及EVT原始波形／签核仍待证据。

# Historical Continuation: E0.2 R42 — C809 (`P47_VGH`) 正压栅极整流输出直连与储能滤波收敛（2026-11-02）

执行者：Codex。先读 [R42 C809 (`P47_VGH`) 正压栅极整流输出直连与储能滤波收敛](E02-R42-C809-VGH-RECTIFIER-LAYOUT-20261102.md)。相对 R41 保持 **零器件迁位**（全部 265 件 908 盘位姿、身份、UUID、值、字段与针网 100% 不变，CPL 226 项逐字节恒等），且**仅改动 `P47_VGH` 单一网络**（其余全板铜轨、过孔与 16 个覆铜区完全保持）：
- `P47_VGH`（`D803.2 -> C809.1 -> U810.35 / R801.1 / J820.3 / TP801.1`）：消除 `D803.2 -> C809.1` 遗留的 `VIA (31.25, 95.675) -> B.Cu -> VIA (30.50, 91.375)` 双过孔 `0.15 mm` 底层绕行、`C809.1 (28.00, 91.95)` 至东侧过孔 `(30.50, 91.375)` 的 `2.57 mm` 往返折返及 65 段 `25 µm` 阶梯碎线，改为沿 `F.Cu` 连续 `0.50 mm` 走线零过孔直连并将 `C809.1` 换层过孔移至焊盘正南 `(28.00, 92.80)`（距 `C809.1` 盘边净空 `100 µm`）：
  - `D803.2 -> C809.1`：平面长度 `6.949 -> 4.968 mm`（**缩短 `1.981 mm` / `-28.5%`**），空间导体长 `8.479 -> 4.968 mm`（**`-41.4%`**），过孔 `2 -> 0` 颗（`['B.Cu', 'F.Cu'] -> ['F.Cu']`），20°C 串联铜阻 `0.0174 -> 0.0049 Ω`（**`-71.8%`**）；
  - `C809.1 -> U810.35`：平面 `13.652 -> 12.141 mm`（`-1.511 mm`），空间 `15.182 -> 13.671 mm`，`2` 孔，铜阻 `0.0175 -> 0.0167 Ω`；
  - `C809.1 -> R801.1`：平面 `12.685 -> 11.175 mm`（`-1.511 mm`），空间 `14.215 -> 12.705 mm`，`2` 孔，铜阻 `0.0143 -> 0.0136 Ω`；
  - `C809.1 -> J820.3`：平面 `30.506 -> 27.287 mm`（`-3.219 mm`），空间 `32.289 -> 29.070 mm`，`4` 孔，铜阻 `0.0481 -> 0.0449 Ω`；
  - `D803.2 -> TP801.1`：平面 `0.604 mm`、空间 `1.369 mm`、`1` 孔、`0.0020 Ω`（完全不变）；
  - 全网 `54.123 -> 51.792 mm`（`204 -> 148` 轨，`-56` 段，过孔 `6` 颗不变），全部端点路径与全网指标单调改善（零回退取舍）。
- `P47_VGH_BASE`（`24.605 mm / 3 孔`）、`P47_VGH_DRV`（`6.857 mm / 2 孔`）及 R40 负压三网（`P47_VEE_BASE` `30.266 mm / 2 孔`、`P47_VEE_DRV` `7.253 mm / 2 孔`、`P47_VGL` `51.515 mm / 7 孔`）100% 保持原样。

默认 R42；两次独立完整 R26→R42 重建、默认入口及历史 R41 回归均通过，原生／ERC **0/0/0/0/0**，全板 `265` 件 `908` 盘、`10765` 轨 `1003` 孔 `16` 区。`inspect_pmic_charge_pump_storage` 守卫现同时锁定负压侧（`C810` / `C812`，`D804.1 -> C812.1` `F.Cu` 同层直连）与正压侧（`C807` / `C809`，`D803.2 -> C809.1` `F.Cu` 同层直连，`P47_VGH <= 52.0 mm / 6 孔`）共 6 个电荷泵网络及全部 22 颗过孔 `>= 50 µm` SMD 盘边净空，并保持 185 地 52 关键链、7 对 PMIC 连续铜参考地走廊、66 件源位姿 0 冲突、背面 6 件 SMT 禁布净空、完整 46 孔 POFV 工艺签名、226 SMT/CPL、BT301 后装及 21 项待供料。468 个不同本地源用例互补全覆盖（geometry 396 pass/72 skip，KiCad 449 pass/19 skip）。

工程候选为 `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r42/engineering-candidate`，默认 PCB SHA-256 `38451516c01a7e7e2599dbb4413ca6e3378308c1106cfcc4c13c1026a60f88a0`，源增量 SHA-256 `49022c5ff102464b69ddf6a31b5425038b2ba36617dfd1d6249a9692385142d3`。电荷泵瞬态／纹波与 PMIC 真实噪声稳定性、供应商最大包络、实际电池全屏与正公差 ≤7mm、板厂 46 孔 CAM 确认／21 项供料建档／EVT 仍待实证，`manufacturing_release=false`。

# Historical Continuation: E0.2 R41 — C807 (`P47_VGH_BASE`) 正压电荷泵储能支路收敛与正负双侧电荷泵原生守卫闭合（2026-11-02）

执行者：Codex。先读 [R41 C807 (`P47_VGH_BASE`) 正压电荷泵储能支路收敛与正负双侧电荷泵原生守卫闭合](E02-R41-C807-VGH-BASE-LAYOUT-20261102.md)。相对 R40 保持 **零器件迁位**（全部 265 件 908 盘位姿、身份、UUID、值、字段与针网 100% 不变，CPL 226 项逐字节恒等），且**仅改动 `P47_VGH_BASE` 单一网络**（其余全板铜轨、过孔与 16 个覆铜区完全保持）：
- `P47_VGH_BASE`（`U810.34 -> C807.1 -> D803.1`）：消除 R37 前遗留的 `B.Cu` 跳层桥 `(19.30, 94.525) -> (20.70, 93.55)`、功率电感 `L801` 下方的东向折返环（`X = 17.545 -> 22.658 -> 17.545 mm`）及 6 处非精确共点折点，重构为仅走 `F.Cu + In2.Cu` 的精确共点 Steiner 树（经 `In2.Cu` 三叉节点 `(19.75, 93.275)` 与 `L801` 西侧净空过孔 `(19.50, 89.0896)`）：
  - `U810.34 -> C807.1`：平面长度 `19.034 -> 14.311 mm`（**缩短 `4.723 mm` / `-24.8%`**），空间导体长 `21.329 -> 15.841 mm`（**`-25.7%`**），过孔 `3 -> 2` 颗，20°C 串联铜阻 `0.0559 -> 0.0408 Ω`（**`-27.0%`**）；
  - `C807.1 -> D803.1`：平面 `22.667 -> 22.332 mm`，空间 `24.197 -> 23.862 mm`，`2` 孔，铜阻 `0.0652 -> 0.0642 Ω`；
  - `U810.34 -> D803.1`：平面 `12.582 -> 12.285 mm`，空间 `14.877 -> 13.815 mm`，过孔 `3 -> 2` 颗，铜阻 `0.0423 -> 0.0382 Ω`；
  - 全网 `27.919 -> 24.605 mm`（`33 -> 22` 轨，`4 -> 3` 孔，层集合 `['B.Cu', 'F.Cu', 'In2.Cu'] -> ['F.Cu', 'In2.Cu']`），三对端点路径与全网指标全面单调改善（零回退取舍）。
- `P47_VGH_DRV`（`6.857 mm / 2 孔`）、`P47_VGH`（`54.123 mm / 6 孔`）及 R40 负压三网（`P47_VEE_BASE` `30.266 mm / 2 孔`、`P47_VEE_DRV` `7.253 mm / 2 孔`、`P47_VGL` `51.515 mm / 7 孔`）100% 保持原样。

默认 R41；两次独立完整 R26→R41 重建、默认入口及历史 R40 回归均通过，原生／ERC **0/0/0/0/0**，全板 `265` 件 `908` 盘、`10821` 轨 `1003` 孔 `16` 区。`inspect_pmic_charge_pump_storage` 守卫现同时锁定负压侧（`C810`）与正压侧（`C807`，`P47_VGH_BASE <= 25.0 mm / 3 孔 / F.Cu+In2.Cu`）共 6 个电荷泵网络及全部 22 颗过孔 `>= 50 µm` SMD 盘边净空，并保持 185 地 52 关键链、7 对 PMIC 连续铜参考地走廊、66 件源位姿 0 冲突、背面 6 件 SMT 禁布净空、完整 46 孔 POFV 工艺签名、226 SMT/CPL、BT301 后装及 21 项待供料。466 个不同本地源用例互补全覆盖（geometry 396 pass/70 skip，KiCad 447 pass/19 skip）。

工程候选为 `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r41/engineering-candidate`，默认 PCB SHA-256 `64d9338d42c2d2ea2584266dc8de43b0edcb11bc44beefdb6683acc0ea85e3b7`，源增量 SHA-256 `8d4e8ad588ae5b9dcb5c68d4eb0194b6724b61a31dd25901dbfd6fc30d8912cb`。电荷泵瞬态／纹波与 PMIC 真实噪声稳定性、供应商最大包络、实际电池全屏与正公差 ≤7mm、板厂 46 孔 CAM 确认／21 项供料建档／EVT 仍待实证，`manufacturing_release=false`。

# Historical Continuation: E0.2 R40 — C810 (`P47_VEE_BASE`) 电荷泵储能支路收敛与 PMIC 负压三网联合闭合（2026-11-02）

执行者：Codex。先读 [R40 C810 (`P47_VEE_BASE`) 电荷泵储能支路收敛与 PMIC 负压三网联合闭合](E02-R40-C810-VEE-BASE-LAYOUT-20261102.md)。相对 R39 保持 **零器件迁位**（全部 265 件 908 盘位姿、身份、UUID、值、字段与针网 100% 不变，CPL 226 项逐字节恒等），仅联合重布 `P47_VEE_BASE`、`P47_VEE_DRV`、`P47_VGL` 三项 PMIC 负压网络并清除死端残枝，其余全板铜轨、过孔与 16 个覆铜区完全保持：
- `P47_VEE_BASE`（`U810.30 -> C810.1`）：平面长度由 `22.623 mm` 缩短至 **`7.953 mm`（`-64.8%`）**，空间导体长 `24.153 -> 9.231 mm`，过孔 `3 -> 2` 颗，20°C 串联铜阻 `0.0945 -> 0.0493 Ω`，彻底消除 `B.Cu` 西侧外环（仅走 `F.Cu` + `In2.Cu`）；全网 `48.687 -> 30.266 mm`（`154 -> 34` 轨，`3 -> 2` 孔）；`C810.1 -> D804.2`（`20.282 mm / 0 孔`）保持原样。
- `P47_VEE_DRV`（`U810.28 -> C811.2`）：接管局部口袋过孔 `(20.425, 98.15)`，释放 `In2.Cu` 西侧走廊，保持 `6.048 mm` 平面 / `7.578 mm` 空间 / `2` 孔（全网 `7.253 mm`）。
- `P47_VGL`：`D804.1 -> C812.1`（`5.547 mm / 0 孔`）与 `C812.1 -> J820.1`（`30.552 mm / 2 孔`）功率主干 100% 不变；仅 `R803.1`（`750k` 高阻反馈分压支路）改由东北向汇入（平面 `15.856 -> 20.194 mm`，空间 `18.663 -> 21.724 mm`，全网 `47.484 -> 51.515 mm`，过孔保持 `7` 颗不变）。

默认 R40；两次独立完整 R26→R40 重建、默认入口及历史 R39 回归均通过，原生／ERC **0/0/0/0/0**，全板 `265` 件 `908` 盘、`10832` 轨 `1004` 孔 `16` 区。构建器新增 `inspect_pmic_charge_pump_storage` 守卫，并保持 185 地 52 关键链、7 对 PMIC 连续铜参考地走廊、66 件源位姿 0 冲突、背面 6 件 SMT 禁布净空、完整 46 孔 POFV 工艺签名、226 SMT/CPL、BT301 后装及 21 项待供料。463 个不同本地源用例互补全覆盖（geometry 396 pass/67 skip，KiCad 444 pass/19 skip）。

工程候选为 `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r40/engineering-candidate`，默认 PCB SHA-256 `c5dcfe47e8d48a2a0c5862cf8d9f9788d043c1dd5daaa390af2d8061ba380eb2`，源增量 SHA-256 `790430afd6c354c9f7099ae12048f81d4ed418851b60dabaadb774fe5d71d8e3`。电荷泵瞬态／纹波与 PMIC 真实噪声稳定性、供应商最大包络、实际电池全屏与正公差 ≤7mm、板厂 46 孔 CAM 确认／21 项供料建档／EVT 仍待实证，`manufacturing_release=false`。

# Historical Continuation: E0.2 R39 — 全源位姿包络闭合与CAM/供料/叠层预审（2026-11-02）

执行者：Codex。先读 [R39 66件源位姿包络闭合、背面净空与CAM/供料/叠层工程预审](E02-R39-POSE-ENVELOPE-AND-PRECAM-AUDIT-20261102.md)。仅将 L905 由 F12.05/123.90/180° 微移至 F12.05/123.65/180°，消除 R38 筛查保留的 L905／R931 保守 250µm 扩张包络重叠（名义 Fab 间距 0.360→0.610mm，L905 庭院距 R931 250µm 扩张框 +0.105mm、距 D905 庭院 +0.460mm）；其余 264 件位姿、全部 265 件 908 盘身份及全板 **10951 轨 1005 孔 16 区与 R38 完全一致（零铜改动）**。

默认 R39；两次独立完整 R26→R39 重建、默认入口及历史 R38 回归均通过，原生／ERC **0/0/0/0/0**。构建器启用 `inspect_source_pose_envelopes`（全部 66 件源变更器件 0 冲突）与 `inspect_backside_smt_clearances`（背面 6 颗阻容最大 0.55mm、25 个裸测点／调试盘，距电池仓 ≥5.405mm、距右上支撑区 ≥56.605mm），并保持 185 地 52 关键链、7 对 PMIC 连续铜参考地走廊、完整 46 孔 POFV 工艺签名、226 SMT/CPL、BT301 后装及 21 项待供料。459 个不同本地源用例互补全覆盖（geometry 396 pass/63 skip，KiCad 440 pass/19 skip）。

工程候选为 `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r39/engineering-candidate`，默认 PCB SHA-256 `64f0ea2d4cfead7cd740d3622da3ff89d30e34db1aad7e6b65d25660005bc2b3`，源增量 SHA-256 `7f27f458a118e80e194ba3a392c693ed362c634440f41d6e3eb1972e1b887c77`。供应商最大实物包络、真实电气／噪声稳定性、实际电池全屏／底壳避让槽与正公差 ≤7mm、板厂 46 孔 CAM 确认／21 项供料建档／EVT 仍待实证，`manufacturing_release=false`。

2026-11-02 Codex勘误：R39说明的供料表已按实际PCB/21项pending逐项更正，撤回旧表的错误厂家、料号、容值和阻值。背面0.55/0.40mm是项目高度预算，检查器没有验证供应商极值；0.55mm底壳、0.45mm挖深、0.25mm余壁的矛盾方案已撤回。历史封存包仍保留原件，采购和机械研究以当前仓库勘误为准。

# Historical Continuation: E0.2 R38 — PMIC联合布局（2026-11-02）

执行者：Codex。先读 [R38 分压、功率支路、实际地铜走廊与取舍](E02-R38-PMIC-JOINT-LAYOUT-20261102.md)。仅迁位 R803／R804，联合处理八个明确网的局部铜；其余263件位姿、全部265件908盘身份／值／字段／网表、未释放铜及原规则／区域／板框保持。VREF36.769→27.098mm／4→3孔，驱动9.564→7.098mm，VN_LX14.762→12.971mm／3→2孔，新增二极管支路为0.35F。VGL与BASE路径、二极管→电感空间长度增加，取舍明确保留。

默认R38；两次独立完整R26重建、默认入口及历史R37通过，原生／ERC **0/0/0/0/0**；全部旧焊盘组、185地52关键链、完整46孔工艺及实际SD／USB／时钟参考保持。构建器启用连续铜检查，七对源／接收铜及连接走廊的0.2mm裕量均由真实In1参考地覆盖。452不同本地源用例互补通过。当前265件908盘、10951轨1005孔16区，SMT／CPL226、BT301后装、21项待供料保持。

工程候选为 `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r38/engineering-candidate`。本次两件加此前43件的位姿包络复核无新冲突；扩展54源位姿筛查保留旧L905／R931的250µm保守裕量重叠，名义实体与焊盘未碰撞、实体Fab间隔0.36mm，实际最大包络／公差仍待核验。真实电气／噪声稳定性、PMIC当前版本、实际电池全屏／背面高度／正公差≤7mm、供料CAM／EVT仍未资格，`manufacturing_release=false`。仅保留单个在试完整候选，已关闭重建只留小验收记录；源及阶段记录按用户要求commit并push功能分支。

# Historical Continuation: E0.2 R37 — 缩短VREF参考树（2026-11-02）

2026-11-02，Codex：[PMIC 连续铜／参考地检查](E02-PMIC-SHIELD-REVIEW-20261102.md)新增原生走廊检查与九个边界用例，452 个本地源用例通过。后续联合重布原型尚未采用，当前 PCB 检查点仍为 R37。

执行者：Codex。先读 [R37 参考树路径、保留噪声风险与完整源回放](E02-R37-VREF-TREE-20261102.md)。只重接VREF铜，全部265器件908焊盘／位姿／身份及非VREF铜、原理图／库／规则保持；全网77.746→36.769mm、过孔6→4，C815唯一100n近端根路径保持。R805改为6.187mm F-only；R804路径缩至29.642mm。原端点和线圈下参考铜仍有未资格化耦合，新增铜没有扩大其物理暴露范围。

默认R37；两独立完整R26回放、默认入口和历史R36、三份独立原生审计通过，43/43、原生／ERC全零，185地52关键链、443不同本地源用例全覆盖。43位姿、7power／4CIN／4COUT、完整46孔工艺和SD／USB／时钟参考保持。当前候选 `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r37/engineering-candidate`。PMIC功率区／真实噪声稳定性／电气、真实电池全屏／背面高度／含正公差≤7mm、供料CAM／EVT仍待证据，`manufacturing_release=false`。验证通过的源及阶段工程记录按用户要求commit并push功能分支。

# Historical Continuation: E0.2 R36 — PMIC参考滤波电容近端摆位（2026-11-02）

执行者：Codex。先读 [R36 C815同值迁位、内层接点保留与完整源回放](E02-R36-PMIC-REFERENCE-FILTER-20261102.md)。原 C815 保持单颗100nF／原料号，移到B12.8/94/0，VREF脚到电容的平面铜路由14.601降至0.846mm，有效过孔2→1。保留265器件908焊盘全部身份／值／针序，其他264器件、原理图／库／规则及全部非审阅铜保持；旧内层过孔接点经显式铜桥与完整焊盘守卫保留，没有直接删掉活接点。

默认R36；两独立完整R26回放、默认入口及historyR35通过，43/43、原生／ERC全零，185地52关键链、439不同本地源用例全覆盖。43位姿、7power／4CIN／4COUT、完整46孔工艺签名和实际SD／USB／时钟参考保持。当前工程候选 `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r36/engineering-candidate`。VREF其余长支路、PMIC开关回路、实际噪声／电气、真实电池全屏／背面高度／含正公差≤7mm、供料CAM／EVT仍待资格；`manufacturing_release=false`。阶段验证完成后按用户指示commit并push功能分支。

# Historical Continuation: E0.2 R35 — 数字电源局部旁路（2026-11-02）

执行者：Codex。先读 [R35 七颗数字旁路、背面地铜与完整源回放](E02-R35-DIGITAL-POWER-BYPASSES-20261102.md)。保留全部旧器件和铜形，新增七颗局部旁路：MCU VDD_SPI的100nF／1µF、Flash的100nF在背面，IMU两电源及两XL9535的100nF在正面；只加八段0.25mm短线、四地孔及一块实际连接MCU地参考的B地铜。原258器件894焊盘／旧铜／身份／库／规则保持，现265器件908焊盘、11602走线1007孔、185地50关键链。

默认R35；两独立完整R26回放、默认入口、历史R34回归及三份独立原生审计通过，43/43、原生／ERC全零，434不同本地源用例全覆盖。42位姿、七组数字旁路、四CIN／四COUT、完整46孔工艺签名及SD／USB／时钟参考保持。SMT／CPL为226件，三颗新电容为Bottom，BT301后装且不入CPL，21项待供料保留。当前工程候选 `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r35/engineering-candidate`。新增背面电容需进入实际高度／净空与正公差≤7mm资格；实际电气、电池全屏、供料／全板CAM／EVT仍待证据，`manufacturing_release=false`。

# Historical Continuation: E0.2 R34 — U403近端输入旁路（2026-11-02）

执行者：Codex。先读 [R34 C536、四组输入旁路与完整源回放](E02-R34-U403-INPUT-BYPASS-20261102.md)。原生检查发现U403标称输入电容C509距IN约28.936mm，最近同网至少1µF电容仍20.472mm；新增同已核SKU的C536，电压盘距IN降至0.971mm。原器件和C509均保留，只加两条0.25F短支路及一颗盘外GND孔。原R33的257器件892焊盘及全部旧铜／身份／库／规则保持，现258器件894焊盘、11594走线1003孔、178地36关键链。

默认R34；两独立完整R26回放、默认入口与历史R33回归均通过，43/43、原生／ERC全零，427不同本地用例全覆盖。四组CIN与四组COUT的实际连接、35位姿、全46孔工艺签名和SD／USB／时钟参考保持。SMT／CPL为219件，BT301后装且不入CPL，21项待供SMT保留。当前工程候选 `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r34/engineering-candidate`。实际电气、供料／全板CAM、电池全屏／含正公差≤7mm及EVT仍待资格化，`manufacturing_release=false`。

# Historical Continuation: E0.2 R33 — 局部旁路与全板孔工艺（2026-11-02）

执行者：Codex。先读 [R33 三处旁路、完整盘中孔工艺与源回放](E02-R33-LOCAL-BYPASS-PROCESS-20261102.md)。保留原负载端电容，新增C533/C534/C535分别为U402/U403/U405的局部1µF输出旁路，加五条0.25F短支路及一颗盘外GND孔；原R32全部254器件886焊盘、旧铜与C532原生身份保持。现257器件892焊盘、11592走线1002孔、177地28关键链。

两独立完整R26回放及默认入口、历史R32回放均通过；43/43、原生／ERC全零、422不同本地用例全覆盖，SD／USB／时钟参考保持。全板原生工艺检查列出46颗焊接接点过孔须填孔盖帽，裸TP8另列、重复TPG2不重复计数；21项待供SMT保持，SMT／CPL为218件且BT301后装。默认R33，当前工程候选 `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r33/engineering-candidate`。四层板的实际工艺／供料／电气／真实电池全屏／含公差≤7mm／EVT仍待资格化，`manufacturing_release=false`。

# Historical Continuation: E0.2 R32 — U404输出局部去耦（2026-11-02）

执行者：Codex。先读 [R32 C532补件、源回放与验证](E02-R32-C532-BYPASS-20261102.md)。补上U404输出端原来缺少的局部1µF电容C532（FH0402X105K100NT/C157353），F50.95/88.4/135°；电压焊盘直接接既有输出走线，只新增两条0.25F接地支路，无新过孔。原253器件884焊盘及全部旧走线／过孔／规则保持，现254器件886焊盘、11587走线1001孔。

默认R32；两独立完整R26回放及默认重建为43/43、原生／ERC全零，174地／22关键链、全部旧组和SD／USB／时钟参考通过，417个不同本地源用例全部覆盖。历史R31入口另行完整回放通过。原理图、本地符号／封装、精确物料与制造资料同步；SMT／CPL为215件，BT301后装且不入CPL，21项待供SMT保持。当前候选 `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r32/engineering-candidate`。真实瞬态／SI、电池与完整屏幕／含正公差≤7mm、背面SMT、供料CAM与EVT仍待证据，`manufacturing_release=false`。

# Historical Continuation: E0.2 R31 — 三处时钟换层接地缝合（2026-11-02）

执行者：Codex。先读 [R31 三孔改动、原生接触与源回放](E02-R31-GROUND-STITCHES-20261102.md)。只新增三颗400/200μm地孔，原11,585条轨形、998旧孔、器件／焊盘／位姿／区域定义／规则保持；现1,001孔。两处CKV、一处XSTL到实际In1/B地孔距离由3.068／2.900／2.315mm降至0.577／1.043／0.577mm；这是几何改善，电气资格仍未证明。

默认R31；两次独立完整回放及默认重建保持43/43、原生／完整ERC全零、173地／20关键链／旧组、SD9104／USB1224及F/In2时钟1657参考点覆盖，407个不同本地源测试覆盖通过。B相邻In2仍有495/633点缺口，背面SMT／实际电池全屏／含正公差≤7mm／供料CAM／实物电气和EVT仍待证据。当前工程候选 `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r31/engineering-candidate`，显式R26–R30及历史包保留，`manufacturing_release=false`。

# Historical Continuation: E0.2 R30 — 顶层时钟局部参考地（2026-11-02）

执行者：Codex。先读 [R30 两孔微移、参考范围及源回放](E02-R30-CLOCK-REFERENCE-20261102.md)。仅微移两颗普通信号孔约0.17mm，保持全部轨形／时钟铜／器件位姿／孔数，消除XSTL顶层的5个In1参考采样缺口。八时钟网的F/In2→In1共1657点零缺失；背面相邻In2的495个缺口另行报告，不当作电气资格通过。

默认R30；两次独立完整回放及默认重建保持43/43、原生/完整ERC全零，173地、20关键链、全部旧组和SDUSB实际参考通过，403个不同本地源测试覆盖通过。当前工程候选 `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r30/engineering-candidate`；R26至R29历史入口和包保持。实物、电气与制造资格仍未关闭，`manufacturing_release=false`。

# Historical Continuation: E0.2 R29 — XSTL源端与下拉支路质量（2026-11-02）

执行者：Codex。先读 [R29 路径变化、取舍与源回放](E02-R29-XSTL-SOURCE-QUALITY-20261102.md)。XSTL 驱动至串阻52.104→5.097mm、下拉支路5.814→1.479mm；两网总铜长86.052→73.777mm，有效主路径也缩短。输出改为65.375mm/9孔，R731移至背面，这些取舍与时序／SMT资格明确保留。

默认源为R29；两次独立完整回放及默认重建保持43/43、原生/完整ERC全零，173地、20关键链、全部旧组、SD18/主USB和实际参考覆盖通过。401个不同本地源测试通过。具名工程候选为 `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r29/engineering-candidate`；显式R26/R27/R28历史回放和旧包保持。电气／真实电池全屏／含正公差≤7mm／背面SMT／供料CAM/EVT尚未资格化，`manufacturing_release=false`。

# Historical Continuation: E0.2 R28 — 43控制网与完整源回放（2026-11-02）

执行者：Codex。先读 [R28 路由、源回放与资格边界](E02-R28-ROUTING-CLOSURE-20261102.md)。43/43 控制网接通；两次独立完整源重建及最终默认入口重建均为 DRC 错误／警告／未连接／一致性／ERC **0/0/0/0/0**，173 地、20 关键链、全部旧连接组和 SD／USB 实际参考覆盖通过。401 个不同本地源测试通过。

默认 `build_pico47_single.py` 为 R28，输入仍是不可变 R26 `v0.1.1`；历史 R26/R27 以 `--revision` 显式重建。具名工程检查点为 `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-r28/engineering-candidate`，生成输出不进入 Git。XSTL 源段52mm/6孔等路由质量、真实时序／电源／阻抗、实际电池和完整屏幕、背面SMT、含正公差≤7mm及CAM/供料/EVT仍未资格化；`manufacturing_release=false`。

# Historical Continuation: E0.2 R27 — 六项布局修订（2026-10-31）

执行者：Codex。先读 [R27 后续电气增补](E02-R27-ELECTRICAL-ANALYSIS-20261031.md)和[R27 布局修订与重建说明](E02-R27-LAYOUT-FIXES-20261031.md)。计入有效过孔段后，D2/D3相对CLK的空间铜长差约为−4.365/−3.235 mm，新增保守空间筛查未通过，电气时序仍待验收。当前工程候选为
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261031-r27/engineering-candidate`，
PCB SHA-256 `94f12df7e05603fcd802378075822178d2e1e048f031a393dc3b349b03da25a8`。

VBUS 等效铜阻降至 0.109231 Ω；晶振下相关顶层数字铜迁出；两组反馈均约 2.925 mm/0 过孔；前光 SW→二极管缩至 2.192 mm；SD 六条平面有效链 46.158–46.921 mm、最大相对 CLK 平面偏差 0.763 mm；USB 主路成对走 B 层，并由原生已铺 In2 地铜覆盖。

两次全新 R26→R27 源回放均得到 DRC 错误/告警/未连接/一致性/ERC **0/0/0/0/0**，173 个地焊盘、20 条关键链及全部原连接组通过。默认 `build_pico47_single.py` 构建 R27；输入仍绑定 `v0.1.1` / R26，新增精确修改数据在 `r25_router/single_r27_layout_delta.json`。`--revision R26` 保留历史回归。归档目录未覆写；当前生成 CAD 和报告在外部目录。

`manufacturing_release=false`。电池/完整屏幕/≤7 mm、供料、散热孔 CAM、实物电源/时序/USB 阻抗与 EVT 的资格边界见 R27 说明，未因零 DRC 而关闭。

---

# Historical Continuation: E0.2 r26 (v0.1.1) — Single Unified 4-Layer PCB Engineering Checkpoint (2026-10-30)

Read [E02-R25-SINGLE-UNIFIED-PCB-20261029.md](E02-R25-SINGLE-UNIFIED-PCB-20261029.md), [MAINLAND-COMPONENT-BOM-AUDIT-20261029.md](MAINLAND-COMPONENT-BOM-AUDIT-20261029.md), and [E02-R25-ROUTING-HANDOFF-20261026.md](E02-R25-ROUTING-HANDOFF-20261026.md).
Versioned in-repository native KiCad release directories:
- [`hardware/pico47/v0.1.1/`](v0.1.1/) (`v0.1.1` / `R26` current release — `Single.kicad_pcb` SHA-256 `31fa221d8a02a7cb00e9bd00a5d6f7907e60b56903269f803973590a1ed2f7b9`)
- [`hardware/pico47/v0.1.0/`](v0.1.0/) (`v0.1.0` / `R25` baseline release — `Single.kicad_pcb` SHA-256 `d14c33f47803453b3f37ecc84f8f5e0d45b33a5ec7150cf18db58259949df6f8`)
Canonical external engineering checkpoint:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261029-r25/engineering-candidate`.

**Single Unified 4-Layer PCB (`Single.kicad_pcb`): 0 opens; DRC errors/warnings/parity/ERC are all ZERO (`manufacturing_release = false` until supplier CAM/supply/stack confirmation).**
- **Zero Mechanical Interference with Full-Size Rectangular Battery Assembly Study**: Upper-left PCB step narrowed from $X = 30.0\text{ mm}$ to **$X = 38.0\text{ mm}$** ($Y = 32.0..83.5\text{ mm}$), providing **$0.0\text{ mm}^2$ XY overlap and $0.0\text{ mm}$ Z overlap** across the full-size **Model 323576** battery assembly study (`BATTERY_PACK` full $35.0 \times 76.0 \times 3.2\text{ mm}$ at $X = 2.0..37.0, Y = 2.0..78.0\text{ mm}$; `BATTERY_SEAL` full $35.8 \times 74.0 \times 0.3\text{ mm}$ at $X = 1.6..37.4, Y = 3.0..77.0\text{ mm}$; `BATTERY_TABS` full $18.0 \times 1.6 \times 0.15\text{ mm}$ at $Y = 77.2..78.8\text{ mm}$; `BATTERY_PCM` full $30.0 \times 3.8 \times 1.3\text{ mm}$ at $X = 4.5..34.5, Y = 78.5..82.3\text{ mm}$; and lateral `BATTERY_WIRE_RED/NTC/BLK` each full $3.7 \times 1.5 \times 1.0\text{ mm}$ at $X = 33.8..37.5, Y = 78.5..83.2\text{ mm}$). `study_only_not_supplier_qualified = true` and `battery_fit_proven = false` remain in effect until the exact replaceable 2050mAh battery supplier drawing is confirmed.
- **Option 1 Upper-Right Structural Support, Poron Cushion, `1511` Speaker & 2.4 GHz FPC Antenna Bay (`upper_right_support_bay`)**: Keeping `Single.kicad_pcb` strictly at $71.0 \times 99.0\text{ mm}$ ($\le 10 \times 10\text{ cm}$ JLCPCB 4L ENIG coupon), the upper-right $35.0 \times 30.0\text{ mm}$ cavity ($X = 38.0..73.0, Y = 2.0..32.0\text{ mm}$) houses a rear-shell cross-rib honeycomb support grid + $Y = 31.2\text{ mm}$ anti-cantilever ledge (`UPPER_RIGHT_RIB_GRID`, $X = 38.5..72.5, Y = 2.5..31.2, Z = 0.55..3.65\text{ mm}$), a $0.30\text{ mm}$ Poron/EVA screen support pad (`UPPER_RIGHT_PORON_PAD`, $X = 39.0..72.0, Y = 3.0..31.0, Z = 3.65..3.95\text{ mm}$, coplanar with the $Z = 3.95\text{ mm}$ battery top surface), a standard $15.0 \times 11.0 \times 2.90\text{ mm}$ sealed micro-speaker box (`SPEAKER_BOX_1511`, $X = 55.5..70.5, Y = 17.5..28.5, Z = 0.75..3.65\text{ mm}$, wired to `J502` `SPK_P/N`), and a $24.0 \times 7.0 \times 0.20\text{ mm}$ 2.4 GHz Wi-Fi/BLE FPC antenna (`FPC_ANTENNA_2G4`, $X = 41.0..65.0, Y = 4.5..11.5, Z = 3.65..3.85\text{ mm}$, wired to `J507` `RF_ANT`) with **$0.0\text{ mm}^2$ XY overlap** against both `Single.kicad_pcb` ($Y \ge 32.0\text{ mm}$) and the `323576` battery assembly ($X \le 37.5\text{ mm}$).
- **Via-in-Pad & Thermal Via Process Accounting**: `C804.2` ground return via moved outside the pad to an external dog-bone location at **`(17.40, 104.80)`** ($0.45/0.20\text{ mm}$ via connected by a $0.30\text{ mm}$ `F.Cu` trace to `C804.2` at `(18.20, 105.00)`), eliminating `C804.2` via-in-pad; `U501.57`'s 9 thermal vias ($0.50/0.25\text{ mm}$) lie inside the exposed-pad solder-mask opening and stencil apertures (`REQUIRED-VIA-IN-PAD.csv`), so `single_board.json` retains `process = "FILLED_AND_COPPER_CAPPED_OR_SUPPLIER_APPROVED_EQUIVALENT"` and `supplier_process_accepted = false` until factory CAM acceptance.
- **100% Chinese Mainland (PRC) Component Provenance & Consignment Manifest**: Verified via `verify_mainland_bom_compliance.py` (`215/215` populated BOM components + `5/5` DNP passives on `Single`, `177/177` + `5/5` on `Core`, `42/42` on `Display`; `0` foreign manufacturers; `0` missing `Manufacturer` or `MPN` fields). Bottom Type-C USB receptacle (`J201` / **`MUP U22401-17`**) positioned at bottom center. `PENDING-SUPPLY.csv` (21 consignment/registration SMT parts) and `REQUIRED-POST-SMT.csv` (`BT301` post-SMT assembly) are exported alongside `BOM_JLCPCB_Single.csv` and `CPL_JLCPCB_Single.csv`.
- **Single-Board Checkpoint, SHA-256-Bound R25 $\rightarrow$ R26 Replay & Pre-Release Gates**: Verified end-to-end via `build_pico47_single.py`, `single_board.json`, and `r25_router/apply_single_r26_x38_eco.py` (which enforces baseline/target SHA-256 and UUID completeness, replays all 51 footprint moves, 27 boundary nets, the $X = 38.0\text{ mm}$ step outline, and the `C804.2` dog-bone via from R25 to R26, and verifies native DRC). Dedicated solid `In1.Cu` GND plane with strictly 0 non-GND signal tracks; all 173 GND pads connected. `manufacturing_release` remains `false` until the 21 pending SMT parts, `BT301` post-SMT assembly, `U501.57` via-in-pad CAM confirmation, and exact 2050mAh battery/screen supplier drawings are confirmed.

---

# Historical continuation: E0.2 r7 — SPV and coordinated panel-control fanout

Read [E02-R7-SPV-CLOSURE-20261014.md](E02-R7-SPV-CLOSURE-20261014.md).
Dated checkpoint:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261014-r7/engineering-candidate`.
The requested `panda47-e0-20261012/engineering-candidate` is its verified copy;
previous r6 is preserved in the sibling pre-r7 archive.

**Core 32 opens; Display 9 opens; DRC errors/warnings/parity/ERC are zero.**
SPV R730.2 -> J601.40 is connected. CKV, XLE and XSTL are independently verified
connected and shorter than before. All 237 ground pads remain reference-connected.
All 9,429 non-control track/via items are unchanged. **41 native unconnected items
remain. NOT FOR FABRICATION OR POWER.** Digital timing, analog/current/return and
physical product qualification have not been granted.

Fresh source replay and independent capture reproduce all four exact control
states, counts and original pad groups. Use `build_pico47.py --routing-checkpoint`
and `capture_pico47_checkpoint.py --require-complete-ground`. The standalone
inspector generates netlists in its candidate directory: use fresh copies for
such inspection and do not mutate published manifests.

Native CAD/reports/manifests remain external or ignored. The old sections below
are historical background, not the current route or manufacturing approval.

# Panda47 E0 — parallel-display redesign checkpoint

Date: 2026-10-12. Status: **INCOMPLETE ENGINEERING DESIGN — DO NOT ORDER OR POWER**.

This is the user-authorized successor to Product D, not a relabelled SPI board.
The confirmed target is the Panda Standard 4.7-inch E0470A01 family: 4.7 inch, 1216 × 684,
approximately 297 PPI, raw 16-bit parallel display, plus a replaceable
2050 mAh LCO battery pack. The old 4.26-inch SPI module and 1100 mAh cell are not
accepted substitutes. Matching mAh alone does not identify the battery pack.

## Non-negotiable requirements and current limitations

Retain two physical PCBs, mainland component identities, 16 MB Flash, 8 MB PSRAM,
touch, frontlight, audio, IMU, microSD, RTC backup and the direct GPIO2 inhibit.
USB-C remains bottom-centre; microSD remains near the lower right corner.
Whole-device maximum thickness remains **7 mm including positive tolerances**.

The 75 × 132 × 6.8 mm coordinates in `design.json` are a temporary electrical
layout study, NOT a frozen enclosure or proof of battery/frontlight fit. Both
engineering PCB candidates currently use four copper layers and 0.8 mm nominal
board thickness. In1 is reserved for the GND reference, not signal routing.

The public reference specification does not establish the battery manufacturer/MPN,
complete maximum dimensions, protection topology, connector polarity, NTC or
charge termination voltage. These remain null in the source contract. Do not
invent them or treat the legacy two-pad bench landing as the production battery connector.
Charging is not authorized. The exact full panel suffix, touch/frontlight stack,
BORDER behaviour, folded FPC/contact side and per-panel VCOM remain unqualified.

## Implemented electrical changes

The new native Core and Display schematics, PCB pad nets and local libraries
contain the complete 40-pin E0470A01 family map and a new 40P + 20P board link.
This link is **not pin-compatible with Product D**. All 33 available MCU GPIO are
allocated; pins reserved for octal PSRAM remain unused externally. The bare-QFN
mapping is independently checked: physical pin 36 is GPIO48 and pin 37 is GPIO47.
USB19/20, GPIO2 inhibit, the existing I2C bus and independent I2S audio are retained.

Two SGM330A-YTS/TR switches share eight GPIO between the parallel display and
four-bit SD/UART. SD/UART transfers and display scans are mutually exclusive.
Firmware must stop the current peripheral, disable both switches, change selection,
configure the new peripheral, then reconnect; reset selects SD/UART. The mux's
analogue bandwidth is not evidence of qualified 3.3 V digital timing. Buffered
reading and audio interaction still need target firmware and bench tests.

Display power uses a SY7636ARMC engineering circuit. Its exposed pad is a negative
reference and **must not be grounded**. The 25 V reference VGH example is not the
selected panel's 22 V target. The old manufacturer PDF is not current supplier
approval; NC/EP interpretation, sequencing, VCOM and power-stage margins require
explicit qualification before energizing a panel.

GPIO2 now reaches the PMIC EN through R813 (1 kΩ), with a 100 kΩ pull-down. U811 P00
is input-only and monitors EN; it must not drive it. This removes an I2C-expander
write from the physical EN-low path. It does not claim to detect a CPU frozen with
GPIO2 held high, and the incomplete routing is not evidence of working hardware.

L801/L802 use Sunlord MWSA0618S-4R7MT / C408421, with actual larger lands rather
than reusing the old 3 mm geometry. The manufacturer drawing gives 1.8 mm maximum
height and 7.3 × 6.8 mm maximum body. The source retains the manufacturer's
Max./Typ. current headings (Isat 4/5 A; heat-rating 3.5/4 A); these are not relabelled
as guaranteed minima. Hot start-up/fault margins and the rectifier remain open.

Selected GND pads now have explicit solid plane connections and real GND stitching
vias. Clearances, hole limits, minimum spokes, ERC severities and exclusions are
not relaxed. Display via drills are at least 0.30 mm; the chosen stitching via is
0.65/0.30 mm. Stencil/reflow heat balance remains a manufacturing qualification,
not something a successful DRC can certify.

## Source and verification tools

`build_pico47.py` builds a new candidate from a native-clean, sourcing-bound D
checkpoint. It never overwrites the donor and reports real DRC/open/parity/ERC
counts. Old disconnected copper is not relabelled onto the new signals.

`pico47_contract.py` and `test_pico47_contract.py` enforce pin allocations, required
features, exact known identities and explicitly unknown supplier properties.
`verify_pico47_native.py` independently exports fresh schematic netlists and checks
33 GPIO, 40 panel contacts, 60 interboard contacts, eight mux channels, 518 retained
Core pad functions, PMIC EP and direct-enable connectivity, actual inductor lands,
and unchanged native design rules. These are electrical-intent checks, not proof
that every trace is connected or that a sample works.

`import_pico47_route.py` imports SES **copper only**, retains native component/pad/
outline intent and reruns native checks. Router completion never grants release.
A trial with smaller router clearances was rejected after native DRC; it is not
adopted and did not change the actual project rules.

`split_pico47_junctions.py` splits existing segments at real same-net junctions.
`prune_pico47_stubs.py` removes only native-reported dead ends and validates all
originally connected pad groups after each trial. A split of a live pad group or
increase in native errors restores that trial. Connectivity snapshots use isolated
KiCad Python processes to avoid repeated-SWIG-wrapper lifetime faults. Fewer
airwires after deleting an orphan are not described as newly routed connections.
`test_pico47_connectivity.py` tests this acceptance logic independently.

## Rebuild and inspect

```sh
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
python3 hardware/pico47/test_pico47_contract.py
python3 hardware/pico47/test_pico47_connectivity.py
"$KPY" hardware/pico47/build_pico47.py \
  --donor /absolute/path/to/verified/sourced-D-candidate \
  --output /absolute/fresh/ignored-or-external/E0-candidate
"$KPY" hardware/pico47/verify_pico47_native.py \
  --candidate /absolute/path/to/E0-candidate \
  --donor /absolute/path/to/verified/sourced-D-candidate \
  --output /absolute/fresh/ignored-or-external/native-check.json
```

Use the current continuation candidate recorded below, not whichever `.work`
directory has the newest mtime. The old `build_seven_mm_product.py` remains a
reversible Product-D regression, not the requested new display design.
Generated native files, SES/DSN, trial snapshots, PDFs, logs, renders and packages
remain outside Git. The existing unrelated `packaging/` is untouched.

## Primary references

- Reference 4.7-inch hardware specification: https://dot.mindreset.tech/docs/read_0
- E0470A01-AF-S manufacturer specification mirror (not proof of the full panel suffix): https://raw.githubusercontent.com/exomind-team/openepd-47/main/materials/vendor/display/E0470A01-AF-S-specification.pdf
- Espressif package pins: https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf
- GPIO API: https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/gpio.html
- SGM330A primary datasheet: https://www.sg-micro.com/rect/assets/7d4de883-c52b-4322-b0a1-24add89dc52c/SGM330A.pdf
- Silergy exact product: https://www.silergy.com/zh/productsview/sy7636armc
- Sunlord original series drawing, pp3/10: https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/2905/MWSA-S_Series_DS.pdf
- KiCad connectivity clusters: https://docs.kicad.org/doxygen/connectivity__data_8cpp_source.html

## Historical E0.1 candidate and native results — superseded by E02-HANDOFF

Canonical external review candidate:
`/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e0-20261012/engineering-candidate/`.
Its `CURRENT-STATUS.json`, native reports and `INDEPENDENT-CHECK.json` bind the
actual files; it is not a manufacturing package. Working ancestry is
`.work/pico47-close-20261012/integration-e06/`. Preserve these when cleaning .work.

Final fresh refill/all-severity/all-track-error/schematic-parity DRC and ERC:

| Board | DRC errors | DRC warnings | Unconnected items | Parity | ERC |
|---|---:|---:|---:|---:|---:|
| Core | 0 | 1 | 161 | 0 | 0 |
| Display | 0 | 4 | 49 | 0 | 0 |

The warnings are remaining copper end/via connection work, not waived checks.
The display routing stage reduced its native unconnected count from104 to49.
Core dead-end cleanup retained all354 original native pad-connectivity groups;
its lower airwire count includes removed orphan islands, not new routed signals.
A native guard restored trials that would split live connections.
58 E0 contract/connectivity tests and71 legacy sourcing/routing tests passed.

Next work: complete the new GPIO/mux/FFC routes and remaining Display nets,
then validate full path timing, power loops, thermal/ripple margins and bus handover.
In parallel obtain exact battery pack and complete panel assembly drawings before
freezing final geometry. No battery procurement or manufacturer acceptance was
created by these source changes. Manufacturing release remains false.
