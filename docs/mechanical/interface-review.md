# routing141 接口位置与坐标核对

2026-09-27，Codex 子代理 `interface_audit`。本记录只读核对 routing141 PCB 与当前产品展示场景；不修改 PCB、`build_assembly.py` 或已生成的场景。

## 结论

外壳开孔必须以 routing141 的 footprint 图形、焊盘和实际器件插入方向为基准。当前 `board-scene.json` 对 J201、J301、J501、SW201、SW202 使用的是“焊盘凸包 + 名义高度”包络；这些包络不是连接器或按键的外形，也不能直接作为外壳开孔边界。J302、J502、J802 使用 KiCad 原生 GLB 模型，位置变换本身没有发现重复平移。

当前渲染脚本的坐标契约如下：

```text
KiCad native PCB [x, y, z] -> assembly [x + 2, y + 2, z + 1]
resolved GLB: KiCad [X, Z, Y] metres -> assembly [1000X + 2, 1000Y + 2, 1000Z + 1] mm
Blender/HTML display: assembly [x, y, z] -> display [(x - 37), (66 - y), z]
```

GLB 器件在 `build_assembly.py` 中已按 `source_level=native_library_model_mpn_unqualified` 跳过二次 `[+2,+2]`；名义包络、板框、铜和焊盘才追加一次 `[+2,+2]`。因此不要再给 GLB 项追加装配偏移。Blender 的 Y 反向与三角面序反转是坐标系镜像补偿；HTML 应保持同一规则，爆炸向量的 Y 也应反号。

当前场景可见几何的包围盒中心是 `[36.875,66,3.4]`，而 Blender 使用产品契约中心 `[37,66]` 且不减去 Z。差异来自 KEY_CAP 向左伸出 `x=-0.25`，以及 HTML 为了居中而减去 Z 中心。若要求 HTML 与 Blender 的端口坐标逐点严格相等，HTML 应使用 `scene.source_center_xy_mm` 的 `[37,66]` 做 XY 基准，并把 Z datum 约定写清；仅做产品展示时，当前额外的整体平移不会改变接口相对位置，但不能把它称为完全相同的坐标变换。

## 连接器和按键事实

