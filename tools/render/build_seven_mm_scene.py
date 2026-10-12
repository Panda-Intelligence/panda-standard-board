"""Blender native-board whole-device engineering assembly, not manufacturing release.

All PCB meshes come from the checked input GLBs. No geometry is scaled to fit a
thickness label. Package proxy solids and enclosure/cable study parts are explicit.
Output stays external/ignored; rendered frames are removed after verified encoding.
"""
from pathlib import Path
import bpy,sys,json,math,hashlib,argparse,subprocess,shutil
from mathutils import Vector
S=.001
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--mode',choices=['preview','stills','video','all'],default='preview');a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
ROOT=Path(__file__).resolve().parents[2];SRC=a.source.resolve();OUT=a.output.resolve()
if OUT.is_relative_to(ROOT) and not OUT.is_relative_to(ROOT/'.work'):raise ValueError('Generated models/media do not belong in Git')
OUT.mkdir(parents=True,exist_ok=True);D=json.loads((SRC/'scene-metadata.json').read_text())
assert D['schema']=='panda-seven-mm-scene-v1' and D['dimensions_mm']==[75,112,6.8]
for n,b in D['boards'].items():
 assert hashlib.sha256((SRC/(n+'.glb')).read_bytes()).hexdigest()==b['glb_sha256']
 assert hashlib.sha256(Path(b['source_path']).read_bytes()).hexdigest()==b['sha256']
 assert b['native_counts']=={'drc':0,'open':0,'parity':0,'erc':0}
scene=bpy.context.scene;bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1920;scene.render.resolution_y=1080;scene.render.resolution_percentage=100;scene.render.fps=24
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.view_settings.view_transform='AgX'
try:scene.view_settings.look='AgX - Medium High Contrast'
except Exception:pass
if hasattr(scene,'eevee') and hasattr(scene.eevee,'taa_render_samples'):scene.eevee.taa_render_samples=16
bpy.context.preferences.filepaths.save_version=0
world=bpy.data.worlds.new('Warm technical studio');world.use_nodes=True;scene.world=world;world.node_tree.nodes['Background'].inputs[0].default_value=(.8,.84,.86,1);world.node_tree.nodes['Background'].inputs[1].default_value=.30

def material(name,color,metal=0,rough=.45,emission=False):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;q=m.node_tree.nodes.get('Principled BSDF');q.inputs['Base Color'].default_value=(*color,1);q.inputs['Metallic'].default_value=metal;q.inputs['Roughness'].default_value=rough
 if emission:
  e=m.node_tree.nodes.new('ShaderNodeEmission');e.inputs['Color'].default_value=(*color,1);e.inputs['Strength'].default_value=1;m.node_tree.links.new(e.outputs[0],m.node_tree.nodes['Material Output'].inputs[0])
 return m
black=material('Molded package',(.015,.019,.025));metal=material('Tin and shield',(.56,.62,.66),.85,.27);gold=material('ENIG / contacts',(.78,.51,.13),.86,.22)
ceramic=material('Ceramic body',(.49,.34,.19));green=material('Solder mask',(.006,.12,.071),.12,.38);silk=material('Package markings',(.8,.86,.83));nylon=material('Connector LCP',(.62,.66,.62));graphite=material('Case graphite',(.055,.069,.083),.18,.31)
frame_mat=material('Front frame',(.09,.11,.13),.12,.32);paper=material('E-paper',(.83,.84,.79),0,.88);glass=material('Touch glass rim',(.028,.036,.04),.25,.21)
foil=material('Pouch envelope',(.48,.54,.58),.67,.3);amber=material('Unqualified flex routing envelope',(.7,.30,.065),.15,.36);teal=material('Key caps',(.015,.27,.23),.12,.35)
ink=material('HUD dark',(.013,.022,.026),0,1,True);muted=material('HUD secondary',(.19,.23,.25),0,1,True);accent=material('HUD teal',(.015,.32,.29),0,1,True);warning=material('HUD open review',(.5,.24,.05),0,1,True)
white=material('Studio floor',(.86,.88,.875),0,.72)

def empty(name,parent=None):
 o=bpy.data.objects.new(name,None);scene.collection.objects.link(o);o.parent=parent;return o

