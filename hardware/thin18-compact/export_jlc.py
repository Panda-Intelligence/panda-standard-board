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
evidence_path=Path(__file__).resolve().parent/'split-c1-sourcing-evidence.json'
manifest_path=root/'production-manifest.json'
reviewed={}
procurement={}
if evidence_path.exists() and manifest_path.exists():
    board_id=json.loads(manifest_path.read_text()).get('board_id')
    registry=json.loads(evidence_path.read_text())
    reviewed={ref:item for item in registry['entries'] if item['board']==board_id
              for ref in item['refs']}
    procurement={ref:item for item in registry.get('procurement_followup',[]) if item['board']==board_id
                 for ref in item['refs']}

for r in bom_rows:
    refs=expand_refs(r['Refs'])
    all_bom_refs.update(refs)
    machine_refs=[ref for ref in refs if ref in cpl_by_ref]
    designators=','.join(machine_refs)
    lcsc=(r.get('LCSC') or '').strip()
    if machine_refs: jlc_bom.append({
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
        item=reviewed.get(ref)
        supply=procurement.get(ref,{})
        if supply and (supply['manufacturer']!=r.get('Manufacturer') or supply['mpn']!=r.get('MPN')):
            raise SystemExit(f'Procurement route identity mismatch: {ref}')
        if item and (item['manufacturer']!=r.get('Manufacturer') or
                     item['mpn']!=r.get('MPN') or item['library_id']!=lcsc):
            raise SystemExit(f'Reviewed sourcing identity mismatch: {ref}')
        evidence_status=('EXACT_MANUFACTURER_MPN_VERIFIED' if item else
                         'PREEXISTING_ID' if lcsc else 'UNMAPPED')
        sourcing.append({
            'Designator':ref,
            'Manufacturer':r.get('Manufacturer',''),
            'MPN':r.get('MPN',''),
            'LCSC Part #':lcsc,
            'In CPL':'TRUE' if in_cpl else 'FALSE',
            'Assembly status':status,
            'Identity evidence':evidence_status,
            'Evidence URL':item['source_url'] if item else '',
            'Procurement route':supply.get('supply_route',''),
            'Supply status':supply.get('supply_status',''),
            'Supply URL':supply.get('source_url') or '',
            'Packing':supply.get('packing',''),
            'Public stock observation':supply.get('stock_observation',{}).get('quantity'),
            'Stock observation date':supply.get('stock_observation',{}).get('observed_date',''),
            'Purchase confirmed':'FALSE',
            'Assembler accepted':'FALSE',
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
    fields=['Designator','Manufacturer','MPN','LCSC Part #','In CPL','Assembly status','Identity evidence','Evidence URL',
            'Procurement route','Supply status','Supply URL','Packing','Public stock observation','Stock observation date','Purchase confirmed','Assembler accepted']
    w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(sourcing)

cpl_refs=set(cpl_by_ref)
unknown=sorted(cpl_refs-all_bom_refs)
if unknown:
    raise SystemExit(f'CPL refs missing from BOM: {unknown}')
summary={
    'full_system_bom_group_rows':len(bom_rows),
    'bom_group_rows':len(jlc_bom),
    'jlc_bom_designators':len(cpl_by_ref),
    'bom_designators':len(all_bom_refs),
    'cpl_rows':len(cpl_rows),
    'cpl_top':sum(r['Side'].lower()=='top' for r in cpl_rows),
    'cpl_bottom':sum(r['Side'].lower()=='bottom' for r in cpl_rows),
    'lcsc_mapped_designators':sum(bool(r['LCSC Part #']) for r in sourcing),
    'lcsc_mapped_smt_designators':sum(bool(r['LCSC Part #']) and r['In CPL']=='TRUE' for r in sourcing),
    'lcsc_mapped_manual_designators':sum(bool(r['LCSC Part #']) and r['In CPL']=='FALSE' for r in sourcing),
    'mpn_only_designators':sum(r['Assembly status']=='MPN_ONLY_REQUIRES_JLC_MAPPING_OR_CONSIGNED_PART' for r in sourcing),
    'manual_or_offboard_designators':sum(r['Assembly status']=='MANUAL_OR_OFFBOARD' for r in sourcing),
    'identity_verified_designators':sum(r['Identity evidence']=='EXACT_MANUFACTURER_MPN_VERIFIED' for r in sourcing),
    'stock_reserved':False,
    'cpl_refs_missing_from_bom':unknown,
    'note':'JLC BOM includes only CPL machine placements; offboard TH301 remains in system BOM and sourcing CSV. JLC format follows official BOM/CPL headers. Blank IDs require mapping/consignment. Present IDs do not reserve stock or confirm an assembly order; new reviewed mappings include identity evidence.'
}
(out/'jlc-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
