#!/usr/bin/env python3
import csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
c=json.load(open(ROOT/'c4d-power-pin-contract.json'))
a=json.load(open(ROOT/'c4-power-architecture.json'))

def fail(msg):
    print('FAIL:',msg,file=sys.stderr)
    raise SystemExit(2)

if c['sgm41513']['exact_mpn']!='SGM41513YTQF24G/TR': fail('charger MPN')
if c['sgm41513']['exact_variant']!='non-D': fail('charger variant')
if c['sgm41513']['bc12'] is not False: fail('non-D must not claim BC1.2')
expected41513={
 '1':'VAC','2':'PSEL','3':'nPG','4':'STAT','5':'SCL','6':'SDA','7':'nINT','8':'NC','9':'nCE','10':'NC','11':'TS','12':'nQON',
 '13':'BAT','14':'BAT','15':'SYS','16':'SYS','17':'GND','18':'GND','19':'SW','20':'SW','21':'BTST','22':'REGN','23':'PMID','24':'VBUS','EP':'GND'
}
if c['sgm41513']['pins']!=expected41513: fail('SGM41513 pin table drift')

expected62125={
 'A1':'EN','A2':'VIN','A3':'VIN','B1':'ADDR','B2':'SW1','B3':'SW1','C1':'AGND','C2':'PGND','C3':'PGND',
 'D1':'SCL','D2':'SW2','D3':'SW2','E1':'SDA','E2':'VOUT','E3':'VOUT'
}
if c['sgm62125']['pins']!=expected62125: fail('SGM62125 pin table drift')
if c['sgm62125']['startup']['ADDR_high']!={'address':'0x76','vout_v':3.4}: fail('SGM62125 startup policy')
if c['cw2215b']['ball_map_frozen'] is not False: fail('CW2215 ball map must remain blocked until authoritative evidence')
if c['usb_c']['default_charge_input_ma']!=500: fail('USB default input-current safety policy')
if any(x in c['usb_c']['product_contract'] for x in ('PD','PPS')) and 'no PD/PPS' not in c['usb_c']['product_contract']: fail('PD policy')

# Architecture must agree with exact variant correction.
if a['base']['charger']['mpn']!=c['sgm41513']['exact_mpn']: fail('architecture charger mismatch')
if a['base']['charger'].get('bc12') is not False: fail('architecture still claims BC1.2')
if a['base']['aon_buckboost']['mpn']!=c['sgm62125']['exact_mpn']: fail('architecture buckboost mismatch')
if a['load_switch_policy']['domesticization_status']!='BLOCKED': fail('unsafe load-switch substitution unblocked')

rows=list(csv.DictReader(open(ROOT/'c4d-power-net-migration.csv',encoding='utf-8')))
if len(rows)<20: fail('migration table too small')
if not any(r['status']=='BLOCKED_BALL_MAP' for r in rows): fail('CW2215 blocker missing')
if not any(r['current_ref']=='U202-U205' for r in rows): fail('USB removal migration missing')

report={
 'date':'2026-09-29',
 'result':'PASS_C4D_PIN_LEVEL_INPUT_CHECKS',
 'sgm41513_exact_pin_map':True,
 'sgm62125_exact_pin_map':True,
 'cw2215_logical_contract':True,
 'cw2215_ball_map_frozen':False,
 'usb_default_current_ma':500,
 'migration_rows':len(rows),
 'ready_for_cad':['C4D-1 SGM41513 charger/NVDC','C4D-2 SGM62125 buck-boost'],
 'blocked':['C4D-3 CW2215B symbol/footprint until authoritative ball map'],
 'manufacturing_release':False
}
(ROOT/'c4d-power-contract-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
