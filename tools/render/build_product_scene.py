"""Whole-product prototype scene around source-bound native Split-C1. No native CAD writes. 22mm fixture, NOT the 7mm product."""
import bpy,sys,json,math,hashlib
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
import argparse
REPO=Path(__file__).resolve().parents[2]
a=argparse.ArgumentParser();a.add_argument('--source',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a.add_argument('--mode',choices=['preview','stills','video'],default='preview')
args=a.parse_args(sys.argv[sys.argv.index('--')+1:]);R=args.source.resolve();OUT=args.output.resolve();MODE=args.mode
if OUT.is_relative_to(REPO) and not OUT.is_relative_to(REPO/'.work'):raise ValueError('Generated renders must remain outside Git source')
OUT.mkdir(parents=True,exist_ok=True)
D=json.loads((R/'scene-metadata.json').read_text())
for board in D['boards'].values():
 assert hashlib.sha256((REPO/board['source_path']).read_bytes()).hexdigest()==board['sha256']
C=json.loads((REPO/'hardware/thin18-compact/split-c1-prototype-enclosure.json').read_text())
sys.path.insert(0,str(Path(__file__).resolve().parent))
from verify_product_envelope import screen
SCREEN=screen(C,D)
scene=bpy.data.scenes.new('Panda Split-C1 / actual main');bpy.context.window.scene=scene
for eng in ['BLENDER_EEVEE','BLENDER_EEVEE_NEXT']:
 try:scene.render.engine=eng;break
 except TypeError:pass
scene.render.resolution_x=1920;scene.render.resolution_y=1080;scene.render.resolution_percentage=100;scene.render.fps=24
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.world=bpy.data.worlds.new('Panda white studio');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.82,.86,.87,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.65
wn=scene.world.node_tree;bg=wn.nodes['Background'];lightpath=wn.nodes.new('ShaderNodeLightPath');paperbg=wn.nodes.new('ShaderNodeBackground');paperbg.inputs[0].default_value=(1,1,1,1);paperbg.inputs[1].default_value=5;mix=wn.nodes.new('ShaderNodeMixShader');wn.links.new(lightpath.outputs['Is Camera Ray'],mix.inputs[0]);wn.links.new(bg.outputs[0],mix.inputs[1]);wn.links.new(paperbg.outputs[0],mix.inputs[2]);wn.links.new(mix.outputs[0],wn.nodes['World Output'].inputs[0])
scene.view_settings.view_transform='AgX'
try:scene.view_settings.look='AgX - Medium High Contrast'
except TypeError:pass
if hasattr(scene,'eevee'):
 scene.eevee.taa_render_samples=32
 if hasattr(scene.eevee,'use_gtao'):scene.eevee.use_gtao=True
S=.001

def mat(name,color,metal=0,rough=.42,emission=False):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
 p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
 if emission:
  out=m.node_tree.nodes.get('Material Output');em=m.node_tree.nodes.new('ShaderNodeEmission');em.inputs['Color'].default_value=(*color,1);em.inputs['Strength'].default_value=1;m.node_tree.links.new(em.outputs[0],out.inputs['Surface'])
 return m
black=mat('Package / molded black',(.012,.018,.020),.05,.4);metal=mat('Tin / contacts',(.55,.60,.64),.8,.25)
gold=mat('ENIG contact plating',(.72,.48,.14),.82,.22);white=mat('Connector nylon',(.74,.77,.71),0,.35)
ceramic=mat('Ceramic',(.43,.29,.15),0,.4);ferrite=mat('Inductor / ferrite',(.075,.087,.09),.1,.45)
green=mat('Manufactured green mask',(.012,.14,.07),.12,.34);silk=mat('Silk white',(.8,.87,.81),0,.5)
shield=mat('Shield / brushed metal',(.58,.63,.65),.75,.3);dark=mat('Typography',(.006,.02,.025),0,.8,True)
muted=mat('Secondary typography',(.035,.055,.065),0,.8,True);teal=mat('Accent typography',(.004,.22,.19),0,.7,True)

def empty(name,parent=None,pos=(0,0,0)):
 o=bpy.data.objects.new(name,None);scene.collection.objects.link(o);o.parent=parent;o.location=Vector(pos)*S;return o

def mesh(name,verts,faces,material,parent=None):
 me=bpy.data.meshes.new(name);me.from_pydata([tuple(Vector(v)*S) for v in verts],[],faces);me.update()
 o=bpy.data.objects.new(name,me);scene.collection.objects.link(o);o.data.materials.append(material);o.parent=parent;return o

def box(name,xyz,whd,material,parent=None,r=.08):
 x,y,z=xyz;w,h,d=whd
 v=[(x+a*w/2,y+b*h/2,z+c*d/2) for a,b,c in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
 o=mesh(name,v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],material,parent)
 if r>0:
  mod=o.modifiers.new('Manufacturing edge softness','BEVEL');mod.width=min(r,min(whd)*.18)*S;mod.segments=2
 return o

def cyl(name,xyz,r,h,material,parent=None,n=40):
 x,y,z=xyz;v=[(x+r*math.cos(i*2*math.pi/n),y+r*math.sin(i*2*math.pi/n),z+k*h/2) for k in [-1,1] for i in range(n)]
 o=mesh(name,v,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],material,parent)
 for p in o.data.polygons:
  if len(p.vertices)==4:p.use_smooth=True
 return o

