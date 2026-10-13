# 7mm product RTC override — 2026-10-06

The old rechargeable-supercapacitor policy below is historical for Split-C1 and MUST NOT be used on the <=7mm product. The current 7mm candidate uses a mainland CR1216 primary cell as BT301 and a hardware BAT54WS series Schottky (D306) with **anode at RTC_CELL_P and cathode at RTC_VBACKUP**. The diode is oriented to supply SD3078 VBAT and oppose reverse current toward the primary cell. This static orientation is NOT a verified zero-charge barrier: worst-case reverse current, temperature, all alternative paths and the cell maker acceptance limit remain unqualified. The primary cell is a manual pre-welded insulated lead/tab assembly; it is never reflowed or directly soldered.

For the 7mm product, SD3078 register 18H charging must remain **disabled** on every boot and after recovery. Firmware must read back the charge-enable bit as zero; it must never write the historical `0x82` charge-enable setting. Do not rely on the diode alone as proof that primary-cell charging is safe. Firmware charge-disable/readback remains mandatory and physical reverse-current qualification is still open. 24h isolated retention, diode drop/leakage over temperature, end-node >=2.3V, reverse-feed paths, actual cell lot/tabs and physical fit remain EVT gates.

The exact source-bound contract is `seven_mm_rtc_contract.json`; `verify_seven_mm_rtc.py` checks native candidate topology and identity.

---

# SD3078 原型固件接口契约
2026-10-02。此文件是原理图迁移契约；本仓库没有产品固件工程，驱动集成／运行测试尚未执行。依据SD3078 Rev4.4；禁止继续使用RV3028寄存器或清零时间作为普通启动行为。

| 项目 | 要求 |
|---|---|
| 总线 | 7位0x32，3.3V时100kHz；共享总线不得以400kHz访问RTC |
| 时间 | 00H..06H BCD；写入全部7字节，不能独立改某一字节；小时bit7=1选24小时，读取屏蔽模式位 |
| 写保护 | 先读改写10H bit7 WRTC1=1，再0FH bit7/bit2 WRTC3/WRTC2=1；操作后先清0FH bit7/bit2，再清10H bit7 |
| 备援充电 | 每次主电上电，解锁后写18H=82H并读回；ENCH=1，Charge[1:0]=10选2kΩ。仅本版1F可充电电容；不允许原电池 |
| 备援耗电 | 保持BATIIC=0，FOBAT=0；禁止无需求的备援I²C、32k输出和频率／倒计时中断；F32K无连接 |
| 中断 | INT接共享EXP_INT，保持开漏；读出并处理各芯片的中断源，不能按单器件专用推挽线使用 |
| 初始状态 | 清标志前保存RTCF/OSF/BLF及时间快照，BCD/日期及时间有效性都检查；时间无效明确通知上层 |
| 警报 | 07H..0DH报警数据、0EH匹配允许，10H中断源选择；保留保护位并按原厂清中断语义操作 |
| 电源恢复 | 不因普通主电复位覆盖RTC时间；首次／停振才校时。重新设置充电并读回，失败记录错误 |
| 冷热／断电 | 不在VBAT模式读总线当作验证；恢复主电后读时间／标志并与独立时基比较 |

所有寄存器写入均需读回关键设置。状态位有特定清除语义，不能用随意的整字节常数覆盖0FH；用原厂掩码及本地驱动测试证明不会丢失状态／锁死写权限。共享INT如何唤醒整机需要结合断开主电后的电源架构验证；本版FOBAT=0仅保障走时，不承诺断电后RTC报警唤醒主系统。

首板Q14：受控预充并实测VBAT≥3.15V；移除USB／主电池／调试供电，排除SCL/SDA/INT反灌；记录温度、源状态、备援节点总电流≤2µA目标、时长≥24h和末端≥2.3V；恢复后有效时间连续、无新停振／电量告警。仪表负载与电压取样漏电纳入预算。批准常温／冷／热／寿命条件分别记录，不能用常温结果代替全部条件。全部结果目前NOT_RUN。
