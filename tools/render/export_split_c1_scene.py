"""Read only: export the actual current two PCBs and placement metadata to an external render directory."""
from pathlib import Path
import sys,json,hashlib,subprocess,math,re,argparse,os
import wx
APP=wx.App(False)
import pcbnew as P
R=Path(__file__).resolve().parents[2];H=R/'hardware/thin18-compact'
p=argparse.ArgumentParser(description='Read-only export of current Split-C1 scene inputs.');p.add_argument('--output',type=Path,required=True);args=p.parse_args();O=args.output.resolve();O.mkdir(parents=True,exist_ok=True)
if O.is_relative_to(R) and not O.is_relative_to(R/'.work') and not O.is_relative_to(R/'visualization'):raise SystemExit('Render outputs must be external or ignored')
sys.path.insert(0,str(H));from _split_c1_sourcing import blocks,property_value
C=json.loads((H/'split-c1-mechanical-inputs.json').read_text());I=json.loads((H/'split-c1-interface.json').read_text())
paths={'Core-C1':H/'core-c1-96x68-split/eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16/PANDA-STD-CORE-EVT-quilter-j501-merged.kicad_pcb','Display-C1':H/'display-c1-45x36-production-bom/PANDA-EPD0426-SPI-EVT.kicad_pcb'}
xy=lambda p:[P.ToMM(p.x),P.ToMM(p.y)]
report={'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'assembly':I['assembly'],'boards':{},'scope':'Native Split-C1 PCB geometry; enclosure/panel/cable/pack solids are separately identified design-study geometry, not manufacturing approval.'}
for name,path in paths.items():
 b=P.LoadBoard(str(path));fptext={property_value(f,'Reference'):f for _,_,f in blocks(path.read_text(),r'\(footprint\s')};rows=[]
 for f in b.GetFootprints():
  if f.IsDNP() or f.IsExcludedFromBOM():continue
  ref=f.GetReference();fields={field.GetName():field.GetText() for field in f.GetFields()}
  pads=[]
  for p in f.Pads():pads.append({'n':p.GetNumber(),'xy':xy(p.GetPosition()),'size':xy(p.GetSize()),'angle':p.GetOrientationDegrees(),'net':str(p.GetNetname()),'drill':xy(p.GetDrillSize())})
  fab=[]
  for g in f.GraphicalItems():
   if g.GetLayer() not in [P.F_Fab,P.B_Fab] or not isinstance(g,P.PCB_SHAPE):continue
   bb=g.GetBoundingBox();fab.append([P.ToMM(bb.GetX()),P.ToMM(bb.GetY()),P.ToMM(bb.GetRight()),P.ToMM(bb.GetBottom())])
  bb=f.GetBoundingBox(False,False)
  body=[min(a[0] for a in fab),min(a[1] for a in fab),max(a[2] for a in fab),max(a[3] for a in fab)] if fab else [P.ToMM(bb.GetX()),P.ToMM(bb.GetY()),P.ToMM(bb.GetRight()),P.ToMM(bb.GetBottom())]
  height=next((v.get('height_maximum_mm',v['height_nominal_mm']) for v in C['published_component_height_screens'] if v['board']==name and v['ref']==ref),None)
  rows.append({'ref':ref,'value':f.GetValue(),'mpn':fields.get('MPN'),'xy':xy(f.GetPosition()),'angle':f.GetOrientationDegrees(),'side':'F' if f.GetLayer()==P.F_Cu else 'B','fab_bbox':body,'pads':pads,'height_screen_mm':height,'models':re.findall(r'\(model\s+"([^"]+)',fptext[ref])})
 report['boards'][name]={'source_path':str(path.relative_to(R)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'thickness_mm':P.ToMM(b.GetDesignSettings().GetBoardThickness()),'dimensions_mm':[96,68] if name=='Core-C1' else [45,36],'components':rows}
from _split_c1_common import kicad_cli
for name,path in paths.items():
 env=os.environ.copy();env['KICAD10_3DMODEL_DIR']='/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels'
 with (O/(name+'-export.log')).open('w') as log:
  subprocess.run([kicad_cli(),'pcb','export','glb','--force','--no-dnp','--include-tracks','--include-pads','--include-zones','--include-silkscreen','--include-soldermask','--output',str(O/(name+'.glb')),str(path)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 assert hashlib.sha256(path.read_bytes()).hexdigest()==report['boards'][name]['sha256']
(O/'scene-metadata.json').write_text(json.dumps(report,indent=2)+'\n')
print('SOURCE_BOUND_METADATA',report['commit'],{n:len(b['components']) for n,b in report['boards'].items()},flush=True)
