#!/usr/bin/env python3
"""Audit all populated system-BOM refs, including manual/offboard parts.

This is an origin/identity and sourcing gate, not electrical qualification.
New identities require an explicit policy review; an unfamiliar manufacturer
or MPN must never silently count as a domestic replacement.
"""
from pathlib import Path
import argparse, csv, json, re
from _split_c1_common import ROOT, REPO, sha, repo_entry

BOARDS={'Core-C1':'core-c1-96x68','Display-C1':'display-c1-45x36'}

def expand_refs(text):
    result=[]
    for token in (v.strip() for v in text.split(',')):
        if not token:continue
        m=re.fullmatch(r'([A-Za-z]+)(\d+)-([A-Za-z]+)?(\d+)',token)
        if m and (not m[3] or m[1]==m[3]):
            result.extend(m[1]+str(i) for i in range(int(m[2]),int(m[4])+1))
        else:result.append(token)
    if len(result)!=len(set(result)):raise ValueError('Duplicate grouped refs')
    return result

def policy_index(policy):
    result={}
    for row in policy['reviewed_identities']:
        if row['origin'] not in {'MAINLAND_MANUFACTURER','FOREIGN_MANUFACTURER'}:
            raise ValueError('Invalid reviewed origin')
        for ref in row['refs']:
            key=(row['board'],ref)
            if key in result:raise ValueError('Duplicate reviewed identity')
            result[key]=row
    return result

def classify(row, reviewed):
    if reviewed is None:return 'UNREVIEWED_IDENTITY'
    fields={'Manufacturer':'manufacturer','MPN':'mpn','Footprint':'footprint','LCSC':'library_id'}
    if any((row.get(k) or '')!=reviewed[v] for k,v in fields.items()):return 'UNREVIEWED_IDENTITY'
    return reviewed['origin']

