#include "../board_control.hpp"
#include <array>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace panda::split_c1;
using namespace panda::split_c1::binding;
#define CHECK(x) do { if (!(x)) throw std::runtime_error(std::string(__func__) + ": " + #x); } while (false)
struct Operation { bool write; std::uint8_t address, reg, value; bool accepted; };

struct FakeBus final : RegisterBus {
    std::array<std::array<std::uint8_t, 256>, 128> reg{};
    std::vector<Operation> operations;
    std::uint32_t time = 0, hz = 100000, delay_ms = 0;
    std::size_t fail_at = 0, count = 0;
    bool persistent = false, failed_write_applies = false, pg = true;
    bool permit_level = false, permit_failed = false, permit_stuck_high = false;
    bool set_hardware_permit(bool high) noexcept override {
        if (permit_failed) return false;
        if (!permit_stuck_high) {
            if (permit_level && !high) reset_light();
            permit_level = high;
        }
        return true;
    }
    bool read_hardware_permit(bool& high) noexcept override {
        if (permit_failed) return false;
        high = permit_level; return true;
    }
    bool protocol_violation = false, unsafe_light_rise = false;
    int ignore_address = -1, ignore_reg = -1;
    std::uint8_t fault_history = 0, fault_current = 0, flags = 0x80;

    FakeBus() {
        reset_expander(); reset_charger(); reset_light();
        reg[kImu][0] = 0x05;
    }
    void reset_expander() { reg[kExpander][2] = 0xFF; reg[kExpander][3] = 0xFF;
        reg[kExpander][4] = 0; reg[kExpander][5] = 0;
        reg[kExpander][6] = 0xFF; reg[kExpander][7] = 0xFF; }
    void reset_charger() {
        reg[kCharger][0] = 0x17; reg[kCharger][1] = 0x1A; reg[kCharger][2] = 0x34;
        reg[kCharger][5] = 0xBF; reg[kCharger][6] = 0xE6;
        reg[kCharger][0x0B] = 0; reg[kCharger][0x0D] = 1;
    }
    void reset_light() { reg[kFrontlight][0] = 0; reg[kFrontlight][1] = 0x8D;
        reg[kFrontlight][2] = 0xE9; reg[kFrontlight][3] = 0x24; }
    bool drive(std::uint8_t bit) const {
        return !(reg[kExpander][7] & bit) && (reg[kExpander][3] & bit);
    }
    bool light_on() const { return permit_level && drive(0x40); }
    bool failed() const { return fail_at && (count == fail_at || (persistent && count >= fail_at)); }
    bool known(std::uint8_t a) const { return a==kExpander || a==kCharger || a==kFrontlight || a==kImu; }
    std::uint32_t frequency_hz() const noexcept override { return hz; }
    std::uint32_t now_ms() const noexcept override { return time; }
    bool read8(std::uint8_t a, std::uint8_t r, std::uint8_t& value, std::uint32_t timeout) noexcept override {
        ++count; time += delay_ms;
        if (!known(a) || timeout != 10) protocol_violation = true;
        const bool ok = !failed() && known(a) && (a != kFrontlight || permit_level);
        if (ok) {
            value = reg[a][r];
            if (a==kExpander && r==1) {
                const auto levels = static_cast<std::uint8_t>(pg ? 0x10 : 0);
                value = static_cast<std::uint8_t>((levels & reg[a][7]) | (reg[a][3] & ~reg[a][7]));
            }
            if (a==kCharger && r==9) { value = static_cast<std::uint8_t>(fault_history | fault_current); fault_history=0; }
            if (a==kCharger && r==0x0E) { value=flags; flags=0; }
        }
        operations.push_back({false,a,r,ok ? value : std::uint8_t{0},ok});
        return ok;
    }
    bool write8(std::uint8_t a, std::uint8_t r, std::uint8_t value, std::uint32_t timeout) noexcept override {
        ++count; time += delay_ms;
        if (!known(a) || timeout != 10 || a==kImu || r==0xFF ||
            (a==kExpander && r==7 && !(value & 0x10)) ||
            (a==kCharger && r==1 && (value & 0x30))) protocol_violation=true;
        const bool on_before=light_on(), enabled_before=permit_level;
        const bool ok=!failed() && known(a) && (a != kFrontlight || enabled_before);
        if ((ok || (failed_write_applies && known(a))) && !(ignore_address==a && ignore_reg==r)) {
            reg[a][r]=value;
            if (a==kCharger && r==1 && (value & 0x40)) {
                reg[a][r] &= 0xBF;
                fault_current &= 0x7F;
            }
            if (enabled_before && !permit_level) reset_light();
        }
        if (!on_before && light_on()) {
            const bool configured=(reg[kFrontlight][0]&3)==1 &&
                reg[kFrontlight][1]>=1 && reg[kFrontlight][1]<=0x56 &&
                reg[kFrontlight][2]==0xA1 && (reg[kFrontlight][3]&0x2F)==0x2B;
            if (!configured) unsafe_light_rise=true;
        }
        operations.push_back({true,a,r,value,ok});
        return ok;
    }
};

