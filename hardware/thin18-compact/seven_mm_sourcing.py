#!/usr/bin/env python3
"""Source-bound catalog metadata ECO for the real Product-D native design.

Only exact catalog identities and assembly dispositions are edited. Routing, pin
functions, land shapes, population and native rule files are never changed. Seven
SMT refs still require an actual JLC registration/receipt; a manual cell assembly
is not an SMT part. A prepared RFQ is not accepted supply or manufacturing release.
"""
from pathlib import Path
import argparse, csv, hashlib, json, re, subprocess, xml.etree.ElementTree as ET
from seven_mm_routing import sexpr_blocks, native_semantic_fingerprint, copper_blocks
from seven_mm_native_evidence import verify_native_clean
from _split_c1_common import ROOT, REPO, kicad_cli

CONTRACT = ROOT / 'seven_mm_product_sourcing.json'
PRODUCT_SOURCE = ROOT / 'seven_mm_product_source.json'
SOURCE_HASH = 'bd8c8f37383eb927574dbf09f8fe17ed1f996da5029a6881ae877095ed12a10f'
FH = 'FH (Fenghua Advanced)'
# Independent exact acceptance table: syntax-valid C-numbers alone are insufficient.
EXACT = {
    'L506': ('Sunlord','SDCL1005C24NJTDF','SDCL1005C24NJTDF','C74301','0402'),
    'L507': ('Sunlord','SDCL1608C2N0STDF','SDCL1608C2N0STDF','C370234','0603'),
    'L508': ('Sunlord','SDCL1005C2N0STDF','SDCL1005C2N0STDF','C43365','0402'),
    'C530': (FH,'0402CG0R8C500NT','0402CG0R8C500NT','C40459','0402'),
    'C531': (FH,'0402CG0R8C500NT','0402CG0R8C500NT','C40459','0402'),
    'Y501': ('YXC (Yangxing)','X322540MOB4SI','XL2EL89COI-111YLC-40M','C18214314','SMD3225-4P'),
    **{f'R{i}': (FH,'RC-02K0000FT','RC-02000FT','C140225','0402') for i in range(540,546)},
}
PENDING = {
    **{f'U{i}': ('SGMICRO','SGM2578SDYG/TR','WLCSP-0.9x0.9-4B-D') for i in range(402,406)},
    'U902': ('SGMICRO','SGM62125AXG/TR','WLCSP-1.46x2.3-15B'),
    'U905': ('SGMICRO','SGM37601YTRL20G/TR','TQFN-3.5x3.5-20L'),
    'J201': ('MUP','U22401-17','U22401-17 / 16-pin mid-mount for 0.80mm PCB'),
}
CELL_MAKER = 'Yichang Power Glory Technology Co., Ltd.'
ALL_REFS = set(EXACT) | set(PENDING) | {'BT301'}
EDITABLE = {'Manufacturer','MPN','LCSC','Datasheet','PandaSupplyRoute',
            'PandaAssemblyStage','PandaSupplyStatus','PandaSourceURL'}
PROP = re.compile(r'^\(property\s+("(?:\\.|[^"\\])*")\s+("(?:\\.|[^"\\])*")')
Q = lambda value: json.dumps(str(value), ensure_ascii=False)
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def indexed(plan):
    rows = {}
    for group in ['catalog','pending_registration','manual_post_assembly']:
        require(isinstance(plan.get(group),list), 'Missing sourcing group: '+group)
        for row in plan[group]:
            require(row.get('board') == 'Core' and row.get('refs'), 'Wrong board or empty refs')
            for ref in row['refs']:
                require(ref not in rows, 'Duplicate sourcing disposition: '+ref)
                rows[ref] = row
    return rows