| 参考 | routing141 native 位置/角度 | assembly 锚点/边界 | 真实接触或插入方向 | 外壳处理 |
|---|---|---|---|---|
| J201 USB-C | `(13.00,128.00)`, `0°`；USB pad row 在 `y=121.23`；footprint Edge.Cuts 局部 `x=±4.62, y=0…-6.6` | 中心 `(15.00,130.00)`；PCB 开窗 assembly `x=10.38…19.62`，位于底边 `y=130` | 外壳开口朝 native/assembly `+Y`；USB 插头插入运动朝 `-Y` | 外部接口，开孔中心线约 `(x=15, y=132)`；宽度/深度须由 USB4500 供应商 STEP 和装配公差确定。 |
| SW201 电源键 | `(2.30,6.75)`, `-90°`；pad nets `KEY_POWER_MCU/GND` | assembly 中心 `(4.30,8.75)`；footprint bbox assembly `x=2.05…6.35, y=5.975…11.525` | Alps `SKSCLCE010` 是 side-push；执行件外向左侧 `-X`，用户按压运动朝 `+X` 入板 | 与 SW202 共用一个外部 rocker/按键机构；左长边按键中心线分别在 `y=8.75` 和 `15.25`，不能把它们画成 USB 类独立端口。 |
| SW202 电源/唤醒键 | `(2.30,13.25)`, `-90°`；pad nets `BQ_QON/GND` | assembly 中心 `(4.30,15.25)`；footprint bbox assembly `x=2.05…6.35, y=12.475…18.025` | 同 SW201，执行件外向 `-X`，用户按压朝 `+X` | 与 SW201 共享 KEY_CAP/KEY_ROCKER 的连续外部执行件；保留两个电触点中心。 |
| J501 microSD | `(62.50,18.75)`, `90°`；pad row local `y=-5.45`；F.Fab card envelope extends to local `y=-9.7` | footprint/model envelope assembly `x≈54.75…71.075, y=13.885…27.615`；socket center assembly `x=64.5` | Molex SD-104031-001 top view/card-entry drawing places the card/front on the side represented by the local negative-Y card envelope. KiCad `+90°` maps local `-Y` to native/assembly `-X`; card moves into the socket in the opposite `+X` direction. The entry is therefore inboard around assembly `x≈54.8…58.8`, not at an outer case edge. | **当前 PCB floorplan 没有形成可从外壳直接插卡的通道。不能在 `x=74` 右侧或 `x=0` 左侧伪造开槽；必须先重排 PCB/机构并关闭卡片扫掠、元件干涉和壳体可达性。** |
| J301 电池连接器 | `(49.75,23.00)`, `0°`；两个 BAT_CONN_P/GND pads 在 `y=20.79` | assembly 中心 `(51.75,25.00)`；footprint bbox assembly `x=49.025…54.475, y=22.175…27.725` | 当前自定义 DF58 STEP 未解析；footprint 只能证明 pads 在 local `y=-2.21`，不能单独证明 mating-face 朝向。最终方向必须以 Hirose 供应商 STEP/装配图冻结 | 电池内部线束连接器；不应开成外壳外部充电口。 |
| J302 NTC 连接器 | `(49.25,16.50)`, `90°`；pads native `x=47.25, y=17.5/16.5/15.5` | 原生 GLB 模型 assembly bounds `x=48.775…53.725, y=16…21` | JST SH side-entry 的接触/插入面在 local `-Y`，经 KiCad `+90°` 后朝 native/assembly `-X`；由 local pad row `y=-2` 的世界结果 `x=47.25` 可验证 local `+Y` 的相反方向为 native `+X`（线束退出侧）。模型已按原生变换读入 | 电池 NTC 内部连接器；仅保留内部线束/插拔空间，不开外壳孔。 |
| J502 扬声器连接器 | `(9.00,13.50)`, `0°`；SPK_P/SPK_N pads native `y=11.5` | 原生 GLB 模型 assembly bounds `x=9…13, y=13.025…17.975` | JST SH side-entry 接触/插入面 local `-Y`，assembly `-Y`；线束退出侧为 `+Y`，模型与 footprint center 对齐 | 扬声器内部线束连接器；不应画成外部充电/数据接口。 |
| J503 调试座 | `(17.00,7.00)`, B.Cu；`exclude_from_bom=true` | assembly nominal pad envelope，`physical=false` | 调试 pogo/TC2030 触点在板背面 | 不属于量产外壳外部接口，不应作为产品端口渲染。 |

## 对当前场景的直接影响

- `board-scene.json` 有 209 个板级对象；接口修复不能移动或重布 PCB、铜、焊盘和 footprint 锚点。若为 J201/J301/J501/SW201/SW202 补充有依据的真实 3D 包络，允许仅替换对应 component proxy 的 `vertices/indices`，并保持其 native footprint/pad/copper 坐标、`explode`、`assembly_role` 和 routing141 PCB hash 不变。
- `board-scene.json` 的 model coverage 明确报告 J201、J301、J501 无法从当前 checkpoint 解析 3D 模型；它们现在的 `source_level` 是 `nominal_envelope_height_unknown`。这解释了 USB、microSD 和 DF58 外形/朝向看起来不对：包络来自焊盘凸包，不是器件实体。
- J302/J502/J802 的原生 GLB 模型已经各自以 `[+2,+2,+1]` 进入 assembly；它们不能再重复平移。J302/J502 当前模型中心分别落在 assembly `(51.25,18.5)`、`(11,15.5)`，即各自 native footprint 锚点加 `[2,2]`。
- USB 的外壳开孔应以器件供应商模型的接触面、止挡面和板边距离冻结。J501 当前入口朝板内且没有外壳可达通道；不能用右侧或左侧展示孔掩盖 floorplan 阻塞，必须先完成 PCB/机构重排。

## 验收建议