void init(FakeBus& bus, BoardControl& control) {
    CHECK(control.begin()==Result::Ok);
    CHECK(control.initialized()); CHECK(!bus.light_on());
    CHECK(bus.reg[kExpander][6]==0xD0 && bus.reg[kExpander][7]==0x3F);
    CHECK(bus.reg[kExpander][2]==0 && bus.reg[kExpander][3]==0);
    CHECK((bus.reg[kCharger][1]&0x30)==0 && (bus.reg[kCharger][2]&0x3F)==0);
}
void illuminate(FakeBus& bus, BoardControl& control, std::uint16_t current=145) {
    CHECK(control.set_frontlight(current)==Result::Pending);
    CHECK(!bus.light_on()); bus.time += 10;
    CHECK(control.poll()==Result::Ok);
    CHECK(control.light_state()==LightState::On && bus.light_on());
    CHECK(!bus.unsafe_light_rise && !bus.protocol_violation);
}

void startup_and_addresses() {
    FakeBus b; BoardControl c(b); init(b,c);
    CHECK(c.diagnostics().shutdown_registers_confirmed);
    CHECK((b.reg[kCharger][0]&0x9F)==0);
    CHECK((b.reg[kCharger][5]&0x38)==0x18);
    CHECK((b.reg[kCharger][6]&0xC0)==0x40);
    for (const auto& op:b.operations) CHECK(op.address==0x20 || op.address==0x1A);
    CHECK(!b.protocol_violation);
}
void latch_before_direction() {
    FakeBus b; BoardControl c(b); init(b,c);
    bool latch0=false,latch1=false;
    for (const auto& o:b.operations) if (o.write && o.address==kExpander) {
        if(o.reg==2 && o.value==0) latch0=true;
        if(o.reg==3 && o.value==0) latch1=true;
        if(o.reg==6 && o.value==0xD0) CHECK(latch0);
        if(o.reg==7 && o.value==0x3F) CHECK(latch1);
        if(o.reg==7) CHECK(o.value&0x10);
    }
}
void wrong_variant_is_not_programmed() {
    for (auto id:{0x08,0x04,0x78,0xFF}) {
        FakeBus b; b.reg[kCharger][0x0B]=static_cast<std::uint8_t>(id); BoardControl c(b);
        CHECK(c.begin()==Result::WrongDevice);
        for(const auto& o:b.operations) CHECK(!(o.write && o.address==kCharger));
        CHECK(!c.initialized() && !c.diagnostics().shutdown_registers_confirmed);
    }
}
void invalid_bus_and_uninitialized() {
    for(auto speed:{0U,400000U}) {
        FakeBus b; b.hz=speed; BoardControl c(b);
        CHECK(c.begin()==Result::BusConfiguration); CHECK(b.count==0);
    }
    FakeBus b; BoardControl c(b); CHECK(c.poll()==Result::NotInitialized);
    CHECK(c.set_frontlight(100)==Result::NotInitialized); CHECK(b.count==0);
}
void every_brightness_and_invalid_values() {
    for(std::uint16_t current=60; current<=145; ++current) {
        FakeBus b; BoardControl c(b); init(b,c); illuminate(b,c,current);
        CHECK(b.reg[kFrontlight][1]==current-59);
        CHECK(c.set_frontlight(0)==Result::Ok && !b.light_on());
    }
    FakeBus b; BoardControl c(b); init(b,c);
    for(auto current:{1,59,146,150,200,65535}) {
        auto before=b.count;
        CHECK(c.set_frontlight(static_cast<std::uint16_t>(current))==Result::InvalidArgument);
        CHECK(b.count==before && !b.light_on());
    }
}
void settle_deadline_and_wrap() {
    FakeBus b; b.time=0xFFFFFFF8U; BoardControl c(b); init(b,c);
    CHECK(c.set_frontlight(145)==Result::Pending);
    b.time+=9; CHECK(c.poll()==Result::Pending); CHECK(!b.light_on());
    b.time+=1; CHECK(c.poll()==Result::Ok && b.light_on());
    FakeBus d; BoardControl e(d); init(d,e); CHECK(e.set_frontlight(100)==Result::Pending);
    d.time+=101; CHECK(e.poll()==Result::StartupTimeout && !d.light_on());
}
void source_grants_revoke_light() {
    FakeBus b; BoardControl c(b); init(b,c); illuminate(b,c);
    CHECK(c.set_source(SourceAllowance::Qualified500mA)==Result::Ok);
    CHECK(!b.light_on() && (b.reg[kCharger][0]&0x9F)==4);
    illuminate(b,c,60);
    CHECK(c.set_source(SourceAllowance::SuspendOrDetach)==Result::Ok);
    CHECK(!b.light_on() && (b.reg[kCharger][0]&0x9F)==0x80);
    CHECK(c.set_frontlight(60)==Result::InvalidArgument);
    CHECK(c.set_source(SourceAllowance::Limited100mA)==Result::Ok);
    CHECK((b.reg[kCharger][0]&0x9F)==0 && !b.light_on());
    CHECK(c.set_source(static_cast<SourceAllowance>(255))==Result::InvalidArgument);
}
void new_input_detection_revokes_old_grant() {
    FakeBus b; BoardControl c(b); init(b,c);
    CHECK(c.set_source(SourceAllowance::Qualified500mA)==Result::Ok);
    illuminate(b,c); b.flags=0x80;
    // Same500mA hardware code, different attach event: never reuse permission.
    CHECK(c.poll()==Result::SourceChanged);
    CHECK(!b.light_on() && (b.reg[kCharger][0]&0x1F)==0);
    CHECK(c.poll()==Result::SourceChanged);
}
void service_deadline_cannot_be_extended_by_setters() {
    FakeBus b; BoardControl c(b); init(b,c);
    b.time=500; CHECK(c.set_source(SourceAllowance::Qualified500mA)==Result::Ok);
    b.time=1001; CHECK(c.set_frontlight(60)==Result::DeadlineMissed);
    CHECK(!c.initialized() && !b.light_on());
    CHECK(c.poll()==Result::DeadlineMissed); // sticky, no automatic recovery
    init(b,c); CHECK(c.light_state()==LightState::Off);
}
void resets_and_external_writes_are_detected() {
    for(int which=0; which<7; ++which) {
        FakeBus b; BoardControl c(b); init(b,c); illuminate(b,c);
        switch(which) {
            case 0:b.reset_expander();break;
            case 1:b.reset_charger();break;
            case 2:b.reset_light();break;
            case 3:b.reg[kExpander][7]&=0xEF;break; // erroneous P14 output
            case 4:b.reg[kCharger][0]=0x17;break;
            case 5:b.reg[kCharger][0x0D]|=0x80;break;
            case 6:b.reg[kExpander][5]=0x10;break; // inverted PG interpretation
        }
        CHECK(c.poll()==Result::ReadbackMismatch);
        CHECK(!c.initialized() && !b.light_on());
        CHECK(b.reg[kExpander][7]&0x10);
    }
}
void fault_history_is_not_lost() {
    FakeBus b; BoardControl c(b); init(b,c);
    b.fault_history=0x20; b.fault_current=0;
    CHECK(c.poll()==Result::ChargerFault);
    CHECK(c.diagnostics().charger_history==0x20);
    CHECK(c.diagnostics().charger_current==0);
    FakeBus d; d.fault_history=0x80; BoardControl e(d); init(d,e);
    CHECK(e.diagnostics().charger_history==0x80);
    d.fault_history=0x80; CHECK(e.poll()==Result::ChargerFault);
}
void pg_loss_and_fast_bus_fail_closed() {
    FakeBus b; BoardControl c(b); init(b,c); illuminate(b,c);
    b.pg=false; CHECK(c.poll()==Result::PowerNotGood); CHECK(!b.light_on());
    FakeBus d; BoardControl e(d); init(d,e); d.hz=400000;
    CHECK(e.poll()==Result::BusConfiguration); CHECK(!e.initialized());
    FakeBus f; f.pg=false; BoardControl g(f); CHECK(g.begin()==Result::PowerNotGood);
}
void read_only_imu_probe() {
    FakeBus b; BoardControl c(b); init(b,c); std::uint8_t id=0;
    CHECK(c.read_imu_identity(id)==Result::Ok && id==5);
    bool seen=false;
    for(const auto& o:b.operations) if(o.address==0x6A) {CHECK(!o.write && o.reg==0);seen=true;}
    CHECK(seen); b.reg[kImu][0]=0x6C;
    CHECK(c.read_imu_identity(id)==Result::WrongDevice);
}
void preserve_unrelated_register_bits() {
    FakeBus b; b.reg[kCharger][0]|=0x60; b.reg[kCharger][1]|=0x80;
    b.reg[kCharger][2]|=0xC0; b.reg[kCharger][5]=0xC7; b.reg[kCharger][6]=0xE6;
    BoardControl c(b); init(b,c);
    CHECK((b.reg[kCharger][0]&0x60)==0x60);
    CHECK((b.reg[kCharger][1]&0x8F)==0x8A);
    CHECK((b.reg[kCharger][2]&0xC0)==0xC0);
    CHECK((b.reg[kCharger][5]&0xC7)==0xC7);
    CHECK((b.reg[kCharger][6]&0x3F)==0x26);
    CHECK(c.set_frontlight(60)==Result::Pending);
    b.reg[kFrontlight][0]=0xFC; b.reg[kFrontlight][3]=0xF4; b.time+=10;
    CHECK(c.poll()==Result::Ok);
    CHECK(b.reg[kFrontlight][0]==0xFD && b.reg[kFrontlight][3]==0xFB);
}
void ignored_writes_do_not_enable_light() {
    for(int r=0;r<4;++r) {
        FakeBus b; BoardControl c(b); init(b,c);
        CHECK(c.set_frontlight(145)==Result::Pending); b.time+=10;
        b.ignore_address=kFrontlight; b.ignore_reg=r;
        CHECK(c.poll()==Result::ReadbackMismatch);
        CHECK(!b.light_on() && !b.unsafe_light_rise);
    }
}
void slow_transfer_deadlines() {
    FakeBus b; BoardControl c(b); init(b,c);
    CHECK(c.set_frontlight(60)==Result::Pending);
    b.time+=10; b.delay_ms=10;
    CHECK(c.poll()==Result::StartupTimeout); CHECK(!b.light_on());
}

