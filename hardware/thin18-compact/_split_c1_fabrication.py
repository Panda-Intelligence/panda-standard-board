"""Source-bound fabrication handoff; changes export metadata, never native CAD.

Raw KiCad job metadata is retained in verification/. Copper, mask, legend,
profile drawing commands and Excellon coordinates must remain unchanged.
"""
from pathlib import Path
import copy
import hashlib
import json
import math
import re
import zipfile
from _split_c1_common import ROOT, REPO, repo_entry, sha

CONTRACT = ROOT / 'split-c1-fabrication-contract.json'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_contract():
    contract = json.loads(CONTRACT.read_text())
    require(contract['schema'] == 'panda-split-c1-fabrication-contract-v1', 'Wrong fabrication contract')
    require(set(contract['boards']) == {'Core-C1', 'Display-C1'}, 'Wrong two-board target')
    require(all(contract[k] is False for k in ['cam_accepted','assembly_order_ready','manufacturing_release']), 'Unproven fabrication approval')
    return contract


def functions(layer_count):
    require(layer_count in [2,4], 'Unsupported copper count')
    return ([f'Copper,L{i},' + ('Top' if i == 1 else 'Bot' if i == layer_count else 'Inr')
             for i in range(1, layer_count+1)] + ['Legend,Top','Legend,Bot','SolderMask,Top','SolderMask,Bot','Profile'])


def geometry_payload(text):
    # Only these file-level attributes may change; no drawing/aperture commands.
    return re.sub(r'^%TF\.(?:ProjectId|CreationDate),[^\r\n]*\r?\n', '', text, flags=re.M)


def normalize_job(raw, spec, board_id, pcb_sha):
    job = copy.deepcopy(raw)
    general = job['GeneralSpecs']
    require(general['LayerNumber'] == len(spec['layers']), 'Job copper count differs')
    require(abs(general['BoardThickness'] - spec['nominal_board_thickness_mm']) < 1e-6, 'Job thickness differs')
    for axis, expected in zip(['X','Y'],spec['dimensions_mm']):
        # KiCad job bounding box includes the Edge.Cuts line thickness. Native
        # nominal dimensions have already been measured by export_production.py.
        require(abs(general['Size'][axis]-expected) <= 0.100001, 'Job outline differs')
        general['Size'][axis] = expected
    cu = [layer['Thickness'] for layer in job['MaterialStackup'] if layer['Type']=='Copper']
    require(len(cu)==len(spec['copper_thickness_mm']) and all(abs(a-b)<0.000002 for a,b in zip(cu,spec['copper_thickness_mm'])), 'Copper weight conflicts with fabrication contract')
    general['Finish'] = spec['finish']
    general['ProjectId']['Revision'] = board_id + '-' + pcb_sha[:12]
    # Native dielectric_constraints is a design flag, not an approved factory
    # impedance recipe. Do not advertise a tested/ordered controlled impedance.
    general.pop('ImpedanceControlled', None)
    masks = [layer for layer in job['MaterialStackup'] if layer['Type']=='SolderMask']
    require(len(masks)==2, 'Both soldermask layers must be declared')
    for layer in masks:
        layer['Color'] = spec['soldermask']
    return job


def validate_job(job, spec, board_id, pcb_sha):
    general = job['GeneralSpecs']
    require(general['LayerNumber']==len(spec['layers']), 'Wrong layer count')
    require(general['BoardThickness']==spec['nominal_board_thickness_mm'], 'Wrong board thickness')
    require([general['Size']['X'],general['Size']['Y']]==spec['dimensions_mm'], 'Wrong nominal outline')
    require(general['Finish']==spec['finish'], 'Wrong finish')
    require(general['ProjectId']['Revision']==board_id+'-'+pcb_sha[:12], 'Stale PCB revision')
    require('ImpedanceControlled' not in general, 'Unapproved impedance declaration')
    cu = [x['Thickness'] for x in job['MaterialStackup'] if x['Type']=='Copper']
    require(cu==spec['copper_thickness_mm'], 'Wrong copper construction')
    masks=[x for x in job['MaterialStackup'] if x['Type']=='SolderMask']
    require(len(masks)==2 and all(x.get('Color')==spec['soldermask'] for x in masks), 'Wrong soldermask color')
    attrs=job['FilesAttributes']
    require(sorted(x['FileFunction'] for x in attrs)==sorted(functions(len(spec['layers']))), 'Missing/duplicate manufacturing layer')
    names=[x['Path'] for x in attrs]
    require(len(names)==len(set(names)) and all(Path(n).name==n and n not in ['.','..'] for n in names), 'Unsafe/duplicate Gerber path')
    return True