1. 将 J201 和按键方向作为硬断言：J201 → bottom `+Y`（插入 `-Y`）；SW201/SW202 → left `-X`（按压 `+X`）。J501 仅记录为 inboard entry `-X` / card motion `+X`，不生成外壳 opening，直到可达性和扫掠资格关闭。
2. 将 J301/J302/J502/J802 标记为内部连接器，检查壳体实体与插拔包络不相交，但不要生成外部孔。
3. 生成 HTML 和 Blender 后，以同一 assembly 坐标抽取端口锚点；HTML 与 Blender 的 `x`、`66-y`、`z` 结果应逐点相等，只有显示坐标系的 Y 反向和三角面序反转允许存在。
4. 对修复前后的 209 个板级对象做结构化比较：routing141 PCB hash、PCB/铜/焊盘/native footprint 锚点、`explode` 和 `assembly_role` 必须保持；只有 J201/J301/J501/SW201/SW202 这类无原生模型对象，才允许在有 footprint/供应商证据时替换 component proxy 的 `vertices/indices`。

## 当前后壳三角网格截面复核

对当前 `build_assembly.py` 临时重建的 `REAR` 网格做了平面三角面并集与射线点测试（没有修改 PCB）：

- routing141 USB 的 +Y 外壳边是 assembly `y=132`。外表面面积 `318.927372 mm²`，完整圆角边墙基准面积 `361.6 mm²`，差值正好是 USB 开口 `[x=10.038067…19.961934, z=0.6…4.9]` 的面积；`(x=15,z=2)` 在 `y=132` 外表面和 `y=131.4` 内表面均无墙，`y=0` 对应面仍有墙。
- 左侧 `x=0` 外表面面积 `661.74 mm²`，在 `(y=12,z=2)` 无墙、`(y=30,z=2)` 有墙；旧 microSD 左孔 `y=22.2…37` 已封闭，新共用按键孔 `y=6.7…17.3` 保留。
- 当前临时 scene 的右侧 `x=74` 外表面面积 `645.575 mm²`，在 `(y=20,z=2)` 无墙、`(y=40,z=2)` 有墙；这证明右孔网格确实被打通，但依据 J501 原图/footprint 方向，**这是错误侧的开孔**。也不能把它迁移到左侧 `x=0`：J501 入口约在 assembly `x=54.8…58.8`，中间隔着 PCB 和器件，当前外壳可达性未闭合。正确展示应移除假右孔、保留两侧壳体，并在审计中标记 microSD 机构阻塞。
- 三个外侧墙面的外表面各为一个连通平面并集，面积与分段矩形解析值一致，当前截面没有发现重复矩形曲面。`FRONT` 的四周薄边仍是 `z=5.7…6.8` 的完整框边，而 USB/按键/SD 开口最高分别到 `z=4.9/3.8/4.1`，不会重新封住后壳侧孔。
- 同一 routing141 PCB 连续两次调用 KiCad `GetBoardPolygonOutlines` 时，`PCB_FRAME` 的 228 个顶点/三角顺序会出现最多 `0.001 mm` 的原生轮廓量化差异；其余 208 个板级对象的 `vertices/indices/explode/assembly_role` 保持一致。板级不变验收应以 routing141 PCB SHA、原生轮廓几何容差和其余对象指纹为准，不能把 KiCad 轮廓枚举顺序的 1 µm 抖动误判为接口移动。

代码里的 `bottom` 审计名称现在明确代表 routing141 的 +Y 外壳边（`y=132`），`top` 代表 `y=0`；这是为了与 `outward_normal=+Y` 保持一致。验收应按实际 `y=132` 三角截面判断，不按屏幕“上/下”标签猜测。

J501 方向依据：Molex 原图 [SD-104031-001 / 1040310811](https://cdn.hackaday.io/files/1649347056536256/molex-memory-connectors-pc-card-sockets-1040310811-sd.pdf) 的 card-entry/front 视图，以及 KiCad 官方 footprint 的 F.Fab card envelope `y=-5.7…-9.7`、contact row `y=-5.45`。在 routing141 的 `90°` footprint 中，pad row 的世界位置从 local `y=-5.45` 变为 native `x=57.05`（中心 `x=62.5` 左侧），因此 local `-Y` 的入口映射为 native `-X`；该入口仍位于板内约 assembly `x=54.8…58.8`，不能直接等同于左侧外壳开口。
