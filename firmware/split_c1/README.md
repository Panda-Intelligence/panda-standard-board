# Split-C1 portable bench-control core

This is executable C++17 control logic for the already split Core-C1/Display-C1
board. It is **not** a complete Panda OS board driver or a flashed/tested ESP32
firmware image. The actual ESP-IDF bus adapter, product integration, scheduler,
USB permission events and physical qualification remain open. No current,
voltage, timing or leakage measurement has been performed by the host tests.

## Implemented behavior

`BoardControl::begin()` first drives native GPIO2 LOW, then quiesces the XL9535 outputs, keeping P14 and P15 input-only, then
checks the SGM41513 part-ID class at **7-bit address 0x1A**. It disables charge and
OTG, sets nominal IINDPM100mA, sets ICHG0, enables the40s charger watchdog and charge
safety timer, selects6.5V input OVP, and disables high-voltage current-pulse control.
It preserves unrelated register bits. A historical watchdog flag is retained in
diagnostics during explicit startup; new watchdog/fault events cause a latched
fault. No API enables battery charging, OTG, RTC charging or higher USB voltage.

The GPIO masks are derived and checked against the actual schematic and PCB:
Port0 directions `D0`, Port1 directions `3F`; quiescent latches `00` and `00`. P05 is active-high CHG_REQUEST and stays LOW. P15 is unused; HWEN is no longer an expander output.
Output latches are verified before enabling their output directions. U906's
push-pull PG output drives P14, never the MCU reset input. Switching SD/touch/EPD/
audio rails on is deliberately outside this initial control core; they stay off.

Frontlight startup is staged: HWEN1/PWM0, an engineering10ms settling interval,
then program/readback DC mode, current,18V OVP/internal compensation/2.7V UVLO and
1MHz/PFM. PWM goes high last, after all readbacks and another PG/GPIO check.
Accepted nominal shared current is6.0..14.5mA in0.1mA steps (integer60..145), or0
to turn off. This is NOT independent warm/cool control, hardware PWM dimming,
continuous dimming below6mA or a measured guarantee that each LED stays below15mA.
No nonvolatile MTP access is made. Source changes revoke a previous light request.

`poll()` monitors GPIO latches/directions/polarity, PG, charger policy, historical
and current fault reads, input-detection events, and active frontlight registers. A reset, readback
mismatch, lost PG, missed service deadline or bus failure latches an error and
attempts shutdown. A caller must explicitly restart with `begin()`; no automatic
relighting or watchdog-reset continuation is performed. A new input-detection
flag revokes a prior500mA permission even if the reset current code is unchanged.

The QMI8658A sanity probe reads WHO_AM_I0x05 at **0x6A**, because U503 SA0 is high.
It performs no reset or CTRL9 write and does not disable the internal pull-up on
reserved pin10. It does not implement sampling, FIFO, motion interrupts or
calibration. WHO_AM_I is a QST family sanity check, not a provenance certificate.

## Integration contract

Implement `RegisterBus` using bounded single-register I2C transfers,7-bit
addresses, clock-stretch/error handling and a monotonic millisecond counter.
Use the native pins **SCL GPIO14 / SDA GPIO15** and a shared bus no faster than
100kHz because the existing SD3078 contract requires that rate at3.3V. The bus
adapter must enforce the requested10ms per-transfer timeout. Every control call
and every other device's transaction must be serialized by the board owner.
There must be no second writer to these XL9535/charger/frontlight registers.

Call `poll()` at least once per1000ms, faster for the required fault response.
The10ms settle,100ms startup deadline and1000ms service deadline are conservative
engineering choices, not manufacturer timing guarantees. Calls detect elapsed
time including transfer execution. Unsigned subtraction handles clock wrap;
service must not be absent for an entire32-bit timer period. Tests run with
injected wrap, slow callbacks and expired deadlines.

Example integration structure (adapter/scheduler still needs implementation):

