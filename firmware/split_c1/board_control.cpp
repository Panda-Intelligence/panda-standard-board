#include "board_control.hpp"

namespace panda::split_c1 {
using namespace binding;
namespace {
constexpr std::uint8_t kChargerOffMask = 0x70; // WD_RST, OTG_CONFIG, CHG_CONFIG
constexpr std::uint8_t kStableChargerOffMask = 0x30;
constexpr std::uint8_t kWatchdogAndTimerMask = 0x38;
constexpr std::uint8_t kWatchdogAndTimer = 0x18; // 40s watchdog; charge safety timer ON
constexpr std::uint8_t kInputMask = 0x9F;
}

bool BoardControl::read(std::uint8_t a, std::uint8_t r, std::uint8_t& v) noexcept {
    if (!bus_.read8(a, r, v, kTransferTimeoutMs)) {
        io_error_ = Result::BusError;
        return false;
    }
    return true;
}

bool BoardControl::expect(std::uint8_t a, std::uint8_t r, std::uint8_t mask,
                          std::uint8_t bits) noexcept {
    std::uint8_t actual = 0;
    if (!read(a, r, actual)) return false;
    if ((actual & mask) != (bits & mask)) {
        io_error_ = Result::ReadbackMismatch;
        return false;
    }
    return true;
}

bool BoardControl::write_checked(std::uint8_t a, std::uint8_t r, std::uint8_t v,
                                 std::uint8_t mask) noexcept {
    if (!bus_.write8(a, r, v, kTransferTimeoutMs)) {
        // A failed transaction MAY have reached silicon. Do not assume no write.
        io_error_ = Result::BusError;
        return false;
    }
    return expect(a, r, mask, v);
}

bool BoardControl::update(std::uint8_t a, std::uint8_t r, std::uint8_t mask,
                          std::uint8_t bits) noexcept {
    std::uint8_t v = 0;
    if (!read(a, r, v)) return false;
    return write_checked(a, r, static_cast<std::uint8_t>((v & ~mask) | (bits & mask)), mask);
}

bool BoardControl::quiesce_expander() noexcept {
    // First release P14 (including an MCU-only restart with retained XL state).
    // P15 remains unused/input. PWM falls low while Port1 is input.
    bool ok = write_checked(kExpander, 0x07, 0xFF);
    const bool out0 = write_checked(kExpander, 0x02, kQuiescent0);
    const bool out1 = write_checked(kExpander, 0x03, kQuiescent1);
    ok = write_checked(kExpander, 0x04, 0) && ok;
    ok = write_checked(kExpander, 0x05, 0) && ok;
    // Never enable output directions after an unverified output-latch write.
    if (out0) ok = write_checked(kExpander, 0x06, kDirection0) && ok;
    if (out1) ok = write_checked(kExpander, 0x07, kDirection1) && ok;
    output1_ = kQuiescent1;
    return ok && out0 && out1;
}

bool BoardControl::permit(bool high) noexcept {
    const bool written = bus_.set_hardware_permit(high);
    bool actual = true;
    const bool sampled = bus_.read_hardware_permit(actual);
    diagnostics_.hardware_inhibit_confirmed = sampled && !actual;
    if (!written || !sampled) { io_error_ = Result::BusError; return false; }
    if (actual != high) { io_error_ = Result::ReadbackMismatch; return false; }
    return true;
}

bool BoardControl::light_off() noexcept {
    // First disable through native GPIO, even if every I2C transfer now fails.
    const bool direct = permit(false);
    const bool pwm = update(kExpander, 0x03, kFrontlightPwm, 0);
    output1_ = 0;
    light_ = diagnostics_.hardware_inhibit_confirmed ? LightState::Off : LightState::Unknown;
    return direct && pwm;
}

Result BoardControl::fail(Result reason) noexcept {
    initialized_ = false;
    diagnostics_.fault = reason;
    // GPIO hardware permit is first; attempt all remaining shutdown paths
    // even if a preceding path failed. Do not silently clear the original fault.
    light_off();
    const bool gpio_ok = quiesce_expander();
    bool charger_ok = false;
    if (charger_identified_) {
        const bool off = update(kCharger, 0x01, kChargerOffMask, 0);
        const bool zero = update(kCharger, 0x02, 0x3F, 0);
        const bool limit = update(kCharger, 0x00, 0x1F, 0);
        charger_ok = off && zero && limit;
    }
    diagnostics_.shutdown_registers_confirmed = gpio_ok && charger_ok;
    light_ = diagnostics_.hardware_inhibit_confirmed ? LightState::Off : LightState::Unknown;
    return reason;
}

bool BoardControl::capture_faults(bool allow_detection) noexcept {
    std::uint8_t history = 0, current = 0, flags = 0;
    if (!read(kCharger, 0x09, history)) return false;
    diagnostics_.charger_history = static_cast<std::uint8_t>(diagnostics_.charger_history | history);
    if (!read(kCharger, 0x09, current)) return false;
    diagnostics_.charger_current = current;
    if (!read(kCharger, 0x0E, flags)) return false;
    diagnostics_.charger_flags = static_cast<std::uint8_t>(diagnostics_.charger_flags | flags);
    if ((flags & 0x80) && !allow_detection) {
        // A new input detection revokes the previous source grant even if its
        // PSEL-selected current code happens to equal the old500mA grant.
        io_error_ = Result::SourceChanged;
        return false;
    }
    if ((history | current) != 0) {
        io_error_ = Result::ChargerFault;
        return false;
    }
    return true;
}

bool BoardControl::guard(bool require_pg) noexcept {
    bool armed = true;
    if (!bus_.read_hardware_permit(armed)) { io_error_ = Result::BusError; return false; }
    const bool expected = light_ == LightState::On || light_ == LightState::Preparing;
    if (armed != expected) { io_error_ = Result::ReadbackMismatch; return false; }
    if (bus_.frequency_hz() == 0 || bus_.frequency_hz() > kBusMaxHz) {
        io_error_ = Result::BusConfiguration;
        return false;
    }
    if (!expect(kExpander, 0x07, 0xFF, kDirection1) ||
        !expect(kExpander, 0x06, 0xFF, kDirection0) ||
        !expect(kExpander, 0x02, 0xFF, kQuiescent0) ||
        !expect(kExpander, 0x03, 0xFF, output1_) ||
        !expect(kExpander, 0x04, 0xFF, 0) ||
        !expect(kExpander, 0x05, 0xFF, 0) ||
        !expect(kCharger, 0x01, kStableChargerOffMask, 0) ||
        !expect(kCharger, 0x02, 0x3F, 0) ||
        !expect(kCharger, 0x00, kInputMask, static_cast<std::uint8_t>(input_limit_ | (hiz_ ? 0x80 : 0))) ||
        !expect(kCharger, 0x05, kWatchdogAndTimerMask, kWatchdogAndTimer) ||
        !expect(kCharger, 0x06, 0xC0, 0x40) || // 6.5V input OVP; not PD negotiation
        !expect(kCharger, 0x0D, 0xE0, 0)) return false; // no high-voltage current pulses
    if (require_pg) {
        std::uint8_t input1 = 0;
        if (!read(kExpander, 0x01, input1)) return false;
        if ((input1 & kPowerGoodMask) == 0) {
            io_error_ = Result::PowerNotGood;
            return false;
        }
    }
    return true;
}

bool BoardControl::check_light() noexcept {
    return expect(kFrontlight, 0x00, 0x03, kFrontlightMode) &&
           expect(kFrontlight, 0x01, 0xFF, light_code_) &&
           expect(kFrontlight, 0x02, 0xFF, kFrontlightVoltage) &&
           expect(kFrontlight, 0x03, 0x2F, kFrontlightFrequency);
}

bool BoardControl::feed_watchdog() noexcept {
    std::uint8_t v = 0;
    if (!read(kCharger, 0x01, v)) return false;
    if ((v & kStableChargerOffMask) != 0) {
        io_error_ = Result::ReadbackMismatch;
        return false;
    }
    // WD_RST is a pulse; exclude it from readback without ignoring CHG/OTG.
    return write_checked(kCharger, 0x01, static_cast<std::uint8_t>((v & ~kChargerOffMask) | 0x40), 0xBF);
}

Result BoardControl::ready() noexcept {
    if (diagnostics_.fault != Result::Ok) return diagnostics_.fault;
    if (!initialized_) return Result::NotInitialized;
    if (static_cast<std::uint32_t>(bus_.now_ms() - last_service_) > kServiceDeadlineMs)
        return fail(Result::DeadlineMissed);
    return Result::Ok;
}

Result BoardControl::begin() noexcept {
    initialized_ = false;
    charger_identified_ = false;
    light_ = LightState::Unknown;
    diagnostics_ = {};
    io_error_ = Result::Ok;
    if (!permit(false)) { diagnostics_.fault = io_error_; return io_error_; }
    if (bus_.frequency_hz() == 0 || bus_.frequency_hz() > kBusMaxHz) {
        diagnostics_.fault = Result::BusConfiguration;
        return diagnostics_.fault; // do not touch an unconfigured shared bus
    }
    const auto started = bus_.now_ms();
    if (!quiesce_expander()) return fail(io_error_);
    std::uint8_t id = 0;
    if (!read(kCharger, 0x0B, id)) return fail(io_error_);
    if ((id & 0x7C) != 0) return fail(Result::WrongDevice); // PN=0000, SGMPART=0
    charger_identified_ = true;
    input_limit_ = 0;
    hiz_ = false;
    if (!update(kCharger, 0x01, kChargerOffMask, 0) ||
        !update(kCharger, 0x02, 0x3F, 0) ||
        !update(kCharger, 0x00, kInputMask, 0) ||
        !update(kCharger, 0x05, kWatchdogAndTimerMask, kWatchdogAndTimer) ||
        !update(kCharger, 0x06, 0xC0, 0x40) ||
        !update(kCharger, 0x0D, 0xE0, 0)) return fail(io_error_);
    // Preserve pre-existing fault evidence. A historical default-mode watchdog
    // flag is acknowledged only during explicit begin; active faults still fail.
    std::uint8_t history = 0;
    if (!read(kCharger, 0x09, history)) return fail(io_error_);
    diagnostics_.charger_history = history;
    if ((history & 0x7F) != 0) return fail(Result::ChargerFault);
    if (!feed_watchdog() || !capture_faults(true) || !guard(true)) return fail(io_error_);
    if (static_cast<std::uint32_t>(bus_.now_ms() - started) > kServiceDeadlineMs)
        return fail(Result::DeadlineMissed);
    initialized_ = true;
    light_ = LightState::Off;
    diagnostics_.shutdown_registers_confirmed = true;
    last_service_ = bus_.now_ms();
    return Result::Ok;
}

Result BoardControl::poll() noexcept {
    const auto state = ready();
    if (state != Result::Ok) return state;
    io_error_ = Result::Ok;
    if (!guard(true) || !capture_faults()) return fail(io_error_);
    if (light_ == LightState::On && !check_light()) return fail(io_error_);
    if (!feed_watchdog()) return fail(io_error_);
    if (static_cast<std::uint32_t>(bus_.now_ms() - last_service_) > kServiceDeadlineMs)
        return fail(Result::DeadlineMissed);
    if (light_ == LightState::Preparing) {
        auto elapsed = static_cast<std::uint32_t>(bus_.now_ms() - prepare_started_);
        if (elapsed > kFrontlightStartDeadlineMs) return fail(Result::StartupTimeout);
        if (elapsed < kFrontlightSettleMs) {
            last_service_ = bus_.now_ms();
            return Result::Pending;
        }
        if (!update(kFrontlight, 0x00, 0x03, kFrontlightMode) ||
            !write_checked(kFrontlight, 0x01, light_code_) ||
            !write_checked(kFrontlight, 0x02, kFrontlightVoltage) ||
            !update(kFrontlight, 0x03, 0x2F, kFrontlightFrequency) ||
            !check_light() || !guard(true)) return fail(io_error_);
        elapsed = static_cast<std::uint32_t>(bus_.now_ms() - prepare_started_);
        if (elapsed > kFrontlightStartDeadlineMs) return fail(Result::StartupTimeout);
        // No writes to frontlight MTP (0xFF); PWM is last, after all readbacks.
        output1_ = kFrontlightPwm;
        if (!write_checked(kExpander, 0x03, output1_)) return fail(io_error_);
        light_ = LightState::On;
        diagnostics_.shutdown_registers_confirmed = false;
    }
    last_service_ = bus_.now_ms();
    return Result::Ok;
}

Result BoardControl::set_source(SourceAllowance allowance) noexcept {
    if (allowance != SourceAllowance::Limited100mA && allowance != SourceAllowance::Qualified500mA &&
        allowance != SourceAllowance::SuspendOrDetach) return Result::InvalidArgument;
    const auto state = ready();
    if (state != Result::Ok) return state;
    if (!guard(true) || !capture_faults()) return fail(io_error_);
    // A source transition revokes prior load requests; never auto-relight.
    if (!light_off()) return fail(io_error_);
    input_limit_ = allowance == SourceAllowance::Qualified500mA ? 4 : 0;
    hiz_ = allowance == SourceAllowance::SuspendOrDetach;
    if (!update(kCharger, 0x00, kInputMask,
                static_cast<std::uint8_t>(input_limit_ | (hiz_ ? 0x80 : 0)))) return fail(io_error_);
    // Do not refresh the service deadline here: callers cannot bypass poll().
    return Result::Ok;
}

Result BoardControl::set_frontlight(std::uint16_t current) noexcept {
    if (current != 0 && (current < 60 || current > 145)) return Result::InvalidArgument;
    const auto state = ready();
    if (state != Result::Ok) return state;
    if (!guard(true) || !capture_faults()) return fail(io_error_);
    if (!light_off()) return fail(io_error_);
    if (current == 0) return Result::Ok;
    if (hiz_) return Result::InvalidArgument; // explicit new source grant first
    light_code_ = static_cast<std::uint8_t>(current - 59);
    output1_ = 0;
    if (!write_checked(kExpander, 0x03, output1_) || !permit(true)) return fail(io_error_);
    prepare_started_ = bus_.now_ms();
    light_ = LightState::Preparing;
    diagnostics_.shutdown_registers_confirmed = false;
    return Result::Pending;
}

Result BoardControl::read_imu_identity(std::uint8_t& identity) noexcept {
    identity = 0;
    const auto state = ready();
    if (state != Result::Ok) return state;
    if (!guard(true)) return fail(io_error_);
    if (!read(kImu, 0x00, identity)) return fail(io_error_);
    // Deliberately no soft reset, CTRL9 or pull-up writes to the reserved pins.
    return identity == 0x05 ? Result::Ok : fail(Result::WrongDevice);
}
}