def text(name,body,size,material,parent=None,pos=(0,0,0)):
 cu=bpy.data.curves.new(name,'FONT');cu.body=body;cu.size=size*S;cu.space_character=1.05
 if 'PandaRenderFont' in bpy.data.fonts:cu.font=bpy.data.fonts['PandaRenderFont']
 o=bpy.data.objects.new(name,cu);scene.collection.objects.link(o);o.data.materials.append(material);o.parent=parent;o.location=Vector(pos)*S;return o

def line(name,pts,width,material,parent=None):
 cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.bevel_depth=width*S/2;cu.bevel_resolution=1
 sp=cu.splines.new('POLY');sp.points.add(len(pts)-1)
 for a,p in zip(sp.points,pts):a.co=(*tuple(Vector(p)*S),1)
 o=bpy.data.objects.new(name,cu);scene.collection.objects.link(o);o.parent=parent;o.data.materials.append(material);return o

font_path=Path('/System/Library/Fonts/Supplemental/Arial.ttf')
if font_path.exists():
 font=bpy.data.fonts.load(str(font_path));font.name='PandaRenderFont'
assembly={};groups={};inventories={};approx=[]
for board,b in D['boards'].items():
 before=set(scene.objects);bpy.ops.import_scene.gltf(filepath=str(R/(board+'.glb')))
 imported=set(scene.objects)-before;root=next(o for o in imported if o.parent is None);root.name=board+' / native CAD'
 anchor=empty(board+' / assembly placement');root.parent=anchor;assembly[board]=anchor
 if board=='Core-C1':anchor.location=Vector((-48,34,0))*S
 else:anchor.location=Vector((-10,-32,-1.5))*S;anchor.rotation_euler.x=math.pi
 groups[board]={side:empty(board+' / '+side+' package group',root) for side in ['F','B']}
 refs={f['ref']:f for f in b['components']};present={}
 for o in tuple(root.children):
  if o.name in refs:
   ref=o.name;present[ref]=o;o.parent=groups[board][refs[ref]['side']];o.name=board+'/'+ref
  elif o.type=='MESH':
   nam=o.data.name.lower()
   for slot in o.material_slots:
    m=slot.material
    if m is None:continue
    p=m.node_tree.nodes.get('Principled BSDF')
    if p:
     if 'soldermask' in nam:
      p.inputs['Base Color'].default_value=(.007,.062,.025,1);p.inputs['Alpha'].default_value=1;p.inputs['Metallic'].default_value=.12;p.inputs['Roughness'].default_value=.34
     elif 'silkscreen' in nam:p.inputs['Base Color'].default_value=(.91,.92,.86,1);p.inputs['Alpha'].default_value=1
     elif 'pcb' in nam:p.inputs['Alpha'].default_value=1
 inventories[board]={'native_model_refs':sorted(present),'approximate_model_refs':sorted(set(refs)-set(present)),'component_count':len(refs)}
 for ref,f in refs.items():
  if ref in present:continue
  approx.append(board+'/'+ref);parent=groups[board][f['side']];sign=1 if f['side']=='F' else -1;surface=b['thickness_mm'] if sign==1 else 0
  x0,y0,x1,y1=f['fab_bbox'];x=(x0+x1)/2;y=-(y0+y1)/2;w=x1-x0;h=y1-y0;zheight=f['height_screen_mm'] or (.65 if ref.startswith(('C','R')) else .65 if ref in ['U402','U403','U404','U405','U902'] else 1.2)
  prefix=board+'/'+ref+' / simplified '
  if ref=='C301':
   x=f['xy'][0];y=-f['xy'][1];cyl(prefix+'insulation',(x,y,surface+3.05),9.35,6.1,black,parent,96);cyl(prefix+'cap',(x,y,surface+6.12),9.05,.22,shield,parent,96)
   text(prefix+'mark','KAMCAP',2.0,dark,parent,(x-5.7,y+1.1,surface+6.25));text(prefix+'rating','1 F / 5.5 V',1.35,dark,parent,(x-4.9,y-2,surface+6.25))
   for p in f['pads']:box(prefix+'lead',(*[p['xy'][0],-p['xy'][1]],surface+1.0),(1,.2,2.0),metal,parent)
   continue
  if ref=='U501':
   box(prefix+'module',(x,y,surface+.4),(18,19.2,.8),green,parent)
   box(prefix+'RF shield',(x,y+.1,surface+1.8),(16,16,2),shield,parent,.2)
   text(prefix+'brand','ESP32-S3',1.6,dark,parent,(x-6.1,y+1.5,surface+2.82));text(prefix+'memory','N16R8  /  WROOM-1U',.65,dark,parent,(x-6.1,y-1.5,surface+2.83))
   cyl(prefix+'external RF',(x+6.8,y-7.4,surface+1.05),.8,.6,gold,parent)
  elif ref=='J201':
   box(prefix+'base',(x,y,surface+.24),(8.9,7.3,.45),black,parent)
   box(prefix+'roof',(x,y,surface+3.1),(9.0,7.3,.28),shield,parent)
   for xx in [x-4.4,x+4.4]:box(prefix+'shell',(xx,y,surface+1.65),(.28,7.3,2.7),shield,parent)
   box(prefix+'tongue',(x,y-1.5,surface+1.65),(6.7,4.1,.45),black,parent)
   for i in range(12):box(prefix+'USB contact',(x-2.75+i*.5,y-2.5,surface+1.91),(.2,1.8,.07),gold,parent,0)
  elif ref=='J501':
   box(prefix+'socket base',(x,y,surface+.35),(w,h,.7),black,parent)
   box(prefix+'socket shield',(x,y,surface+1.7),(w,h,.25),shield,parent)
   for yy in [y-h/2+.15,y+h/2-.15]:box(prefix+'socket rail',(x,yy,surface+1), (w,.3,1.4),shield,parent)
  elif ref in ['J601','J1']:
   zheight=.75;box(prefix+'mating base',(x,y,surface+sign*.19),(w,h,.38),black,parent)
   for yy in [y-h*.42,y+h*.42]:box(prefix+'mating rim',(x,yy,surface+sign*.55),(w,.28,.7),white,parent)
  elif ref.startswith('J'):
   box(prefix+'connector',(x,y,surface+sign*zheight*.4),(w*.96,h*.94,zheight*.8),white,parent)
   box(prefix+'connector slot',(x,y-h*.10,surface+sign*zheight*.82),(w*.82,h*.46,.06),black,parent,0)
   if ref in ['J803','J804','J2']:box(prefix+'FPC latch',(x,y-h*.34,surface+sign*zheight*.9),(w*.92,.65,.2),black,parent)
  elif ref.startswith('L'):
   box(prefix+'magnetics',(x,y,surface+sign*zheight*.5),(w*.93,h*.92,zheight),ferrite,parent,.15)
   if sign==1:text(prefix+'mark','1R0' if '1R0' in str(f['mpn']) else 'R47' if 'R47' in str(f['mpn']) else '470',.8,silk,parent,(x-1,y-.2,surface+zheight+.01))
  else:
   material=ceramic if ref.startswith('C') else black
   if ref.startswith('Q'):
    w,h=(1.4,2.9) if abs(f['angle']) in [0,180] else (2.9,1.4);x,y=f['xy'][0],-f['xy'][1]
   box(prefix+'body',(x,y,surface+sign*(.07+zheight*.5)),(max(.4,w*.91),max(.4,h*.91),zheight),material,parent)
   if ref.startswith(('U','Q')) and sign>0:cyl(prefix+'pin 1 mark',(x-w*.32,y+h*.31,surface+zheight+.08),min(.14,w*.10),.016,silk,parent,16)
  for p in f['pads']:
   if not p['n'] or p['drill']!=[0,0]:continue
   box(prefix+'termination '+p['n'],(p['xy'][0],-p['xy'][1],surface+sign*.15),(max(.12,p['size'][0]*.82),max(.12,p['size'][1]*.82),.16),metal,parent,.02)