std::size_t injected_cases=0;
void all_single_transfer_failures() {
    // Stages: begin, light request, light programming, illuminated monitoring,
    // USB policy change. Every transaction in each success trace is failed once.
    for(int stage=0;stage<5;++stage) {
        auto prepare=[stage](FakeBus& b,BoardControl& c) {
            if(stage>0)init(b,c);
            if(stage>=2){CHECK(c.set_frontlight(145)==Result::Pending);b.time+=10;}
            if(stage>=3)CHECK(c.poll()==Result::Ok);
        };
        auto action=[stage](BoardControl& c) {
            if(stage==0)return c.begin();
            if(stage==1)return c.set_frontlight(145);
            if(stage==4)return c.set_source(SourceAllowance::Qualified500mA);
            return c.poll();
        };
        FakeBus base; BoardControl original(base);prepare(base,original);auto before=base.count;
        auto result=action(original);CHECK(result==Result::Ok || result==Result::Pending);
        const auto total=base.count-before;
        for(std::size_t i=1;i<=total;++i) for(bool applied:{false,true}) {
            FakeBus b; BoardControl c(b);prepare(b,c);b.fail_at=b.count+i;b.failed_write_applies=applied;
            const auto r=action(c);
            CHECK(r!=Result::Ok && r!=Result::Pending && !c.initialized());
            CHECK(c.light_state()!=LightState::On && !b.light_on());
            CHECK(!b.unsafe_light_rise && !b.protocol_violation);++injected_cases;
        }
    }
}
void permanent_bus_loss_uses_direct_shutdown() {
    FakeBus b; BoardControl c(b);init(b,c);illuminate(b,c);
    b.fail_at=b.count+1;b.persistent=true;
    CHECK(c.poll()==Result::BusError);
    CHECK(c.light_state()==LightState::Off);
    CHECK(c.diagnostics().hardware_inhibit_confirmed);
    CHECK(!c.diagnostics().shutdown_registers_confirmed);
    CHECK(!b.light_on() && !b.permit_level);
}

