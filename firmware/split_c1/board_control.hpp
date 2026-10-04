#pragma once
// Split-C1 bench control core. See README.md for electrical/firmware boundaries.
// No allocation, exceptions, scheduler or hardware-specific SDK dependency.
#include <cstdint>

namespace panda::split_c1 {
namespace binding {
inline constexpr std::uint8_t kExpander = 0x20;
inline constexpr std::uint8_t kCharger = 0x1A;
inline constexpr std::uint8_t kFrontlight = 0x36;
inline constexpr std::uint8_t kImu = 0x6A;
inline constexpr std::uint8_t kDirection0 = 0xD0;
inline constexpr std::uint8_t kDirection1 = 0x1F;
inline constexpr std::uint8_t kQuiescent0 = 0x20;
inline constexpr std::uint8_t kQuiescent1 = 0x00;
inline constexpr std::uint8_t kPowerGoodMask = 0x10;
inline constexpr std::uint8_t kFrontlightEnable = 0x20;
inline constexpr std::uint8_t kFrontlightPwm = 0x40;
inline constexpr std::uint8_t kFrontlightMode = 0x01;
inline constexpr std::uint8_t kFrontlightVoltage = 0xA1;
inline constexpr std::uint8_t kFrontlightFrequency = 0x2B;
inline constexpr std::uint32_t kBusMaxHz = 100000;
inline constexpr std::uint32_t kTransferTimeoutMs = 10;
inline constexpr std::uint32_t kServiceDeadlineMs = 1000;
inline constexpr std::uint32_t kFrontlightSettleMs = 10;
inline constexpr std::uint32_t kFrontlightStartDeadlineMs = 100;
}
static_assert((binding::kDirection1 & binding::kPowerGoodMask) != 0,
              "P14 is driven by a push-pull supervisor and MUST remain an input");

// Single serialized owner required for both XL9535 ports and charger/frontlight.
// Every callback must obey timeout_ms, including clock stretching/NACK/recovery.
// The adapter must use 7-bit addresses and one addressed register per transfer.
class RegisterBus {
public:
    virtual ~RegisterBus() = default;
    virtual bool read8(std::uint8_t address, std::uint8_t reg, std::uint8_t& value,
                       std::uint32_t timeout_ms) noexcept = 0;
    virtual bool write8(std::uint8_t address, std::uint8_t reg, std::uint8_t value,
                        std::uint32_t timeout_ms) noexcept = 0;
    virtual std::uint32_t frequency_hz() const noexcept = 0;
    virtual std::uint32_t now_ms() const noexcept = 0;
};

enum class Result : std::uint8_t {
    Ok, Pending, InvalidArgument, NotInitialized, BusConfiguration,
    BusError, ReadbackMismatch, WrongDevice, PowerNotGood,
    ChargerFault, SourceChanged, DeadlineMissed, StartupTimeout
};
enum class SourceAllowance : std::uint8_t {
    Limited100mA, Qualified500mA, SuspendOrDetach
};
enum class LightState : std::uint8_t { Off, Preparing, On, Unknown };
struct Diagnostics {
    Result fault = Result::Ok;
    std::uint8_t charger_history = 0;
    std::uint8_t charger_current = 0;
    std::uint8_t charger_flags = 0;
    bool shutdown_registers_confirmed = false;
};

class BoardControl final {
public:
    explicit BoardControl(RegisterBus& bus) noexcept : bus_(bus) {}
    // Explicit recovery only. All switched rails/frontlight/charging remain OFF.
    // Not proof of safe power-up before the MCU runs: R607 currently pulls nCE LOW.
    Result begin() noexcept;
    // Call at least every kServiceDeadlineMs. Missing service is detected only
    // when execution resumes; this is NOT an independent hardware watchdog.
    Result poll() noexcept;
    // Caller, not this library, must establish actual USB/source permission.
    // HIZ may remove power on a batteryless board. Charging and OTG stay disabled.
    Result set_source(SourceAllowance allowance) noexcept;
    // 0=off; 60..145=6.0..14.5mA nominal shared current. No CCT/per-string control.
    Result set_frontlight(std::uint16_t current_tenths_ma) noexcept;
    // Read-only presence sanity check; WHO_AM_I does not certify exact provenance.
    Result read_imu_identity(std::uint8_t& identity) noexcept;
    LightState light_state() const noexcept { return light_; }
    const Diagnostics& diagnostics() const noexcept { return diagnostics_; }
    bool initialized() const noexcept { return initialized_; }

private:
    RegisterBus& bus_;
    bool initialized_ = false;
    bool charger_identified_ = false;
    LightState light_ = LightState::Unknown;
    std::uint8_t output1_ = binding::kQuiescent1;
    std::uint8_t input_limit_ = 0;
    bool hiz_ = false;
    std::uint8_t light_code_ = 0;
    std::uint32_t last_service_ = 0;
    std::uint32_t prepare_started_ = 0;
    Diagnostics diagnostics_{};
    Result io_error_ = Result::Ok;
    bool read(std::uint8_t address, std::uint8_t reg, std::uint8_t& value) noexcept;
    bool write_checked(std::uint8_t address, std::uint8_t reg, std::uint8_t value,
                       std::uint8_t mask = 0xFF) noexcept;
    bool update(std::uint8_t address, std::uint8_t reg, std::uint8_t mask,
                std::uint8_t bits) noexcept;
    bool expect(std::uint8_t address, std::uint8_t reg, std::uint8_t mask,
                std::uint8_t bits) noexcept;
    bool quiesce_expander() noexcept;
    bool capture_faults(bool allow_detection = false) noexcept;
    bool guard(bool require_pg) noexcept;
    bool check_light() noexcept;
    bool feed_watchdog() noexcept;
    bool light_off() noexcept;
    Result ready() noexcept;
    Result fail(Result reason) noexcept;
};
}
