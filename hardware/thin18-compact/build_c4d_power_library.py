#!/usr/bin/env python3
from pathlib import Path
import json, math, shutil, subprocess, sys

ROOT=Path(__file__).resolve().parent
LIB=ROOT/'c4d-power-lib'
PRETTY=LIB/'PandaDomesticPower.pretty'
PRETTY.mkdir(parents=True,exist_ok=True)

def fp_header(name,desc):
    return [
      f'(footprint "{name}"',
      '  (version 20250318)',
      '  (generator "pcbnew")',
      f'  (descr "{desc}")',
      '  (attr smd)'
    ]

def fp_tail():
    return ['  (embedded_fonts no)',')']

# SGM41513 exact recommended land pattern.
# Datasheet: 4x4 body, 0.5 pitch, outer row center spacing 3.8mm => ±1.9mm,
# land 0.70 x 0.24mm, EP 2.7x2.7mm.
lines=fp_header('SGM41513_YTQF24_4x4_P0.5_EP2.7','SGMICRO SGM41513 TQFN-4x4-24L; datasheet recommended land 0.7x0.24, P0.5, EP2.7')
lines += [
'  (fp_rect (start -2 -2) (end 2 2) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))',
'  (fp_rect (start -2.25 -2.25) (end 2.25 2.25) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))',
'  (fp_circle (center -2.45 1.5) (end -2.30 1.5) (stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))',
'  (fp_text reference "REF**" (at 0 -3) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
'  (fp_text value "SGM41513YTQF24G/TR" (at 0 3) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))',
]
# Top-view numbering: pin1 bottom-left, 1..6 left->right; 7..12 right bottom->top;
# 13..18 top right->left; 19..24 left top->bottom.
xs=[-1.25,-0.75,-0.25,0.25,0.75,1.25]
for i,x in enumerate(xs,1):
    lines.append(f'  (pad "{i}" smd roundrect (at {x} 1.9) (size 0.24 0.70) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.20))')
ys=[1.25,0.75,0.25,-0.25,-0.75,-1.25]
for j,y in enumerate(ys,7):
    lines.append(f'  (pad "{j}" smd roundrect (at 1.9 {y}) (size 0.70 0.24) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.20))')
for j,x in enumerate(reversed(xs),13):
    lines.append(f'  (pad "{j}" smd roundrect (at {x} -1.9) (size 0.24 0.70) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.20))')
for j,y in enumerate(reversed(ys),19):
    lines.append(f'  (pad "{j}" smd roundrect (at -1.9 {y}) (size 0.70 0.24) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.20))')
lines += [
'  (pad "25" smd rect (at 0 0) (size 2.7 2.7) (layers "F.Cu" "F.Mask") (zone_connect 2))',
'  (pad "" smd rect (at -0.68 -0.68) (size 1.12 1.12) (layers "F.Paste"))',
'  (pad "" smd rect (at 0.68 -0.68) (size 1.12 1.12) (layers "F.Paste"))',
'  (pad "" smd rect (at -0.68 0.68) (size 1.12 1.12) (layers "F.Paste"))',
'  (pad "" smd rect (at 0.68 0.68) (size 1.12 1.12) (layers "F.Paste"))',
] + fp_tail()
(PRETTY/'SGM41513_YTQF24_4x4_P0.5_EP2.7.kicad_mod').write_text('\n'.join(lines)+'\n')

