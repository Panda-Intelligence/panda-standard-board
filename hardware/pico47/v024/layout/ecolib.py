"""ecolib.py: small helpers for hand ECO scripts on a KiCad board (run with KiCad Python)."""
import pcbnew as P
MM, T = P.FromMM, P.ToMM
_KEEP = []

def near(p, x, y, tol=0.012): return abs(T(p.x) - x) < tol and abs(T(p.y) - y) < tol

def remove(b, items):
    """items: [(net, (x1, y1), (x2, y2) | None)]; None = via. Every item must match exactly one track."""
    hit = {}
    for t in b.GetTracks():
        for k, (net, a, c) in enumerate(items):
            if t.GetNetname() != net: continue
            if c is None: ok = t.GetClass() == 'PCB_VIA' and near(t.GetPosition(), *a)
            else: ok = t.GetClass() != 'PCB_VIA' and ((near(t.GetStart(), *a) and near(t.GetEnd(), *c)) or (near(t.GetStart(), *c) and near(t.GetEnd(), *a)))
            if ok: hit.setdefault(k, t)
    miss = [items[k] for k in range(len(items)) if k not in hit]
    assert not miss, miss
    for t in hit.values(): b.Remove(t)
    _KEEP.extend(hit.values())           # pcbnew crashes later if a removed item's Python proxy is freed

def trk(b, net, layer, w, pts):
    for a, c in zip(pts, pts[1:]):
        t = P.PCB_TRACK(b); t.SetNet(b.FindNet(net)); t.SetLayer(b.GetLayerID(layer)); t.SetWidth(MM(w))
        t.SetStart(P.VECTOR2I(MM(a[0]), MM(a[1]))); t.SetEnd(P.VECTOR2I(MM(c[0]), MM(c[1]))); b.Add(t)

def via(b, net, x, y, d=0.55, drill=0.3):
    v = P.PCB_VIA(b); v.SetNet(b.FindNet(net)); v.SetPosition(P.VECTOR2I(MM(x), MM(y))); v.SetWidth(P.F_Cu, MM(d)); v.SetDrill(MM(drill)); b.Add(v)

def move(b, ref, x, y, rot=None):
    f = b.FindFootprintByReference(ref); f.SetPosition(P.VECTOR2I(MM(x), MM(y)))
    if rot is not None: f.SetOrientationDegrees(rot)