void loss_of_both_control_paths_is_unknown() {
    FakeBus b; BoardControl c(b);init(b,c);illuminate(b,c);
    b.fail_at=b.count+1;b.persistent=true;b.permit_failed=true;
    CHECK(c.poll()==Result::BusError);
    CHECK(c.light_state()==LightState::Unknown && b.light_on());
    CHECK(!c.diagnostics().hardware_inhibit_confirmed);
}
void stuck_high_gpio_is_not_claimed_safe() {
    FakeBus b;b.permit_stuck_high=true;b.permit_level=true;BoardControl c(b);
    CHECK(c.begin()==Result::ReadbackMismatch);
    CHECK(!c.initialized() && !c.diagnostics().hardware_inhibit_confirmed);
}
void charging_request_stays_low_when_lighting() {
    FakeBus b;BoardControl c(b);init(b,c);illuminate(b,c);
    CHECK((b.reg[kExpander][2]&0x20)==0);
    CHECK((b.reg[kExpander][7]&0x30)==0x30); // PG and unused P15 remain inputs
}

int main() {
    const std::vector<std::pair<const char*,std::function<void()>>> tests={
        {"startup_and_addresses",startup_and_addresses},{"latch_before_direction",latch_before_direction},
        {"wrong_variant_is_not_programmed",wrong_variant_is_not_programmed},
        {"invalid_bus_and_uninitialized",invalid_bus_and_uninitialized},
        {"brightness_boundaries",every_brightness_and_invalid_values},{"settle_deadline_and_wrap",settle_deadline_and_wrap},
        {"source_grants_revoke_light",source_grants_revoke_light},
        {"new_source_detection",new_input_detection_revokes_old_grant},
        {"service_deadline",service_deadline_cannot_be_extended_by_setters},
        {"reset_detection",resets_and_external_writes_are_detected},{"fault_history",fault_history_is_not_lost},
        {"pg_and_bus_limits",pg_loss_and_fast_bus_fail_closed},{"read_only_imu",read_only_imu_probe},
        {"unrelated_bits",preserve_unrelated_register_bits},{"ignored_writes",ignored_writes_do_not_enable_light},
        {"slow_transfers",slow_transfer_deadlines},{"single_transfer_faults",all_single_transfer_failures},
        {"permanent_bus_loss",permanent_bus_loss_uses_direct_shutdown},
        {"both_control_paths_lost",loss_of_both_control_paths_is_unknown},
        {"stuck_high_gpio",stuck_high_gpio_is_not_claimed_safe},
        {"charging_request_low",charging_request_stays_low_when_lighting}
    };
    for(const auto& test:tests) {
        try {test.second();std::cout<<"PASS "<<test.first<<'\n';}
        catch(const std::exception& error){std::cerr<<"FAIL "<<test.first<<": "<<error.what()<<'\n';return 1;}
    }
    std::cout<<"{\"test_groups\":"<<tests.size()<<",\"single_transfer_fault_cases\":"<<injected_cases
             <<",\"brightness_values_tested\":86,\"passed\":true,\"physical_hardware_tested\":false}\n";
    return 0;
}
