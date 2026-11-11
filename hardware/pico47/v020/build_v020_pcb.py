"""Build the Panda47 v0.2.0 board from netlist_v020.json and a placement file (KiCad Python).

usage:
  build_v020_pcb.py sizes  netlist.json out_sizes.json
  build_v020_pcb.py build  netlist.json placement.json out_dir

The R50 board is used only as a template for the 4-layer 0.8 mm stack-up and title block; every
footprint, track, via, zone and drawing is removed before the v0.2.0 parts are added.
"""
import json
import os
import shutil
import sys
from pathlib import Path

import pcbnew as P

REPO = Path(__file__).resolve().parents[3]
TEMPLATE = REPO / 'hardware/pico47/v0.1.3/Single.kicad_pcb'
PANDA_LIB = REPO / 'hardware/pico47/v0.1.3/Panda47.pretty'
KICAD_FP = Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints')
MM = P.FromMM


FP_DIR = os.environ.get('PANDA47_FP_DIR')   # e.g. hardware/pico47/v0.2.0/Panda47v2.pretty (DFM-fixed footprints)


def lib_path(lib):
    if FP_DIR:
        return Path(FP_DIR)
    return PANDA_LIB if lib == 'Panda47' else KICAD_FP / f'{lib}.pretty'


def load_fp(part):
    fp = P.FootprintLoad(str(lib_path(part['lib'])), part['footprint'])
    if fp is None:
        raise SystemExit(f"footprint not found: {part['lib']}:{part['footprint']}")
    return fp


def courtyard_bbox(fp):
    xs, ys = [], []
    for g in fp.GraphicalItems():
        if g.GetLayer() in (P.F_CrtYd, P.B_CrtYd):
            bb = g.GetBoundingBox()
            xs += [bb.GetX(), bb.GetRight()]
            ys += [bb.GetY(), bb.GetBottom()]
    if not xs:
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            xs += [bb.GetX() - MM(0.25), bb.GetRight() + MM(0.25)]
            ys += [bb.GetY() - MM(0.25), bb.GetBottom() + MM(0.25)]
    return [P.ToMM(min(xs)), P.ToMM(min(ys)), P.ToMM(max(xs)), P.ToMM(max(ys))]


def sizes(netlist, out):
    res = {}
    for ref, part in netlist['parts'].items():
        fp = load_fp(part)
        res[ref] = dict(bbox=courtyard_bbox(fp), pads={p.GetNumber(): [P.ToMM(p.GetPosition().x), P.ToMM(p.GetPosition().y)] for p in fp.Pads()})
    json.dump(res, open(out, 'w'), indent=0)
    print(len(res), 'footprints sized')


def clear(board):
    for item in list(board.GetFootprints()) + list(board.GetTracks()) + list(board.Zones()) + list(board.GetDrawings()):
        board.Delete(item)


def build(netlist, placement, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    board = P.LoadBoard(str(TEMPLATE))
    clear(board)

    nets = {}
    def net(name):
        if name not in nets:
            n = P.NETINFO_ITEM(board, name)
            board.Add(n)
            nets[name] = n
        return nets[name]

    # outline
    pts = placement['outline']
    for a, b in zip(pts, pts[1:] + pts[:1]):
        seg = P.PCB_SHAPE(board, P.SHAPE_T_SEGMENT)
        seg.SetLayer(P.Edge_Cuts)
        seg.SetWidth(MM(0.1))
        seg.SetStart(P.VECTOR2I(MM(a[0]), MM(a[1])))
        seg.SetEnd(P.VECTOR2I(MM(b[0]), MM(b[1])))
        board.Add(seg)

    missing = []
    for ref, part in sorted(netlist['parts'].items()):
        pose = placement['parts'].get(ref)
        if pose is None:
            missing.append(ref)
            continue
        fp = load_fp(part)
        lib_dir = out / 'Panda47v2.pretty'
        lib_dir.mkdir(exist_ok=True)
        shutil.copy2(lib_path(part['lib']) / f"{part['footprint']}.kicad_mod", lib_dir / f"{part['footprint']}.kicad_mod")
        fp.SetFPID(P.LIB_ID('Panda47v2', part['footprint']))
        board.Add(fp)
        fp.SetReference(ref)
        fp.SetValue(part['value'])
        for k, v in part['fields'].items():
            if k not in ('Reference', 'Value', 'Footprint'):
                fp.SetField(k, str(v))
        fp.SetDNP(bool(part['dnp']))
        fp.SetPosition(P.VECTOR2I(MM(pose[0]), MM(pose[1])))
        fp.SetOrientationDegrees(pose[2])
        bottom_native = all(p.IsOnLayer(P.B_Cu) and not p.IsOnLayer(P.F_Cu) for p in fp.Pads())
        if len(pose) > 3 and pose[3] == 'B' and not bottom_native:
            fp.Flip(fp.GetPosition(), P.FLIP_DIRECTION_LEFT_RIGHT)
        for pad in fp.Pads():
            name = part['pins'].get(pad.GetNumber(), '')
            if name:
                pad.SetNet(net(name))
    if missing:
        raise SystemExit(f'unplaced parts: {missing}')

    # ground planes: In1 solid GND, F/B GND pour (In2 is left for signals and local power)
    poly = P.SHAPE_LINE_CHAIN()
    for x, y in pts:
        poly.Append(MM(x), MM(y))
    poly.SetClosed(True)
    for layer, prio in ((P.In1_Cu, 0),):
        z = P.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(net('GND'))
        z.Outline().AddOutline(poly)
        z.SetAssignedPriority(prio)
        z.SetLocalClearance(MM(0.2))
        z.SetMinThickness(MM(0.15))
        z.SetPadConnection(P.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(MM(0.2))
        z.SetThermalReliefSpokeWidth(MM(0.25))
        z.SetIslandRemovalMode(P.ISLAND_REMOVAL_MODE_ALWAYS)
        board.Add(z)

    pcb = out / 'Panda47-v020.kicad_pcb'
    board.Save(str(pcb))
    (out / 'fp-lib-table').write_text('(fp_lib_table (version 7)\n  (lib (name "Panda47v2")(type "KiCad")(uri "${KIPRJMOD}/Panda47v2.pretty")(options "")(descr "Panda47 v0.2.0 footprints"))\n)\n')
    (out / 'sym-lib-table').write_text('(sym_lib_table (version 7)\n  (lib (name "Panda7")(type "KiCad")(uri "${KIPRJMOD}/Panda7.kicad_sym")(options "")(descr "Panda47 v0.2.0 symbols"))\n)\n')
    import subprocess
    subprocess.run([sys.executable if False else 'python3', str(Path(__file__).with_name('rules_v020.py')), str(pcb.with_suffix('.kicad_pro'))], check=True)
    print('saved', pcb, len(board.GetFootprints()), 'footprints', len(nets), 'nets')


if __name__ == '__main__':
    mode = sys.argv[1]
    nl = json.load(open(sys.argv[2]))
    if mode == 'sizes':
        sizes(nl, sys.argv[3])
    else:
        build(nl, json.load(open(sys.argv[3])), sys.argv[4])
