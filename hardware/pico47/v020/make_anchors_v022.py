"""anchors_v022.json from placement_v021.json: SD to the left edge, PMIC and MCU blocks shifted right,
expander / flash / audio into the old SD area, buttons on the right edge level with the SD slot."""
import json, re, sys
src = json.load(open(sys.argv[1]))['parts']
out = {}
DY_BOTTOM = 0.6                     # bottom edge 114.8 -> 115.4
MCU_DX = 18.0                       # MCU block over the panel connector's data pins

PMIC = {r for r in src if re.fullmatch(r'(U|L|D|C|R|TH|TP)8\d\d', r)}
MCU = set('''J507 C527 R513 Y501 C522 C529 R511 C501 C503 C528 C532 C530 C531 C525 L508 C526 L506 C502 C543
C524 C523 C510 U501 C520 R726 R530 R529 C521 L507 C504 R512 R510 TP18 TP19 TP804 TP806 R731'''.split())
CHARGER = set('U901 L402 C201 C202 R201 R204 C303'.split())
FREE = set('''C203 C207 C206 C208 TP1 TP11 TP12 TP2 TPG1 C601 R604 R608 R609 R615 R616 R903 R904 R613
U402 C508 C533 C513 R523 R524 R525 R526 R527 C512 R612 C505 C506 J502
C209 R810 R811 R910 R911 C501 C206 C303 J502
L507 C504 C523 R512 R510 C510 C520 R726 R530 R529 C521'''.split())
for r, v in src.items():
    x, y, rot = v[:3]
    side = v[3] if len(v) > 3 else 'F'
    if r in FREE or r in ('J501', 'SW201', 'SW202', 'U506', 'U601', 'U904'):
        continue
    if r in PMIC:
        x += 14.0
    elif r in MCU:
        x += MCU_DX
        y += 0.3
    elif r in CHARGER:
        x += 3.5
    elif r in ('J201',):
        y += DY_BOTTOM
    out[r] = [round(x, 3), round(y, 3), rot, side]
SD_Y = 100.2
out['J501'] = [12.68, SD_Y, 270, 'F']
out['SW201'] = [61.6, SD_Y - 5.0, 90, 'F']
out['SW202'] = [61.6, SD_Y + 5.0, 90, 'F']
out['U506'] = [55.8, 93.0, 0, 'F']
out['U601'] = [6.6, 86.0, 0, 'F']             # expander next to the PMIC / SD switch it controls
out['U904'] = [55.6, 102.2, 0, 'F']
out['U402'] = [12.6, 89.4, 0, 'F']
# Bottom edge: touch / front-light FPCs left, USB-C centred, panel FPC right of USB-C under the MCU
out['J820'] = [50.2, 112.4, 0, 'F']
out['D203'] = [21.0, 114.5, 0, 'F']
out['J502'] = [56.9, 107.6, 0, 'F']            # speaker landing, bottom-right corner above J820            # status LED, lens towards the bottom wall (+y)
# USB-C ESD and CC parts at their v0.2.1 spots above J201 (J201 moved down 0.6 mm with the board edge);
# usb_fix_v022.py later lifts R206 by 0.35 mm for the hand-laid D+/D- crossover
for r in ('D201', 'D202', 'R206', 'R207'):
    x, y, rot = src[r][:3]
    out[r] = [x, round(y + DY_BOTTOM, 3), rot, 'F']
out['J804'] = [6.8, 112.6, 0, 'F']
out['J803'] = [13.2, 112.6, 0, 'F']
W, T, B, R4 = 0.5, 72.4, 115.4, 4.0
outline = [[W, T], [63.5, T], [63.5, B - R4], {'arc': [63.5 - R4, B - R4, R4, 0, 90]},
           [36.62, B], [36.62, 109.85], [27.38, 109.85], [27.38, B],
           {'arc': [W + R4, B - R4, R4, 90, 180]}]
# USB series resistors between U501.25/26 and J201; the rest of the MCU bottom row goes to its own pins so
# the area between U501 and the panel connector stays free for the 18-line data bus
out['R529'] = [38.6, 105.4, 90, 'F']
out['R530'] = [39.9, 105.4, 90, 'F']
target = {'C501': 'U501.46', 'R208': 'D203.2', 'R726': 'J820.13', 'C520': 'U501.29', 'C521': 'U501.29', 'C510': 'U501.4', 'R510': 'U501.4',
          'L507': 'U501.2', 'C504': 'U501.20', 'C523': 'U501.46', 'R512': 'U501.8'}
json.dump(dict(outline=outline, margin=0.2, edge=0.3, target=target,
               allow_edge={'J201': True, 'J501': True, 'SW201': True, 'SW202': True},
               parts=out), open(sys.argv[2], 'w'), indent=0)
print(len(out), 'anchors;', len(src) - len(out), 'left to the placer')
