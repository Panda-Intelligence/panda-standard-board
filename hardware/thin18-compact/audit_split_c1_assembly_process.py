#!/usr/bin/env python3
"""Read-only native SMT/via process screen, distinct from electrical DRC.

Uses KiCad's saved copper polygons, not bounding-box overlap or library labels.
No CAD/plot/clearance edits; no inference of accepted CAM, stencil or assembly.
"""
import csv
import io
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from _split_c1_common import ROOT, REPO, REL, STEM, repo_entry, sha
from _split_c1_fabrication import require, load_contract

REPORT = ROOT / 'split-c1-assembly-process.json'
RENDER_ERROR_MM = 0.001
SMALL_LAND_MM = 0.25


def point_to_polygon(point, polygon):
    """Distance to a filled simple polygon, zero on its interior/boundary."""
    require(len(polygon) >= 3, 'Degenerate pad polygon')
    require(all(len(p) == 2 and all(math.isfinite(v) for v in p) for p in [point, *polygon]),
            'Invalid/nonfinite pad geometry')
    area2 = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(polygon,polygon[1:]+polygon[:1]))
    require(abs(area2) > 1e-12, 'Degenerate zero-area pad polygon')
    inside = False
    distance = math.inf
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        dx, dy = b[0]-a[0], b[1]-a[1]
        length2 = dx*dx + dy*dy
        t = max(0., min(1., ((point[0]-a[0])*dx + (point[1]-a[1])*dy)/length2)) if length2 else 0.
        distance = min(distance, math.hypot(point[0]-a[0]-t*dx, point[1]-a[1]-t*dy))
        if (a[1] > point[1]) != (b[1] > point[1]):
            cross = (b[0]-a[0])*(point[1]-a[1])/(b[1]-a[1]) + a[0]
            if point[0] < cross:
                inside = not inside
    return 0. if inside else distance


def hole_overlap(center, diameter, polygons):
    require(math.isfinite(diameter) and diameter > 0 and polygons, 'Missing/invalid drill or pad')
    distance = min(point_to_polygon(center, polygon) for polygon in polygons)
    gap = distance - diameter/2
    if gap > RENDER_ERROR_MM:
        return None
    return {'classification': 'center_in_land' if distance < 1e-9 else
            'hole_crosses_land_edge' if gap <= 0 else 'within_polygon_render_tolerance',
            'nominal_hole_to_land_gap_mm': round(gap, 6)}