# SGM62125 exact manufacturer land pattern.
lines=fp_header('SGM62125_XG_WLCSP15_1.46x2.3_P0.4','SGMICRO SGM62125 WLCSP-1.46x2.3-15B; P0.4, recommended pad diameter 0.23mm')
lines += [
'  (fp_rect (start -0.7415 -1.1635) (end 0.7415 1.1635) (stroke (width 0.08) (type default)) (fill none) (layer "F.Fab"))',
'  (fp_rect (start -1.0 -1.4) (end 1.0 1.4) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))',
'  (fp_circle (center -0.86 -1.28) (end -0.76 -1.28) (stroke (width 0.10) (type solid)) (fill none) (layer "F.SilkS"))',
'  (fp_text reference "REF**" (at 0 -2) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
'  (fp_text value "SGM62125AXG/TR" (at 0 2) (layer "F.Fab") (effects (font (size 0.7 0.7) (thickness 0.10))))',
]
rows='ABCDE'
for ri,row in enumerate(rows):
    y=-0.8 + ri*0.4
    for ci in range(3):
        x=-0.4 + ci*0.4
        ball=f'{row}{ci+1}'
        lines.append(f'  (pad "{ball}" smd circle (at {x:.1f} {y:.1f}) (size 0.23 0.23) (layers "F.Cu" "F.Paste" "F.Mask"))')
lines += fp_tail()
(PRETTY/'SGM62125_XG_WLCSP15_1.46x2.3_P0.4.kicad_mod').write_text('\n'.join(lines)+'\n')

def pin(ptype,x,y,rot,name,num,hide=False):
    h=' (hide yes)' if hide else ''
    return f'(pin {ptype} line (at {x} {y} {rot}) (length 2.54){h} (name "{name}" (effects (font (size 1 1)))) (number "{num}" (effects (font (size 1 1)))))'

def props(value,footprint,datasheet,desc,mfr,mpn,lcsc):
    return ' '.join([
      '(property "Reference" "U" (at 0 15.24 0) (effects (font (size 1.1 1.1))))',
      f'(property "Value" "{value}" (at 0 12.7 0) (effects (font (size 1.1 1.1))))',
      f'(property "Footprint" "{footprint}" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))',
      f'(property "Datasheet" "{datasheet}" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))',
      f'(property "Description" "{desc}" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))',
      f'(property "Manufacturer" "{mfr}" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))',
      f'(property "MPN" "{mpn}" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))',
      f'(property "LCSC" "{lcsc}" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))'
    ])

# Build symbol definitions.
syms=[]
body='(symbol "SGM41513YTQF24G_TR_0_1" (rectangle (start -10.16 12.7) (end 10.16 -12.7) (stroke (width 0.254) (type default)) (fill (type background))))'
# Migration-friendly schematic geometry: semantically equivalent pins line up with old BQ25628 positions.
pins=[]
pin_defs_41513=[
 ('passive',-12.7,10.16,0,'BTST','21',False),
 ('power_out',-12.7,7.62,0,'REGN','22',False),
 ('open_collector',-12.7,5.08,0,'nPG','3',False),
 ('input',-12.7,2.54,0,'PSEL','2',False),
 ('input',-12.7,-2.54,0,'TS','11',False),
 ('input',-12.7,-5.08,0,'nQON','12',False),
 ('power_in',-12.7,-7.62,0,'BAT','13',False),
 ('power_in',-12.7,-7.62,0,'BAT','14',False),
 ('power_out',-12.7,-10.16,0,'SYS','15',False),
 ('power_out',-12.7,-10.16,0,'SYS','16',False),
 ('open_collector',12.7,-7.62,180,'STAT','4',False),
 ('open_collector',12.7,-5.08,180,'nINT','7',False),
 ('bidirectional',12.7,-2.54,180,'SDA','6',False),
 ('input',12.7,0,180,'SCL','5',False),
 ('input',12.7,2.54,180,'nCE','9',False),
 ('passive',12.7,5.08,180,'SW','19',False),
 ('passive',12.7,5.08,180,'SW','20',False),
 ('passive',12.7,7.62,180,'PMID','23',False),
 ('power_in',12.7,10.16,180,'VBUS','24',False),
 ('input',12.7,10.16,180,'VAC','1',False),
 ('power_in',0,-15.24,90,'GND','17',False),
 ('power_in',0,-15.24,90,'GND','18',False),
 ('power_in',0,-15.24,90,'GND','25',False),
 ('no_connect',-2.54,15.24,270,'NC','8',False),
 ('no_connect',2.54,15.24,270,'NC','10',False),
]
for pd in pin_defs_41513:
    pins.append(pin(*pd))
