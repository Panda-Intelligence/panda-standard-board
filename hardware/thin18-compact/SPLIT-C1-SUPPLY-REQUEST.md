# Split-C1 精确供料与 CAM 询价入口

本轮以 `develop` 的已完成双板原生设计为准。系统 BOM 共162个位号；Core125（123SMT+C301后装+TH301板外），Display37SMT。所有厂家身份已核对为国产；这不是库存、装配接收或整机所有零件产地认证。

## 当前缺口，不再沿用旧的“七个位号都缺码”结论

| 位号 | 精确订货型号 | 每套数量 | 精确贴片码 | 待关闭事项 |
|---|---|---:|---|---|
| U402–U405 | SGMICRO SGM2578SDYG/TR | 4 | 待分配 | 精确映射、授权供料、批次和装配接收 |
| U902 | SGMICRO SGM62125AXG/TR | 1 | 待分配 | 精确A版本/WLCSP15映射、授权供料和接收 |
| U905 | SGMICRO SGM37601YTRL20G/TR | 1 | 待分配 | 精确20脚型号映射、MSL2包装和接收；禁止24脚代用 |
| U906 | SGMICRO SGM809B-TXN3LG/TR | 1 | **C699619** | 映射已核实；实际库存、分配与收货尚未证明 |
| D202 | SGMICRO SGM05HU1ALXUGY2G/TR | 1 | C55274065 | 实际供料与精确批次接收 |
| C301 | KAMCAP SE-5R5-D105VYH3C | 1 | C2894294 | 客户独立采购、PCBA回板后手焊；不进入SMT CPL |

缺精确映射的是 **6个位号／3个型号组**。原先追踪的7个SMT客供位号仍需要真实接收凭证，U906不会因为查到C码就自动标为已供料。

U906的厂家、精确后缀与SOT-23封装，已与JLC官方目录核对：
https://jlcpcb.com/partdetail/SGMICRO-SGM809B_TXN3LGTR/C699619
原厂精确型号和MSL1见 https://www.sg-micro.com/product/SGM809B 。
本次已将C699619同步到原理图、PCB、重建器和独立校验，不改变任何接脚、阈值或封装几何。

其余三组精确型号仍列在原厂产品页。没有精确公开C码结果，不代表停产或所有渠道无货：
https://www.sg-micro.com/product/SGM62125
https://www.sg-micro.com/product/SGM37601
https://www.sg-micro.com/product/SGM2578SD

## CAM / 装配必须回复

使用最新生成包，不使用旧13处焊盘内孔的坐标表。本轮已移出9处，当前剩余4处仍需树脂填孔、研平、盖铜；以实际 `VIA-IN-PAD.csv` 为准。不能以普通盖油代替，也不能堵住元件PTH、USB壳脚槽或C301的1.9mm引脚圆孔。

确认两板0.8mm、ENIG、绿色阻焊；Core四层铜均为名义35µm，不能默认降为内层0.5oz。确认细间距WLCSP、0.20/0.25mm过孔、钢网/EP锡膏量、底面旋转角及单板CPL坐标。供应商不得自行改线宽、镜像或缩放。

索取精确型号、封装、批次、原厂包装、MSL状态、切带/头尾、损耗和最低上机量；以真实入库量和接收号关闭，不用报价或公开库存替代。每套数量为U902=N、U905=N、U906=N、SGM2578SD=4N；打样套数尚未指定，不擅自下单。

## 生成可提交的询价资料

先运行完整验证，再运行：

```sh
python3 hardware/thin18-compact/release_split_c1.py --target split-c1
python3 hardware/thin18-compact/prepare_split_c1_rfq.py --output /absolute/external/output
```

有明确套数后可加 `--sets N`。输出包含已验证打样包、逐组精确料号、CAM和供料问题清单；仅生成资料，不发信、不预留、不下单。官方LCSC联络页 https://www.lcsc.com/service/question 列出元件询价 `quote@lcsc.com`、PCBA `pcba@lcsc.com`。由用户选定加工路线后提交并保存真实回复。

C301保留20mm脚距、极性及独立后装；首板仍须确认插入、剪脚、0.8mm板手焊工艺与24小时RTC保持。完整机壳目前只提供22mm的装配验证原型，不是7mm成品，不能把渲染图或几何检查当作实物合格证明。
