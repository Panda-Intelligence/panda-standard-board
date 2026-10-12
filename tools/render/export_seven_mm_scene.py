#!/usr/bin/env python3
"""Export source-bound native 7mm boards for an explicitly unqualified assembly study.

Never uses the obsolete22mm enclosure. All GLB/native geometry and output metadata
are generated outside Git. Generic package proxies are listed, not certified models.
"""
from pathlib import Path
import sys,json,hashlib,subprocess,argparse,os
import wx
APP=wx.App(False)
import pcbnew as P
R=Path(__file__).resolve().parents[2];H=R/'hardware/thin18-compact'
sys.path.insert(0,str(H));from _split_c1_common import kicad_cli
from seven_mm_native_evidence import verify_native_clean


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 src=a.candidate.resolve();out=a.output.resolve()
 if out.is_relative_to(R) and not out.is_relative_to(R/'.work'):raise ValueError('Render products do not belong in Git')
 out.mkdir(parents=True,exist_ok=True)
 layout=json.loads((H/'seven_mm_layout.json').read_text());height_source=json.loads((H/'split-c1-mechanical-inputs.json').read_text())['published_component_height_screens']
 by_mpn={v['mpn']:v for v in height_source};sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest();xy=lambda q:[round(P.ToMM(q.x),6),round(P.ToMM(q.y),6)]
 report={'schema':'panda-seven-mm-scene-v1','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'revision':'D-engineering','dimensions_mm':[75,112,6.8],'maximum_design_thickness_mm':7.0,'qualification':{'native_connected':True,'case_manufacturing_approved':False,'component_models_certified':False,'maximum_supplier_envelopes_verified':False,'manufacturing_release':False},'layout':layout,'boards':{},'render_scope':'Native copper,lands,holes,outlines and actual part placement. Package proxy solids and case/panel/cable assembly study are not certified production geometry.'}
 for name in ['Core','Display']:
  path=src/(name+'.kicad_pcb');before=sha(path);native=verify_native_clean(path);board=P.LoadBoard(str(path));rows=[]
  for f in board.GetFootprints():
   if f.IsDNP():continue
   ref=f.GetReference();fields={v.GetName():v.GetText() for v in f.GetFields()};mpn=fields.get('MPN','');pads=[]
   for q in f.Pads():pads.append({'n':q.GetNumber(),'xy':xy(q.GetPosition()),'size':xy(q.GetSize()),'angle':q.GetOrientationDegrees(),'drill':xy(q.GetDrillSize()),'net':str(q.GetNetname())})
   fab=[]
   for q in f.GraphicalItems():
    if q.GetLayer() not in [P.F_Fab,P.B_Fab] or not isinstance(q,P.PCB_SHAPE):continue
    bb=q.GetBoundingBox();fab.append([*xy(bb.GetOrigin()),*xy(bb.GetEnd())])
   bb=f.GetBoundingBox(False,False)
   body=[min(v[0] for v in fab),min(v[1] for v in fab),max(v[2] for v in fab),max(v[3] for v in fab)] if fab else [*xy(bb.GetOrigin()),*xy(bb.GetEnd())]
   source=by_mpn.get(mpn);height=source.get('height_maximum_mm',source['height_nominal_mm']) if source else None
   rows.append({'ref':ref,'value':f.GetValue(),'manufacturer':fields.get('Manufacturer',''),'mpn':mpn,'catalog_code':fields.get('LCSC',''),'xy':xy(f.GetPosition()),'angle':f.GetOrientationDegrees(),'side':'F' if f.GetLayer()==P.F_Cu else 'B','excluded_from_bom':f.IsExcludedFromBOM(),'fab_bbox':body,'pads':pads,'reviewed_height_mm':height,'height_source':source,'package_model_is_proxy':True})
  edges=[]
  for q in board.GetDrawings():
   if q.GetLayer()==P.Edge_Cuts:edges.append([xy(q.GetStart()),xy(q.GetEnd())])
  entry={'source_path':str(path),'sha256':before,'native_counts':native['counts'],'thickness_mm':P.ToMM(board.GetDesignSettings().GetBoardThickness()),'edges':edges,'components':rows}
  env=os.environ.copy();env['KICAD10_3DMODEL_DIR']='/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels'
  args=[kicad_cli(),'pcb','export','glb','--force','--no-components','--include-tracks','--include-pads','--include-zones','--include-silkscreen','--include-soldermask','--output',str(out/(name+'.glb')),str(path)]
  with (out/(name+'-export.log')).open('w') as log:subprocess.run(args,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  if sha(path)!=before:raise ValueError('Render export changed native input')
  entry['glb_sha256']=sha(out/(name+'.glb'));report['boards'][name]=entry
 (out/'scene-metadata.json').write_text(json.dumps(report,indent=2)+'\n');print('NATIVE_SCENE_EXPORTED',{k:len(v['components']) for k,v in report['boards'].items()},flush=True)
if __name__=='__main__':main()