def inspect_board(path):
    import pcbnew as P
    before = sha(path)
    board = P.LoadBoard(str(path))
    xy = lambda p: [round(P.ToMM(p.x), 6), round(P.ToMM(p.y), 6)]
    vias = sorted((t for t in board.GetTracks() if isinstance(t, P.PCB_VIA)),
                  key=lambda v: str(v.m_Uuid.AsString()))
    inventory = []
    for via in vias:
        require(via.TopLayer() == P.F_Cu and via.BottomLayer() == P.B_Cu,
                'Blind/buried vias require a separate process audit')
        diameter = [round(P.ToMM(via.GetWidth(layer)), 6) for layer in [P.F_Cu, P.B_Cu]]
        hole = round(P.ToMM(via.GetDrill()), 6)
        require(hole > 0 and min(diameter) > hole, 'Invalid native via land/drill')
        inventory.append({'uuid': str(via.m_Uuid.AsString()), 'center_mm': xy(via.GetPosition()),
                          'net': str(via.GetNetname()), 'drill_mm': hole,
                          'front_copper_diameter_mm': diameter[0], 'back_copper_diameter_mm': diameter[1]})
    require(len({v['uuid'] for v in inventory}) == len(inventory), 'Duplicate native via UUID')
    hits, small = [], defaultdict(list)
    all_positions = defaultdict(set)
    identities = {}
    for footprint in board.GetFootprints():
        if footprint.IsDNP() or footprint.IsExcludedFromBOM():
            continue
        ref = footprint.GetReference()
        fields = {f.GetName(): f.GetText() for f in footprint.GetFields()}
        identities[ref] = {'mpn': fields.get('MPN', ''), 'value': str(footprint.GetValue())}
        for pad in footprint.Pads():
            if pad.GetAttribute() != P.PAD_ATTRIB_SMD:
                continue
            for layer, mask, paste, side in [(P.F_Cu,P.F_Mask,P.F_Paste,'F.Cu'),
                                             (P.B_Cu,P.B_Mask,P.B_Paste,'B.Cu')]:
                if not pad.IsOnLayer(layer):
                    continue
                shapes = P.SHAPE_POLY_SET()
                pad.TransformShapeToPolygon(shapes, layer, 0, P.FromMM(RENDER_ERROR_MM), P.ERROR_OUTSIDE)
                require(all(shapes.HoleCount(i) == 0 for i in range(shapes.OutlineCount())),
                        'Custom pad voids need explicit polygon-hole support')
                polygons = [[xy(shapes.Outline(i).CPoint(j))
                             for j in range(shapes.Outline(i).PointCount())]
                            for i in range(shapes.OutlineCount())]
                require(polygons, 'Empty native SMT copper shape')
                size = xy(pad.GetSize())
                if pad.GetShape() == P.PAD_SHAPE_CUSTOM:
                    # A custom pad's nominal anchor is not its solderable extent.
                    pts = [p for polygon in polygons for p in polygon]
                    size = [round(max(p[i] for p in pts)-min(p[i] for p in pts),6) for i in range(2)]
                all_positions[(ref, side)].add(tuple(xy(pad.GetPosition())))
                if min(size) <= SMALL_LAND_MM + 1e-6 and pad.IsOnLayer(mask):
                    small[(ref, side)].append({'pad': pad.GetNumber(), 'size_mm': size})
                if not pad.IsOnLayer(mask):
                    continue
                for via, entry in zip(vias, inventory):
                    if not via.IsOnLayer(layer):
                        continue
                    overlap = hole_overlap(entry['center_mm'], entry['drill_mm'], polygons)
                    if overlap is None:
                        continue
                    require(entry['net'] == str(pad.GetNetname()), 'Different-net via overlaps an SMT land')
                    hits.append({'via_uuid': entry['uuid'], 'ref': ref, 'pad': pad.GetNumber(),
                                 'pad_uuid': str(pad.m_Uuid.AsString()), 'side': side, 'net': entry['net'],
                                 'center_mm': entry['center_mm'], 'drill_mm': entry['drill_mm'],
                                 'via_copper_diameter_mm': entry['front_copper_diameter_mm' if side == 'F.Cu' else 'back_copper_diameter_mm'],
                                 'native_pad_has_paste_layer': pad.IsOnLayer(paste), **overlap})
    groups = []
    for (ref, side), pads in sorted(small.items()):
        points = sorted(all_positions[(ref, side)])
        nearest = min((math.dist(a,b) for i,a in enumerate(points) for b in points[i+1:]),default=None)
        groups.append({'ref': ref, 'side': side, **identities[ref],
                       'small_pad_count': len(pads), 'pad_numbers': sorted(p['pad'] for p in pads),
                       'copper_sizes_mm': sorted({tuple(p['size_mm']) for p in pads}),
                       'minimum_distinct_pad_center_distance_mm': round(nearest,6) if nearest is not None else None})
    require(sha(path) == before, 'Native CAD changed during process inspection')
    sizes = Counter((v['drill_mm'],v['front_copper_diameter_mm'],v['back_copper_diameter_mm']) for v in inventory)
    return {'pcb': repo_entry(path), 'via_count': len(inventory), 'via_inventory': inventory,
            'via_sizes': [{'drill_mm': k[0], 'front_copper_diameter_mm': k[1],
                           'back_copper_diameter_mm': k[2], 'count': n} for k,n in sorted(sizes.items())],
            'land_overlap_hole_count': len({h['via_uuid'] for h in hits}),
            'land_overlap_contacts': sorted(hits,key=lambda h:(h['ref'],h['pad'],h['side'],h['via_uuid'])),
            'small_smt_land_groups': groups,
            'required_via_treatment': 'EPOXY_FILLED_AND_CAPPED' if hits else 'NO_IN_PAD_FILL_REQUIRED_BY_THIS_SCREEN',
            'cam_accepted': False, 'stencil_accepted': False, 'assembly_process_qualified': False}