```cpp
panda::split_c1::BoardControl control(bus);
auto result = control.begin();
// Only an independently qualified USB/source event may grant500mA:
if (result == panda::split_c1::Result::Ok && source_has_500ma_permission) {
    result = control.set_source(panda::split_c1::SourceAllowance::Qualified500mA);
}
// set_frontlight(145) returns Pending; subsequent scheduled poll() completes it.
// On any error inspect diagnostics; do NOT automatically re-run begin().
```

Suspend/detach requests put the charger input in HIZ after deasserting the light.
That may cut system power on a batteryless board. Software100/500mA settings and
HIZ are not proof of USB enumeration, inrush, suspend-current or reset compliance.
The pre-AON PSEL divider remains a nominal reset selection, not a hard current cap.

## Hardware-finish compatibility and boundaries

Implement the two additional RegisterBus callbacks with **native GPIO2 only**:
`set_hardware_permit(bool)` and `read_hardware_permit(bool&)`. They must never
call I2C. Set the LOW output latch before enabling output direction; disable
GPIO hold and unintended pulls. Readback samples the MCU pad before R931, not
the downstream TP19 analog voltage. Older adapters intentionally cannot compile
without implementing the direct path.

The hardware now pulls nCE to pre-AON REGN, with two series MOS permissions.
P05 request and direct permit both defaultLOW; the bench controller never enables
P05. This fixes the old default-low nCE topology. Actual startup/ramp, temperature,
partial-power and charging behavior still need prototype measurement.

On I2C loss, native GPIO2 is driven LOW before attempted bus cleanup, so the
inhibit does not depend on a responsive expander. The host model now demonstrates
that path and separately tests simultaneous GPIO+I2C failure as UNKNOWN. A stuck
HIGH GPIO is not reported as confirmed shutdown. Diagnostics distinguish direct
inhibit readback from shutdown-register confirmation. None are current measurements.

A CPU frozen with GPIO2 retainedHIGH is not independently detected by this design:
use TP19 FORCE-LOW access or power removal. There is no external autonomous
watchdog. See ../../hardware/thin18-compact/SPLIT-C1-HARDWARE-FINISH.md.

## Reproduce tests and native binding checks

```sh
python3 hardware/thin18-compact/test_split_c1_control.py
python3 hardware/thin18-compact/verify_split_c1_control.py
python3 hardware/thin18-compact/release_split_c1.py --target split-c1
```

The runner compiles with warnings-as-errors and AddressSanitizer/UBSan, executes
mock transactions (no physical device), and emits a source-hash-bound report.
The checker exports a fresh native netlist, checks actual PCB pads, derives GPIO
masks, checks exact MPNs and rejects wrong-address/direction/strap variants.
`verify_split_c1_control.py --require-target-integration` intentionally exits2:
passing a host test does not complete product firmware integration.

## Primary references

SGMICRO SGM41513 family, April2025 Rev.C.1: printed pp5,23,30,32,37-46.
https://www.sg-micro.com/rect/assets/58a4fe4d-da1d-49a3-b312-5664211d9016/SGM41513_SGM41513A_SGM41513D.pdf

SGMICRO SGM37601, June2026 Rev.A.2: printed pp27-30; see product page for the
current original PDF. Exact populated variant is SGM37601YTRL20G/TR.
https://www.sg-micro.com/product/SGM37601

XINLUDA XL9535/XL9555 Rev2.3: printed pp12-14,19. Original manufacturer document;
mirror used where the manufacturer's PDF endpoint was unavailable.
https://xinluda.com/en/content/viewpdf/aid-578.html
https://wiki.lilygo.cc/datasheet/XL9535.pdf

QST QMI8658A, document13-52-25 RevA: pp11,29,83. Manufacturer document mirror.
https://files.waveshare.com/upload/5/5f/QMI8658A_Datasheet_Rev_A.pdf

See `SPLIT-C1-RTC-FIRMWARE.md` for the separate SD3078 bus/retention contract.
