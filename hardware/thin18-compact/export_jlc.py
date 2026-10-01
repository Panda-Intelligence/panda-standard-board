#!/usr/bin/env python3
from pathlib import Path
import argparse,csv,re,json,hashlib

ap=argparse.ArgumentParser()
ap.add_argument('--production',type=Path,required=True)
a=ap.parse_args()
root=a.production
mfg=root/'manufacturing'
bom=mfg/'bom.csv'
cpl=mfg/'cpl.csv'
out=mfg/'jlcpcb'
out.mkdir(exist_ok=True)

def expand_refs(text):
    result=[]
    for token in [x.strip() for x in text.split(',') if x.strip()]:
        m=re.fullmatch(r'([A-Za-z]+)(\d+)-([A-Za-z]+)?(\d+)',token)
        if m and (not m.group(3) or m.group(1)==m.group(3)):
            prefix=m.group(1); a=int(m.group(2)); b=int(m.group(4))
            result.extend(f'{prefix}{i}' for i in range(a,b+1))
        else:
            result.append(token)
    return result

bom_rows=list(csv.DictReader(bom.open(encoding='utf-8-sig',newline='')))
cpl_rows=list(csv.DictReader(cpl.open(encoding='utf-8-sig',newline='')))
cpl_by_ref={r['Ref']:r for r in cpl_rows}

jlc_bom=[]
sourcing=[]
all_bom_refs=set()
for r in bom_rows:
    refs=expand_refs(r['Refs'])
    all_bom_refs.update(refs)
    designators=','.join(refs)
    lcsc=(r.get('LCSC') or '').strip()
    jlc_bom.append({
        'Comment':r['Value'],
        'Designator':designators,
        'Footprint':r['Footprint'].split(':')[-1],
        'LCSC Part #':lcsc,
    })
    for ref in refs:
        in_cpl=ref in cpl_by_ref
        if not in_cpl:
            status='MANUAL_OR_OFFBOARD'
        elif lcsc:
            status='JLC_LIBRARY_ID_PRESENT'
        else:
            status='MPN_ONLY_REQUIRES_JLC_MAPPING_OR_CONSIGNED_PART'
        sourcing.append({
            'Designator':ref,
            'Manufacturer':r.get('Manufacturer',''),
            'MPN':r.get('MPN',''),
            'LCSC Part #':lcsc,
            'In CPL':'TRUE' if in_cpl else 'FALSE',
            'Assembly status':status,
        })

with (out/'BOM_JLCPCB.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=['Comment','Designator','Footprint','LCSC Part #'],lineterminator='\n')
    w.writeheader();w.writerows(jlc_bom)

jlc_cpl=[]
for r in cpl_rows:
    jlc_cpl.append({
        'Designator':r['Ref'],
        'Mid X':r['PosX'],
        'Mid Y':r['PosY'],
        'Rotation':r['Rot'],
        'Layer':'Top' if r['Side'].lower()=='top' else 'Bottom',
    })
with (out/'CPL_JLCPCB.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=['Designator','Mid X','Mid Y','Rotation','Layer'],lineterminator='\n')
    w.writeheader();w.writerows(jlc_cpl)

with (out/'assembly-sourcing.csv').open('w',newline='',encoding='utf-8-sig') as f:
    fields=['Designator','Manufacturer','MPN','LCSC Part #','In CPL','Assembly status']
    w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(sourcing)

cpl_refs=set(cpl_by_ref)
unknown=sorted(cpl_refs-all_bom_refs)
if unknown:
    raise SystemExit(f'CPL refs missing from BOM: {unknown}')
summary={
    'bom_group_rows':len(bom_rows),
    'bom_designators':len(all_bom_refs),
    'cpl_rows':len(cpl_rows),
    'cpl_top':sum(r['Side'].lower()=='top' for r in cpl_rows),
    'cpl_bottom':sum(r['Side'].lower()=='bottom' for r in cpl_rows),
    'lcsc_mapped_designators':sum(bool(r['LCSC Part #']) for r in sourcing),
    'mpn_only_designators':sum(r['Assembly status']=='MPN_ONLY_REQUIRES_JLC_MAPPING_OR_CONSIGNED_PART' for r in sourcing),
    'manual_or_offboard_designators':sum(r['Assembly status']=='MANUAL_OR_OFFBOARD' for r in sourcing),
    'cpl_refs_missing_from_bom':unknown,
    'note':'JLC format follows official BOM/CPL headers. Blank LCSC IDs are not claimed as automatic JLC library matches.'
}
(out/'jlc-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
