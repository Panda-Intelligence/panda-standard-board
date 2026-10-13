"""Resume partial routing from an external source-bound native checkpoint.

The checkpoint is not committed output and never grants fabrication approval.
Only its copper is imported; all component intent, outlines and rule settings
remain those freshly rebuilt from source. Every claim is rechecked natively.
"""
from pathlib import Path
import hashlib
import json
import re
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'thin18-compact'))
from seven_mm_routing import copper_blocks,native_semantic_fingerprint
from import_pico47_route import run
from pico47_contract import CONTRACT
from pico47_placement import LAYOUT
from verify_pico47_native import inspect


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(value,message):
    if not value:
        raise ValueError(message)


def validate_manifest(data):
    require(data.get('schema')=='panda47-external-routing-checkpoint-v1','Wrong checkpoint schema')
    require(data.get('manufacturing_release') is False,'Checkpoint is not fabrication approval')
    require(set(data.get('boards',{}))=={'Core','Display'},'Both native boards are required')
    for key in ['source_design_sha256','source_layout_sha256']:
        require(isinstance(data.get(key),str) and re.fullmatch('[a-f0-9]{64}',data[key]) is not None,
                'Invalid source binding')
    for name,row in data['boards'].items():
        for key in ['pcb_sha256','schematic_sha256','project_sha256','rules_sha256','geometry_sha256']:
            require(isinstance(row.get(key),str) and re.fullmatch('[a-f0-9]{64}',row[key]) is not None,
                    name+': invalid native file binding')
        counts=row.get('counts',{})
        require(set(counts)=={'drc_errors','drc_warnings','open','parity','erc'},'Incomplete native counts')
        require(all(type(v) is int and v>=0 for v in counts.values()),'Invalid count type')
        require(all(counts[k]==0 for k in ['drc_errors','parity','erc']),
                'Do not resume a checkpoint with native errors or mismatched circuitry')
    return True


def restore(built,checkpoint,donor):
    built,checkpoint,donor=map(lambda p:Path(p).resolve(),[built,checkpoint,donor])
    require(built!=checkpoint and built!=donor,'Never overwrite a checkpoint or donor')
    data=json.loads((checkpoint/'ROUTING-CHECKPOINT.json').read_text())
    validate_manifest(data)
    require(data['source_design_sha256']==sha(CONTRACT)
            and data['source_layout_sha256']==sha(LAYOUT),'Checkpoint belongs to a different design')
    backups={};input_hashes={};counts={}
    for name,row in data['boards'].items():
        for suffix,key in [('.kicad_pcb','pcb_sha256'),('.kicad_sch','schematic_sha256'),
                           ('.kicad_pro','project_sha256'),('.kicad_dru','rules_sha256')]:
            source=checkpoint/(name+suffix)
            require(sha(source)==row[key],name+': checkpoint bytes changed')
            input_hashes[source]=row[key]
            if suffix!='.kicad_pcb':
                require(sha(built/(name+suffix))==row[key],name+': rebuilt schematic or rules differ')
        pcb=built/(name+'.kicad_pcb')
        require(native_semantic_fingerprint(pcb)==row['geometry_sha256']
                and native_semantic_fingerprint(checkpoint/pcb.name)==row['geometry_sha256'],
                name+': placement or pad/outline geometry changed')
        backups[pcb]=pcb.read_bytes()
    try:
        for name,row in data['boards'].items():
            pcb=built/(name+'.kicad_pcb');text=pcb.read_text()
            for block in copper_blocks(pcb):
                text=text.replace(block,'',1)
            items=copper_blocks(checkpoint/pcb.name)
            require(items,'Routing checkpoint contains no copper')
            ids=[]
            for block in items:
                m=re.search(r'\(uuid "([^\"]+)"\)',block)
                require(m is not None,'Missing copper identity');ids.append(m[1])
            require(len(ids)==len(set(ids)),'Duplicate routing copper identities')
            i=text.rfind(')')
            pcb.write_text(text[:i]+'\n'+'\n'.join(items)+'\n'+text[i:])
            run(['pcb','drc','--refill-zones','--save-board','--severity-all','--all-track-errors',
                 '--schematic-parity','--format','json','--output',built/(name+'-drc.json'),pcb],
                built/(name+'-drc.log'))
            run(['sch','erc','--severity-all','--format','json','--output',built/(name+'-erc.json'),
                 built/(name+'.kicad_sch')],built/(name+'-erc.log'))
            d=json.loads((built/(name+'-drc.json')).read_text())
            e=json.loads((built/(name+'-erc.json')).read_text())
            counts[name]={'drc_errors':sum(v['severity']=='error' for v in d['violations']),
                          'drc_warnings':sum(v['severity']=='warning' for v in d['violations']),
                          'open':len(d['unconnected_items']),'parity':len(d.get('schematic_parity',[])),
                          'erc':sum(len(s['violations']) for s in e['sheets'])}
            require(counts[name]==row['counts'],name+': rebuilt routing does not reproduce the native checkpoint')
            require(native_semantic_fingerprint(pcb)==row['geometry_sha256'],name+': native intent changed')
        check=inspect(built,donor)
        require(all(sha(p)==digest for p,digest in input_hashes.items()),'External checkpoint changed during replay')
        report={'source_checkpoint':str(checkpoint),'native_counts':counts,'independent_native':check,
                'copper_only_replay':True,'source_geometry_rebuilt':True,'manufacturing_release':False}
        (built/'ROUTING-RESUME.json').write_text(json.dumps(report,indent=2)+'\n')
        status_path=built/'E0-STATUS.json'
        if status_path.exists():
            status=json.loads(status_path.read_text())
            for n,c in counts.items():
                status['boards'][n]['counts']={'drc':c['drc_errors']+c['drc_warnings'],
                    'open':c['open'],'parity':c['parity'],'erc':c['erc']}
                status['boards'][n]['pcb_sha256']=sha(built/(n+'.kicad_pcb'))
            status['routing_checkpoint_resumed']=str(checkpoint)
            status['manufacturing_release']=False
            status_path.write_text(json.dumps(status,indent=2)+'\n')
        print(json.dumps({'checkpoint_resumed':str(checkpoint),'counts':counts,'manufacturing_release':False},indent=2))
        return report
    except Exception:
        for pcb,content in backups.items():
            pcb.write_bytes(content)
        (built/'ROUTING-RESUME-FAILED.txt').write_text('Routing replay failed; base copper restored. Generated reports from the rejected replay must not be treated as current acceptance.\n')
        raise
