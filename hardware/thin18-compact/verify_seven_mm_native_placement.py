"""Native pad-containment and connector-face checks, independent of rendering.

A clean DRC can miss a pad entirely beyond a board outline. This check compares
actual pad copper to Edge.Cuts, and derives port faces from the native footprint
pose rather than trusting an enclosure label. It is not whole-device fit approval.
"""
from pathlib import Path
import argparse,json,math,hashlib

ROOT=Path(__file__).resolve().parent

def require(value,message):
    if not value:raise ValueError(message)

def world_point(origin,angle,local):
    radians=math.radians(angle);c,s=math.cos(radians),math.sin(radians)
    return [origin[0]+c*local[0]+s*local[1],origin[1]-s*local[0]+c*local[1]]

def check_port_pose(ref,origin,angle,manufacturer,mpn):
    if ref=='J201':
        require((manufacturer,mpn)==('MUP','U22401-17'),'Unreviewed USB connector identity')
        local=[0,6.5];target=[37.5,112];direction=[0,1]
    elif ref=='J501':
        require((manufacturer,mpn)==('XUNPU','TF-122-CCP9'),'Unreviewed microSD connector identity')
        local=[0,13.95];target=[75,96];direction=[1,0]
    else:raise ValueError('Unknown external port')
    mouth=world_point(origin,angle,local);outward=world_point([0,0],angle,[0,1])
    require(math.dist(outward,direction)<1e-8,'Connector faces the wrong edge')
    require(math.dist(mouth,target)<=.5,'Connector mouth misses the requested opening datum')
    return {'ref':ref,'native_mouth_xy_mm':[round(v,6) for v in mouth],
            'required_opening_xy_mm':target,'mouth_to_opening_distance_mm':round(math.dist(mouth,target),6),
            'nominal_pose_passed':True,'plug_card_clearance_physically_verified':False}

def inspect(pcb,board_id):
    import wx
    app=wx.GetApp() or wx.App(False)
    import pcbnew as P
    pcb=Path(pcb).resolve();before=hashlib.sha256(pcb.read_bytes()).hexdigest()
    b=P.LoadBoard(str(pcb));outline=P.SHAPE_POLY_SET()
    require(b.GetBoardPolygonOutlines(outline,False),'Unclosed/invalid native board outline')
    require(outline.OutlineCount()==1,'Unexpected multiple board outlines')
    layers=[P.F_Cu,P.B_Cu] if board_id=='Display' else [P.F_Cu,P.In1_Cu,P.In2_Cu,P.B_Cu]
    outside=[];checked=0;scale=float(P.FromMM(1))**2
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetAttribute()==P.PAD_ATTRIB_NPTH:continue
            for layer in layers:
                if not p.IsOnLayer(layer):continue
                copper=P.SHAPE_POLY_SET()
                p.TransformShapeToPolygon(copper,layer,0,P.FromMM(.001),P.ERROR_OUTSIDE)
                if copper.Area()<=0:continue
                checked+=1;copper.BooleanSubtract(outline);area=copper.Area()/scale
                if area>1e-8:outside.append({'ref':f.GetReference(),'pad':p.GetNumber(),'layer':b.GetLayerName(layer),'outside_copper_mm2':round(area,9)})
    require(not outside,'Copper pads outside the actual board: '+json.dumps(outside))
    ports=[]
    if board_id=='Core':
        for ref in ['J201','J501']:
            f=b.FindFootprintByReference(ref);require(f is not None,'Missing external port '+ref)
            require(f.GetLayer()==P.F_Cu,'External port unexpectedly mirrored')
            fields={v.GetName():v.GetText() for v in f.GetFields()}
            origin=[P.ToMM(f.GetPosition().x),P.ToMM(f.GetPosition().y)]
            ports.append(check_port_pose(ref,origin,f.GetOrientationDegrees(),fields.get('Manufacturer'),fields.get('MPN')))
    require(hashlib.sha256(pcb.read_bytes()).hexdigest()==before,'Read-only placement check modified PCB')
    return {'board':board_id,'pcb_sha256':before,'copper_shapes_checked':checked,'all_copper_pads_within_outline':True,'ports':ports,'component_maximum_height_qualified':False,'whole_device_7mm_qualified':False,'manufacturing_release':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);a=p.parse_args()
    result={name:inspect(a.candidate/(name+'.kicad_pcb'),name) for name in ['Core','Display']}
    print(json.dumps(result,indent=2))