def mesh(name,verts,faces,mat,parent=None):
 me=bpy.data.meshes.new(name);me.from_pydata([tuple(Vector(v)*S) for v in verts],[],faces);me.update();o=bpy.data.objects.new(name,me);scene.collection.objects.link(o);o.parent=parent;o.data.materials.append(mat);return o

def box(name,xyz,size,mat,parent=None,r=.06):
 x,y,z=xyz;w,h,d=size;verts=[(x+i*w/2,y+j*h/2,z+k*d/2) for i,j,k in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
 o=mesh(name,verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat,parent)
 if r:
  m=o.modifiers.new('Edge radius','BEVEL');m.width=min(r,min(size)*.2)*S;m.segments=2
 return o

def cylinder(name,xyz,r,h,mat,parent=None,n=48):
 x,y,z=xyz;v=[(x+r*math.cos(i*math.tau/n),y+r*math.sin(i*math.tau/n),z+k*h/2) for k in [-1,1] for i in range(n)]
 return mesh(name,v,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],mat,parent)

def text(name,body,xyz,size,mat,parent=None,align='LEFT'):
 cu=bpy.data.curves.new(name,'FONT');cu.body=body;cu.size=size*S;cu.align_x=align;cu.space_character=1.08;o=bpy.data.objects.new(name,cu);scene.collection.objects.link(o);o.parent=parent;o.location=Vector(xyz)*S;o.data.materials.append(mat);return o

def line(name,pts,width,mat,parent=None):
 cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.bevel_depth=width*S/2;cu.bevel_resolution=1;sp=cu.splines.new('POLY');sp.points.add(len(pts)-1)
 for v,pnt in zip(sp.points,pts):v.co=(*tuple(Vector(pnt)*S),1)
 o=bpy.data.objects.new(name,cu);scene.collection.objects.link(o);o.parent=parent;o.data.materials.append(mat);return o

def contour(w,h,r,n=8):
 pts=[]
 for x,y,ang in [(w/2-r,-h/2+r,-90),(w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180)]:
  for j in range(n):q=math.radians(ang+90*j/(n-1));pts.append((x+r*math.cos(q),y+r*math.sin(q)))
 return pts

def prism(name,w,h,z0,z1,mat,parent=None,r=1,cx=0,cy=0):
 pts=contour(w,h,min(r,w/2,h/2));n=len(pts);v=[(x+cx,y+cy,z) for z in [z0,z1] for x,y in pts]
 return mesh(name,v,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],mat,parent)

def ring(name,w,h,iw,ih,z0,z1,mat,parent=None,r=3,ir=1,inner_cy=0):
 a=contour(w,h,r);b=[(x,y+inner_cy) for x,y in contour(iw,ih,ir)];n=len(a);v=[(x,y,z) for z in [z0,z1] for ps in [a,b] for x,y in ps];f=[]
 for i in range(n):
  j=(i+1)%n;f.extend([(i,j,j+2*n,i+2*n),(i+n,i+3*n,j+3*n,j+n),(i+2*n,j+2*n,j+3*n,i+3*n),(i,i+n,j+n,j)])
 return mesh(name,v,f,mat,parent)