sym='(symbol "SGM41513YTQF24G_TR" (exclude_from_sim no) (in_bom yes) (on_board yes) '+props(
    'SGM41513YTQF24G/TR','PandaDomesticPower:SGM41513_YTQF24_4x4_P0.5_EP2.7',
    'https://www.sg-micro.com/product/SGM41513',
    'SGMICRO non-D 3A 1S switching charger with NVDC; exact VAC/PSEL/nPG variant',
    'SGMICRO','SGM41513YTQF24G/TR','C5153778')+' '+body+' (symbol "SGM41513YTQF24G_TR_1_1" '+' '.join(pins)+'))'
syms.append(sym)

body='(symbol "SGM62125AXG_TR_0_1" (rectangle (start -8.89 8.89) (end 8.89 -8.89) (stroke (width 0.254) (type default)) (fill (type background))))'
pin_defs=[
 ('input','EN','A1',-11.43,6.35,0),
 ('power_in','VIN','A2',-11.43,3.81,0),('power_in','VIN','A3',-11.43,1.27,0),
 ('input','ADDR','B1',-11.43,-1.27,0),
 ('passive','SW1','B2',-11.43,-3.81,0),('passive','SW1','B3',-11.43,-6.35,0),
 ('power_in','AGND','C1',0,-11.43,90),('power_in','PGND','C2',2.54,-11.43,90),('power_in','PGND','C3',5.08,-11.43,90),
 ('bidirectional','SCL','D1',11.43,-6.35,180),('passive','SW2','D2',11.43,-3.81,180),('passive','SW2','D3',11.43,-1.27,180),
 ('bidirectional','SDA','E1',11.43,1.27,180),('power_out','VOUT','E2',11.43,3.81,180),('power_out','VOUT','E3',11.43,6.35,180),
]
pins=[pin(p[0],p[3],p[4],p[5],p[1],p[2]) for p in pin_defs]
sym='(symbol "SGM62125AXG_TR" (exclude_from_sim no) (in_bom yes) (on_board yes) '+props(
    'SGM62125AXG/TR','PandaDomesticPower:SGM62125_XG_WLCSP15_1.46x2.3_P0.4',
    'https://www.sg-micro.com/product/SGM62125',
    'SGMICRO 3.5A I2C buck-boost; exact WLCSP-15 P0.4; ADDR high starts at 3.4V',
    'SGMICRO','SGM62125AXG/TR','')+' '+body+' (symbol "SGM62125AXG_TR_1_1" '+' '.join(pins)+'))'
syms.append(sym)

lib='(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor") '+' '.join(syms)+')\n'
(LIB/'PandaDomesticPower.kicad_sym').write_text(lib)

contract={
 'date':'2026-09-29',
 'assets':{
   'SGM41513':{'symbol':'SGM41513YTQF24G_TR','footprint':'SGM41513_YTQF24_4x4_P0.5_EP2.7','pin_count':25,'source':'SGMICRO datasheet APRIL 2025','land':'0.7x0.24mm / P0.5 / EP2.7'},
   'SGM62125':{'symbol':'SGM62125AXG_TR','footprint':'SGM62125_XG_WLCSP15_1.46x2.3_P0.4','pin_count':15,'source':'SGMICRO datasheet AUGUST 2026 REV.A','land':'15x dia0.23mm / P0.4'}
 },
 'cw2215_generated':False,
 'reason':'authoritative CW2215B ball map still unavailable',
 'manufacturing_release':False
}
(LIB/'library-contract.json').write_text(json.dumps(contract,indent=2)+'\n')
print(json.dumps(contract,indent=2))