# All geometry below is explicitly a prototype enclosure / envelope study.
case_mat=mat('Prototype enclosure graphite',(.035,.045,.055),.12,.38)
key_mat=mat('Prototype key caps',(.02,.18,.17),.05,.40)
foil_mat=mat('Unselected pack envelope',(.54,.58,.59),.45,.43)
seal_mat=mat('Panel gasket concept',(.035,.039,.04),0,.73)
paper_mat=mat('E-paper face',(.77,.78,.72),0,.86)
flex_mat=mat('FPC routing envelope',(.56,.25,.045),.12,.45)
roots={name:empty(name) for name in ['Rear enclosure','Display retention','Battery envelope','Panel gasket','Screen module','Front frame','Side keys','Fastener envelopes']}

def contour(w,h,r,n=10):
 out=[]
 for x,y,angle in [(w/2-r,-h/2+r,-90),(w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180)]:
  for i in range(n):
   a=math.radians(angle+90*i/(n-1));out.append((x+r*math.cos(a),y+r*math.sin(a)))
 return out

def prism(name,w,h,z0,z1,material,parent=None,r=1,cx=0,cy=0):
 points=contour(w,h,min(r,w/2,h/2));n=len(points)
 verts=[(x+cx,y+cy,z) for z in [z0,z1] for x,y in points]
 faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 return mesh(name,verts,faces,material,parent)

