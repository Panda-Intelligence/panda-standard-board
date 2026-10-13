#!/usr/bin/env python3
"""Read-only native copper/keepout export for geometry reviews and route planning.

Unlike older routing-only exports this includes board AND footprint rule areas,
layer-qualified pad shapes, polygon holes and the real Edge.Cuts outline. The
native DRC remains the authority. No fabrication acceptance is implied.
"""
from pathlib import Path
import argparse,hashlib,json


def export(pcb: Path) -> dict:
    import wx
    app=wx.GetApp() or wx.App(False)
    import pcbnew as P
    pcb=Path(pcb).resolve();before=hashlib.sha256(pcb.read_bytes()).hexdigest()
    b=P.LoadBoard(str(pcb));layers=[l for l in [P.F_Cu,P.In1_Cu,P.In2_Cu,P.B_Cu] if b.IsLayerEnabled(l)]
    if b.GetCopperLayerCount() not in (2,4):raise ValueError('Only reviewed two/four-layer stack supported')
    def xy(q):return [round(P.ToMM(q.x),6),round(P.ToMM(q.y),6)]
    def ring(c):return [xy(c.CPoint(j)) for j in range(c.PointCount())]
    def polys(ps):return [{'outer':ring(ps.Outline(i)),'holes':[ring(ps.Hole(i,j)) for j in range(ps.HoleCount(i))]} for i in range(ps.OutlineCount())]
    def shape(item,layer):
        ps=P.SHAPE_POLY_SET();item.TransformShapeToPolygon(ps,layer,0,P.FromMM(.001),P.ERROR_OUTSIDE);return polys(ps)
    rows=[];holes=[];edges=[];areas=[]
    def rulearea(z,owner):
        if not z.GetIsRuleArea():return
        areas.append({'owner':owner,'uuid':str(z.m_Uuid.AsString()),'layers':[b.GetLayerName(l) for l in layers if z.IsOnLayer(l)],
                      'tracks_forbidden':bool(z.GetDoNotAllowTracks()),'vias_forbidden':bool(z.GetDoNotAllowVias()),
                      'copper_pour_forbidden':bool(z.GetDoNotAllowZoneFills()),'pads_forbidden':bool(z.GetDoNotAllowPads()),'polygons':polys(z.Outline())})
    for f in b.GetFootprints():
        for p in f.Pads():
            for l in layers:
                if p.IsOnLayer(l):rows.append({'type':'pad','ref':f.GetReference(),'pad':p.GetNumber(),'net':str(p.GetNetname()),'layer':b.GetLayerName(l),'position':xy(p.GetPosition()),'polygons':shape(p,l),'uuid':str(p.m_Uuid.AsString()),'size':xy(p.GetSize()),'angle':p.GetOrientationDegrees(),'smd':p.GetAttribute()==P.PAD_ATTRIB_SMD,'surface_only_no_drill':p.GetAttribute() in (P.PAD_ATTRIB_SMD,P.PAD_ATTRIB_CONN) and not p.GetDrillSize().x and not p.GetDrillSize().y and sum(p.IsOnLayer(c) for c in layers)==1,'drill_mm':xy(p.GetDrillSize())})
            dr=p.GetDrillSize()
            if dr.x:holes.append({'position':xy(p.GetPosition()),'size':xy(dr),'uuid':str(p.m_Uuid.AsString()),'net':str(p.GetNetname()),'ref':f.GetReference(),'plated':p.GetAttribute()!=P.PAD_ATTRIB_NPTH,'angle':p.GetOrientationDegrees()})
        for z in f.Zones():rulearea(z,f.GetReference())
    for t in b.GetTracks():
        isvia=isinstance(t,P.PCB_VIA)
        if isinstance(t,P.PCB_ARC):raise ValueError('Arc centrelines require an explicit route model')
        for l in layers:
            if not t.IsOnLayer(l):continue
            r={'type':'via' if isvia else 'track','net':str(t.GetNetname()),'layer':b.GetLayerName(l),'polygons':shape(t,l),'uuid':str(t.m_Uuid.AsString()),'width':round(P.ToMM(t.GetWidth(l) if isvia else t.GetWidth()),6),'locked':bool(t.IsLocked())}
            if isvia:r['position']=xy(t.GetPosition())
            else:r.update(start=xy(t.GetStart()),end=xy(t.GetEnd()))
            rows.append(r)
        if isvia:holes.append({'position':xy(t.GetPosition()),'size':[P.ToMM(t.GetDrill())]*2,'uuid':str(t.m_Uuid.AsString()),'net':str(t.GetNetname()),'plated':True,'angle':0})
    for z in b.Zones():
        if z.GetIsRuleArea():rulearea(z,None);continue
        for l in layers:
            if z.IsOnLayer(l):rows.append({'type':'zone','net':str(z.GetNetname()),'layer':b.GetLayerName(l),'uuid':str(z.m_Uuid.AsString()),'clearance':P.ToMM(z.GetLocalClearance()),'polygons':polys(z.GetFilledPolysList(l))})
    for d in b.GetDrawings():
        if d.GetLayer()!=P.Edge_Cuts:continue
        if not isinstance(d,P.PCB_SHAPE) or d.GetShape()!=P.SHAPE_T_SEGMENT:raise ValueError('Nonlinear board edge is not supported by this exporter')
        edges.append([xy(d.GetStart()),xy(d.GetEnd())])
    if hashlib.sha256(pcb.read_bytes()).hexdigest()!=before:raise ValueError('Source PCB changed during geometry read')
    return {'pcb_sha256':before,'layers':[b.GetLayerName(l) for l in layers],'items':rows,'holes':holes,'edges':edges,'rule_areas':areas,'native_cad_modified':False,'manufacturing_release':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pcb',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    if a.output.resolve()==a.pcb.resolve():raise ValueError('Output may not overwrite native input')
    g=export(a.pcb);a.output.write_text(json.dumps(g,separators=(',',':'))+'\n');print('Native geometry',len(g['items']),'items',len(g['rule_areas']),'rule areas',len(g['holes']),'holes')
