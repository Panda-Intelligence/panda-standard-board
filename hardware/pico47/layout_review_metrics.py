"""2026-10-30 Codex：只读原生铜几何，按实际接触拆分并核算连接路径。"""
import collections
import heapq
import json
import math
import networkx as nx
import numpy as np
from pathlib import Path
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import nearest_points, unary_union
from shapely.strtree import STRtree

LAYERS = ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu']


def layer_centers_from_job(job):
    """读取 KiCad 原生 Gerber job 的材料叠层，返回以顶层铜中心为零的层坐标。"""
    rows = [r for r in job['MaterialStackup'] if r['Type'] in ('Copper','Dielectric')]
    if [r['Type'] for r in rows] != ['Copper','Dielectric','Copper','Dielectric','Copper','Dielectric','Copper']:
        raise ValueError('Expected the complete four-layer native stackup')
    if [r['Name'] for r in rows if r['Type']=='Copper'] != LAYERS:
        raise ValueError('Native copper layer order differs')
    z = 0.0
    centers = {}
    for row in rows:
        thickness = float(row['Thickness'])
        if not math.isfinite(thickness) or thickness <= 0:
            raise ValueError('Native stackup thickness must be finite and positive')
        if row['Type']=='Copper':
            centers[row['Name']] = z + thickness/2
        z += thickness
    origin = centers['F.Cu']
    return {layer:position-origin for layer,position in centers.items()}