def ring(name,w,h,iw,ih,z0,z1,material,parent=None,r=3,ir=1,cx=0,cy=0):
 a=contour(w,h,r);b=contour(iw,ih,ir);n=len(a)
 v=[(x+cx,y+cy,z) for z in [z0,z1] for pts in [a,b] for x,y in pts];f=[]
 for i in range(n):
  j=(i+1)%n;f.extend([(i,j,j+2*n,i+2*n),(i+n,i+3*n,j+3*n,j+n),(i+2*n,j+2*n,j+3*n,i+3*n),(i,i+n,j+n,j)])
 return mesh(name,v,f,material,parent)

def boolean(target,tool,operation):
 bpy.context.view_layer.update();mod=target.modifiers.new(operation,'BOOLEAN');mod.operation=operation;mod.solver='EXACT';mod.object=tool
 bpy.context.view_layer.objects.active=target;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(tool,do_unlink=True)

w,h,t=C['outer_dimensions_mm'];bottom=C['rear_bottom_z_mm'];split=C['shell_split_z_mm'];top=C['front_top_z_mm'];wall=C['wall_thickness_mm'];floor=bottom+C['rear_floor_thickness_mm']
rear=prism('Rear-shell / service apertures',w,h,bottom,split,case_mat,roots['Rear enclosure'],C['corner_radius_mm'])
pocket=prism('Rear cavity',w-2*wall,h-2*wall,floor,split+1,black,r=3)
boolean(rear,pocket,'DIFFERENCE')
# Connector openings use the unchanged native connector datums. Clearances and
# insertion/actuation remain explicitly unqualified in the source contract.
u=C['ports']['J201'];ux=u['center_core_xy_mm'][0]-48
boolean(rear,box('USB-C service opening',(ux,-37, u['opening_center_z_mm']),(u['opening_width_mm'],9,u['opening_height_mm']),black,r=0),'DIFFERENCE')
sd=C['ports']['J501'];ya,yb=sd['opening_span_y_mm'];sy=34-(ya+yb)/2
boolean(rear,box('microSD service well',(52,sy,sd['opening_center_z_mm']),(14,yb-ya,sd['opening_height_mm']),black,r=0),'DIFFERENCE')
for button in C['buttons']:
 y=34-button['center_core_xy_mm'][1];z=button['cap_center_z_mm']
 boolean(rear,box(button['ref']+' aperture',(-55.8,y,z),(5,5.5,3.6),black,r=0),'DIFFERENCE')
 cap=box(button['ref']+' outer cap',(-56.6,y,z),(1.8,4.8,3.0),key_mat,roots['Side keys'],.2)
 box(button['ref']+' long plunger / travel unqualified',(-52.25,y,z),(8.0,1.6,1.0),key_mat,roots['Side keys'],.12)
 box(button['ref']+' inner retention shoulder',(-53.8,y,z),(.9,6.0,4.0),case_mat,roots['Side keys'],.1)
 # A nominal rest gap is shown; no switch force/overtravel claim is made.
