#!/usr/bin/env python3
from pathlib import Path
import json, shutil, hashlib, re

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'hardware/thin18/routing142'
DST=ROOT/'hardware/thin18-compact/c0-fold70x64'
REL=Path('eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16')
STEM='PANDA-STD-CORE-EVT-quilter-j501-merged'
SHIFT_Y=-64.0
CORNERS={'H801':(14.5,2.5),'H802':(64.0,6.0),'H803':(67.0,42.0),'H804':(7.0,44.0)}

class Quoted(str): pass

def parse(text):
    tokens=re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+',text)
    stack=[];roots=[]
    for token in tokens:
        if token=='(':
            node=[];(stack[-1] if stack else roots).append(node);stack.append(node)
        elif token==')':
            if not stack: raise ValueError('Unmatched closing parenthesis')
            stack.pop()
        else:
            if not stack: raise ValueError('Atom outside root expression')
            stack[-1].append(Quoted(json.loads(token)) if token.startswith('"') else token)
    if stack or len(roots)!=1: raise ValueError('Incomplete or multiple root expressions')
    return roots[0]

def render(node):
    if isinstance(node,list): return '('+' '.join(render(x) for x in node)+')'
    return json.dumps(str(node),ensure_ascii=False) if isinstance(node,Quoted) else str(node)

def children(node,tag):
    return [x for x in node[1:] if isinstance(x,list) and x and x[0]==tag]

def child(node,tag):
    a=children(node,tag)
    if len(a)!=1: raise ValueError(f'Expected one {tag}, got {len(a)}')
    return a[0]

def props(node):
    return {str(a[1]):str(a[2]) for a in children(node,'property')}

def edge_item(node):
    if not isinstance(node,list) or not node or node[0] not in {'gr_line','gr_arc','gr_rect','gr_circle'}: return False
    ls=children(node,'layer')
    return bool(ls and str(ls[0][1])=='Edge.Cuts')

def main():
    if DST.exists(): shutil.rmtree(DST)
    shutil.copytree(SRC,DST)
    pcb=DST/REL/(STEM+'.kicad_pcb')
    root=parse(pcb.read_text())
    assert root[0]=='kicad_pcb'

    before={'segment':len(children(root,'segment')),'via':len(children(root,'via')),
            'zone':len(children(root,'zone')),'edge':sum(edge_item(x) for x in root[1:]),
            'footprint':len(children(root,'footprint'))}
    assert before['footprint']==202

    # placement study: no old copper/routing/pours and no old outline
    root[:]=[x for x in root if not (isinstance(x,list) and x and
             (x[0] in {'segment','via','zone'} or edge_item(x)))]

    moved=[]
    for f in children(root,'footprint'):
        ref=props(f).get('Reference')
        at=child(f,'at')
        x=float(at[1]);y=float(at[2]);old=[x,y]
        if ref in CORNERS:
            x,y=CORNERS[ref]
        elif y>=100.0:
            y+=SHIFT_Y
        else:
            continue
        at[1]=format(x,'.9g');at[2]=format(y,'.9g')
        moved.append({'ref':ref,'old_mm':old,'new_mm':[x,y]})

    for x1,y1,x2,y2 in [(0,0,70,0),(70,0,70,64),(70,64,17.62,64),(8.38,64,0,64),(0,64,0,0)]:
        root.append(parse(f'(gr_line (start {x1} {y1}) (end {x2} {y2}) (stroke (width 0.05) (type default)) (layer "Edge.Cuts"))'))

    assert len(children(root,'segment'))==0 and len(children(root,'via'))==0 and len(children(root,'zone'))==0
    assert sum(edge_item(x) for x in root[1:])==5
    refs={props(f).get('Reference'):f for f in children(root,'footprint')}
    assert abs(float(child(refs['J201'],'at')[2])-64.0)<1e-9
    assert len(refs)==202

    pcb.write_text(render(root)+'\n')
    report={
      'kind':'placement_feasibility_only','source':'thin18/routing142','target_mm':[70,64],
      'source_counts':before,'removed_tracks':before['segment']+before['via'],'removed_zones':before['zone'],
      'upper_cluster_shift_y_mm':SHIFT_Y,'moved_count':len(moved),'moved':moved,
      'mounting_holes':CORNERS,'j201_anchor_mm':[float(child(refs['J201'],'at')[1]),64.0],
      'routing_authority':False,'manufacturing_release':False,'physical_qualification':False,
      'pcb_sha256':hashlib.sha256(pcb.read_bytes()).hexdigest()
    }
    (DST/'c0-fold-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='moved'},indent=2))

if __name__=='__main__': main()