def analyze(data, net, queries, layer_z_mm=None):
    tracks = [t for t in data['tracks'] if t['net'] == net]
    pads = [p for p in data['pads'] if p['net'] == net and p['num']]
    vias = [v for v in data['vias'] if v['net'] == net]
    if layer_z_mm is not None:
        if set(layer_z_mm)!=set(LAYERS) or not all(math.isfinite(v) for v in layer_z_mm.values()):
            raise ValueError('Layer coordinates must define every native copper layer')
        if not all(layer_z_mm[a]<layer_z_mm[b] for a,b in zip(LAYERS,LAYERS[1:])):
            raise ValueError('Layer coordinates must follow the physical copper order')
        if any(len(p['polys'])!=1 for p in pads):
            raise ValueError('Layer-resolved endpoint model requires single-sided pads')
        if any(v.get('via_type','through')!='through'
               or v.get('copper_layer_span',['F.Cu','B.Cu'])!=['F.Cu','B.Cu'] for v in vias):
            raise ValueError('Layer-resolved model requires full through vias')
    def via_node(index, layer):
        return ('v',index,layer) if layer_z_mm is not None else ('v',index)
    lines = [LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]) for t in tracks]
    cuts = [{0.0,1.0} for t in tracks]
    links = []
    graph = collections.defaultdict(list)
    def fraction(i, pt):
        f = round(lines[i].project(pt, normalized=True),9)
        cuts[i].add(f)
        return ('t',i,f)
    tree = STRtree(lines)
    for i,(t,line) in enumerate(zip(tracks,lines)):
        for j0 in tree.query(line.buffer(t['w']/2+0.5)):
            j = int(j0)
            if j <= i or t['layer'] != tracks[j]['layer']:
                continue
            a,b = nearest_points(line,lines[j])
            if a.distance(b) <= (t['w']+tracks[j]['w'])/2+1e-5:
                links.append((fraction(i,a),fraction(j,b)))
    for pi,p in enumerate(pads):
        for layer,polys in p['polys'].items():
            poly = unary_union([Polygon(q) for q in polys if len(q)>2])
            for i0 in tree.query(poly.buffer(0.5)):
                i = int(i0)
                if tracks[i]['layer'] != layer:
                    continue
                a,b = nearest_points(lines[i],poly)
                if a.distance(b) <= tracks[i]['w']/2+1e-5:
                    links.append((('p',pi),fraction(i,a)))
        for vi,v in enumerate(vias):
            for layer,polys in p['polys'].items():
                if any(Polygon(q).distance(Point(v['x'],v['y'])) <= v['d']/2+1e-5 for q in polys if len(q)>2):
                    links.append((('p',pi),via_node(vi,layer)))
    for vi,v in enumerate(vias):
        pt = Point(v['x'],v['y'])
        for i0 in tree.query(pt.buffer(v['d']/2+0.5)):
            i = int(i0)
            if lines[i].distance(pt) <= (v['d']+tracks[i]['w'])/2+1e-5:
                links.append((via_node(vi,tracks[i]['layer']),fraction(i,pt)))
    def edge(a,b,weight,detail):
        graph[a].append((b,weight,detail))
        graph[b].append((a,weight,detail))
    for i,(t,line) in enumerate(zip(tracks,lines)):
        ss = sorted(cuts[i])
        for a,b in zip(ss,ss[1:]):
            length = line.length*(b-a)
            thickness = 0.0175 if t['layer'].startswith('In') else 0.035
            ohm = 1.724e-5*length/(t['w']*thickness)
            edge(('t',i,a),('t',i,b),length,dict(t,length_mm=length,ohm_20C=ohm))
    for a,b in links:
        edge(a,b,0,None)
    if layer_z_mm is not None:
        for vi,v in enumerate(vias):
            for a,b in zip(LAYERS,LAYERS[1:]):
                vertical = layer_z_mm[b]-layer_z_mm[a]
                edge(via_node(vi,a),via_node(vi,b),vertical,
                     dict(kind='via_span',length_mm=vertical,ohm_20C=0.0,via_index=vi))
    equivalent=None
    if net=='VBUS_USB':
        # 先合并理想接触点，再按所有铜路径并联求直流等效电阻。
        dsu=nx.utils.UnionFind(graph)
        for a,adj in graph.items():
            for b,_,detail in adj:
                if detail is None or detail['ohm_20C']<1e-12:dsu.union(a,b)
        sources=[('p',i) for i,p in enumerate(pads) if p['ref']=='J201']
        for p in sources:dsu.union(sources[0],p)
        src=dsu[sources[0]]
        sink=dsu[next(('p',i) for i,p in enumerate(pads) if p['ref']=='U901' and p['num']=='24')]
        nodes={dsu[a] for a in graph};nodes.remove(sink);nodes=list(nodes);index={n:i for i,n in enumerate(nodes)}
        lap=np.zeros((len(nodes),len(nodes)));inj=np.zeros(len(nodes));inj[index[src]]=1
        for a,adj in graph.items():
            for b,_,d in adj:
                aa,bb=dsu[a],dsu[b]
                if d is None or aa==bb or repr(a)>repr(b):continue
                conductance=1/d['ohm_20C']
                if aa!=sink:lap[index[aa],index[aa]]+=conductance
                if bb!=sink:lap[index[bb],index[bb]]+=conductance
                if aa!=sink and bb!=sink:
                    lap[index[aa],index[bb]]-=conductance;lap[index[bb],index[aa]]-=conductance
        solution=np.linalg.solve(lap,inj)
        equivalent={'all_four_USB_power_pads_to_U901_24_ohm_20C':float(solution[index[src]]),'via_and_contact_resistance_included':False,'rho_ohm_mm':1.724e-5,'outer_copper_mm':0.035,'inner_copper_mm':0.0175}
    def search(a,b):
        aa = [('p',i) for i,p in enumerate(pads) if p['ref']+'.'+p['num']==a]
        bb = {('p',i) for i,p in enumerate(pads) if p['ref']+'.'+p['num']==b}
        queue = [(0,0,aa[0])];cost={aa[0]:0};prev={};counter=1;found=None
        while queue:
            c,_,n=heapq.heappop(queue)
            if c != cost[n]:continue
            if n in bb:found=n;break
            for other,w,d in graph[n]:
                if c+w < cost.get(other,math.inf):
                    cost[other]=c+w;prev[other]=(n,d);heapq.heappush(queue,(c+w,counter,other));counter+=1
        if found is None:return {'from':a,'to':b,'connected_in_geometry_model':False}
        path=[];nodes=[found];spans=[]
        while found in prev:
            previous,d=prev[found]
            if d and d.get('kind')=='via_span':
                spans.append(dict(via_index=d['via_index'],from_layer=previous[2],to_layer=found[2],
                                  length_mm=d['length_mm']))
            elif d:
                path.append(d)
            found=previous
            nodes.append(found)
        widths=collections.defaultdict(float);layers=collections.defaultdict(float)
        for t in path:widths[str(round(t['w'],5))]+=t['length_mm'];layers[t['layer']]+=t['length_mm']
        result = {'from':a,'to':b,'connected_in_geometry_model':True,'length_mm':sum(t['length_mm'] for t in path),
                'copper_series_ohm_20C':sum(t['ohm_20C'] for t in path),'via_count':len({n[1] for n in nodes if n[0]=='v'}),
                'length_by_width_mm':dict(widths),'length_by_layer_mm':dict(layers),'segments':path}
        if layer_z_mm is not None:
            transitions=[]
            for span in reversed(spans):
                if transitions and transitions[-1]['via_index']==span['via_index']:
                    transitions[-1]['to_layer']=span['to_layer']
                    transitions[-1]['length_mm']+=span['length_mm']
                else:
                    transitions.append(dict(span))
            full_span = layer_z_mm['B.Cu']-layer_z_mm['F.Cu']
            for span in transitions:
                v=vias[span['via_index']]
                span.update(x=v['x'],y=v['y'],unused_barrel_length_mm=max(0.0,full_span-span['length_mm']))
            result.update(vertical_length_mm=sum(s['length_mm'] for s in transitions),
                          total_conductor_length_mm=result['length_mm']+sum(s['length_mm'] for s in transitions),
                          via_transitions=transitions)
        return result
    return {'net':net,'whole_net_length_mm':sum(l.length for l in lines),'whole_net_vias':len(vias),'dc_equivalent':equivalent,
            'pads':[{k:p[k] for k in ['ref','num','x','y']} for p in pads], 'paths':[search(*q) for q in queries]}


