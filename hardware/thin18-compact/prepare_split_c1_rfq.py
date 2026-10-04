#!/usr/bin/env python3
"""Prepare a source-bound RFQ handoff outside Git; never send or place an order."""
import argparse,csv,hashlib,json,shutil
from pathlib import Path
from _split_c1_common import ROOT,REPO,sha
from verify_split_c1_fabrication import verify
from verify_split_c1_supply import audit

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--sets',type=int);a=p.parse_args()
    out=a.output.resolve()
    if out.is_relative_to(REPO) and not out.is_relative_to(REPO/'.work'):raise ValueError('RFQ output must stay outside Git source')
    if out.exists():raise ValueError('Refusing to replace an existing RFQ packet')
    if a.sets is not None and a.sets<1:raise ValueError('Set count must be positive')
    verified=verify();plan=json.loads((ROOT/'split-c1-supply-plan.json').read_text());supply=audit(plan,a.sets)
    process=json.loads((ROOT/'split-c1-assembly-process.json').read_text())
    out.mkdir(parents=True)
    archive=REPO/verified['archive']['path'];shutil.copy2(archive,out/archive.name)
    for name in ['SPLIT-C1-SUPPLY-REQUEST.md','SPLIT-C1-HARDWARE-FINISH.md']:
        shutil.copy2(ROOT/name,out/name)
    with (out/'exact-parts.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['Board','Refs','Manufacturer','Exact_MPN','Package','Catalog_ID','Quantity_per_set','Required_excluding_attrition','Route','Receipt_verified'])
        for row in plan['rows']:
            state=next(s for s in supply['groups'] if s['group']==row['group'])
            w.writerow([row['board'],','.join(row['refs']),row['manufacturer'],row['mpn'],row['footprint'],row.get('catalog_code') or '',row['quantity_per_two_board_set'],state['required_units_excluding_attrition'] or f"{row['quantity_per_two_board_set']} x N",row['assembly_route'],state['supply_closed']])
    pending=[r for r in plan['rows'] if r['assembly_route']=='JLC_SMT' and not r.get('catalog_code')]
    core=process['boards']['Core-C1'];holes=core['land_overlap_contacts']
    quantity=str(a.sets)+' two-board sets' if a.sets else 'N two-board sets; quantity must be confirmed before quotation/order'
    text=f'''# Split-C1 prototype RFQ — NOT SENT\n\nPlease quote {quantity}. This request is for two separate board designs, not a combined panel.\n\nCore:96x68mm/4layers/0.8mm; Display:45x36mm/2layers/0.8mm. Both ENIG/green mask. Core nominal copper35um on ALL four layers.\n\n## CAM confirmation\n\nCore has {core['via_count']} through vias. Exactly {core['land_overlap_hole_count']} holes currently overlap SMT lands and require epoxy fill, planarization and copper cap. Use the attached package's current VIA-IN-PAD.csv; old13-site maps are obsolete. Confirm named-site or full-via treatment and cost, while retaining every component PTH/slot and NPTH open.\n\n'''
    text+='\n'.join(f"- {h['ref']}.{h['pad']}: {h['side']}, X={h['center_mm'][0]} Y={h['center_mm'][1]}mm, drill={h['drill_mm']}mm, net={h['net']}." for h in holes)
    text+='''\n\nConfirm0.20/0.25mm drills,0.22/0.23mm WLCSP lands, actual dielectric/impedance build, stencil thickness/apertures, QFN exposed-pad paste, inspection, tooling rails and CPL rotation conventions. No copper scaling, mirror, pad resizing or trace-width edits are authorized. C301 has two1.9mm circular plated lead holes at20mm pitch.\n\n## Exact sourcing / receiving\n\nThe following exact MPNs still require a catalog mapping or approved receiving workflow. No lookalike variants are authorized:\n\n'''
    text+='\n'.join(f"- {','.join(r['refs'])}: {r['manufacturer']} {r['mpn']} ({r['footprint']}); {r['quantity_per_two_board_set']} per set." for r in pending)
    text+='''\n\nU906 is now exactly mapped to C699619 / SGM809B-TXN3LG/TR / SOT-23; this does not reserve stock. Confirm supplier provenance, exact labels/lot, MSL, cut-tape leaders and trailers, actual usable inventory, additional quantities and acceptance references for all supplied groups.\n\nC301 is customer post-assembly, not SMT consignment; TH301 is offboard. Do not omit other required placements. Please return outstanding engineering questions and a marked-up CAM preview before any order is approved.\n\nSuggested official contact routes (not a sent message): components quote@lcsc.com; PCBA pcba@lcsc.com, as listed at https://www.lcsc.com/service/question .\n\nNo quotation, allocation, payment, submission, shipment, CAM approval or assembly acceptance has been performed by this generator.\n'''
    (out/'RFQ-TO-SEND.md').write_text(text)
    record={'source_archive':verified['archive'],'kit_quantity':a.sets,'core_in_pad_holes':core['land_overlap_hole_count'],'unmapped_refs':[ref for row in pending for ref in row['refs']],'request_sent':False,'order_placed':False,'supplier_receipts_verified':False,'cam_accepted':False}
    (out/'rfq-status.json').write_text(json.dumps(record,indent=2)+'\n')
    (out/'SHA256SUMS').write_text(''.join(sha(f)+'  '+f.name+'\n' for f in sorted(out.iterdir()) if f.is_file()))
    print(json.dumps({'output':str(out),**record},indent=2))

if __name__=='__main__':main()
