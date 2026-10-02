"""Blender: dimensionally exact Thin7 partition study, not native routed CAD.
Run: blender -b --python build_thin7_scene.py -- stills|animation OUTPUT_DIR
"""
import bpy, math, json, sys, os
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path(__file__).resolve().parent
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
MODE=args[0] if args else 'stills'
OUT=Path(args[1]) if len(args)>1 else Path('/tmp/panda-thin7-visualization')
OUT.mkdir(parents=True,exist_ok=True)
C=json.loads((ROOT/'thin7-mechanical-contract.json').read_text())
sys.path.insert(0,str(ROOT))
from audit_thin7 import check
check(C)
S=.001
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
for engine in ['BLENDER_EEVEE_NEXT','BLENDER_EEVEE']:
 try:scene.render.engine=engine;break
 except TypeError:pass
scene.render.resolution_x=1920;scene.render.resolution_y=1080
scene.render.resolution_percentage=100;scene.render.fps=12
scene.frame_start=1;scene.frame_end=144
scene.render.image_settings.file_format='PNG'
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.80,.82,.83,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.25
scene.view_settings.view_transform='AgX'
if hasattr(scene,'eevee'):scene.eevee.taa_render_samples=12
def mat(name,c,metal=0,rough=.4,emission=False):
 m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF')
 p.inputs['Base Color'].default_value=(*c,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
 if emission:
  out=m.node_tree.nodes.get('Material Output');e=m.node_tree.nodes.new('ShaderNodeEmission');rgb=(.002,.02,.018) if 'teal' in name else (.0015,.002,.0025) if 'secondary' in name else (.0004,.001,.0015);e.inputs['Color'].default_value=(*rgb,1);e.inputs['Strength'].default_value=1;m.node_tree.links.new(e.outputs[0],out.inputs['Surface'])
 return m
mask=mat('Core soldermask / green',(.017,.145,.075),.08,.36)
dmask=mat('Display soldermask / blue',(.017,.072,.115),.08,.36)
fr4=mat('FR4 edges',(.17,.21,.095),0,.68)
gold=mat('ENIG / exposed pads',(.72,.48,.13),.78,.3)
masked_trace=mat('Copper beneath mask',(.035,.205,.115),.18,.4)
blue_trace=mat('Copper beneath blue mask',(.035,.13,.17),.15,.4)
silver=mat('Brushed shield / steel',(.57,.62,.65),.85,.29)
black=mat('Moulded semiconductor',(.014,.020,.025),.05,.47)
beige=mat('MLCC ceramic',(.49,.37,.22),.05,.4)
inductor=mat('Magnetic core',(.085,.10,.11),.12,.55)
white=mat('Connector polymer',(.79,.79,.72),0,.42)
case=mat('Graphite enclosure concept',(.070,.085,.100),.58,.3)
seal=mat('Seam / black elastomer',(.016,.020,.026),0,.65)
paper=mat('E-paper substrate',(.76,.77,.70),0,.78)
ink=mat('E-paper typography',(.018,.024,.023),0,.62)
foil=mat('Battery foil / conceptual max envelope',(.54,.58,.57),.62,.31)
tape=mat('Insulation / amber',(.61,.29,.035),.12,.46)
hudmat=mat('Annotation / charcoal',(.11,.17,.20),0,.45,True)
accent=mat('Annotation / teal',(.01,.35,.34),0,.5,True)
hudmuted=mat('Annotation / secondary',(.32,.38,.39),0,.5,True)
silk=mat('Silkscreen / warm white',(.70,.76,.70),0,.5)
def empty(name,pos=(0,0,0),rot=(0,0,0)):
 o=bpy.data.objects.new(name,None);scene.collection.objects.link(o);o.location=Vector(pos)*S;o.rotation_euler=rot;return o
def mesh(name,verts,faces,m,parent=None,pos=(0,0,0),rot=(0,0,0)):
 d=bpy.data.meshes.new(name);d.from_pydata([tuple(Vector(v)*S) for v in verts],[],faces);d.update()
 o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.data.materials.append(m);o.parent=parent;o.location=Vector(pos)*S;o.rotation_euler=rot;return o
def contour(w,h,r=0,n=8):
 r=min(r,w/2,h/2)
 if r<=0:return [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]
 pts=[]
 for cx,cy,a in [(w/2-r,-h/2+r,-90),(w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180)]:
  for i in range(n):
   t=math.radians(a+i*90/(n-1));pts.append((cx+r*math.cos(t),cy+r*math.sin(t)))
 return pts
def prism(name,w,h,z,m,parent=None,pos=(0,0,0),r=0,angle=0):
 p=contour(w,h,r);n=len(p);v=[(x,y,k) for k in [-z/2,z/2] for x,y in p]
 f=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 return mesh(name,v,f,m,parent,pos,(0,0,math.radians(angle)))
def ring(name,w,h,iw,ih,z,m,parent=None,pos=(0,0,0),r=4,ir=3):
 a=contour(w,h,r);b=contour(iw,ih,ir);n=len(a);v=[(x,y,k) for k in [-z/2,z/2] for p in [a,b] for x,y in p];f=[]
 for i in range(n):
  j=(i+1)%n;f += [(i,j,j+2*n,i+2*n),(i+n,i+3*n,j+3*n,j+n),(i+2*n,j+2*n,j+3*n,i+3*n),(i,i+n,j+n,j)]
 return mesh(name,v,f,m,parent,pos)
def cylinder(name,r,h,m,parent=None,pos=(0,0,0),n=40):
 v=[(r*math.cos(2*math.pi*i/n),r*math.sin(2*math.pi*i/n),z) for z in [-h/2,h/2] for i in range(n)]
 f=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 o=mesh(name,v,f,m,parent,pos)
 for p in o.data.polygons:
  if len(p.vertices)==4:p.use_smooth=True
 return o
def line(name,points,width,m,parent=None):
 d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D';d.resolution_u=1;d.bevel_depth=width*S/2;d.bevel_resolution=1
 sp=d.splines.new('POLY');sp.points.add(len(points)-1)
 for v,p in zip(sp.points,points):v.co=(*tuple(Vector(p)*S),1)
 o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.data.materials.append(m);o.parent=parent;return o
font=None
for path in [str(OUT/'RenderFont.ttf'),'/System/Library/Fonts/PingFang.ttc','/System/Library/Fonts/STHeiti Light.ttc','/System/Library/Fonts/Supplemental/Arial Unicode.ttf']:
 if Path(path).exists():
  try:font=bpy.data.fonts.load(path);break
  except RuntimeError:pass
def text(name,body,size,m,parent=None,pos=(0,0,0),align='LEFT'):
 d=bpy.data.curves.new(name,'FONT');d.body=body;d.size=size*S*(3.2 if font and 'Panda-CJK' in font.filepath else 1);d.align_x=align;d.extrude=0;d.space_character=1.02
 if font:d.font=font
 o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.data.materials.append(m);o.parent=parent;o.location=Vector(pos)*S;return o
def poly_prism(name,pts,z,m,parent,pos_z):
 n=len(pts);p=[(x-56,37.5-y) for x,y in pts]
 v=[(x,y,k) for k in [-z/2,z/2] for x,y in p]
 faces=[tuple(reversed(range(n))),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 return mesh(name,v,faces,m,parent,(0,0,pos_z))
def offset_window_ring(name,z,m,parent,pos_z,iw=93.8,ih=56.68,ir=1.1):
 a=contour(112,75,5);b=[(x,y+4.315) for x,y in contour(iw,ih,ir)]
 n=len(a);v=[(x,y,k) for k in [-z/2,z/2] for p in [a,b] for x,y in p];f=[]
 for i in range(n):
  j=(i+1)%n;f += [(i,j,j+2*n,i+2*n),(i+n,i+3*n,j+3*n,j+n),(i+2*n,j+2*n,j+3*n,i+3*n),(i,i+n,j+n,j)]
 return mesh(name,v,f,m,parent,(0,0,pos_z))
rear=empty('01 Rear enclosure / 0..6.3mm')
middle=empty('02 Coplanar PCBs + battery / PARTITIONS ONLY')
panel=empty('03 Panel / 2.2mm budget')
front=empty('04 Front bezel / top 7.0mm')
prism('Rear floor / 0.55mm',112,75,.55,case,rear,(0,0,.275),r=5)
shell=ring('Rear perimeter / 0.65mm wall budget',112,75,110.7,73.7,5.75,case,rear,(0,0,3.425),r=5,ir=4.35)
offset_window_ring('Front border above panel / no overlap',.2,case,front,6.9)
offset_window_ring('Panel underside pocket / 0.25mm XY clearance',.5,case,front,6.55,105.83,62.87,.55)
offset_window_ring('Frame seam outside panel pocket',.02,seal,front,6.31,105.83,62.87,.55)
text('Front brand','P A N D A',1.6,silk,front,(-45,-31.6,7.005))
for x in [-12,2,16,30]:
 prism('Button cap / concept',7,2.2,.4,black,front,(x,-31,6.8),r=1)
# Port is a planning aperture. No exact connector solid or access signoff implied.
cut=prism('USB aperture cutter',9,2,3,black,None,(0,-37.15,3.2),r=.5)
bpy.context.view_layer.update();mod=shell.modifiers.new('USB planning aperture','BOOLEAN')
mod.operation='DIFFERENCE';mod.object=cut;bpy.context.view_layer.objects.active=shell
bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
prism('USB interior darkness / conceptual',8.3,.10,2.6,black,rear,(0,-36.3,3.2),r=.35)
for name,b in C['boards'].items():
 bm=mask if name.startswith('Core') else dmask
 poly_prism(name+' EMPTY PCB TEMPLATE',b['outline_xy_mm'],.8,fr4,middle,1.1)
 poly_prism(name+' soldermask face',b['outline_xy_mm'],.02,bm,middle,1.505)
 # Outline-height cages show placement budgets, not imaginary components.
 for k,r in enumerate(b['partition_rects_xyxy_mm']):
  x0,y0,x1,y1=r;x0-=56;x1-=56;y0=37.5-y0;y1=37.5-y1
  line(name+' component ceiling '+str(k),[(x0,y0,3.9),(x1,y0,3.9),(x1,y1,3.9),(x0,y1,3.9),(x0,y0,3.9)],.075,gold,middle)
  for x,y in [(x0,y0),(x1,y1)]:line(name+' cage pillar',[(x,y,1.52),(x,y,3.9)],.05,gold,middle)
text('Core label','CORE / RE-LAYOUT',1.65,silk,middle,(-47,-24.5,1.53))
text('Core status','4 LAYERS   /   EMPTY TEMPLATE',.95,silk,middle,(-47,-27.1,1.53))
text('Display label','DISPLAY',1.8,silk,middle,(14,17,1.53))
text('Display status','45 x 36 / ECO REQUIRED',1.0,silk,middle,(14,13.5,1.53))
# A flat flexible link replaces the previous stacked board pair.
prism('60-contact flex ROUTING ENVELOPE ONLY',30,10,.3,tape,middle,(28.5,-3.5,2.8),r=.3)
text('Flex label','60 CONTACTS / TBD',.95,black,middle,(16,-3.5,2.97))
prism('Main battery complete-pack MAX REQUIREMENT',62,51,3.1,foil,middle,(-22,9,2.25),r=1.5)
prism('Battery insulation budget',62,51,.15,tape,middle,(-22,9,.625),r=1.2)
prism('Battery folded tab budget / not accepted SKU',58,2,.06,tape,middle,(-22,-14.1,3.83),r=.2)
text('Battery title','1S / Li-Po',2.6,black,middle,(-46,10,3.84))
text('Battery capacity','1100 mAh TARGET',1.65,black,middle,(-46,5.4,3.84))
text('Battery dimensions','62 x 51 x 3.1 mm MAX',1.15,black,middle,(-46,1.4,3.84))
text('Battery qualification','SUPPLIER NOT SELECTED',1.1,black,middle,(-46,-2.2,3.84))
# Supplier-declared panel body size retained; no Z or XY scale compression.
prism('Panel 105.33x62.37x2.2mm budget',105.33,62.37,2.2,black,panel,(0,4.315,5.7),r=.55)
prism('Active area 92.8x55.68mm',92.8,55.68,.015,paper,panel,(0,4.315,6.8075),r=.15)
text('Screen heading','PANDA  /  OPEN READ',1.4,ink,panel,(-42,27.7,6.83))
line('Screen rule',[(-42,25.3,6.83),(42,25.3,6.83)],.1,ink,panel)
text('Screen chapter','01   THE OPEN PAGE',1.35,ink,panel,(-42,21.3,6.83))
text('Screen title','Quiet pages.',4.2,ink,panel,(-42,13.8,6.83))
for i,t in enumerate(['A small page can hold a wide world.','Read slowly. Let the details settle.','Leave room for a new thought,','and keep a place for the next page.']):
 text('Screen paragraph '+str(i),t,1.55,ink,panel,(-42,7.5-i*3.5,6.83))
text('Screen footer','42 / 128                         PANDA READER',1.2,ink,panel,(-42,-20.1,6.83))
floor=prism('Studio ground',800,800,.1,mat('Studio',(.68,.71,.73),0,.72),None,(0,0,-1.2),r=2)
camdata=bpy.data.cameras.new('Orthographic / true proportions');camdata.type='ORTHO';camdata.ortho_scale=.205
cam=bpy.data.objects.new('Camera',camdata);scene.collection.objects.link(cam);scene.camera=cam
camdata.lens=55;camdata.clip_start=.001;camdata.clip_end=5
def look(o,p):o.rotation_euler=(Vector(p)*S-o.location).to_track_quat('-Z','Y').to_euler()
for name,power,pos,size in [('Key',.3,(-100,-60,180),160),('Fill',.16,(90,40,130),140),('Rim',.38,(20,100,110),120)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size*S
 o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=Vector(pos)*S;look(o,(0,0,4))
header=text('Header','PANDA / THIN7',6.3,hudmat,cam)
sub=text('Subheader','112 x 75 x 7.0 mm / TWO-BOARD REDESIGN',2.8,hudmuted,cam)
footer=text('Review boundary','PARTITION STUDY / PCB RELAYOUT + BATTERY + RTC QUALIFICATION REQUIRED',2.3,hudmuted,cam)
labels=[]
for title,detail,uv,root,anchor in [
 ('Front frame','Panel face recessed 0.2 mm',(.045,.74),front,(-48,12,6.7)),
 ('Display panel','105.33 x 62.37 x 2.2 mm budget',(.045,.61),panel,(-48,10,5.7)),
 ('One internal layer','2 PCBs + battery in separate XY regions',(.045,.45),middle,(-48,-20,1.1)),
 ('Rear enclosure','0.55 mm floor / 7.0 mm whole device',(.045,.29),rear,(-48,-20,.4))]:
 label=text(title,title,2.8,hudmat,cam);detailobj=text(title+' detail',detail,1.9,hudmuted,cam)
 leader=line(title+' leader',[(0,0,0),(1,1,1)],.06,hudmuted,cam)
 labels.append((label,detailobj,leader,uv,root,Vector(anchor)*S))
def hud(o,u,v,z=.10):
 w=camdata.ortho_scale;h=w/(scene.render.resolution_x/scene.render.resolution_y)
 o.location=((u-.5)*w,(v-.5)*h,-z)
def pose(frame):
 t=(frame-1)/143
 e=0 if t<.16 else min(1,(t-.16)/.25) if t<.41 else 1 if t<.72 else max(0,1-(t-.72)/.28)
 e=e*e*(3-2*e)
 middle.location.z=15*e*S;panel.location.z=46*e*S;front.location.z=82*e*S
 floor.hide_render=e>.1
 aim=(0,0,4+40*e)
 cam.location=Vector((155, -172, 155+50*e))*S;look(cam,aim)
 cam.location+=cam.rotation_euler.to_quaternion()@Vector((-35*e*S,0,0))
 camdata.ortho_scale=(205+95*e)*S
 hud(header,.045,.93);hud(sub,.045,.875);hud(footer,.045,.055)
 bpy.context.view_layer.update()
 for label,detail,leader,uv,root,anchor in labels:
  hud(label,*uv);hud(detail,uv[0],uv[1]-.033)
  label.hide_render=detail.hide_render=leader.hide_render=e<.90
  point=world_to_camera_view(scene,cam,root.matrix_world@anchor)
  w=camdata.ortho_scale;h=w/(scene.render.resolution_x/scene.render.resolution_y)
  a=Vector(((uv[0]+.19-.5)*w,(uv[1]-.012-.5)*h,-.10))
  b=Vector(((point.x-.5)*w,(point.y-.5)*h,-.10))
  for dest,val in zip(leader.data.splines[0].points,[a,b]):dest.co=(*val,1)
 return e
for frame in range(1,145):
 scene.frame_set(frame);pose(frame)
 for o in [middle,panel,front,cam,header,sub,footer,floor]:
  o.keyframe_insert(data_path='location',frame=frame);o.keyframe_insert(data_path='hide_render',frame=frame)
 cam.keyframe_insert(data_path='rotation_euler',frame=frame)
 camdata.keyframe_insert(data_path='ortho_scale',frame=frame)
 for a,b,lineobj,_,_,_ in labels:
  for o in [a,b,lineobj]:o.keyframe_insert(data_path='hide_render',frame=frame);o.keyframe_insert(data_path='location',frame=frame)
  for p in lineobj.data.splines[0].points:p.keyframe_insert(data_path='co',frame=frame)
scene.frame_set(1);pose(1);bpy.context.view_layer.update()
caseobjects=[o for o in scene.objects if o.type=='MESH' and o.parent in [rear,front] and 'darkness' not in o.name]
world=[o.matrix_world@Vector(v) for o in caseobjects for v in o.bound_box]
measured=[round((max(v[i] for v in world)-min(v[i] for v in world))/S,6) for i in range(3)]
if any(abs(a-b)>.0001 for a,b in zip(measured,C['outer_xyz_mm'])):raise ValueError('Assembled enclosure dimension mismatch: '+str(measured))
for obj_name,expected in [('Panel 105.33x62.37x2.2mm budget',[C['panel']['rect_xyxy_mm'][2]-C['panel']['rect_xyxy_mm'][0],C['panel']['rect_xyxy_mm'][3]-C['panel']['rect_xyxy_mm'][1],C['panel']['thickness_budget_mm']]),('Main battery complete-pack MAX REQUIREMENT',C['battery']['maximum_complete_pack_xyz_mm'])]:
 actual=[v/S for v in bpy.data.objects[obj_name].dimensions]
 if any(abs(a-b)>.0001 for a,b in zip(actual,expected)):raise ValueError('Model/contract mismatch: '+obj_name)
if any(tuple(o.scale)!=(1.0,1.0,1.0) for o in scene.objects):raise ValueError('Unexpected object scale')
for path in [ROOT/'thin7-mechanical-contract.json',Path(__file__).resolve()]:
 t=bpy.data.texts.new(path.name);t.write(path.read_text())
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Panda-Thin7.blend'),compress=True)
(OUT/'render-dimension-check.json').write_text(json.dumps({'case_xyz_mm':measured,'all_object_scales_one':True,'native_routed_cad':False,'assembly_frame':1,'exploded_frame':80},indent=2)+'\n')
print('THIN7_SCENE_READY',measured,flush=True)
if MODE=='stills':
 for frame,name in [(1,'Panda-Thin7-Assembled.png'),(80,'Panda-Thin7-Exploded.png')]:
  scene.frame_set(frame);scene.render.filepath=str(OUT/name);bpy.ops.render.render(write_still=True)
elif MODE=='animation':
 (OUT/'frames').mkdir(exist_ok=True);scene.render.image_settings.file_format='JPEG';scene.render.image_settings.quality=94
 scene.render.filepath=str(OUT/'frames/frame_');bpy.ops.render.render(animation=True)
