# PMIC 连续铜与参考地检查

2026-11-02，执行者：Codex。本检查器源阶段以 [R37](E02-R37-VREF-TREE-20261102.md) 为 PCB 基线，检查器提交为 `0826d8f`；本节的早期联合原型未采用。后续 [R38](E02-R38-PMIC-JOINT-LAYOUT-20261102.md) 已完成联合重布并在构建入口启用本检查，当前工程候选与取舍以 R38 说明为准。

审查发现，仅凭 DRC 全零和参考线下方有同名 GND，无法证明噪声源与参考线之间的地铜连续。原 R37 的 R803.2 与 VEE_DRV 内层铜投影距离约 0.063 mm。重布原型虽做到 DRC 错误／告警／未连接／原理图一致性全零，连续铜检查仍发现两处未满足地铜裕量的走廊，因此保留原型的拒绝结论。

新增 `build_pico47_single.inspect_pmic_analog_shield(board, contract)` 读取 KiCad 已填铜的原生板。它先合并同网、同层的连续走线，再检查敏感铜与开关铜投影；切分同一走线不改变判定。近邻区域只有在顶层噪声铜与 In2／B 层 VREF 走线之间，才允许使用实际连接到 U501.57 的 In1 地铜作为隔离条件。地铜必须覆盖源侧、接收侧及两者连接凸包的完整裕量；同层、敏感过孔、噪声过孔及电感庭院均不使用该例外。

[ADI AN-136](https://www.analog.com/en/resources/app-notes/an-136.html)建议用中间地层隔离功率层与敏感信号层；[ADI 电感布局指导](https://www.analog.com/en/resources/analog-dialogue/raqs/raq-issue-164.html)同时要求敏感线避开电感下方。这里的 0.5 mm 投影预算、两侧 0.2 mm 地铜裕量和 2 µm 多边形数值容差均为项目检查参数，属于几何筛查。通过后 `actual_noise_and_stability_qualified` 仍为 `false`，真实波形、噪声及稳定性需要另行验证。

调用前须完成原生填铜。完整配置示例：

```python
contract = {
    'reference_net': 'P47_VREF',
    'sensitive_nets': ['P47_VREF', 'P47_VEE_FB', 'P47_VGH_FB'],
    'noise_nets': ['P47_VP_LX', 'P47_VN_LX', 'P47_VGH_DRV',
                   'P47_VEE_DRV', 'P47_PUMP_POS', 'P47_PUMP_NEG'],
    'inductor_refs': ['L801', 'L802'],
    'clearance_mm': 0.5,
    'ground_margin_mm': 0.2,
    'shape_tolerance_um': 2,
}
result = inspect_pmic_analog_shield(board, contract)
```

后续修订可在 `inspection_overrides.pmic_analog_shield` 中启用该契约；构建器会在原生检查阶段执行。R37 保留其原有构建入口和已知模拟资格边界。实现复用 KiCad 的原生多边形、偏移、裁切和实际地连接检查，未增加 Python 依赖或改变原生 DRC 规则。

九个新增用例覆盖完整地层、走廊孔洞、孤立同名地铜、同层敏感线、同侧内层噪声、敏感通孔、电感庭院、参数减弱及等价铜分段。分段用例先复现了逐原语检查产生 164 对结果的问题，再验证合并后的等价铜只有一对连续铜检查，地洞仍被拒绝。**452 个不同本地源用例**互补通过：geometry 396 pass／56 native skip，KiCad 433 pass／19 geometry skip，旧 443 IDs 保留，全部跳过均由另一环境覆盖。没有使用 CI。

最终源另行完整重建默认 R37，DRC 错误／告警／未连接／一致性／ERC 仍为 0/0/0/0/0，185 地焊盘、52 关键链和完整 46 孔工艺保持。该回归验证新增检查代码对历史入口的兼容性；当前 R37 的模拟噪声仍未资格化。

紧凑审查证据位于 `/Users/isaac/workspace/AI/panda-board-deliverables/panda47-e02-20261102-pmic-shield-audit`。其中保存被拒绝原型的源绑定差异、原生与独立几何结果及测试记录。诊断差异从不可变 R37 在内存回放后，铜与位姿语义指纹相同；新铜 UUID 由 KiCad 分配，重建 PCB 的逐字 SHA 可不同。完整中间 CAD 与回归副本在核验后清理，已接受的 R37 和历史封存保持。

后续布局继续处理短换流路径、分压区域及局部 PGND2 返回。真实 PMIC 版本／EP 澄清、噪声稳定性／DC bias／功率波形／SI／USB、真实 2050 mAh 电池与完整 E0470A01 包络、背面高度／含正公差≤7 mm、供料／全板 CAM／EVT 仍待证据；`manufacturing_release=false`。