def validate(plan):
    require(plan.get('schema') == 'panda-seven-mm-product-sourcing-v1', 'Wrong sourcing schema')
    require(plan.get('product_source_sha256') == SOURCE_HASH, 'Wrong product predecessor')
    require(plan.get('scope_original_refs') == sorted(ALL_REFS), 'Original twenty-ref scope changed')
    require(all(plan.get(k) is False for k in ['supply_acceptance_complete','manufacturing_release','orders_submitted']),
            'No supplier receipt/order/release may be invented')
    rows = indexed(plan)
    require(set(rows) == ALL_REFS, 'A required reference was removed or introduced')
    require({r for row in plan['catalog'] for r in row['refs']} == set(EXACT), 'Wrong catalog set')
    require({r for row in plan['pending_registration'] for r in row['refs']} == set(PENDING), 'Wrong registration set')
    require(len(plan['manual_post_assembly']) == 1 and plan['manual_post_assembly'][0]['refs'] == ['BT301'], 'Wrong manual set')
    for ref, (maker,old,new,code,package) in EXACT.items():
        r=rows[ref]
        require(tuple(r.get(k) for k in ['manufacturer','old_mpn','mpn','lcsc','package']) == (maker,old,new,code,package),
                'Exact manufacturer/model/code/package mismatch: '+ref)
        kind='EXACT_CODE' if old==new else 'REVIEWED_MPN_REPLACEMENT'
        require(r.get('change_kind') == kind, 'A replacement must not be disguised as an alias: '+ref)
        require(r.get('route') == 'JLC_CATALOG' and r.get('assembly_stage') == 'SMT', 'Catalog assembly disposition mismatch')
        require(r.get('catalog_identity_verified') is True and re.fullmatch('[a-f0-9]{64}',r.get('source_page_sha256','')),
                'Catalog identity evidence missing: '+ref)
        require(r['source_url'].startswith('https://jlcpcb.com/partdetail/') and r['source_url'].endswith('/'+code), 'Wrong exact source URL')
        require(r.get('stock_reserved') is False and r.get('order_supply_accepted') is False, 'Identity is not inventory/receipt')
    r=rows['Y501'];sp=r['electrical_spec']
    for key,value in {'frequency_mhz':40,'load_capacitance_pf':12,'frequency_tolerance_ppm':10,
                      'temperature_stability_ppm':20,'esr_max_ohm':40,'temperature_min_c':-40,'temperature_max_c':85,
                      'body_maximum_mm':[3.3,2.6,.8],'land_size_mm':[1.4,1.2],
                      'land_centers_mm':[[-1.1,.85],[1.1,.85],[1.1,-.85],[-1.1,-.85]],
                      'ground_pins':['2','4'],'signal_pins':['1','3']}.items():
        require(sp.get(key)==value, 'Unreviewed crystal specification: '+key)
    require(r.get('drawing_reviewed') is True, 'Crystal land drawing not reviewed')
    require(rows['R540']['electrical_spec']['resistance_ohm'] == 0, 'Flash jumpers are not 22-ohm parts')
    for ref in ['C530','C531']:
        require(rows[ref]['electrical_spec']=={'capacitance_pf':.8,'tolerance_pf':.25,'voltage_v':50,'dielectric':'C0G'},
                'RF capacitor value/tolerance/voltage changed')
    for ref,(maker,mpn,package) in PENDING.items():
        r=rows[ref]
        require((r['manufacturer'],r['mpn'],r['package'])==(maker,mpn,package), 'Unreviewed exact variant: '+ref)
        require(r['lcsc']=='' and r['route']=='EXACT_MANUFACTURER_TO_JLC_CONSIGNMENT' and r['assembly_stage']=='SMT',
                'Do not fabricate catalog codes or omit a required SMT part: '+ref)
        for key in ['catalog_identity_verified','jlc_custom_code_assigned','quote_received','stock_reserved','order_supply_accepted']:
            require(r.get(key) is False, 'Unproven supplier/catalog acceptance: '+key)
        require(r.get('jlc_registration_required') is True and r['submission_state']=='PREPARED_NOT_SUBMITTED', 'Unproven submission')
    r=rows['BT301']
    require(r['manufacturer']==CELL_MAKER and r['mpn']=='CR1216' and r['lcsc']=='', 'Wrong cell/assembly identity')
    require(r['route']=='FACTORY_TABBED_POST_SMT' and r['assembly_stage']=='POST_SMT_MANUAL', 'Primary cell cannot enter reflow')
    require(r['required_in_system_bom'] is True and r['bare_cell_code_is_not_assembly_code'] is True, 'Do not omit the RTC cell assembly')
    for key in ['reflow_allowed','direct_solder_to_cell_allowed','assembly_drawing_accepted','stock_reserved','order_supply_accepted']:
        require(r.get(key) is False, 'Unproven/unsafe primary-cell assembly disposition: '+key)
    expected={'original_missing_references':20,'new_jlc_catalog_mapped_references':12,
              'pending_jlc_registration_references':7,'manual_post_assembly_references':1}
    require(plan.get('summary') == expected, 'Counts cannot hide unresolved supply')
    return rows