for i,(x,y) in enumerate(C['fastener_centers_core_xy_mm']):
 x-=48;y=34-y
 boss=cyl('Perimeter receiver', (x,y,(floor+split)/2),2.15,split-floor+.2,case_mat,None,32);boolean(rear,boss,'UNION')
 bore=cyl('Pilot / NOT a released thread',(x,y,0),.7,26,black,None,24);boolean(rear,bore,'DIFFERENCE')
 cyl('Fastener head envelope '+str(i),(x,y,top+.45),1.45,.65,shield,roots['Fastener envelopes'],32)
 cyl('Fastener shank envelope '+str(i),(x,y,top-7.8),.75,16,metal,roots['Fastener envelopes'],24)
# Core supports follow existing mounting-hole positions, excluding the pack and
# Display projections. Printed supports are prototypes, not supplier STEP models.
mechanical=json.loads((REPO/'hardware/thin18-compact/split-c1-mechanical-audit.json').read_text())
supports=[]
for hole in mechanical['mounting_holes']:
 if hole['board']!='Core-C1':continue
 x,y=hole['world_center_mm'];bx0,by0,bx1,by1=C['battery_envelope']['core_xyxy_mm']
 if bx0-1.8<x<bx1+1.8 and by0-1.8<y<by1+1.8:continue
 if 36.2<x<84.8 and 28.2<y<67.8:continue
 supports.append(hole['ref']);xx,yy=x-48,34-y
 post=cyl(hole['ref']+' support',(xx,yy,(floor-.04)/2),1.6,-.04-floor+.12,case_mat,None,32);boolean(rear,post,'UNION')
 boolean(rear,cyl('Support pilot',(xx,yy,-2),.55,7,black,None,24),'DIFFERENCE')
