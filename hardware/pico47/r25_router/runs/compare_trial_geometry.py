"""核对试验板导出的焊盘和铜与路由模型；任何差异均拒绝通过。"""
import collections
import json
import sys
from shapely.geometry import Polygon


def unique_pads(geometry):
    counts = collections.Counter((pad['ref'], pad['num']) for pad in geometry['pads'])
    pads = {}
    for pad in geometry['pads']:
        base = (pad['ref'], pad['num'])
        key = base + ((pad['uuid'],) if counts[base] > 1 else ())
        if key in pads:
            raise ValueError('重复焊盘：' + str(key))
        pads[key] = pad
    return pads


def track_key(t):
    ends = sorted(((round(t['x1'], 4), round(t['y1'], 4)),
                   (round(t['x2'], 4), round(t['y2'], 4))))
    return (t['net'], t['layer'], round(t['w'], 4), *ends)


def via_key(v):
    return (v['net'], round(v['x'], 4), round(v['y'], 4), round(v['d'], 4), round(v['drill'], 4))


def compare(model, actual):
    issues = []
    expected, observed = unique_pads(model), unique_pads(actual)
    if expected.keys() != observed.keys():
        issues.append('焊盘清单不同：缺失 %s；多出 %s' % (sorted(expected.keys() - observed.keys()), sorted(observed.keys() - expected.keys())))
    for key in expected.keys() & observed.keys():
        a, b = expected[key], observed[key]
        if a['net'] != b['net'] or set(a['layers']) != set(b['layers']) or a['drill'] != b['drill']:
            issues.append('%s 焊盘网络、铜层或钻孔不一致' % (key,))
        if abs(a['x'] - b['x']) > .003 or abs(a['y'] - b['y']) > .003:
            issues.append('%s 焊盘中心不一致' % (key,))
        if set(a['polys']) != set(b['polys']):
            issues.append('%s 焊盘铜层轮廓不一致' % (key,))
            continue
        for layer in a['polys']:
            if len(a['polys'][layer]) != 1 or len(b['polys'][layer]) != 1:
                issues.append('%s 焊盘铜轮廓不受支持' % (key,))
                continue
            pa, pb = Polygon(a['polys'][layer][0]), Polygon(b['polys'][layer][0])
            if not pa.is_valid or not pb.is_valid or pa.hausdorff_distance(pb) > .003:
                issues.append('%s %s 焊盘轮廓不一致' % (key, layer))
    for name, key in (('tracks', track_key), ('vias', via_key)):
        a, b = collections.Counter(map(key, model[name])), collections.Counter(map(key, actual[name]))
        if a != b:
            issues.append('%s 模型缺失 %d 项，实际多出 %d 项' % (name, sum((a - b).values()), sum((b - a).values())))
    return issues


if __name__ == '__main__':
    with open(sys.argv[1]) as handle:
        expected = json.load(handle)
    with open(sys.argv[2]) as handle:
        actual = json.load(handle)
    errors = compare(expected, actual)
    for error in errors:
        print(error)
    print('%d pads, %d tracks, %d vias, %d differences' % (len(actual['pads']), len(actual['tracks']), len(actual['vias']), len(errors)))
    sys.exit(bool(errors))
