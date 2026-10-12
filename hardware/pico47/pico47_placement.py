"""Explicit Core placement and grounded MCU paddle via policy for E0.2.

These are design inputs, not generated native boards or a manufacturing release.
The SY7636 negative paddle is never handled by the MCU ground-via routine.
"""
from pathlib import Path
import json
import math

LAYOUT = Path(__file__).with_name('ordered_core_layout.json')
EXPECTED = {'U710','U711','C710','C711','TP712'} | {'R'+str(i) for i in range(710,733)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_layout(data):
    require(data['schema']=='panda47-ordered-core-layout-v1','Wrong layout schema')
    require(data['manufacturing_release'] is False and data['native_routing_complete'] is False,
            'An electrical layout is not fabrication evidence')
    poses=data['core_poses']
    require(set(poses)==EXPECTED,'Missing or unexpected layout override')
    for ref,pose in poses.items():
        require(len(pose)==3 and all(type(v) in (int,float) and math.isfinite(v) for v in pose),
                'Invalid component pose '+ref)
        require(2<=pose[0]<=73 and 2<=pose[1]<=131 and pose[2] in [0,90,180,270,-90],
                'Pose outside electrical study '+ref)
    for i in range(16):
        require(poses['R'+str(710+i)]==[46.45,86.45+i,180.0],
                'Data resistor order or header alignment changed')
    require(poses['U711']==[64.0,69.5,0.0] and poses['C711']==[68.4,69.5,90.0],
            'Mux and decoupler placement changed without review')
    policy=data['core_solid_ground_pads']
    require(policy['U501']==['57'] and policy['U711']==['8'],'Wrong grounded IC pads')
    require('U810' not in policy,'Negative PMIC paddle is not a ground paddle')
    via=data['mcu_ep_vias']
    require(via['ref']=='U501' and via['pad']=='57' and via['net']=='GND',
            'MCU ground-via exception applies only to U501.57')
    require(via['diameter_mm']==.5 and via['drill_mm']==.25,'Unreviewed drill geometry')
    points=via['offsets_mm']
    require(len(points)==9 and len({tuple(v) for v in points})==9,'Nine unique ground vias required')
    require(all(len(v)==2 and all(type(x) in (int,float) and math.isfinite(x) for x in v) for v in points),
            'Invalid ground-via positions')
    require(all(abs(x)<=1.5 and abs(y)<=1.5 for x,y in points),'Ground via outside reviewed MCU paddle area')
    require(all(math.dist(a,b)>=.75 for i,a in enumerate(points) for b in points[i+1:]),
            'Ground via spacing below reviewed limit')
    require(via['filled_capped_process_required'] is True and via['supplier_process_accepted'] is False,
            'Missing via-in-pad process gate')
    extra=data['display_ground_return_via']
    require(extra['ref']=='C804' and extra['pad']=='2' and extra['net']=='GND',
            'Only the reviewed capacitor ground land may use this return via')
    require(extra['offset_from_pad_center_mm']==[-.1,-.25]
            and extra['expected_pad_center_mm']==[18.2,105.0]
            and extra['expected_via_center_mm']==[18.1,104.75],
            'Display ground-return geometry differs')
    require(extra['diameter_mm']==.65 and extra['drill_mm']==.30,
            'Display ground via must meet original hole/diameter limits')
    require(extra['manufacturing_process']=='RESIN_FILLED_AND_COPPER_CAPPED_VIA_IN_PAD'
            and extra['supplier_process_accepted'] is False,
            'Unverified via-in-pad manufacture must remain an explicit gate')
    return True


def load_layout():
    data=json.loads(LAYOUT.read_text())
    validate_layout(data)
    return data


def add_mcu_ground_vias(board, data):
    import pcbnew as P
    validate_layout(data)
    spec=data['mcu_ep_vias']
    fp=board.FindFootprintByReference(spec['ref'])
    require(fp is not None,'Missing MCU')
    pads=[p for p in fp.Pads() if p.GetNumber()==spec['pad']]
    require(len(pads)==1 and str(pads[0].GetNetname())=='GND','Not the expected MCU GND paddle')
    pad=pads[0]
    require(fp.GetOrientationDegrees()==0,'Ground offsets require the reviewed MCU orientation')
    center=pad.GetPosition()
    result=[]
    for x,y in spec['offsets_mm']:
        q=P.VECTOR2I(center.x+P.FromMM(x),center.y+P.FromMM(y))
        require(abs(x)+.25<P.ToMM(pad.GetSize().x)/2
                and abs(y)+.25<P.ToMM(pad.GetSize().y)/2,'Via not contained by MCU paddle')
        via=P.PCB_VIA(board)
        via.SetViaType(P.VIATYPE_THROUGH)
        via.SetPosition(q)
        via.SetWidth(P.FromMM(spec['diameter_mm']))
        via.SetDrill(P.FromMM(spec['drill_mm']))
        via.SetLayerPair(P.F_Cu,P.B_Cu)
        board.Add(via)
        via.SetNet(board.FindNet('GND'))
        result.append([round(P.ToMM(q.x),6),round(P.ToMM(q.y),6)])
    return result


def route_ordered_data_necks(board, data):
    """Route the sixteen reviewed short F.Cu links from R-bank to header.

    This is only the connector-side portion, not the complete MCU-to-panel path.
    Native all-track DRC must validate the fresh build after these links are added.
    """
    import pcbnew as P
    validate_layout(data)
    header=board.FindFootprintByReference('J601')
    require(header is not None,'Missing display interconnect')
    links=[]
    for bit in range(16):
        ref='R'+str(710+bit)
        resistor=board.FindFootprintByReference(ref)
        require(resistor is not None,'Missing ordered resistor '+ref)
        a=next(p for p in header.Pads() if p.GetNumber()==str(2*bit+1))
        z=next(p for p in resistor.Pads() if p.GetNumber()=='2')
        signal='P47_D'+str(bit)
        require(str(a.GetNetname())==str(z.GetNetname())==signal,'Wrong ordered data net')
        require(a.GetPosition().y==z.GetPosition().y,'Ordered connection is not aligned')
        require(0<P.ToMM(z.GetPosition().x-a.GetPosition().x)<=1.2,'Unexpected neck length')
        t=P.PCB_TRACK(board)
        t.SetStart(a.GetPosition())
        t.SetEnd(z.GetPosition())
        t.SetWidth(P.FromMM(.15))
        t.SetLayer(P.F_Cu)
        board.Add(t)
        t.SetNet(board.FindNet(signal))
        links.append({'bit':bit,'header_pin':2*bit+1,'resistor':ref,'layer':'F.Cu',
                      'width_mm':.15,'pad_center_distance_mm':P.ToMM(z.GetPosition().x-a.GetPosition().x)})
    return links


def add_display_ground_return(board, data):
    """One explicitly specified filled/capped C804 ground-land via.

    This is not a general permission for via-in-pad or the negative PMIC paddle.
    Factory acceptance of filling/capping and stencil heat balance remains open.
    """
    import pcbnew as P
    validate_layout(data)
    spec=data['display_ground_return_via']
    fp=board.FindFootprintByReference('C804')
    require(fp is not None,'Missing display return capacitor')
    pads=[p for p in fp.Pads() if p.GetNumber()=='2']
    require(len(pads)==1 and str(pads[0].GetNetname())=='GND','Expected C804 ground land')
    pad=pads[0]
    center=[P.ToMM(pad.GetPosition().x),P.ToMM(pad.GetPosition().y)]
    require(all(abs(a-b)<1e-6 for a,b in zip(center,spec['expected_pad_center_mm'])),
            'Return-via coordinates require review after moving C804')
    x,y=spec['expected_via_center_mm']
    q=P.VECTOR2I(P.FromMM(x),P.FromMM(y))
    poly=P.SHAPE_POLY_SET()
    pad.TransformShapeToPolygon(poly,P.F_Cu,0,P.FromMM(.001),P.ERROR_INSIDE)
    # Check the complete circular annulus, not only the drill centre.
    radius=P.FromMM(spec['diameter_mm']/2+.01)
    for angle in range(0,360,10):
        t=math.radians(angle)
        edge=P.VECTOR2I(q.x+int(round(radius*math.cos(t))),q.y+int(round(radius*math.sin(t))))
        require(poly.Contains(edge),'Ground via annulus outside the reviewed land')
    via=P.PCB_VIA(board)
    via.SetViaType(P.VIATYPE_THROUGH)
    via.SetPosition(q)
    via.SetWidth(P.FromMM(spec['diameter_mm']))
    via.SetDrill(P.FromMM(spec['drill_mm']))
    via.SetLayerPair(P.F_Cu,P.B_Cu)
    board.Add(via)
    via.SetNet(board.FindNet('GND'))
    return {'ref':'C804','pad':'2','xy_mm':[x,y],'diameter_mm':.65,'drill_mm':.30,
            'requires_resin_fill_and_copper_cap':True,'supplier_process_accepted':False}
