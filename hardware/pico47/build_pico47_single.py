#!/usr/bin/env python3
"""2026-10-30 Codex：从绑定的原生源重建 Single 并重新生成验收和制造资料。

显式输入为 single_board.json 指定的外部原生文件及完整本地库，输入可迁移但
内容必须匹配。每次在新目录重铺铜和检查，不使用输入包中的旧验收报告。
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SPEC = HERE / 'single_board.json'
sys.path.insert(0, str(HERE.parent / 'thin18-compact'))
from _split_c1_common import kicad_cli
from seven_mm_routing import native_semantic_fingerprint
from capture_pico47_checkpoint import counts_from_reports
from pico47_contract import CONTRACT, validate, GPIO_PACKAGE, PANEL_PINS
from pico47_ground_returns import inspect_ground_returns
from prune_pico47_stubs import pad_components, preserves_groups
from verify_mainland_bom_compliance import verify_board_mainland_compliance
from verify_jlc_coupon_compliance import export_jlc_orderpack, inspect_board_native


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def verify_inputs(source, spec):
    """逐个核对必需原生文件和完整库清单，临时报告不作为源。"""
    bindings = spec['input_sha256']
    required = {'Single' + s for s in ('.kicad_pcb', '.kicad_sch', '.kicad_pro', '.kicad_dru')}
    required.update(('Panda7.kicad_sym', 'fp-lib-table', 'sym-lib-table'))
    require(required <= set(bindings), 'Incomplete Single source bindings')
    libraries = {str(p.relative_to(source)) for p in (source / 'Panda47.pretty').glob('*.kicad_mod')}
    require(libraries and libraries == {p for p in bindings if p.startswith('Panda47.pretty/')},
            'Footprint library inventory differs')
    for relative, digest in bindings.items():
        require(not Path(relative).is_absolute() and '..' not in Path(relative).parts,
                'Source binding must be relative')
        path = source / relative
        require(path.is_file() and sha(path) == digest, 'Source differs: ' + relative)


def run_cli(arguments, log):
    with log.open('w') as stream:
        subprocess.run([kicad_cli(), *map(str, arguments)], check=True,
                       stdout=stream, stderr=subprocess.STDOUT, timeout=180)


def inspect_single(candidate, spec):
    """以源针序、独立原理图网表和原生物理连接组检查 Single。"""
    import pcbnew as P
    plan = json.loads(CONTRACT.read_text())
    validate(plan)
    board = P.LoadBoard(str(candidate / 'Single.kicad_pcb'))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    require(not set(spec['removed_connectors']) & set(fps), 'Old interboard connectors remain')
    require(board.GetCopperLayerCount() == 4, 'Expected four copper layers')
    require(not any(t.GetClass() == 'PCB_TRACK' and t.GetLayer() == P.In1_Cu
                    and t.GetNetname() != 'GND' for t in board.GetTracks()), 'Signal on In1.Cu')
    xml = candidate / 'Single-independent-netlist.xml'
    run_cli(['sch', 'export', 'netlist', '--format', 'kicadxml', '--output', xml,
             candidate / 'Single.kicad_sch'], candidate / 'Single-independent-netlist.log')
    root = ET.parse(xml).getroot()
    actual = {(n.get('ref'), n.get('pin')): net.get('name')
              for net in root.findall('nets/net') for n in net.findall('node')}
    def normal(net):
        return '' if not net or net.startswith('unconnected-') else net
    def pads(ref, pin):
        require(ref in fps, 'Missing part: ' + ref)
        found = [p for p in fps[ref].Pads() if p.GetNumber() == str(pin)]
        require(found, 'Missing pad: ' + ref + '.' + str(pin))
        return found
    def expect(ref, pin, net):
        require(all(normal(p.GetNetname()) == net for p in pads(ref, pin)),
                'PCB pin mismatch: ' + ref + '.' + str(pin))
        require(normal(actual.get((ref, str(pin)))) == net,
                'Schematic pin mismatch: ' + ref + '.' + str(pin))
    for gpio, pin in GPIO_PACKAGE.items():
        expect('U501', pin, plan['gpio'][str(gpio)]['net'])
    for pin in (28, 38, 39, 40, 41, 42):
        expect('U501', pin, '')
    for pin, net in enumerate(PANEL_PINS, 1):
        expect('J820', pin, net)
    for index, ref in enumerate(('U710', 'U711')):
        require(fps[ref].GetValue() == 'SGM330A-YTS/TR', 'Wrong mux identity')
        for channel, triple in zip(plan['mux']['channels'][index * 4:index * 4 + 4],
                                   ((2, 3, 4), (5, 6, 7), (11, 10, 9), (14, 13, 12))):
            for pin, key in zip(triple, ('select_0_net', 'select_1_net', 'common_net')):
                expect(ref, pin, channel[key])
        for pin, net in {1:'P47_BUS_SELECT', 8:'GND', 15:'P47_BUS_OE_N', 16:'3V3_AON'}.items():
            expect(ref, pin, net)
    require(fps['U501'].GetValue() == 'ESP32-S3R8', 'Wrong MCU memory variant')
    require(fps['U506'].GetValue() == 'GD25Q128ESIG', 'Wrong 16MB flash')
    expect('U810', 49, '')
    expect('U810', 21, 'P47_HV_EN')
    for pin in (8, 32, 41, 48):
        expect('U810', pin, 'GND')
    expect('U811', 4, 'P47_HV_EN')
    groups = pad_components(board)
    group_for = {u:g for g in groups for u in g}
    links = []
    for ref, pin, other_ref, other_pin in spec['critical_links']:
        a, b = pads(ref, pin), pads(other_ref, other_pin)
        linked = all(str(y.m_Uuid.AsString()) in group_for[str(x.m_Uuid.AsString())]
                     for x in a for y in b)
        require(linked, f'Open critical path: {ref}.{pin} -> {other_ref}.{other_pin}')
        links.append({'from':ref+'.'+pin, 'to':other_ref+'.'+other_pin, 'connected':linked})
    ground = inspect_ground_returns(board, 'U501', '57',
                                   [('C804','2'), ('J820','9'), ('J820','22'), ('R809','2'),
                                    ('R810','2'), ('U810','32'), ('U810','41')])
    require(ground['all_ground_pads_connected_to_reference']
            and ground['ground_pad_count'] == spec['required_ground_pad_count'], 'Incomplete ground')
    bom = verify_board_mainland_compliance(candidate, 'Single')
    require(bom['all_passed'], 'BOM identity audit failed')
    geometry = inspect_board_native(candidate, 'Single')
    vip = []
    for target in spec['via_in_pad']['targets']:
        pad = pads(target['ref'], target['pin'])[0]
        found = [v for v in board.GetTracks() if v.GetClass() == 'PCB_VIA'
                 and pad.HitTest(v.GetPosition()) and v.GetNetname() == pad.GetNetname()]
        require(len(found) == target['count'], 'Prescribed via-in-pad inventory differs')
        for via in found:
            require(abs(P.ToMM(via.GetDrill())-target['drill_mm']) < 1e-6
                    and abs(P.ToMM(via.GetWidth(P.F_Cu))-target['diameter_mm']) < 1e-6,
                    'Prescribed via-in-pad geometry differs')
            vip.append({'uuid':via.m_Uuid.AsString(), 'ref':target['ref'], 'pin':target['pin'],
                        'x_mm':P.ToMM(via.GetPosition().x), 'y_mm':P.ToMM(via.GetPosition().y),
                        'diameter_mm':target['diameter_mm'], 'drill_mm':target['drill_mm'],
                        'process':spec['via_in_pad']['process']})
    dogbone = []
    for target in spec['via_in_pad'].get('external_dogbone_vias', []):
        pad = pads(target['ref'], target['pin'])[0]
        in_pad = [v for v in board.GetTracks() if v.GetClass() == 'PCB_VIA' and pad.HitTest(v.GetPosition())]
        require(not in_pad, f"Via-in-pad must be eliminated on {target['ref']}.{target['pin']}")
        found = [v for v in board.GetTracks() if v.GetClass() == 'PCB_VIA'
                 and abs(P.ToMM(v.GetPosition().x) - target['x_mm']) < 1e-3
                 and abs(P.ToMM(v.GetPosition().y) - target['y_mm']) < 1e-3
                 and v.GetNetname() == pad.GetNetname()]
        require(len(found) == 1, f"Missing external dog-bone via for {target['ref']}.{target['pin']}")
        via = found[0]
        require(abs(P.ToMM(via.GetDrill())-target['drill_mm']) < 1e-6
                and abs(P.ToMM(via.GetWidth(P.F_Cu))-target['diameter_mm']) < 1e-6,
                'Dog-bone via geometry differs')
        dogbone.append({'uuid':via.m_Uuid.AsString(), 'ref':target['ref'], 'pin':target['pin'],
                        'x_mm':P.ToMM(via.GetPosition().x), 'y_mm':P.ToMM(via.GetPosition().y),
                        'diameter_mm':target['diameter_mm'], 'drill_mm':target['drill_mm']})
    bay = spec.get('battery_bay_clearance')
    if bay:
        require(bay.get('study_only_not_supplier_qualified') is True,
                'Battery study envelope must not claim supplier qualification without exact Pico pack drawing')
        edge_pts = []
        for d in board.GetDrawings():
            if d.GetLayer() == P.Edge_Cuts:
                edge_pts.append((round(P.ToMM(d.GetStart().x), 3), round(P.ToMM(d.GetStart().y), 3)))
                edge_pts.append((round(P.ToMM(d.GetEnd().x), 3), round(P.ToMM(d.GetEnd().y), 3)))
        require(edge_pts and all(x >= bay['upper_left_pcb_step_min_x_mm'] - 1e-3
                                 or y >= bay['upper_left_pcb_step_max_y_mm'] - 1e-3
                                 for x, y in edge_pts),
                'PCB outline encroaches on 323576 battery bay')
        envs = bay.get('battery_assembly_envelopes_mm', {})
        pack = envs.get('BATTERY_PACK')
        pcm = envs.get('BATTERY_PCM')
        require(pack and abs((pack[2] - pack[0]) - 35.0) < 1e-3 and abs((pack[3] - pack[1]) - 76.0) < 1e-3,
                'BATTERY_PACK must preserve full 35.0 x 76.0 mm 323576 body dimensions')
        require(pcm and abs((pcm[2] - pcm[0]) - 30.0) < 1e-3 and abs((pcm[3] - pcm[1]) - 3.8) < 1e-3,
                'BATTERY_PCM must preserve full 30.0 x 3.8 mm protection board dimensions')
        for part_name, (bx1, by1, bx2, by2) in envs.items():
            require(bx1 >= 1.1 and by1 >= 1.1,
                    f'Battery assembly sub-part {part_name} encroaches on housing perimeter wall')
            require(bx2 <= bay['upper_left_pcb_step_min_x_mm'] + 1e-3
                    and by2 <= bay['upper_left_pcb_step_max_y_mm'] + 1e-3,
                    f'Battery assembly sub-part {part_name} overlaps PCB step')
    supplies, manual = [], []
    for ref, fp in sorted(fps.items()):
        if fp.IsDNP() or fp.GetAttributes() & P.FP_EXCLUDE_FROM_BOM:
            continue
        fields = {f.GetName():f.GetText() for f in fp.GetFields()}
        row = {'ref':ref, 'manufacturer':fields.get('Manufacturer',''), 'mpn':fields.get('MPN',''),
               'value':fp.GetValue(), 'footprint':fp.GetFPIDAsString(), 'lcsc':fields.get('LCSC',''),
               'supply_status':fields.get('PandaSupplyStatus','')}
        if ref in spec['manual_assembly_refs']:
            manual.append(row)
        elif not row['lcsc']:
            supplies.append(row)
    return board, groups, {'ground':ground, 'critical_links':links, 'bom':bom,
                           'geometry':geometry, 'via_in_pad':vip, 'pending_supply':supplies,
                           'required_post_smt':manual}


def write_csv(path, rows):
    require(rows, 'Missing required manufacturing rows')
    with path.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build(source, output, spec_path=SPEC):
    import wx
    app = wx.GetApp() or wx.App(False)
    import pcbnew as P
    source, output = Path(source).resolve(), Path(output).resolve()
    spec = json.loads(Path(spec_path).read_text())
    verify_inputs(source, spec)
    require(not output.exists() and not output.is_relative_to(source)
            and not source.is_relative_to(output), 'Choose a new independent output directory')
    require(not output.is_relative_to(REPO) or output.is_relative_to(REPO / '.work'),
            'Generated candidates belong in .work or external delivery')
    output.mkdir(parents=True)
    for relative in spec['input_sha256']:
        dest = output / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, dest)
    pcb = output / 'Single.kicad_pcb'
    before = P.LoadBoard(str(pcb))
    old_groups = pad_components(before)
    fingerprint = native_semantic_fingerprint(pcb)
    run_cli(['pcb','drc','--refill-zones','--save-board','--severity-all','--all-track-errors',
             '--schematic-parity','--exit-code-violations','--format','json','--output',
             output / 'Single-drc.json', pcb], output / 'Single-drc.log')
    run_cli(['sch','erc','--severity-all','--exit-code-violations','--format','json','--output',
             output / 'Single-erc.json', output / 'Single.kicad_sch'], output / 'Single-erc.log')
    counts = counts_from_reports(json.loads((output/'Single-drc.json').read_text()),
                                 json.loads((output/'Single-erc.json').read_text()))
    require(not any(counts.values()), 'Single native checks are not all zero')
    require(native_semantic_fingerprint(pcb) == fingerprint, 'Native roundtrip changed intent')
    board, groups, inspection = inspect_single(output, spec)
    require(preserves_groups(old_groups, groups), 'Native pad groups were split')
    orderpack = output / 'orderpack'
    export_jlc_orderpack(output, orderpack)
    write_csv(orderpack/'REQUIRED-VIA-IN-PAD.csv', inspection['via_in_pad'])
    write_csv(orderpack/'PENDING-SUPPLY.csv', inspection['pending_supply'])
    write_csv(orderpack/'REQUIRED-POST-SMT.csv', inspection['required_post_smt'])
    (orderpack/'MANUFACTURING-REQUIREMENTS.md').write_text(
        '# Single 制造工艺要求\n\n2026-10-30，R26。\n\n'
        '四层、0.8 mm 标称、绿油、ENIG；详细层叠以 Single-job.gbrjob 为准。\n'
        '左上板阶已收窄至 X = 38.0..73.0 mm (Y = 32.0..83.5 mm)，与 323576 (35x76x3.2 mm) 电池全组件（电芯、封边、极耳、保护板及引线）实现 0.0 mm² 重叠。\n'
        'C804.2 接地回流过孔已移至焊盘外狗骨位置 (17.40, 104.80) (0.45/0.20 mm)，无盘中孔；U501.57 的 9 个 0.50/0.25 mm 散热过孔位于阻焊开窗及钢网开口内（见 REQUIRED-VIA-IN-PAD.csv），需树脂塞孔+电镀盖帽 (FILLED_AND_COPPER_CAPPED_OR_SUPPLIER_APPROVED_EQUIVALENT) 或板厂 CAM 确认的等效工艺，确认前 supplier_process_accepted = false。\n'
        '214 个 SMT 器件见 BOM/CPL；PENDING-SUPPLY.csv 保留 21 个需客供/建档的物料，不能空贴。\n'
        'BT301 必须使用工厂绝缘引脚/焊片组件，SMT 后安装（见 REQUIRED-POST-SMT.csv）；不得回流或直接焊裸电池。\n'
        'J201 为 MUP U22401-17 沉板式 USB-C 母座；上述工艺、供料及实际电池包/完整屏幕模组规格确认前，manufacturing_release 保持为 false。\n')
    manifest = {'schema':'panda47-single-rebuild-v1', 'revision':spec['revision'],
                'source_spec_sha256':sha(spec_path), 'source_design_sha256':sha(CONTRACT),
                'input_sha256':spec['input_sha256'], 'counts':counts,
                'all_original_pad_groups_preserved':True, 'geometry_sha256':fingerprint,
                'inspection':inspection, 'manufacturing_release':False,
                'files_sha256':{str(f.relative_to(output)):sha(f) for f in sorted(output.rglob('*'))
                                if f.is_file()}}
    (output/'SINGLE-CHECKPOINT.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    verify_inputs(source, spec)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    default = json.loads(SPEC.read_text())['input_checkpoint']
    result = build(args.source or default, args.output)
    print(json.dumps({'counts':result['counts'], 'ground_pads':result['inspection']['ground']['ground_pad_count'],
                      'pending_supply':len(result['inspection']['pending_supply']),
                      'manufacturing_release':False}, indent=2))