def review(data, plan, layer_z_mm=None):
    """沿真实 MCU→mux→串阻→卡座铜链测量，支路不计入总线长度。"""
    queries = {
        'VBUS_USB':[('J201.A4','U901.24')],
        'P47_VGH_FB':[('U810.33','R802.1'),('U810.33','R801.2')],
        'P47_VEE_FB':[('U810.31','R804.1'),('U810.31','R803.2')],
        'FL_SW':[('U905.16','D905.2'),('U905.16','L905.2')],
        'USB_DP':[('J201.A6','R529.1')],
        'USB_DM':[('J201.A7','R530.1')],
    }
    chains = {}
    for channel in plan['mux']['channels']:
        net = channel['select_0_net']
        if not net.startswith('SDMMC_'):
            continue
        common = channel['common_net']
        mux = next(p for p in data['pads'] if p['net']==common and p['ref'].startswith('U71'))
        series = next(p for p in data['pads'] if p['net']==net and p['ref'].startswith('R'))
        source = next(p for p in data['pads'] if p['net']==net and p['ref'].startswith('U71'))
        card = next(p for p in data['pads'] if p['net']==net+'_CARD' and p['ref']=='J501')
        queries[common] = [('U501.'+str(channel['package_pin']),mux['ref']+'.'+mux['num'])]
        queries[net] = [(source['ref']+'.'+source['num'],series['ref']+'.'+series['num'])]
        queries[net+'_CARD'] = [(series['ref']+'.2','J501.'+card['num'])]
        chains[net] = [common,net,net+'_CARD']
    paths = {net:analyze(data,net,qs,layer_z_mm) for net,qs in queries.items()}
    sd = []
    for net, parts in chains.items():
        chain = [paths[n]['paths'][0] for n in parts]
        connected = all(p['connected_in_geometry_model'] for p in chain)
        sd.append(dict(signal=net,connected=connected,
                       length_mm=sum(p['length_mm'] for p in chain) if connected else None,
                       via_count=sum(p['via_count'] for p in chain) if connected else None))
        if layer_z_mm is not None and connected:
            sd[-1].update(vertical_length_mm=sum(p['vertical_length_mm'] for p in chain),
                          total_conductor_length_mm=sum(p['total_conductor_length_mm'] for p in chain))
    crystal = Polygon([(59.9,87.15),(63.1,87.15),(63.1,89.65),(59.9,89.65)])
    digital = {c['common_net'] for c in plan['mux']['channels']}
    digital.update(n for n in queries if n.startswith(('USB','SDMMC')))
    crystal_hits = []
    for t in data['tracks']+data['vias']:
        if t['net'] not in digital or t.get('layer','F.Cu')!='F.Cu':
            continue
        shape = (LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]).buffer(t['w']/2)
                 if 'x1' in t else Point(t['x'],t['y']).buffer(t['d']/2))
        if crystal.intersects(shape):
            crystal_hits.append(t['uuid'])
    for net in paths.values():
        for path in net['paths']:
            path.pop('segments',None)
    reference=any(z.get('name')=='USB_REFERENCE_GND' and z['net']=='GND'
                  and z['layers']==['In2.Cu'] and not z['rule'] for z in data['zones'])
    report = dict(paths=paths,sd=sd,crystal_digital_copper=crystal_hits,
                usb_in2_reference_declared=reference,
                model='20C planar centerline copper; ideal contacts; excludes via/contact resistance, via vertical length and package/mux delay')
    if layer_z_mm is not None:
        report['layer_model'] = dict(copper_centers_mm=layer_z_mm,stackup_supplier_qualified=False,
            model='Shortest spatial conductor centerline; single-sided pads and through vias; excludes pad spreading, via L/C, dielectric propagation and package/mux delay',
            acceptance_scope='Existing seven checks remain planar-layout checks')
    return report