def drill_summary(text, plated, layer_count):
    require(text.startswith('M48\n') and 'METRIC' in text and text.rstrip().endswith('M30'), 'Malformed or nonmetric drill file')
    role='Plated' if plated else 'NonPlated'; tail='PTH' if plated else 'NPTH'
    require(f'TF.FileFunction,{role},1,{layer_count},{tail}' in text, 'Drill plating/span mismatch')
    tools={int(n):float(d) for n,d in re.findall(r'^T(\d+)C([0-9.]+)$',text,re.M)}
    require(all(math.isfinite(v) and v>0 for v in tools.values()), 'Invalid drill diameter')
    active=None; count=0; slots=[]; rounds=[]
    for line in text.splitlines():
        match=re.fullmatch(r'T(\d+)',line)
        if match:
            active=int(match[1]);require(active in tools, 'Undeclared drill tool')
        elif line.startswith('X'):
            require(active is not None, 'Drill hit without tool');count+=1
            if 'G85' in line:
                match=re.fullmatch(r'X(-?[0-9.]+)Y(-?[0-9.]+)G85X(-?[0-9.]+)Y(-?[0-9.]+)',line)
                require(match is not None, 'Unrecognized slot command')
                x,y,xx,yy=map(float,match.groups());width=tools[active]
                length=round(math.hypot(xx-x,yy-y)+width,6)
                slots.append({'width_mm':width,'length_mm':length,'center_mm':[round((x+xx)/2,6),round(-(y+yy)/2,6)],'shorter_than_2_to_1':length < 2*width-1e-6})
            else:
                match=re.fullmatch(r'X(-?[0-9.]+)Y(-?[0-9.]+)',line)
                require(match is not None,'Unknown round drill command')
                x,y=map(float,match.groups());rounds.append({'diameter_mm':tools[active],'center_mm':[x,-y]})
    return {'plated':plated,'hit_count':count,'tool_diameters_mm':sorted(set(tools.values())),
            'minimum_tool_mm':min(tools.values()) if tools else None,'slots':slots,'round_holes':rounds}


def validate_gerber_contents(contents, spec, board_id, pcb_sha):
    job_names=[n for n in contents if n.endswith('.gbrjob')]
    require(len(job_names)==1, 'Exactly one fabrication job is required')
    job=json.loads(contents[job_names[0]])
    validate_job(job,spec,board_id,pcb_sha)
    revision=job['GeneralSpecs']['ProjectId']['Revision']
    for row in job['FilesAttributes']:
        require(row['Path'] in contents, 'Gerber job references a missing file')
        text=contents[row['Path']].decode('utf-8')
        require('%MOMM*%' in text, 'Gerber units are not millimeters')
        actual=re.findall(r'%TF\.FileFunction,([^*]+)\*%',text)
        require(len(actual)==1,'Missing/duplicate layer function')
        expected=row['FileFunction'].lower()
        require(actual[0].lower()==expected or (expected=='profile' and actual[0].lower() in ['profile,np','profile,p']), 'Swapped/mislabeled Gerber layer')
        require(re.search(r'%TF.ProjectId,[^\r\n]*,'+re.escape(revision)+r'\*%',text), 'Gerber layer PCB revision differs')
        require(text.rstrip().endswith('M02*'), 'Incomplete Gerber layer')
    drill_files={}
    for plated in [True,False]:
        suffix='-PTH.drl' if plated else '-NPTH.drl'
        names=[n for n in contents if n.endswith(suffix)]
        require(len(names)==1,'Missing/duplicate '+suffix)
        drill_files['PTH' if plated else 'NPTH']=drill_summary(contents[names[0]].decode(),plated,len(spec['layers']))
    require(len([n for n in contents if n.endswith('.drl')])==2,'Unexpected drill file')
    allowed={r['Path'] for r in job['FilesAttributes']}|set(job_names)|{n for n in contents if n.endswith('.drl')}|{'drill-report.txt'}
    require(set(contents)==allowed,'Unexpected files in bare-board ZIP')
    return drill_files


def verify_cap_drill_export(drills):
    pth=drills['PTH']
    for center in [[49.4,43.5],[69.4,43.5]]:
        hits=[r for r in pth['round_holes'] if all(abs(x-y)<.001 for x,y in zip(r['center_mm'],center))]
        require(len(hits)==1 and abs(hits[0]['diameter_mm']-1.9)<1e-6,'C301 missing/wrong round plated hole')
        require(not any(all(abs(x-y)<.001 for x,y in zip(r['center_mm'],center)) for r in pth['slots']),'Obsolete C301 short slot exported')
    require(not any(s['shorter_than_2_to_1'] for s in pth['slots']),'Unreviewed short plated slot remains')
    return True


