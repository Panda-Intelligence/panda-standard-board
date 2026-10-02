# Split-C1 RTC and backup domestic redesign

Date: 2026-10-02. No physical board exists. U302 and C301 remain foreign in current CAD and block the all-domestic order; there is no retention exception. The user has confirmed **at least 24 hours of RTC backup retention after the main supply is removed**. This is an RTC requirement, separate from reading runtime and the X4 Pro battery-capacity reference.

The newly retrieved manufacturer [SD3900 Rev2.4](https://www.whwave.com.cn/filedownload/3021773), linked by the [official product](https://www.whwave.com.cn/SD3078), is a credible integrated-crystal candidate. PDF SHA256: `ee59dba774d8854f2a4e7e6a41478d3ec6347a0551ade33635bdbb8c4df4cc8a`.

| Item | SD3900 design implication |
|---|---|
| Package | 10-pad3225, maximum0.78mm height; not the native8-pad RV3028 footprint |
| Pins, top view | 1NC,2VDD,3VBAT,4FREQ,5SCL,6NC,7SDA,8NC,9GND,10INT |
| Supply | VDD2.7..5.5V; VBAT1.8..3.6V |
| Backup draw |0.8uA typical at3V; maximum not supplied, roughly18x the original45nA typical |
| Bus |7-bit0x32; use100kHz at3.3V,400kHz only specified at4.5..5.5V |
| Firmware |New BCD/register driver, protection bits, oscillator/power-loss and alarm handling; not RV3028 register compatible |
| Order grade |Ambient±3.8ppm vs full-temperature±5ppm variants share the printed SD3900 name; exact grade must be specified |

A nominal11mF capacitor dropping3.3→1.8V would supply only5.7h at0.8uA, even before capacitor leakage, tolerance, temperature and other backup-node loads. Keeping above the2.2V warning reduces this illustrative estimate to4.2h. The current capacitor cannot be carried into SD3900 as a24h backup design.

Repository evidence resolves the unused-pin question: `docs/design/key-calculations.md`, `schematic-spec.md` and `layout-constraints.md` explicitly call EVI unused. The current native netlist contains only U302.8 and R303.2 on `RTC_EVI`; R303.1 connects to `3V3_AON`. There is no external event requirement. A reviewed SD3900 ECO may remove R303 and its orphan EVI net. CLKOUT is also unused. INT must retain the existing open-drain `EXP_INT`/GPIO4 shared interrupt contract. R304 is a **10k no-backup shunt marked DNP**, not an installed backup load; it must remain absent in any populated backup assembly.

The capacitor planning equation is `t = C_effective * (V_start - V_end) / (I_RTC + I_cap_leak + I_other)`. Use minimum effective capacitance, minimum charged voltage, and reviewed load/leakage limits. With3.3→2.2V and an80mF minimum (100mF at−20%), the total current budget for24h is only1.019uA. SD3900's0.8uA **typical** leaves0.219uA for every other load and no allowance for its unpublished maximum. This does not establish compliance.

Charging register18H resets to0. Do not copy the rechargeable-cell82H recommendation before selecting a qualified backup source. Primary cells must never be charged. VBAT/no-charge operation, permitted charge voltage/current, leakage and cold/hot corners need a reviewed circuit and fail-closed firmware contract.

The [FH coin-supercapacitor catalog](https://www.fhcomp.com/zh-cn/product_page/?code=011013&page=7) links the [manufacturer specification bundle](https://www.fhcomp.com/uploads/20251105/174307_%E7%BA%BD%E6%89%A3%E8%B6%85%E7%BA%A7%E7%94%B5%E5%AE%B9%E5%99%A8-Coin-type%20Supercapacitor%20Products%20Specification.zip). Retrieved ZIP SHA256: `7f359670eae606b4b4d75ed34283ccb436e84bae3a60ef4011fe8a94cc47feec`. Its H-type conventional PDF SHA256 is `1ae93ece3405ec51600a67af6bff1750c598fae383d50a7b6dff9886a9d16047`; pages2–3 were read and the dimensional/table drawing rendered for inspection.

FH5R5H104T-D009 lists100mF and5uA leakage at5V/25C after24h; body-terminal thickness is4.5±0.5mm, diameter9.5±0.5mm, and pin pitch10±0.5mm. At that leakage scenario and0.8uA RTC draw,80mF/3.3→2.2V gives only4.21h. FH5R5H474T lists4uA;376mF gives23.94h under the same assumptions, already below24h before temperature/aging. These leakage entries are not a guarantee at every voltage or temperature. The family lists hand/wave solder constraints rather than a qualified SMT reflow process. No FH candidate is selected; nominal catalog height alone is insufficient for the two-board clearance audit.

A no-charge primary-cell architecture is the preferred next study because it can provide more retention margin with less height than these coin capacitors. The manufacturer-authored [EVE CR1220 sheet](https://valbis.com/wp-content/uploads/2019/01/cr1220_eve.pdf) is dated2010.05, SHA256 `7cc7ccf2439be02ba1f1e6f585473a265309d9606cbd04e80cb8834b9485fe43`; it specifies35mAh nominal to2.0V, not guaranteed usable capacity above the SD3900 warning after an isolation-diode drop. At a proposed10uA complete-backup-node design budget,24h consumes0.24mAh; a reviewed1mAh usable-capacity allocation would provide4.17x charge margin. These are proposed budgets, not guaranteed cell/RTC limits or a selected assembly. Exact current manufacturer revision, cold/hot discharge, shelf-life, diode drop/reverse leakage, holder polarity/lands/height and mainland supply identity must close first. Do not solder an ordinary bare primary cell or include it in reflow.

Before applying the RTC ECO: select an exact mainland backup assembly and review its usable-capacity/leakage budget, review SD3900 terminal lands and all10 pins, and specify its exact grade/supply. A primary-cell circuit needs hardware reverse-charge isolation as well as charge-disabled firmware; do not rely on the register reset alone. The shared3.3V I2C bus must run at100kHz when accessing SD3900. Port the actual driver and power-loss/alarm handling; a document is not firmware integration. BM8563EMA remains a separate external-crystal/no-dedicated-backup redesign candidate.

Q14 now requires a24h main-supply-disconnected state, measured duration, end voltage, valid uninterrupted time and proof that USB/main battery/debugger do not supply the RTC. Record initial charge/cell state, temperatures, backup current and final RTC flags; do not accept main-battery-powered sleep as backup retention. All physical backup/startup/interrupt qualification remains NOT_RUN and manufacturing release remains false.

2026-10-02 continuation: physical24h Q14 is performed after prototypes and is not a prerequisite for applying an electrically reviewed prototype RTC ECO. Before CAD approval, close the primary pin/land/polarity and no-charge circuit, exact backup assembly identity, mechanical placement and firmware interface contract. Running driver/retention validation remains after samples.

JLC custom C9900195775 is labelled JLCPCB Assembly SD3900; it does not verify WHWAVE identity or exact temperature grade. Q&J C70381/CR1220-2 primary cover matches the family, but its final drawing names BS-12-B3AA004/QJ1220-2SMT and has selectable housing/contact/plating codes. Confirm exact SKU coupling and solder process before applying a holder footprint. The drawing includes locating holes. No bare primary cell enters reflow. Source URLs/hashes and the complete24h current/capacity targets are preserved in split-c1-candidate-review.json.