def acceptance(report):
    """工程几何回归门槛；物理时序、阻抗与温升仍须单独验收。"""
    paths=report['paths']
    checks={
        'vbus_copper_ohm_le_0_15':paths['VBUS_USB']['dc_equivalent']['all_four_USB_power_pads_to_U901_24_ohm_20C']<=.15,
        'crystal_digital_keepout':not report['crystal_digital_copper'],
        'feedback_local_front_only':all(paths[n]['whole_net_length_mm']<=8 and paths[n]['whole_net_vias']==0
                                       and all(set(p.get('length_by_layer_mm',{}))<={'F.Cu'} for p in paths[n]['paths'])
                                       for n in ['P47_VGH_FB','P47_VEE_FB']),
        'frontlight_local_switch':paths['FL_SW']['whole_net_length_mm']<=8 and paths['FL_SW']['whole_net_vias']==0,
        'sd_full_chain_length':all(s['connected'] and s['length_mm']<=50.8 for s in report['sd']),
    }
    clk=next(s['length_mm'] for s in report['sd'] if s['signal']=='SDMMC_CLK')
    checks['sd_clock_skew_le_1_27']=clk is not None and all(s['connected'] and abs(s['length_mm']-clk)<=1.27 for s in report['sd'])
    usb=[paths[n]['paths'][0] for n in ['USB_DP','USB_DM']]
    checks['usb_common_layer_and_reference']=(report['usb_in2_reference_declared']
        and all(p['connected_in_geometry_model'] and p['length_by_layer_mm'].get('B.Cu',0)>=p['length_mm']*.85
                and p['length_by_layer_mm'].get('F.Cu',0)<=6 for p in usb)
        and abs(usb[0]['length_mm']-usb[1]['length_mm'])<=1)
    return checks


def spatial_screen(report):
    """对完整空间铜长使用保守几何预算；结果不代表传播时延或数字时序资格。"""
    sd = report['sd']
    clock = next(s['total_conductor_length_mm'] for s in sd if s['signal']=='SDMMC_CLK')
    rows = [dict(signal=s['signal'],total_conductor_length_mm=s['total_conductor_length_mm'],
                 delta_to_clock_mm=s['total_conductor_length_mm']-clock) for s in sd]
    checks = dict(sd_spatial_length_le_50_8=all(s['total_conductor_length_mm']<=50.8 for s in sd),
                  sd_spatial_skew_le_1_27=all(abs(s['delta_to_clock_mm'])<=1.27 for s in rows))
    return dict(basis='Conservative geometric screen applying 50.8 mm and +/-1.27 mm to spatial conductor length; not a manufacturer-guaranteed timing limit',
                checks=checks,all_passed=all(checks.values()),signals=rows,electrical_timing_qualified=False)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('geometry',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--gerber-job',type=Path,help='可选原生 Gerber job；补充实际铜层间距和有效过孔段')
    args=parser.parse_args()
    plan=json.loads(Path(__file__).with_name('design.json').read_text())
    layer_z = layer_centers_from_job(json.loads(args.gerber_job.read_text())) if args.gerber_job else None
    result=review(json.loads(args.geometry.read_text()),plan,layer_z)
    result['checks']=acceptance(result)
    if layer_z is not None:
        import hashlib
        result['spatial_screen']=spatial_screen(result)
        result['input_sha256']={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in (args.geometry,args.gerber_job)}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(checks=result['checks'],sd=result['sd'],spatial_screen=result.get('spatial_screen')),indent=2))
    if not all(result['checks'].values()) or (layer_z is not None and not result['spatial_screen']['all_passed']):
        raise SystemExit(1)