# Removable Display edge retainer, not a claim the connector bears the load.
retainer=ring('Display removable edge retainer',46.2,37.2,43.0,34.0,-2.85,-2.35,case_mat,roots['Display retention'],r=.8,ir=.45,cx=12.5,cy=-14)
# Pack is a clearly marked required envelope, never an invented accepted SKU.
bat=C['battery_envelope'];x0,y0,x1,y1=bat['core_xyxy_mm'];bw,bh,bt=bat['nominal_maximum_pack_mm'];bx=(x0+x1)/2-48;by=34-(y0+y1)/2;bz=bat['bottom_z_mm']
prism('Battery / unselected complete-pack envelope',bw,bh,bz,bz+bt,foil_mat,roots['Battery envelope'],r=1.3,cx=bx,cy=by)
box('Pack tabs / schematic', (bx,by-bh/2+1,bz+bt+.02),(bw-3,2,.05),flex_mat,roots['Battery envelope'],0)
text('Pack label','PACK ENVELOPE',1.8,dark,roots['Battery envelope'],(bx-bw/2+3,by+5,bz+bt+.07))
text('Pack status','SKU / HARNESS TBD',1.35,dark,roots['Battery envelope'],(bx-bw/2+3,by+1,bz+bt+.07))
# Full frame with a recessed panel pocket and ledge, not a paper cover floating
# over a bare board. Pocket and active window have separate dimensions.
p=C['panel'];pw,ph,pt=p['nominal_body_mm'];px=p['center_core_xy_mm'][0]-48;py=34-p['center_core_xy_mm'][1];pz=p['body_bottom_z_mm']
front=prism('Front frame / recessed panel window',w,h,split,top,case_mat,roots['Front frame'],C['corner_radius_mm'])
boolean(front,prism('Panel underside pocket',pw+.6,ph+.6,split-1,p['lip_bottom_z_mm'],black,r=1,cx=px,cy=py),'DIFFERENCE')
boolean(front,prism('Active display opening',*p['window_mm'],split-1,top+1,black,r=.8,cx=px,cy=py),'DIFFERENCE')
ledge=ring('Panel support ledge',107,64,99,58,pz-.6,pz-.3,case_mat,None,r=1.5,ir=1,cx=px,cy=py);boolean(front,ledge,'UNION')
for x,y in C['fastener_centers_core_xy_mm']:
 boolean(front,cyl('Frame screw clearance',(x-48,34-y,10),.9,8,black,None,24),'DIFFERENCE')
ring('Panel gasket / adhesive',105.1,62.1,99,58,pz-.3,pz,seal_mat,roots['Panel gasket'],r=1.1,ir=1,cx=px,cy=py)
prism('FT01C full screen module / nominal body',pw,ph,pz,pz+pt,black,roots['Screen module'],r=.6,cx=px,cy=py)
aw,ah=p['active_area_nominal_mm'];prism('E-paper active area',aw,ah,pz+pt+.005,pz+pt+.02,paper_mat,roots['Screen module'],r=.12,cx=px,cy=py)
text('E-paper brand','PANDA / OPEN READ',1.3,black,roots['Screen module'],(-41,23,pz+pt+.03))
text('E-paper heading','A quieter page.',4.0,black,roots['Screen module'],(-41,14,pz+pt+.035))
for i,content in enumerate(['Space to read. Room to think.','An open book, wherever you go.','A new chapter starts here.']):text('E-paper line '+str(i),content,1.5,black,roots['Screen module'],(-41,6-i*4,pz+pt+.035))
text('Page number','42 / 128',1.2,black,roots['Screen module'],(-41,-23,pz+pt+.035))
text('Case mark','P A N D A',1.5,silk,roots['Front frame'],(-45,-34,top+.008))
# Deliberately detached FPC envelopes: actual contact sides, bends and tails are
# NOT frozen. Do not draw a fictitious verified harness through native copper.
for i,width in enumerate([12,3,3]):
 box('FPC tail envelope / connection TBD '+str(i),(22-i*17,-32,pz-.18),(width,9,.15),flex_mat,roots['Screen module'],.1)
 for j in range(int(width/.5)):box('FPC exposed contact',(22-i*17-width/2+.25+j*.5,-35.5,pz-.09),(.25,1.5,.025),gold,roots['Screen module'],0)
# Verify exported fixture meshes before making STL studies. No fonts are packed.
import bmesh
mesh_checks={}
for name,obj in [('Rear-shell-study',rear),('Front-frame-study',front)]:
 deps=bpy.context.evaluated_depsgraph_get();me=bpy.data.meshes.new_from_object(obj.evaluated_get(deps));bm=bmesh.new();bm.from_mesh(me)
 boundary=sum(not edge.is_manifold for edge in bm.edges);mesh_checks[name]={'non_manifold_edges':boundary,'volume_mm3':round(abs(bm.calc_volume())*1e9,3)};bm.free();bpy.data.meshes.remove(me)
 if boundary==0:
  bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
  bpy.ops.wm.stl_export(filepath=str(OUT/(name+'.stl')),export_selected_objects=True,global_scale=1000,apply_modifiers=True)