def verify_fresh(report):
    if report['schema']!='panda-split-c1-domestic-audit-v1':raise ValueError('Wrong domestic audit schema')
    for entry in report['inputs'].values():
        if sha(REPO/entry['path'])!=entry['sha256']:raise ValueError('Stale domestic audit: '+entry['path'])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--require-complete',action='store_true',help='Fail while any foreign/unreviewed identity remains')
    args=ap.parse_args()
    policy_path=ROOT/'split-c1-domestic-policy.json'
    eco_path=ROOT/'split-c1-domestic-eco.json'
    policy=json.loads(policy_path.read_text());eco=json.loads(eco_path.read_text())
    if policy.get('no_foreign_exception') is not True:raise ValueError('All-domestic policy requires no foreign exception')
    reviewed=policy_index(policy)
    inputs={'policy':repo_entry(policy_path),'eco':repo_entry(eco_path)}
    boards={};foreign=[];unknown=[];identities={}
    for board,folder in BOARDS.items():
        prod=ROOT/'production'/folder;manifest_path=prod/'production-manifest.json'
        manifest=json.loads(manifest_path.read_text())
        if manifest['board_id']!=board or any(manifest['native_checks'].values()):
            raise ValueError('Wrong board or failed native checks')
        for label in ('pcb','bom','cpl'):
            entry=manifest['files'][label]
            if sha(REPO/entry['path'])!=entry['sha256']:raise ValueError('Stale export: '+label)
            inputs[board+'/'+label]=entry
        rows=list(csv.DictReader((prod/'manufacturing/bom.csv').open(encoding='utf-8-sig')))
        cpl=list(csv.DictReader((prod/'manufacturing/cpl.csv').open(encoding='utf-8-sig')))
        machine={row['Ref'] for row in cpl}
        if len(machine)!=len(cpl):raise ValueError('Duplicate CPL refs')
        total=set();domestic=set();foreign_refs=set();unknown_refs=set();missing=[]
        for row in rows:
            if row.get('DNP'):raise ValueError('DNP leaked into populated BOM')
            for ref in expand_refs(row['Refs']):
                if ref in total:raise ValueError('Duplicate system BOM ref')
                total.add(ref);identities[(board,ref)]=row
                origin=classify(row,reviewed.get((board,ref)))
                result={'board':board,'ref':ref,'manufacturer':row['Manufacturer'],'mpn':row['MPN'],
                        'footprint':row['Footprint'],'library_id':row.get('LCSC') or '',
                        'assembly':'SMT' if ref in machine else 'MANUAL_OR_OFFBOARD'}
                if origin=='MAINLAND_MANUFACTURER':domestic.add(ref)
                elif origin=='FOREIGN_MANUFACTURER':foreign.append(result);foreign_refs.add(ref)
                else:unknown.append(result);unknown_refs.add(ref)
                if ref in machine and not row.get('LCSC'):missing.append(ref)
        if not machine<=total:raise ValueError('CPL has refs outside system BOM')
        boards[board]={'populated_refs':len(total),'smt_refs':len(machine),
                       'manual_or_offboard_refs':sorted(total-machine),'domestic_refs':len(domestic),
                       'foreign_refs':sorted(foreign_refs),'unreviewed_refs':sorted(unknown_refs),
                       'mapped_smt_refs':len(machine)-len(missing),'unmapped_smt_refs':sorted(missing)}
    applied=[]
    for group in eco['applied_groups']:
        for ref in group['refs']:
            row=identities[(group['board'],ref)];fields=group['new_fields']
            for field in ('Manufacturer','MPN','LCSC'):
                if (row.get(field) or '')!=fields[field]:raise ValueError('Applied ECO identity mismatch: '+ref)
            applied.append({'board':group['board'],'ref':ref})
    stale=set(reviewed)-set(identities)
    if stale:raise ValueError('Policy contains removed populated refs: '+str(sorted(stale)))
    requirements={(r['board'],ref):r for r in policy['remaining_redesigns'] for ref in r['refs']}
    for row in foreign:
        if (row['board'],row['ref']) not in requirements:raise ValueError('Foreign ref has no next action')
        row['next_action']=requirements[(row['board'],row['ref'])]['next_action']
    # Changing a manufacturer label without reviewing the exact part fails closed.
    key=next(iter(identities));sample=identities[key].copy()
    sample['Manufacturer']='FH (Fenghua Advanced)' if sample['Manufacturer']!='FH (Fenghua Advanced)' else 'UNREVIEWED_MAKER'
    if classify(sample,reviewed.get(key))!='UNREVIEWED_IDENTITY':
        raise ValueError('Manufacturer-only relabel was accepted')
    complete=not foreign and not unknown
    report={'schema':'panda-split-c1-domestic-audit-v1','requirement':'All populated two-board BOM parts must have a mainland manufacturer; no retained foreign exception.',
            'scope':policy['scope'],'inputs':inputs,'boards':boards,
            'total_populated_refs':sum(v['populated_refs'] for v in boards.values()),
            'domestic_refs':sum(v['domestic_refs'] for v in boards.values()),
            'foreign_ref_count':len(foreign),'unreviewed_ref_count':len(unknown),
            'remaining_foreign':foreign,'unreviewed_identities':unknown,
            'applied_replacement_refs':len(applied),'applied_replacement_identities_verified':True,
            'manufacturer_only_relabel_rejected':True,'all_domestic_bom_complete':complete,
            'smt_mapping_complete':all(not v['unmapped_smt_refs'] for v in boards.values()),
            'assembly_order_ready':False,'physical_evt_passed':False,'manufacturing_release':False,
            'status':'ALL_DOMESTIC_BOM_COMPLETE' if complete else 'BLOCKED_ALL_DOMESTIC_REQUIREMENT'}
    verify_fresh(report)
    out=ROOT/'split-c1-domestic-audit.json';out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('total_populated_refs','domestic_refs','foreign_ref_count',
          'unreviewed_ref_count','applied_replacement_refs','all_domestic_bom_complete','status')},indent=2))
    if args.require_complete and not complete:raise SystemExit(1)

if __name__=='__main__':main()