def verify_fresh(report):
    require(report.get('schema') == 'panda-split-c1-assembly-process-v1', 'Wrong assembly process schema')
    for entry in report['inputs'].values():
        require(sha(REPO/entry['path']) == entry['sha256'], 'Stale process source: '+entry['path'])
    require(report['policy'] == load_contract()['assembly_process'], 'Process policy differs from reviewed selection')
    require(report['policy']['core_via_treatment'] == 'Epoxy Filled & Capped', 'Unreviewed via treatment substitution')
    require(all(report['policy'][k] is False for k in ['cam_accepted','stencil_accepted','physical_qualification_passed']), 'Unproven process-policy approval')
    require(set(report['boards']) == {'Core-C1','Display-C1'}, 'Missing process board')
    for board, result in report['boards'].items():
        require(result['pcb'] == report['inputs'][board+'/pcb'], 'Process PCB source differs')
        vias = {v['uuid']:v for v in result['via_inventory']}
        require(len(vias) == len(result['via_inventory']) == result['via_count'], 'Duplicate/missing via inventory')
        hits = result['land_overlap_contacts']
        require(result['land_overlap_hole_count'] == len({h['via_uuid'] for h in hits}), 'Wrong unique hole count')
        require(len({(h['via_uuid'],h['pad_uuid'],h['side']) for h in hits}) == len(hits), 'Duplicate via/land contact')
        for hit in hits:
            require(hit['via_uuid'] in vias, 'In-pad hole absent from via inventory')
            via = vias[hit['via_uuid']]
            require(all(hit[k] == via[k] for k in ['net','drill_mm','center_mm']), 'In-pad drill identity differs')
        require(result['required_via_treatment'] == ('EPOXY_FILLED_AND_CAPPED' if hits else 'NO_IN_PAD_FILL_REQUIRED_BY_THIS_SCREEN'),
                'SMT in-pad hole process requirement removed')
        require(all(result[k] is False for k in ['cam_accepted','stencil_accepted','assembly_process_qualified']), 'Unproven process acceptance')
    require(all(report[k] is False for k in ['native_cad_modified','physical_qualification_passed','manufacturing_release']), 'Unproven process release')


def drill_coverage(result, drills):
    for via in result['via_inventory']:
        matches = [h for h in drills['PTH']['round_holes']
                   if math.dist(h['center_mm'],via['center_mm']) < .001 and abs(h['diameter_mm']-via['drill_mm']) < 1e-6]
        require(len(matches) == 1, 'Via inventory does not match PTH Excellon: '+via['uuid'])
    return True


def contact_csv(result):
    stream = io.StringIO(newline='')
    fields = ['Ref','Pad','Side','X_mm','Y_mm','Drill_mm','ViaCopper_mm','Net','Via_UUID','Classification']
    writer = csv.writer(stream,lineterminator='\n');writer.writerow(fields)
    for h in result['land_overlap_contacts']:
        writer.writerow([h['ref'],h['pad'],h['side'],*h['center_mm'],h['drill_mm'],h['via_copper_diameter_mm'],h['net'],h['via_uuid'],h['classification']])
    return stream.getvalue()


def main():
    import wx
    app = wx.App(False)
    contract = load_contract()
    paths = {'Core-C1': ROOT/'core-c1-96x68-split'/REL/(STEM+'.kicad_pcb'),
             'Display-C1': ROOT/'display-c1-45x36-production-bom/PANDA-EPD0426-SPI-EVT.kicad_pcb'}
    sources = {'auditor': Path(__file__), 'fabrication_contract': ROOT/'split-c1-fabrication-contract.json'}
    for name,path in paths.items():
        sources.update({name+'/pcb': path, name+'/project': path.with_suffix('.kicad_pro')})
    inputs = {name:repo_entry(path) for name,path in sources.items()}
    report = {'schema': 'panda-split-c1-assembly-process-v1', 'inputs': inputs,
              'method': 'Native filled SMT copper polygons versus circular via drill; mask-layer membership required; plated component/NPTH holes excluded.',
              'polygon_max_error_mm': RENDER_ERROR_MM, 'small_land_threshold_mm': SMALL_LAND_MM,
              'boards': {name:inspect_board(path) for name,path in paths.items()},
              'policy': contract['assembly_process'],
              'boundaries': ['Native nominal geometry, not finished-hole tolerance or solder-process qualification.',
                             'Paste-layer membership is recorded; actual stencil apertures/area ratios/voiding are not certified.',
                             'No hits on Display does not waive its small-land or general assembly review.'],
              'native_cad_modified': False, 'physical_qualification_passed': False, 'manufacturing_release': False}
    verify_fresh(report)
    REPORT.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({name:{key:result[key] for key in ['via_count','land_overlap_hole_count','required_via_treatment']}
                      for name,result in report['boards'].items()},indent=2))


if __name__ == '__main__':
    main()