def properties(block):
    result={}
    for prop in sexpr_blocks(block,'(property'):
        m=PROP.match(prop)
        if m is None:
            require(prop in {'(property pad_prop_heatsink)','(property pad_prop_bga)'}, 'Malformed native property')
            continue  # Native pad function flags are NOT editable string fields.
        key,value=json.loads(m[1]),json.loads(m[2])
        require(key not in result, 'Duplicate native property: '+key)
        result[key]=value
    return result


def set_properties(block, fields):
    require(set(fields)<=EDITABLE, 'Only catalog/assembly metadata may be edited')
    # Match/rewrite one native property at a time; never use global model renames.
    for key,value in fields.items():
        found=[p for p in sexpr_blocks(block,'(property') if PROP.match(p) and json.loads(PROP.match(p)[1])==key]
        require(len(found)<=1, 'Ambiguous property '+key)
        if found:
            p=found[0];m=PROP.match(p);new=p[:m.start(2)]+Q(value)+p[m.end(2):]
            block=block.replace(p,new,1)
        else:
            pos=block.rfind(')')
            new=f'(property {Q(key)} {Q(value)} (at 0 0 0) (hide yes) (effects (font (size 1 1))))'
            block=block[:pos]+'\n'+new+'\n'+block[pos:]
    return block


