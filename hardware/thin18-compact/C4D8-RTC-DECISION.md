# Split-C1 RTC and backup domestic redesign

Date: 2026-10-02. No physical board exists. U302 and C301 remain foreign in current CAD and block the all-domestic order; there is no retention exception.

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

A nominal11mF capacitor dropping3.3→1.8V would supply only5.7h at0.8uA, even before capacitor leakage, tolerance, temperature and converter loss. Keeping above the2.2V warning reduces this illustrative estimate to4.2h. These are scenario calculations, not guaranteed retention. The required ship/off-state duration must be explicitly budgeted.

Charging register18H resets to0. Do not copy the rechargeable-cell82H recommendation before selecting a qualified backup source. Primary cells must never be charged. VBAT/no-charge operation, permitted charge voltage/current, leakage and cold/hot corners need a reviewed circuit and fail-closed firmware contract.

The [FH coin-supercapacitor catalog](https://www.fhcomp.com/zh-cn/product_page/?code=011013&page=7) has a9.5mm-diameter/4.5mm-high100mF variant among its smaller entries. It is not a3225 low-profile footprint replacement. Exact part leakage, polarity, lands, process and mechanical placement remain unqualified; no capacitor selected. A domestically sourced primary backup cell plus controlled charge-disable is another architecture to evaluate without silently dropping retention.

Next: establish retention and the native RTC_EVI event-function requirement; select an exact mainland backup assembly; review SD3900 terminal lands and full10-pin mapping; update native symbol/routing and the actual firmware repository together; obtain exact grade/supply acceptance. BM8563EMA remains a separate external-crystal/no-dedicated-backup redesign candidate. Physical backup/startup/interrupt qualification is NOT_RUN. Manufacturing release remains false.