def cut(o,xyz,size):
 cutter=box('temporary case opening',xyz,size,black,o.parent,r=0);bpy.context.view_layer.objects.active=o;m=o.modifiers.new('Opening','BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=cutter;bpy.ops.object.modifier_apply(modifier=m.name);bpy.data.objects.remove(cutter,do_unlink=True)

assembly=empty('PANDA7 / 112 x75 x6.8 nominal');assembly.location.x=.02
parts={name:empty(name,assembly) for name in ['Rear shell','PCB set','Pouch cell','FFC links','Screen module','Front frame','Side keys','microSD card']}
# Board meshes are not scaled. KiCad GLB already uses metres with Z up and -Y.
models=[]
for name,meta in D['boards'].items():
 before=set(scene.objects);bpy.ops.import_scene.gltf(filepath=str(SRC/(name+'.glb')));imported=set(scene.objects)-before
 anchors=[o for o in imported if o.parent not in imported]
 for root in anchors:
  root.parent=parts['PCB set'];root.location+=Vector((-37.5,56,.75))*S;root.name=name+' / native board'
 for o in imported:
  if o.type!='MESH':continue
  for slot in o.material_slots:
   m=slot.material
   if m is None or not m.use_nodes:continue
   q=m.node_tree.nodes.get('Principled BSDF')
   if not q:continue
   low=(o.name+' '+o.data.name+' '+m.name).lower()
   if 'soldermask' in low:q.inputs['Base Color'].default_value=(.006,.09,.047,1);q.inputs['Alpha'].default_value=1;q.inputs['Roughness'].default_value=.39
   elif 'silkscreen' in low:q.inputs['Base Color'].default_value=(.84,.88,.85,1)
 for f in meta['components']:
  ref=f['ref'];bdy=f['fab_bbox'];x=(bdy[0]+bdy[2])/2-37.5;y=56-(bdy[1]+bdy[3])/2;w=bdy[2]-bdy[0];h=bdy[3]-bdy[1];top=.75+meta['thickness_mm'];par=parts['PCB set'];prefix=name+'/'+ref
  if f['excluded_from_bom'] or ref.startswith(('TP','J507')):continue
  nominal=f['reviewed_height_mm'];estimated=nominal is None
  if nominal is None:
   nominal=.55 if ref.startswith(('R','C','D')) else .9 if ref.startswith(('U','Y')) else 1.15 if ref.startswith('Q') else 1.4 if ref.startswith('L') else 1.0
  if ref=='U501' and name=='Core':w=h=7.;nominal=.9;x=f['xy'][0]-37.5;y=56-f['xy'][1]
  if ref=='U506':nominal=1.75
  if ref.startswith('BT'):
   x=f['xy'][0]-37.5;y=56-f['xy'][1];cylinder(prefix+' / primary coin-cell proxy',(x,y,top+.9),6.25,1.6,metal,par,64);text(prefix+' mark','CR1216',(x,y,top+1.72),1.2,black,par,'CENTER');models.append({'ref':prefix,'proxy':True,'height_mm':1.6,'source':'CR1216 nominal; tab insulation acceptance pending'});continue
  if ref=='J201' and name=='Core':
   x=f['xy'][0]-37.5;y=56-f['xy'][1]-3.25;low=top-.78;zh=2.56
   box(prefix+' shell roof',(x,y,low+zh-.08),(8.94,6.5,.16),metal,par,.07)
   box(prefix+' shell floor',(x,y,low+.08),(8.94,6.5,.16),metal,par,.07)
   for xx in [-4.39,4.39]:box(prefix+' shell side',(x+xx,y,low+zh/2),(.16,6.5,zh-.12),metal,par,.07)
   box(prefix+' tongue',(x,y-1.35,low+zh/2),(6.6,3.65,.45),black,par,.1)
   for i in range(12):
    for zz in [-.245,.245]:box(prefix+' contact',(x-2.75+i*.5,y-1.9,low+zh/2+zz),(.23,1.9,.04),gold,par,0)
   models.append({'ref':prefix,'proxy':True,'height_mm':zh,'lower_than_board_top_mm':.78,'source':'MUP U22401-17 Rev2 body drawing; maximum tolerances pending'});continue
  if ref=='J501' and name=='Core':
   # Body datum and entry direction come from the native XUNPU land definition.
   x=f['xy'][0]-37.5+6.7;y=56-f['xy'][1];w=14.5;h=14.75;nominal=1.8
   box(prefix+' socket base',(x,y,top+.28),(w,h,.5),black,par,.08);box(prefix+' shield roof',(x,y,top+1.69),(w,h,.2),metal,par,.12)
   for yy in [y-h/2+.15,y+h/2-.15]:box(prefix+' side rail',(x,yy,top+.95),(w,.3,1.5),metal,par,.04)
   models.append({'ref':prefix,'proxy':True,'height_mm':1.8,'source':'XUNPU body nominal1.8,max2.0mm'});continue
  if ref.startswith('SW'):
   nominal=1.5;box(prefix+' metal switch',(f['xy'][0]-37.5,56-f['xy'][1],top+.65),(3,4.5,1.3),metal,par,.12);box(prefix+' actuator',(f['xy'][0]-37.5+1.7,56-f['xy'][1],top+.9),(.65,1.8,.75),black,par,.06)
  elif ref.startswith('J'):
   box(prefix+' connector proxy',(x,y,top+.40),(max(.5,w*.94),max(.6,h*.86),.8),nylon,par,.06);box(prefix+' latch',(x,y,top+.9),(max(.4,w*.88),max(.4,h*.35),.2),black,par,.04)
  else:
   m=ceramic if ref.startswith('C') else black
   if ref.startswith('L'):m=black
   box(prefix+' package proxy',(x,y,top+.05+nominal/2),(max(.35,w*.91),max(.35,h*.91),nominal),m,par,.06)
   if ref.startswith(('U','Q')):cylinder(prefix+' pin-one',(x-w*.30,y+h*.28,top+nominal+.06),min(.13,w*.08),.01,silk,par,12)
   if ref=='U501':text(prefix+' marking','ESP32-S3',(x,y,top+nominal+.065),.85,silk,par,'CENTER')
  models.append({'ref':prefix,'proxy':True,'height_mm':nominal,'height_estimated':estimated})
# Enclosure geometry in the actual requested envelope, not the old22mm model.
rear=prism('Rear cover / nominal .55mm floor',75,112,0,.55,graphite,parts['Rear shell'],3)
walls=ring('Rear perimeter walls',75,112,72.8,109.8,.50,4.60,graphite,parts['Rear shell'],3,2)
cut(walls,(0,-55.7,2.1),(10.2,4,3.5));cut(rear,(0,-52.5,.65),(10,7.4,.6))
cut(walls,(37.1,-40,2.75),(4,16.8,2.7))
for yy in [31.5,47.5]:cut(walls,(37.0,yy,2.55),(4,5.4,2.3))
# Board retention lips are case-side study features; no fictitious PCB holes.
for yy in [-18,14,38]:box('Core retaining lip',(35.7,yy,1.3),(1.4,3,.4),graphite,parts['Rear shell'],.1)
for yy in [-35,-17]:box('Display retaining lip',(-35.7,yy,1.3),(1.4,3,.4),graphite,parts['Rear shell'],.1)
# Stepped underside pocket: the screen body must not intersect the frame.
front=ring('Front frame / panel-body clearance pocket',75,112,63.17,106.13,4.60,6.27,frame_mat,parts['Front frame'],3,.75,1.335)
ring('Front frame / thin aperture lip',75,112,56.8,93.9,6.27,6.8,frame_mat,parts['Front frame'],3,.75,1.335)
text('Front brand','P A N D A',(0,-52.7,6.815),1.7,silk,parts['Front frame'],'CENTER')
# Separate screen body, real FT01C nominal stack, not scaled bare glass.
prism('FT01C touch/frontlight module',62.37,105.33,4.27,6.25,glass,parts['Screen module'],.45,0,1.335)
box('E-paper active area',(0,1.335,6.269),(55.68,92.8,.018),paper,parts['Screen module'],.3)
text('Reading interface title','PANDA READER',(-23,39,6.29),2.05,black,parts['Screen module'])
text('Reading interface chapter','A quieter way to read',(-23,31.5,6.29),2.1,black,parts['Screen module'])
for i,width in enumerate([43,46,39,45,42,46,35,44,46,40,45,32,45,44,38]):
 box('E-paper typesetting rule',(-23+width/2,24.5-i*3.9,6.287),(width,.28,.006),black,parts['Screen module'],0)
text('Reading progress','12 / 248',(-23,-39,6.29),1.65,black,parts['Screen module'])
# Real selected nominal raw-cell envelope, protection is on Core.
prism('275060 pouch / nominal only',50,60,.75,3.45,foil,parts['Pouch cell'],1.6,-10,24)
text('Pouch label','275060',(-10,35,3.465),3,black,parts['Pouch cell'],'CENTER')
text('Pouch capacity','3.7 V  /  1100 mAh',(-10,28,3.465),1.65,black,parts['Pouch cell'],'CENTER')
text('Pouch status','MAXIMUM SIZE TO CONFIRM',(-10,19,3.465),1.1,black,parts['Pouch cell'],'CENTER')
for i in [-1,1]:box('Cell welded tab',(-10+i*5,-7,1.0),(4,3,.15),metal,parts['Pouch cell'],0)
# FFC bands span the exact coplanar connector pairs; supplier cut length remains open.
for y,count in [(56-76.2,40),(56-94.2,20)]:
 x0,x1=35-37.5,42.5-37.5;width=count*.5+.7
 box('FFC '+str(count)+'P / cut-length study',((x0+x1)/2,y,2.04),(x1-x0+3.5,width,.3),amber,parts['FFC links'],.025)
 for j in range(count):box('FFC conductor',((x0+x1)/2,y-(count-1)*.25+j*.5,2.197),(x1-x0+2.4,.12,.005),gold,parts['FFC links'],0)
# Simplified panel-tail envelopes explicitly remain an assembly study.
for name,x,y,wid in [('Display FPC',-19.5,-43,12.5),('Touch tail',24,8,3.5),('Frontlight tail',24,-3,3.5)]:
 box(name+' folded envelope',(x,y,4.16),(wid,8,.12),amber,parts['Screen module'],.02)
for yy in [31.5,47.5]:
 prism('Side button cap',.8,4.8,1.5,3.5,teal,parts['Side keys'],.18,37.08,yy)
 box('Button actuator study',(35.8,yy,2.5),(2.0,1.4,.7),black,parts['Side keys'],.06)
# Removable card, not included in enclosure dimensions.
prism('microSD removable card',15,11,2.04,3.04,black,parts['microSD card'],.6,30.3,-40)
text('microSD marking','SD',(30.3,-40,3.057),1.4,silk,parts['microSD card'],'CENTER')
for j in range(8):box('microSD contacts',(24.8,-43.6+j*.9,2.022),(3,.5,.035),gold,parts['microSD card'],.02)
# Studio and camera. No scale transform is applied to any product group.
prism('Studio ground',650,650,-24.5,-24,white,None,10)
camdata=bpy.data.cameras.new('Technical camera');camera=bpy.data.objects.new('Technical camera',camdata);scene.collection.objects.link(camera);scene.camera=camera
camera.location=Vector((195,-235,205))*S;target=Vector((13,0,16))*S;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=.305;camdata.clip_start=.01;camdata.clip_end=4
for name,pos,energy,size in [('Key',(100,-70,240),1.5,.2),('Fill',(-150,-5,130),.85,.16),('Rim',(20,180,190),1.2,.15)]:
 data=bpy.data.lights.new(name,'AREA');o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=Vector(pos)*S;o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler();data.energy=energy;data.shape='DISK';data.size=size
hud=empty('Technical labels',camera)
text('Title','PANDA  /  SEVEN',(-142,74,-100),5.4,ink,hud)
subtitle=text('Subtitle','112 x 75 mm  |  6.8 mm nominal case',(-142,66,-100),3.0,ink,hud)
phase=text('Phase','ASSEMBLED',(-142,56,-100),3.2,accent,hud)
labels=[]
for i,(title,sub) in enumerate([('01  FRONT FRAME','Window and side openings'),('02  SCREEN STACK','Touch + frontlight + e-paper'),('03  FFC LINKS','40P + 20P / coplanar'),('04  PCB SET','Core 4-layer + Display 2-layer'),('05  POUCH CELL','275060 / nominal envelope'),('06  REAR HOUSING','Keys + USB-C + microSD')]):
 yy=39-i*13.5;labels.append(text('Callout '+str(i),title,(-142,yy,-100),3.7,ink,hud));labels.append(text('Subcallout '+str(i),sub,(-142,yy-5.3,-100),2.6,ink,hud))
text('Verification scope','ENGINEERING ASSEMBLY STUDY  /  NOT AN ORDER RELEASE',(-142,-71,-100),2.6,warning,hud)
text('Qualification note','Native PCB geometry. Package and cable proxies. Supplier maximum dimensions pending.',(-142,-77,-100),2.0,ink,hud)
# Smooth assembly/disassembly animation. Exploded gaps are visualization distances.
shifts={'Rear shell':(0,0,-20),'PCB set':(0,0,3),'Pouch cell':(-45,-40,8),'FFC links':(0,0,20),'Screen module':(0,0,34),'Front frame':(0,0,52),'Side keys':(17,0,3),'microSD card':(22,0,3)}
def smooth(v):v=max(0,min(1,v));return v*v*(3-2*v)
def pose(frame):
 if frame<=64:k=0
 elif frame<188:k=smooth((frame-64)/124)
 elif frame<330:k=1
 elif frame<450:k=1-smooth((frame-330)/120)
 else:k=0
 angle=-.10+.46*smooth((frame-105)/175)-.46*smooth((frame-330)/140)
 assembly.rotation_euler.z=angle
 for name,shift in shifts.items():parts[name].location=Vector(shift)*S*k
 phase.data.body='EXPLODED ASSEMBLY' if k>.98 else 'ASSEMBLED' if k<.02 else 'ASSEMBLY SEQUENCE'
 for o in labels:o.hide_render=k<.65
 bpy.context.view_layer.update()
 return k
for fr in [1,64,100,150,188,240,300,330,390,450,480]:
 pose(fr)
 for o in [assembly,*parts.values()]:o.keyframe_insert(data_path='location',frame=fr);o.keyframe_insert(data_path='rotation_euler',frame=fr)
scene.frame_start=1;scene.frame_end=480
report={'schema':'panda-seven-mm-render-v1','revision':D['revision'],'source_pcb_sha256':{n:b['sha256'] for n,b in D['boards'].items()},'case_nominal_xyz_mm':[75,112,6.8],'maximum_product_target_mm':7,'native_input_scale_changed':False,'source_native_counts':{n:b['native_counts'] for n,b in D['boards'].items()},'package_proxy_inventory':models,'full_enclosure_screen_keys_interfaces_included':True,'all_60_ffc_contacts_represented':True,'case_and_harness_are_engineering_studies':True,'physical_fit_qualified':False,'manufacturing_release':False}
(OUT/'RENDER-SCOPE.json').write_text(json.dumps(report,indent=2)+'\n')
scene.frame_set(240);pose(240);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Panda7-Revision-D.blend'))
def render(frame,path,width=1920,height=1080):
 scene.frame_set(frame);pose(frame);scene.render.resolution_x=width;scene.render.resolution_y=height;scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
if a.mode=='preview':render(240,OUT/'preview.png',1600,900)
if a.mode in ['stills','all']:
 render(240,OUT/'Panda7-Exploded-4K.png',3840,2160);render(1,OUT/'Panda7-Assembled-4K.png',3840,2160)
 for n in ['Screen module','Front frame']:parts[n].hide_render=True
 for n in ['Screen module','Front frame']:
  for o in parts[n].children_recursive:o.hide_render=True
 render(1,OUT/'Panda7-Internal-4K.png',3840,2160)
 for n in ['Screen module','Front frame']:
  parts[n].hide_render=False
  for o in parts[n].children_recursive:o.hide_render=False
if a.mode in ['video','all']:
 if shutil.disk_usage(OUT).free<650*1024*1024:raise ValueError('Not enough room for bounded video frames')
 frames=OUT/'_video_frames';frames.mkdir(exist_ok=True)
 for fr in range(1,481):render(fr,frames/('frame_%04d.png'%fr))
 video=OUT/'Panda7-Full-Assembly-1080p.mp4';ffmpeg=shutil.which('ffmpeg') or '/opt/homebrew/bin/ffmpeg'
 subprocess.run([ffmpeg,'-y','-loglevel','warning','-framerate','24','-i',str(frames/'frame_%04d.png'),'-c:v','libx264','-preset','medium','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],check=True)
 ffprobe=shutil.which('ffprobe') or '/opt/homebrew/bin/ffprobe';probe=json.loads(subprocess.check_output([ffprobe,'-v','error','-show_streams','-show_format','-of','json',str(video)],text=True));stream=next(s for s in probe['streams'] if s['codec_type']=='video');assert int(stream['nb_frames'])==480 and stream['width']==1920 and stream['height']==1080
 (OUT/'VIDEO-VERIFICATION.json').write_text(json.dumps({'frames':480,'fps':24,'seconds':20,'codec':stream['codec_name'],'width':1920,'height':1080,'sha256':hashlib.sha256(video.read_bytes()).hexdigest()},indent=2)+'\n')
 for f in frames.glob('frame_*.png'):f.unlink()
 frames.rmdir()
print('PANDA7_RENDER_COMPLETE',a.mode,OUT,flush=True)