def strip_metadata(text):
    for p in sexpr_blocks(text,'(property'):
        if PROP.match(p) and json.loads(PROP.match(p)[1]) in EDITABLE:
            text=text.replace(p,'',1)
    # Outside these property expressions there must be no semantic/text edits.
    return tuple(re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()"]+',text))


def desired(row):
    status=('CATALOG_IDENTITY_ONLY_NOT_RESERVED' if row['route']=='JLC_CATALOG' else
            'FACTORY_ASSEMBLY_DRAWING_AND_RECEIPT_PENDING' if row['assembly_stage']=='POST_SMT_MANUAL' else
            'JLC_REGISTRATION_AND_RECEIPT_PENDING')
    return {'Manufacturer':row['manufacturer'],'MPN':row['mpn'],'LCSC':row['lcsc'],
            'Datasheet':row.get('datasheet',row['source_url']),'PandaSupplyRoute':row['route'],
            'PandaAssemblyStage':row['assembly_stage'],'PandaSupplyStatus':status,'PandaSourceURL':row['source_url']}


def patch_blocks(text, token, rows, definitions=False):
    seen=[]
    for block in sexpr_blocks(text,token):
        fields=properties(block);ref=fields.get('Reference')
        if ref not in rows:
            continue
        row=rows[ref]
        # Definitions have no MPN in the immutable donor; actual instances do.
        if not definitions or 'MPN' in fields:
            require(fields.get('MPN') == row.get('old_mpn',row['mpn']), 'Wrong native predecessor MPN: '+ref)
            require(fields.get('Manufacturer') == row['manufacturer'], 'Native manufacturer mismatch: '+ref)
            require(fields.get('LCSC','') == '', 'Refusing to overwrite an existing catalog mapping: '+ref)
        replacement=set_properties(block,desired(row))
        require(strip_metadata(block)==strip_metadata(replacement), 'Non-metadata native edit: '+ref)
        require(text.count(block)==1, 'Non-unique native object: '+ref)
        text=text.replace(block,replacement,1);seen.append(ref)
    return text,seen


def native_netlist(candidate, board):
    path=candidate/(board+'-netlist.xml')
    with (candidate/(board+'-sourcing-netlist.log')).open('w') as log:
        subprocess.run([kicad_cli(),'sch','export','netlist','--format','kicadxml','--output',str(path),str(candidate/(board+'.kicad_sch'))],
                       cwd=candidate,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=90)
    root=ET.parse(path).getroot()
    comps={c.get('ref'):{'value':c.findtext('value',''),'footprint':c.findtext('footprint',''),
            'fields':{f.get('name'):f.text or '' for f in c.findall('fields/field')}} for c in root.findall('components/comp')}
    nets={(n.get('ref'),n.get('pin')):net.get('name') for net in root.findall('nets/net') for n in net.findall('node')}
    return comps,nets


def inspect_fields(candidate, plan):
    import wx
    app=wx.GetApp() or wx.App(False)
    import pcbnew as P
    candidate=Path(candidate).resolve();rows=validate(plan);physical=[];netlists={}
    for name in ['Core','Display']:
        comps,nets=native_netlist(candidate,name);netlists[name]={'comps':comps,'nets':nets}
        board=P.LoadBoard(str(candidate/(name+'.kicad_pcb')))
        for fp in board.GetFootprints():
            ref=fp.GetReference();fs={f.GetName():f.GetText() for f in fp.GetFields()}
            if name=='Core' and ref in rows:
                expected=desired(rows[ref]);require(not fp.IsDNP() and not fp.IsExcludedFromBOM(), 'Required component omitted: '+ref)
                require(all(fs.get(k)==v for k,v in expected.items()), 'Native catalog fields differ: '+ref)
                xf=comps[ref]['fields']
                require(all(xf.get(k)==v for k,v in expected.items() if k!='Datasheet'), 'Netlist catalog differs: '+ref)
                lf=properties((candidate/'Panda7.pretty'/(ref+'_Core.kicad_mod')).read_text())
                require(all(lf.get(k)==v for k,v in expected.items()), 'Local land metadata differs: '+ref)
                if ref=='Y501':
                    # Check the actual unrotated local-land definition, not a generic package label.
                    lf=P.FootprintLoad(str(candidate/'Panda7.pretty'),'Y501_Core')
                    pads={p.GetNumber():p for p in lf.Pads()}
                    require(set(pads)=={'1','2','3','4'}, 'Crystal pin count changed')
                    for num,xy in zip(['1','2','3','4'],rows[ref]['electrical_spec']['land_centers_mm']):
                        pad=pads[num]
                        require([round(P.ToMM(pad.GetPosition().x),6),round(P.ToMM(pad.GetPosition().y),6)]==xy, 'Crystal land position differs')
                        require([round(P.ToMM(pad.GetSize().x),6),round(P.ToMM(pad.GetSize().y),6)]==[1.4,1.2], 'Crystal pad size differs')
                    require({n:nets[('Y501',n)] for n in pads}=={'1':'XTAL_P','2':'GND','3':'XTAL_N','4':'GND'}, 'Crystal signal/GND mapping changed')
                    require('18p' in comps['C528']['value'] and '18p' in comps['C529']['value'], 'Crystal load caps changed')
            if fp.IsDNP() or fp.IsExcludedFromBOM():
                continue
            physical.append({'board':name,'ref':ref,'manufacturer':fs.get('Manufacturer',''),'mpn':fs.get('MPN',''),
                             'lcsc':fs.get('LCSC',''),'value':fp.GetValue(),'footprint':str(fp.GetFPID().GetUniStringLibId()),
                             'assembly_stage':fs.get('PandaAssemblyStage','SMT'),
                             'supply_route':fs.get('PandaSupplyRoute','EXISTING_CATALOG_IDENTITY_NOT_REAUDITED'),
                             'supply_status':fs.get('PandaSupplyStatus','NOT_RESERVED_OR_RECEIVED')})
    for path in [candidate/'Core.kicad_sch',candidate/'Panda7.kicad_sym']:
        seen={}
        for block in sexpr_blocks(path.read_text(),'(symbol'):
            fs=properties(block);ref=fs.get('Reference')
            if ref not in rows:continue
            require(all(fs.get(k)==v for k,v in desired(rows[ref]).items()), 'Symbol/instance metadata mismatch: '+ref)
            seen[ref]=seen.get(ref,0)+1
        expected_count=2 if path.suffix=='.kicad_sch' else 1
        require(seen=={r:expected_count for r in rows}, 'Missing duplicate source definition/instance metadata')
    actual_missing={r['ref'] for r in physical if not re.fullmatch(r'C\d+',r['lcsc'])}
    require(actual_missing==set(PENDING)|{'BT301'}, 'Unexpected native missing-code set: '+repr(actual_missing))
    return physical,netlists


def apply(candidate, contract=CONTRACT):
    candidate=Path(candidate).resolve();plan=json.loads(Path(contract).read_text());rows=validate(plan)
    require(candidate.is_dir(), 'Missing fresh native candidate')
    require(not candidate.is_relative_to(REPO) or candidate.is_relative_to(REPO/'.work'), 'Never patch tracked CAD/output')
    require(sha(PRODUCT_SOURCE)==SOURCE_HASH, 'Product-D source changed; review sourcing predecessor')
    require((candidate/'PRODUCT-D-REBUILD.json').is_file(), 'Rebuild Product D before applying this overlay')
    files=[candidate/'Core.kicad_pcb',candidate/'Core.kicad_sch',candidate/'Panda7.kicad_sym']
    files += [candidate/'Panda7.pretty'/(ref+'_Core.kicad_mod') for ref in sorted(rows)]
    before={p:p.read_bytes() for p in files}
    semantics={name:native_semantic_fingerprint(candidate/(name+'.kicad_pcb')) for name in ['Core','Display']}
    copper={name:copper_blocks(candidate/(name+'.kicad_pcb')) for name in ['Core','Display']}
    unchanged={p:sha(p) for p in candidate.glob('*') if p.suffix in {'.kicad_pro','.kicad_dru'} or p.name.startswith('Display.') or p.name in {'sym-lib-table','fp-lib-table'}}
    product=json.loads(PRODUCT_SOURCE.read_text())
    require(semantics['Core']==product['output_semantic_sha256'], 'Not the reviewed Product-D geometry')
    for name in ['Core.kicad_sch','Panda7.kicad_sym','Core.kicad_pro']:
        require(sha(candidate/name)==product['source_text_patches'][name]['output_sha256'],
                'Not the reviewed Product-D electrical source: '+name)
    pre_nets={n:native_netlist(candidate,n)[1] for n in ['Core','Display']}
    try:
        for p in files:
            text=p.read_text()
            if p.suffix=='.kicad_pcb':text,seen=patch_blocks(text,'(footprint',rows)
            elif p.suffix in {'.kicad_sym','.kicad_sch'}:text,seen=patch_blocks(text,'(symbol',rows,definitions=True)
            else:
                ref=properties(text)['Reference'];row=rows[ref];old=properties(text)
                require(old.get('MPN')==row.get('old_mpn',row['mpn']) and old.get('LCSC','')=='', 'Wrong local library predecessor')
                text=set_properties(text,desired(row));seen=[ref]
            require(strip_metadata(before[p].decode())==strip_metadata(text), 'A non-metadata source object changed: '+p.name)
            if p.suffix in {'.kicad_pcb','.kicad_sch','.kicad_sym'}:
                require(set(seen)==ALL_REFS and len(seen)==(40 if p.suffix=='.kicad_sch' else 20), 'Missing catalog patch targets')
            p.write_text(text)
        require(all(sha(p)==v for p,v in unchanged.items()), 'Source project/rules or Display changed')
        for name in ['Core','Display']:
            require(native_semantic_fingerprint(candidate/(name+'.kicad_pcb'))==semantics[name], 'Footprint/pin/outline geometry changed')
            require(copper_blocks(candidate/(name+'.kicad_pcb'))==copper[name], 'Routed copper changed')
        physical,netlists=inspect_fields(candidate,plan)
        require(all(netlists[n]['nets']==pre_nets[n] for n in pre_nets), 'Schematic pin-to-net relation changed')
        native={n:verify_native_clean(candidate/(n+'.kicad_pcb')) for n in ['Core','Display']}
        result={'schema':'panda-seven-mm-sourcing-rebuild-v1','source_revision':'D','contract_sha256':sha(contract),
                'native':native,'summary':plan['summary'],'native_physical_bom_references':len(physical),
                'geometry_copper_rules_pin_nets_unchanged':True,'all_20_required_references_retained':True,
                'remaining_smt_registration_refs':sorted(PENDING),'post_smt_refs':['BT301'],
                'catalog_mapping_complete':False,'supplier_acceptance_complete':False,'manufacturing_release':False}
        (candidate/'SOURCING-REBUILD.json').write_text(json.dumps(result,indent=2)+'\n')
        (candidate/'SOURCING-NATIVE-BOM.json').write_text(json.dumps(physical,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'native':{n:v['counts'] for n,v in native.items()},'summary':plan['summary'],
                          'geometry_copper_rules_pin_nets_unchanged':True,'supplier_acceptance_complete':False},indent=2))
        return result
    except Exception:
        for p,data in before.items():p.write_bytes(data)
        for n in ['Core','Display']:native_netlist(candidate,n)
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',type=Path,required=True)
    args=parser.parse_args();apply(args.candidate)
