#!/usr/bin/env python3
"""2026-11-06 Claude：R49 前光升压供电修正，从不可变 R26 经 R48 回放后套用。

R26 合板后 `VSYS_FL_IN`（L905.1／R920.1／C920.1）没有任何电源，前光升压无输入。
R49 把它并入 `VSYS_RAW`：原理图三处全局标签改名，三颗焊盘改网，原 18 段
`VSYS_FL_IN` 铜改名，并按 `r25_router/single_r49_frontlight_supply_delta.json`
新增 0.40 mm 连接铜。其余器件、铜、区、规则与 R48 逐项相同；起止均校验原生语义
与铜指纹。生成物只写入 .work 或外部目录，制造放行状态保持 false。
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_pico47_single as B

DELTA = HERE / 'r25_router' / 'single_r49_frontlight_supply_delta.json'


def apply_schematic(sch: Path, delta):
    text = sch.read_text()
    for edit in delta['schematic_global_label_renames']:
        old = f'(global_label "{edit["from_net"]}"'
        start = text.find(f'(uuid "{edit["uuid"]}")')
        B.require(start > 0, 'Missing schematic label ' + edit['uuid'])
        head = text.rfind(old, 0, start)
        B.require(head >= 0 and text.rfind('(global_label', 0, start) == head, 'Label ' + edit['uuid'] + ' is not ' + edit['from_net'])
        text = text[:head] + f'(global_label "{edit["to_net"]}"' + text[head + len(old):]
    sch.write_text(text)


def apply_board(board, delta):
    import pcbnew as P
    from r25_router.apply_single_r27_layout_eco import copper_fingerprint
    B.require(copper_fingerprint(board, True) == delta['baseline_copper_fingerprint'], 'R49 requires the R48 copper')
    net = lambda name: board.FindNet(name)
    for e in delta['pad_net_edits']:
        pad = board.FindFootprintByReference(e['ref']).FindPadByNumber(e['pad'])
        B.require(pad.GetNetname() == e['from_net'], f'{e["ref"]}.{e["pad"]} is not {e["from_net"]}')
        pad.SetNet(net(e['to_net']))
    # 回放新增铜的 UUID 每次重建都不同，故按网络改名并核对段数；最终由目标铜指纹逐项确认。
    old = [t for t in board.GetTracks() if t.GetNetname() == 'VSYS_FL_IN']
    B.require(len(old) == len(delta['relabelled_copper_uuids']), 'Unexpected VSYS_FL_IN copper count')
    for t in old:
        t.SetNet(net('VSYS_RAW'))
    keep = []
    for t in delta['added_tracks']:
        tr = P.PCB_TRACK(board)
        tr.SetStart(P.VECTOR2I(*t['start_nm'])); tr.SetEnd(P.VECTOR2I(*t['end_nm']))
        tr.SetWidth(t['width_nm']); tr.SetLayer(board.GetLayerID(t['layer'])); tr.SetNet(net('VSYS_RAW'))
        board.Add(tr); keep.append(tr)
    for v in delta['added_vias']:
        via = P.PCB_VIA(board)
        via.SetViaType(P.VIATYPE_THROUGH); via.SetLayerPair(P.F_Cu, P.B_Cu)
        via.SetWidth(v['diameter_nm']); via.SetDrill(v['drill_nm'])
        via.SetPosition(P.VECTOR2I(v['x_nm'], v['y_nm'])); via.SetNet(net('VSYS_RAW'))
        board.Add(via); keep.append(via)
    B.require(not any(t.GetNetname() == 'VSYS_FL_IN' for t in board.GetTracks()), 'VSYS_FL_IN copper remains')
    return keep


def build(output: Path, source: Path | None = None, readable: bool = True):
    import pcbnew as P
    from seven_mm_routing import native_semantic_fingerprint
    from r25_router.apply_single_r27_layout_eco import copper_fingerprint
    from verify_jlc_coupon_compliance import export_jlc_orderpack
    output = output.resolve()
    B.require(not output.exists(), 'Choose a new output directory')
    B.require(not output.is_relative_to(B.REPO) or output.is_relative_to(B.REPO / '.work'),
              'Generated candidates belong in .work or external delivery')
    spec = json.loads(B.SPEC.read_text())
    default = Path(spec['input_checkpoint'])
    if not default.exists():
        default = B.REPO / spec['version_directory']
    r48 = output.parent / (output.name + '-r48-replay')
    B.require(not r48.exists(), 'Remove the stale R48 replay directory ' + str(r48))
    B.build(source or default, r48, revision='R48')
    delta = json.loads(DELTA.read_text())
    # 整个 R48 工程（含 R35+ 回放新建的封装库文件），不带其报告与下单包
    shutil.copytree(r48, output, ignore=shutil.ignore_patterns('orderpack', 'Single-*.json', 'Single-*.log',
                                                               'Single-independent-netlist.*', 'SINGLE-CHECKPOINT.json'))
    pcb, sch = output / 'Single.kicad_pcb', output / 'Single.kicad_sch'
    B.require(native_semantic_fingerprint(pcb) == delta['baseline_semantic_fingerprint'], 'R49 requires the R48 replay')
    apply_schematic(sch, delta)
    if readable:
        # 网表式原理图（每个引脚一个全局标签）重排为带连线的可读原理图；元件、引脚与网络不变
        import readable_schematic
        net = output / 'Single-pre-readable-netlist.xml'
        B.run_cli(['sch', 'export', 'netlist', '--format', 'kicadxml', '--output', net, sch],
                  output / 'Single-pre-readable-netlist.log')
        flat = output / 'Single.netlist-style.kicad_sch'
        shutil.copy2(sch, flat)
        readable_schematic.main(str(flat), str(net), str(sch))
        flat.unlink()
        after = output / 'Single-readable-netlist.xml'
        B.run_cli(['sch', 'export', 'netlist', '--format', 'kicadxml', '--output', after, sch],
                  output / 'Single-readable-netlist.log')
        def nets(path):
            root = B.ET.parse(path).getroot()
            return {frozenset((x.get('ref'), x.get('pin')) for x in n.iter('node')): n.get('name')
                    for n in root.iter('net')}
        B.require(nets(net) == nets(after), 'Readable schematic changed the netlist')
    board = P.LoadBoard(str(pcb))
    keepalive = apply_board(board, delta)
    P.SaveBoard(str(pcb), board)
    B.require(native_semantic_fingerprint(pcb) == delta['target_semantic_fingerprint'], 'R49 geometry differs from the checked candidate')
    B.require(copper_fingerprint(P.LoadBoard(str(pcb)), True) == delta['target_copper_fingerprint'], 'R49 copper differs from the checked candidate')
    B.run_cli(['pcb', 'drc', '--refill-zones', '--save-board', '--severity-all', '--all-track-errors',
               '--schematic-parity', '--exit-code-violations', '--format', 'json', '--output',
               output / 'Single-drc.json', pcb], output / 'Single-drc.log')
    B.run_cli(['sch', 'erc', '--severity-all', '--exit-code-violations', '--format', 'json', '--output',
               output / 'Single-erc.json', sch], output / 'Single-erc.log')
    counts = B.counts_from_reports(json.loads((output / 'Single-drc.json').read_text()),
                                   json.loads((output / 'Single-erc.json').read_text()))
    B.require(not any(counts.values()), 'R49 native checks are not all zero')
    rspec = {**spec, 'revision': 'R49',
             'layout_ecos': {**spec.get('layout_ecos', {}),
                             'R49': {**spec['layout_ecos']['R48'], 'source': str(DELTA.relative_to(HERE)), 'sha256': B.sha(DELTA)}}}
    board, groups, inspection = B.inspect_single(output, rspec)
    orderpack = output / 'orderpack'
    export_jlc_orderpack(output, orderpack, revision='R49')
    B.write_csv(orderpack / 'REQUIRED-VIA-IN-PAD.csv', inspection['via_in_pad'])
    B.write_csv(orderpack / 'PENDING-SUPPLY.csv', inspection['pending_supply'])
    B.write_csv(orderpack / 'REQUIRED-POST-SMT.csv', inspection['required_post_smt'])
    qualification = B.build_qualification_report(output, rspec, inspection, B.SPEC)
    (orderpack / 'QUALIFICATION-STATUS.json').write_text(json.dumps(qualification, indent=2, ensure_ascii=False) + '\n')
    shutil.copy2(r48 / 'orderpack' / 'MANUFACTURING-REQUIREMENTS.md', orderpack / 'MANUFACTURING-REQUIREMENTS.md')
    with (orderpack / 'MANUFACTURING-REQUIREMENTS.md').open('a') as f:
        f.write('\nR49（2026-11-06）：前光升压输入 VSYS_FL_IN 并入 VSYS_RAW，新增 0.40 mm 连接铜；'
                f'焊接盘过孔清单 {len(inspection["via_in_pad"])} 颗、待供 {len(inspection["pending_supply"])} 项，以本目录 CSV 为准。\n')
    manifest = dict(schema='panda47-single-rebuild-v1', revision='R49', baseline_revision='R48',
                    delta={'path': str(DELTA.relative_to(HERE)), 'sha256': B.sha(DELTA)}, counts=counts,
                    via_in_pad=len(inspection['via_in_pad']), pending_supply=len(inspection['pending_supply']),
                    **qualification['status_flags'],
                    files_sha256={str(f.relative_to(output)): B.sha(f) for f in sorted(output.rglob('*')) if f.is_file()})
    (output / 'SINGLE-CHECKPOINT.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    del keepalive
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--netlist-style-schematic', action='store_true',
                        help='保留原来每个引脚一个全局标签的原理图，不重排为可读原理图')
    args = parser.parse_args()
    m = build(args.output, args.source, readable=not args.netlist_style_schematic)
    print(json.dumps({k: m[k] for k in ('counts', 'via_in_pad', 'pending_supply', 'manufacturing_release')}, indent=2))
