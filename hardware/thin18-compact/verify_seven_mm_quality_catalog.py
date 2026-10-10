#!/usr/bin/env python3
"""Exact native catalog identity checks. A catalog code is not inventory/receipt acceptance."""
from pathlib import Path
import argparse,json,xml.etree.ElementTree as ET
from _split_c1_sourcing import blocks,property_value
H=Path(__file__).resolve().parent
CONTRACT=H/'seven_mm_quality_catalog.json'


def validate_identity(fields,expected):
    for key,source in [('Manufacturer','manufacturer'),('MPN','mpn'),('LCSC','code')]:
        if fields.get(key)!=expected[source]:raise ValueError('Catalog/native mismatch '+key)
    return True


def verify(candidate):
    candidate=Path(candidate);contract=json.loads(CONTRACT.read_text())
    if contract['schema']!='panda-seven-mm-exact-catalog-v1' or contract['stock_reserved'] is not False or contract['supplier_acceptance'] is not False:
        raise ValueError('Unverified catalog or supplier acceptance')
    rows={ref:r for r in contract['entries'] for ref in r['refs']}
    if len(rows)!=10:raise ValueError('Unexpected exact-catalog scope')
    native={property_value(b,'Reference'):b for _,_,b in blocks((candidate/'Core.kicad_pcb').read_text(),r'\(footprint\s')}
    root=ET.parse(candidate/'Core-netlist.xml');components={c.get('ref'):c for c in root.findall('components/comp')}
    for ref,row in rows.items():
        b=native[ref];fields={k:property_value(b,k) for k in ['Manufacturer','MPN','LCSC']};validate_identity(fields,row)
        validate_identity({f.get('name'):f.text or '' for f in components[ref].findall('fields/field')},row)
        land=(candidate/'Panda7.pretty'/(ref+'_Core.kicad_mod')).read_text()
        validate_identity({k:property_value(land,k) for k in ['Manufacturer','MPN','LCSC']},row)
    return {'exact_native_identities_checked':len(rows),'pcb_schematic_local_library_agree':True,'stock_reserved':False,'supplier_acceptance':False,'manufacturing_release':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('candidate',type=Path);a=p.parse_args();print(json.dumps(verify(a.candidate),indent=2))