# Camera, full assembly animation and annotations.
camdata=bpy.data.cameras.new('Whole-product camera');camdata.type='ORTHO';camdata.clip_start=.001;camdata.clip_end=5
cam=bpy.data.objects.new('Camera',camdata);scene.collection.objects.link(cam);scene.camera=cam
look=lambda o,p:setattr(o,'rotation_euler',(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler())
for name,power,pos,size in [('Key',.75,(-140,-100,220),180),('Fill',.42,(150,-30,130),150),('Rim',.9,(10,170,170),150),('Rear',.35,(-80,20,-180),140)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size*S;o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=Vector(pos)*S;look(o,(0,0,0))
header=text('Product title','PANDA / COMPLETE ASSEMBLY',7.2,dark,cam)
subtitle=text('Product scope','SPLIT-C1 / 112 x 75 x 22 mm PROTOTYPE / NOT THE 7 mm PRODUCT',3.1,muted,cam)
footer=text('Qualification boundary','NATIVE PCB + CONCEPT ENCLOSURE / PACK, FPC, ACTUATION AND PHYSICAL FIT NOT QUALIFIED',2.5,muted,cam)
chapter=text('View label','FULL-PRODUCT EXPLODED VIEW',2.7,teal,cam)
labelspec=[('01 / FRONT FRAME','Recessed window + two side keys','Front frame',.81),('02 / SCREEN + GASKET','FT01C nominal body / FPC tails TBD','Screen module',.68),('03 / CORE PCB','96 x 68 / 4 layers / current layout','Core-C1',.53),('04 / DISPLAY PCB','45 x 36 / 2 layers / 60-pin mate','Display-C1',.40),('05 / PACK ENVELOPE','36 x 54 x 5.5 maximum / SKU TBD','Battery envelope',.28),('06 / REAR ENCLOSURE','USB-C + microSD openings / supports','Rear enclosure',.16)]
labels=[]
for title,description,key,y in labelspec:labels.append((text(title,title,4.2,dark,cam),text(title+' note',description,3.0,muted,cam),key,y))
# High-contrast, readable HUD; fonts remain external references, never packed.
for material,color in [(dark,(.0001,.0001,.0001,1)),(muted,(.003,.004,.005,1)),(teal,(.0005,.09,.07,1))]:
 for node in material.node_tree.nodes:
  if node.type=='EMISSION':node.inputs['Color'].default_value=color
bold_path=Path('/System/Library/Fonts/Supplemental/Arial Bold.ttf')
if bold_path.exists():
 bold=bpy.data.fonts.load(str(bold_path))
 for obj in [header,*[a for a,b,k,y in labels]]:obj.data.font=bold
base={o:o.location.copy() for o in [*roots.values(),*assembly.values()]}
def hud(o,x,y):
 width=camdata.ortho_scale;height=width*scene.render.resolution_y/scene.render.resolution_x;o.location=((x-.5)*width,(y-.5)*height,-.12)
def smooth(q):q=max(0,min(1,q));return q*q*(3-2*q)
def pose(e,az=-58,el=25,annotations=True):
 offsets={'Rear enclosure':-60,'Display retention':-19,'Battery envelope':-36,'Panel gasket':23,'Screen module':32,'Front frame':57,'Side keys':12,'Fastener envelopes':65}
 for key,obj in roots.items():obj.location=base[obj]+Vector((0,0,offsets[key]*e*S))
 roots['Side keys'].location.x-=16*e*S
 roots['Side keys'].location.y-=35*e*S
 assembly['Core-C1'].location=base[assembly['Core-C1']]+Vector((0,0,3*e*S))
 assembly['Display-C1'].location=base[assembly['Display-C1']]+Vector((0,0,-15*e*S))
 target=Vector((0,0,4*e))*S;a=math.radians(az);b=math.radians(el);radius=.4
 cam.location=target+Vector((radius*math.cos(a)*math.cos(b),radius*math.sin(a)*math.cos(b),radius*math.sin(b)));look(cam,target)
 camdata.ortho_scale=(215+163*e)*S;cam.location+=cam.rotation_euler.to_quaternion()@Vector((-55*e*S,0,0))
 hud(header,.04,.95);hud(subtitle,.042,.90);hud(footer,.04,.035);hud(chapter,.04,.075)
 for aa,bb,key,y in labels:aa.hide_render=bb.hide_render=not annotations;hud(aa,.04,y);hud(bb,.041,y-.032)
 bpy.context.view_layer.update()

scene.frame_start=1;scene.frame_end=480
animated=[*roots.values(),*assembly.values(),cam,header,subtitle,footer,chapter,*[v for row in labels for v in row[:2]]]
for frame in range(1,481):
 t=(frame-1)/24
 if t<2.5:e=0;az=-58;el=40;show=False
 elif t<6:e=smooth((t-2.5)/3.5);az=-58;el=40-15*e;show=False
 elif t<10:e=1;az=-58;el=25;show=True
 elif t<15:e=1;az=-58+110*smooth((t-10)/5);el=25;show=False
 else:q=smooth((t-15)/4.95);e=1-q;az=52-110*q;el=25+15*q;show=False
 scene.frame_set(frame);pose(e,az,el,show)
 for obj in animated:obj.keyframe_insert(data_path='location',frame=frame);obj.keyframe_insert(data_path='hide_render',frame=frame)
 cam.keyframe_insert(data_path='rotation_euler',frame=frame);camdata.keyframe_insert(data_path='ortho_scale',frame=frame)
camera_steps=[];previous=None
for frame in range(1,481):
 scene.frame_set(frame);position=cam.location.copy()
 if previous is not None:camera_steps.append((position-previous).length/S)
 previous=position
if max(camera_steps)>30:raise ValueError('Unexpected camera jump at a label transition')
if any(font.packed_file is not None for font in bpy.data.fonts):raise ValueError('Do not embed system fonts')
report={'source_commit':D['commit'],'native_boards':{n:{k:v for k,v in b.items() if k!='components'} for n,b in D['boards'].items()},'native_component_inventory':inventories,'enclosure_contract_sha256':hashlib.sha256((REPO/'hardware/thin18-compact/split-c1-prototype-enclosure.json').read_bytes()).hexdigest(),'nominal_screen':SCREEN,'max_adjacent_camera_step_mm':max(camera_steps),'fixture_mesh_checks':mesh_checks,'core_support_refs':supports,'screen_nominal_model':True,'battery_is_unselected_envelope':True,'fpc_routing_verified':False,'native_cad_modified':False,'physical_fit_verified':False,'manufacturing_release':False}
(OUT/'render-provenance.json').write_text(json.dumps(report,indent=2)+'\n')
scene.frame_set(190);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Panda-Split-C1-Full-Product.blend'),compress=True)
if MODE in ['preview','stills']:
 scene.render.resolution_percentage=65 if MODE=='preview' else 200
 for frame,name in [(190,'Full-Product-Exploded'),(1,'Full-Product-Assembled')]:
  scene.frame_set(frame);chapter.data.body='COMPLETE PRODUCT / EXPLODED PROTOTYPE STUDY' if frame==190 else 'ASSEMBLED / 22 mm ENGINEERING PROTOTYPE'
  scene.render.filepath=str(OUT/(name+('-preview' if MODE=='preview' else '-4K')+'.png'));bpy.ops.render.render(write_still=True)
  if MODE=='preview':break
else:
 frames=OUT/'frames';frames.mkdir(exist_ok=True);scene.render.image_settings.file_format='JPEG';scene.render.image_settings.quality=94
 for frame in range(1,481):
  scene.frame_set(frame);chapter.data.body='COMPLETE PRODUCT / ASSEMBLE - EXPLODE - ORBIT - REASSEMBLE';scene.render.filepath=str(frames/('frame_%04d.jpg'%frame));bpy.ops.render.render(write_still=True)
print('FULL_PRODUCT_DONE',MODE,mesh_checks,flush=True)
