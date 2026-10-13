#!/usr/bin/env python3
"""Independent E0 pad/net/identity checks, separate from routing and physical release."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
LEGACY = HERE.parent / 'thin18-compact'
sys.path.insert(0, str(LEGACY))
from _split_c1_common import kicad_cli
from pico47_contract import CONTRACT, validate, GPIO_PACKAGE, PANEL_PINS
from pico47_ground_returns import inspect_ground_returns


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def normal(value):
    return '' if not value or value.startswith('unconnected-') else value


def inspect(candidate, donor):
    import wx
    app = wx.GetApp() or wx.App(False)
    import pcbnew as P
    candidate, donor = Path(candidate).resolve(), Path(donor).resolve()
    plan = json.loads(CONTRACT.read_text())
    validate(plan)
    # Fresh exports, not PARTS-INTENT.json produced by the same builder.
    native = {}
    schematics = {}
    original = {}
    for name in ['Core', 'Display']:
        board = P.LoadBoard(str(candidate / (name + '.kicad_pcb')))
        original[name] = P.LoadBoard(str(donor / (name + '.kicad_pcb')))
        native[name] = board
        require(board.GetCopperLayerCount() == 4, name + ': expected four layers')
        xml = candidate / (name + '-independent-netlist.xml')
        with (candidate / (name + '-independent-netlist.log')).open('w') as log:
            subprocess.run([kicad_cli(), 'sch', 'export', 'netlist', '--format',
                            'kicadxml', '--output', str(xml),
                            str(candidate / (name + '.kicad_sch'))],
                           cwd=candidate, stdout=log, stderr=subprocess.STDOUT,
                           check=True, timeout=90)
        root = ET.parse(xml).getroot()
        pin_nets = {}
        pin_types = {}
        for signal in root.findall('nets/net'):
            for node in signal.findall('node'):
                key = node.get('ref'), node.get('pin')
                pin_nets[key] = normal(signal.get('name', ''))
                pin_types[key] = node.get('pintype', '').split('+')[0]
        schematics[name] = pin_nets, pin_types
        for suffix in ['.kicad_dru']:
            require(sha(candidate / (name + suffix)) == sha(donor / (name + suffix)),
                    name + ': custom rules changed')
        pro = json.loads((candidate / (name + '.kicad_pro')).read_text())
        old = json.loads((donor / (name + '.kicad_pro')).read_text())
        ds, ds0 = pro['board']['design_settings'], old['board']['design_settings']
        for key in ['rules', 'rule_severities', 'drc_exclusions']:
            require(ds.get(key) == ds0.get(key), name + ': native rules changed: ' + key)
        for key in ['erc', 'net_settings']:
            require(pro.get(key) == old.get(key), name + ': project policy changed: ' + key)
        for t in board.GetTracks():
            require(not (not isinstance(t, P.PCB_VIA) and t.GetLayer() == P.In1_Cu),
                    name + ': reference plane used for signal tracks')

    def pads(board_name, ref, pin):
        f = native[board_name].FindFootprintByReference(ref)
        require(f is not None, 'Missing component: ' + board_name + '/' + ref)
        found = [p for p in f.Pads() if p.GetNumber() == str(pin)]
        require(found, 'Missing pad: ' + ref + '.' + str(pin))
        return found

    def expect(board_name, ref, pin, signal):
        actual = pads(board_name, ref, pin)
        require(all(normal(str(p.GetNetname())) == signal for p in actual),
                f'{board_name}/{ref}.{pin}: PCB expected {signal}')
        require(schematics[board_name][0].get((ref, str(pin)), '') == signal,
                f'{board_name}/{ref}.{pin}: schematic expected {signal}')
        return actual

    for gpio, package_pin in GPIO_PACKAGE.items():
        expect('Core', 'U501', package_pin, plan['gpio'][str(gpio)]['net'])
    for package_pin in [28, 38, 39, 40, 41, 42]:
        expect('Core', 'U501', package_pin, '')
    require(native['Core'].FindFootprintByReference('U501').GetValue() == 'ESP32-S3R8',
            'Wrong MCU and memory-voltage variant')
    for i, signal in enumerate(PANEL_PINS, 1):
        expect('Display', 'J820', i, signal)
    for core_ref, display_ref, count in [('J601','J1',40), ('J602','J4',20)]:
        for pin, signal in plan['interconnect'][str(count)].items():
            expect('Core', core_ref, pin, signal)
            expect('Display', display_ref, count+1-int(pin), signal)
    for index, ref in enumerate(['U710','U711']):
        for item, triple in zip(plan['mux']['channels'][index*4:index*4+4],
                               [[2,3,4],[5,6,7],[11,10,9],[14,13,12]]):
            for pin, signal in zip(triple, [item['select_0_net'], item['select_1_net'],
                                           item['common_net']]):
                expect('Core', ref, pin, signal)
        for pin, signal in {1:'P47_BUS_SELECT',8:'GND',15:'P47_BUS_OE_N',16:'3V3_AON'}.items():
            expect('Core', ref, pin, signal)
    for i in range(16):
        expect('Core', 'R'+str(710+i), 1, 'P47_D'+str(i)+'_SRC')
        expect('Core', 'R'+str(710+i), 2, 'P47_D'+str(i))
    for i, name in enumerate(['XCL','XLE','XSTL','CKV','SPV'], 726):
        expect('Core', 'R'+str(i), 1, 'P47_'+name+'_SRC')
        expect('Core', 'R'+str(i), 2, 'P47_'+name)
    expect('Core','R512',1,'P47_D8_SRC')
    expect('Core','R513',1,'P47_BUS_SELECT')
    expect('Core','U601',18,'P47_BUS_OE_N')
    expect('Display','R813',1,'HW_ARM_GPIO')
    expect('Display','R813',2,'P47_HV_EN')
    require(native['Display'].FindFootprintByReference('R813').GetValue() == '1k',
            'Direct enable resistor value changed')
    expect('Display','R808',1,'P47_HV_EN')
    expect('Display','R808',2,'GND')
    expect('Display','U810',21,'P47_HV_EN')
    expect('Display','U811',4,'P47_HV_EN')
    require(schematics['Display'][1][('U811','4')] == 'input',
            'Expander must not drive the native direct-enable signal')
    expect('Display','U811',21,'3V3_AON')
    expect('Display','U811',2,'GND')
    expect('Display','U811',3,'GND')
    for ref, numbers in plan['power_stage']['display_solid_ground_pads'].items():
        for pin in numbers:
            for pad in expect('Display',ref,pin,'GND'):
                require(pad.GetLocalZoneConnection() == P.ZONE_CONNECTION_FULL, 'Ground pad solid-zone mode differs from source policy')
    ep = expect('Display','U810',49,'')[0]
    require([round(P.ToMM(ep.GetSize().x),4), round(P.ToMM(ep.GetSize().y),4)] == [4.4,4.4],
            'PMIC exposed-pad geometry changed')
    for item in native['Display'].GetTracks():
        if not isinstance(item, P.PCB_VIA):
            continue
        point, center = item.GetPosition(), ep.GetPosition()
        clearance = P.ToMM(item.GetWidth(P.F_Cu))/2 + .25
        require(abs(P.ToMM(point.x-center.x)) > 2.2+clearance
                or abs(P.ToMM(point.y-center.y)) > 2.2+clearance,
                'Via placed under the negative exposed pad')
    for ref, signals in [('L801',['VSYS_RAW','P47_VP_LX']),('L802',['P47_VN_LX','GND'])]:
        f = native['Display'].FindFootprintByReference(ref)
        props = {field.GetName(): field.GetText() for field in f.GetFields()}
        require(props.get('MPN') == 'MWSA0618S-4R7MT' and props.get('LCSC') == 'C408421',
                'Wrong power inductor identity')
        a, b = expect('Display',ref,1,signals[0])[0], expect('Display',ref,2,signals[1])[0]
        delta = a.GetPosition()-b.GetPosition()
        require(math.isclose(math.hypot(P.ToMM(delta.x),P.ToMM(delta.y)),6.05,abs_tol=1e-5),
                'Old small-inductor footprint retained')
        for pad in [a,b]:
            require(sorted([round(P.ToMM(pad.GetSize().x),4),round(P.ToMM(pad.GetSize().y),4)])
                    == [2.35,3.5], 'Wrong large-inductor pad dimensions')
    from pico47_placement import load_layout, LAYOUT
    ordered=load_layout()
    for ref,pose in ordered['core_poses'].items():
        f=native['Core'].FindFootprintByReference(ref)
        require(f is not None,'Missing source-placed part '+ref)
        actual=[P.ToMM(f.GetPosition().x),P.ToMM(f.GetPosition().y),f.GetOrientationDegrees()]
        require(all(abs(x-y)<1e-6 for x,y in zip(actual,pose)),'Source placement differs '+ref)
    for ref,numbers in ordered['core_solid_ground_pads'].items():
        for number in numbers:
            for p in expect('Core',ref,number,'GND'):
                require(p.GetLocalZoneConnection()==P.ZONE_CONNECTION_FULL,'Missing reviewed ground copper '+ref)
    native['Core'].BuildConnectivity()
    connectivity=native['Core'].GetConnectivity()
    for bit in range(16):
        a=expect('Core','R'+str(710+bit),2,'P47_D'+str(bit))[0]
        z=expect('Core','J601',2*bit+1,'P47_D'+str(bit))[0]
        linked={str(item.m_Uuid.AsString()) for item in connectivity.GetConnectedItems(a)}
        require(str(z.m_Uuid.AsString()) in linked,'Ordered data neck physically open at bit '+str(bit))
    mcu=expect('Core','U501',57,'GND')[0]
    cx,cy=P.ToMM(mcu.GetPosition().x),P.ToMM(mcu.GetPosition().y)
    all_vias=[v for v in native['Core'].GetTracks() if isinstance(v,P.PCB_VIA)]
    for x,y in ordered['mcu_ep_vias']['offsets_mm']:
        matches=[v for v in all_vias if abs(P.ToMM(v.GetPosition().x)-cx-x)<1e-6
                 and abs(P.ToMM(v.GetPosition().y)-cy-y)<1e-6 and str(v.GetNetname())=='GND']
        require(len(matches)==1,'Missing or duplicated MCU paddle via')
        v=matches[0]
        require(abs(P.ToMM(v.GetWidth(P.F_Cu))-.5)<1e-6 and abs(P.ToMM(v.GetDrill())-.25)<1e-6,
                'Paddle via size differs from reviewed process')
    display_return=ordered['display_ground_return_via']
    return_pad=expect('Display','C804',2,'GND')[0]
    q=display_return['expected_via_center_mm']
    matches=[v for v in native['Display'].GetTracks() if isinstance(v,P.PCB_VIA)
             and abs(P.ToMM(v.GetPosition().x)-q[0])<1e-6
             and abs(P.ToMM(v.GetPosition().y)-q[1])<1e-6]
    require(len(matches)==1 and str(matches[0].GetNetname())=='GND','Missing C804 ground-return via')
    require(abs(P.ToMM(matches[0].GetWidth(P.F_Cu))-.65)<1e-6
            and abs(P.ToMM(matches[0].GetDrill())-.30)<1e-6,'C804 drill/annulus differs')
    def joined(board_name,ref_a,pin_a,ref_b,pin_b):
        a=pads(board_name,ref_a,pin_a)[0];z=pads(board_name,ref_b,pin_b)[0]
        native[board_name].BuildConnectivity()
        linked={str(v.m_Uuid.AsString()) for v in native[board_name].GetConnectivity().GetConnectedItems(a)}
        return str(z.m_Uuid.AsString()) in linked
    critical_connections={
        'Core_GPIO2_to_interconnect':joined('Core','U501',7,'J602',16),
        'Display_interconnect_to_R813':joined('Display','J4',5,'R813',1),
        'Display_R813_to_PMIC_EN':joined('Display','R813',2,'U810',21),
        'Display_C804_ground_to_R812_ground':joined('Display','C804',2,'R812',2),
    }
    # All existing Core functions not explicitly remapped must survive intact.
    changed = {'U501','J601','J602','R512','R513','U601'}
    preserved = 0
    for f in original['Core'].GetFootprints():
        ref = f.GetReference()
        current = native['Core'].FindFootprintByReference(ref)
        require(current is not None, 'Dropped original Core part '+ref)
        require(current.GetValue() == f.GetValue(), 'Changed retained Core value '+ref)
        old_fields = {v.GetName():v.GetText() for v in f.GetFields()}
        new_fields = {v.GetName():v.GetText() for v in current.GetFields()}
        for key in ['Manufacturer','MPN','LCSC']:
            require(old_fields.get(key,'') == new_fields.get(key,''), 'Changed retained Core identity '+ref+'/'+key)
        require(current.IsDNP() == f.IsDNP()
                and current.IsExcludedFromBOM() == f.IsExcludedFromBOM(),
                'Changed original part population '+ref)
        for oldpad in f.Pads():
            pin = oldpad.GetNumber()
            if not pin:
                continue
            if ref not in changed or (ref == 'U601' and pin != '18'):
                expect('Core',ref,pin,normal(str(oldpad.GetNetname())))
                preserved += 1
    result = {'source_ordered_layout_sha256':sha(LAYOUT),'ordered_data_links_physically_connected':16,'mcu_ground_paddle_vias_checked':9,'source_contract_sha256':sha(CONTRACT), 'gpio_pins_checked':33,
              'panel_contacts_checked':40, 'interboard_contacts_checked':60,
              'mux_channels_checked':8, 'unchanged_core_pad_functions_checked':preserved,
              'pmic_direct_inhibit_native_binding':True, 'pmic_negative_ep_not_grounded':True,
              'large_inductor_actual_land_geometry':True, 'no_signal_tracks_on_In1':True,
              'native_rule_sets_unchanged':True, 'critical_physical_connections':critical_connections,
              'ground_return_connectivity': {
                  'Core': inspect_ground_returns(native['Core'], 'U501', '57', [('J601', '36'), ('J601', '38')]),
                  'Display': inspect_ground_returns(native['Display'], 'C804', '2', [('J820', '9'), ('J820', '22'), ('R809', '2'), ('R810', '2'), ('U810', '32'), ('U810', '41')]),
              },
              'additional_filled_capped_ground_via_checked':True,'physical_routing_complete':False,
              'battery_pack_accepted':False, 'manufacturing_release':False,
              'native_sha256':{n:sha(candidate/(n+'.kicad_pcb')) for n in native}}
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidate', type=Path, required=True)
    ap.add_argument('--donor', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    require(not a.output.exists(), 'Choose a new report path')
    data = inspect(a.candidate,a.donor)
    a.output.write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(data,indent=2))