def prepare(gerber_dir, verify_dir, pcb, board_id, dimensions, layers):
    """Normalize only manufacturing metadata before export ZIP/hash freezing."""
    contract=load_contract();spec=contract['boards'][board_id]
    require(dimensions==spec['dimensions_mm'] and layers==spec['layers'], 'Export selected wrong board')
    pcb_hash=sha(pcb);gerber_dir=Path(gerber_dir);verify_dir=Path(verify_dir)
    jobs=list(gerber_dir.glob('*.gbrjob'));require(len(jobs)==1,'Missing KiCad job')
    job_path=jobs[0];raw=job_path.read_bytes();raw_path=verify_dir/'raw-kicad-job.json';raw_path.write_bytes(raw)
    job=normalize_job(json.loads(raw),spec,board_id,pcb_hash)
    before={p.name:sha(p) for p in gerber_dir.iterdir() if p.is_file() and p.suffix!='.gbrjob'}
    payloads={}
    for row in job['FilesAttributes']:
        p=gerber_dir/row['Path'];text=p.read_text();payload=geometry_payload(text)
        pattern=r'(%TF\.ProjectId,[^\r\n]*,)[^,\r\n]*\*%'
        text,n=re.subn(pattern,lambda m:m[1]+job['GeneralSpecs']['ProjectId']['Revision']+'*%',text)
        require(n==1,'Missing/nonunique ProjectId attribute')
        require(geometry_payload(text)==payload,'Unexpected Gerber geometry modification')
        p.write_text(text);payloads[p.name]=hashlib.sha256(payload.encode()).hexdigest()
    job_path.write_text(json.dumps(job,indent=2)+'\n')
    contents={p.name:p.read_bytes() for p in gerber_dir.iterdir() if p.is_file()}
    drills=validate_gerber_contents(contents,spec,board_id,pcb_hash)
    if board_id=='Core-C1':verify_cap_drill_export(drills)
    for p in gerber_dir.glob('*.drl'):
        require(sha(p)==before[p.name], 'Drill coordinates modified')
    short_slots=[s for item in drills.values() for s in item['slots'] if s['shorter_than_2_to_1']]
    record={'schema':'panda-split-c1-fabrication-v1','board_id':board_id,'native_pcb':repo_entry(pcb),
            'contract':repo_entry(CONTRACT),'normalizer':repo_entry(Path(__file__)),
            'selection':spec,'gerber_job':repo_entry(job_path),'raw_kicad_job':repo_entry(raw_path),
            'raw_metadata_replaced':json.loads(raw)['GeneralSpecs'],'layer_drawing_sha256':payloads,
            'drills':drills,'short_slots_requiring_cam_review':short_slots,
            'native_cad_changed':False,'gerber_geometry_preserved':True,'drill_bytes_preserved':True,
            'cam_confirmations':contract['cam_confirmations'],'cam_accepted':False,
            'assembly_order_ready':False,'manufacturing_release':False}
    report=verify_dir/'fabrication.json';report.write_text(json.dumps(record,indent=2)+'\n')
    notes=verify_dir/'FABRICATION.md'
    copper=' / '.join(f'{v*1000:g} um' for v in spec['copper_thickness_mm'])
    notes.write_text(f'''# {board_id} fabrication selection\n\nNative PCB SHA-256: `{pcb_hash}`\n\nNominal size: {dimensions[0]:g} x {dimensions[1]:g} mm; {len(layers)} layers; nominal board thickness 0.8 mm.\n\nLayer order: {' -> '.join(layers)}. Copper: {copper}.\nFinish: ENIG (Nickel, Gold). Solder mask: green.\n\nCore inner copper must not silently become the vendor's default 0.5 oz.\nThe sanitized job file corrects historical revision/color/finish fields; no copper, mask, outline or drill geometry is changed.\nThe omitted legacy impedance flag is not a waiver or an impedance certification; agree the actual construction/impedance recipe with CAM before fabrication.\n\nThis is a CAM review package, not automatic order approval. Native DRC alone does not approve short slots, assembly or supplier substitutions.\n\n## Required confirmations\n\n'''+'\n'.join('- '+line for line in contract['cam_confirmations'])+'\n\nSee fabrication.json for the measured slot/hole inventory and source hashes.\n')
    return {'fabrication_record':report,'fabrication_notes':notes,'gerber_job':job_path,'raw_kicad_job':raw_path,'fabrication_contract':CONTRACT}


def validate_archive(path,spec,board_id,pcb_sha):
    with zipfile.ZipFile(path) as z:
        require(z.testzip() is None,'Gerber ZIP CRC failed')
        require(len(z.namelist())==len(set(z.namelist())),'Duplicate ZIP entries')
        return validate_gerber_contents({n:z.read(n) for n in z.namelist()},spec,board_id,pcb_sha)
