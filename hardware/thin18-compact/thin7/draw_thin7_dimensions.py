"""Dimension drawing from the same contract as Blender; engineering envelope only."""
import json,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Rectangle,FancyBboxPatch
ROOT=Path(__file__).resolve().parent
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT; OUT.mkdir(exist_ok=True,parents=True)
c=json.loads((ROOT/'thin7-mechanical-contract.json').read_text())
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.edgecolor':'#c2cdd1','text.color':'#20333c'})
fig=plt.figure(figsize=(14,10),facecolor='#f5f7f8')
fig.text(.05,.955,'PANDA / THIN7',fontsize=23,weight='bold')
fig.text(.05,.916,'112 x 75 x 7.0 mm  |  Two coplanar PCBs and battery',fontsize=13)
ax=fig.add_axes([.05,.30,.56,.55]); ax.set_aspect('equal');ax.set_xlim(-10,123);ax.set_ylim(87,-7);ax.axis('off')
ax.add_patch(FancyBboxPatch((0,0),112,75,boxstyle='round,pad=0,rounding_size=5',fc='#e9edef',ec='#334b58',lw=1.5))
p=c['panel']['rect_xyxy_mm'];ax.add_patch(Rectangle((p[0],p[1]),p[2]-p[0],p[3]-p[1],fill=False,ls=(0,(4,3)),ec='#778c98',lw=1.2))
for name,b in c['boards'].items():
 color='#408c6c' if name.startswith('Core') else '#498ba9'
 ax.add_patch(Polygon(b['outline_xy_mm'],closed=True,fc=color,ec='white',lw=1.5))
b=c['battery']['rect_xyxy_mm'];ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fc='#d3ba7f',ec='white',lw=1.5))
ax.text(34,24,'BATTERY REGION\n62 x 51 mm\n3.1 mm complete-pack max',ha='center',va='center',linespacing=1.6,fontsize=10)
ax.text(34,42,'1100 mAh target\nNO PACK SELECTED',ha='center',va='center',fontsize=9,linespacing=1.5)
ax.text(88.4,21.7,'DISPLAY\n45 x 36 x 0.8 mm\n2 layers / ECO required',ha='center',va='center',color='white',fontsize=9,linespacing=1.5)
ax.text(48,64,'CORE / L-SHAPED\n99 x 30 mm bounds / 0.8 mm / 4 layers',ha='center',va='center',color='white',fontsize=9,linespacing=1.4)
ax.annotate('',xy=(0,80),xytext=(112,80),arrowprops={'arrowstyle':'<->','color':'#334b58'});ax.text(56,83.5,'112 mm',ha='center')
ax.annotate('',xy=(117,0),xytext=(117,75),arrowprops={'arrowstyle':'<->','color':'#334b58'});ax.text(120,37.5,'75 mm',ha='center',rotation=90)
fig.text(.065,.30,'Dashed: panel body 105.33 x 62.37 mm. Board outlines are empty templates.',fontsize=9,color='#637984')
side=fig.add_axes([.065,.16,.55,.09]);side.set_aspect('equal');side.set_xlim(-5,128);side.set_ylim(-2,12);side.axis('off')
side.add_patch(Rectangle((0,0),112,7,fc='#33434e'))
side.add_patch(Rectangle((3.335,6.8),105.33,.2,fc='#c3d0d3'))
side.annotate('',xy=(117,0),xytext=(117,7),arrowprops={'arrowstyle':'<->','color':'#334b58'});side.text(120,3.5,'7.0 mm',va='center',fontsize=10)
side.text(0,10.5,'ASSEMBLED SIDE / true aspect ratio',fontsize=10,weight='bold')
fig.text(.67,.835,'BATTERY SECTION / REQUIREMENTS',fontsize=11,weight='bold')
terms=list(c['z_budget_mm'].items());labels=['Rear wall','Insulation','Complete protected pack','Swelling space','Clearance + reserve','Panel bond','Panel + light + touch','Screen recess']
colors=['#33434e','#ac8d52','#d3ba7f','#e8cdae','#d8e1e5','#829ba8','#aebac0','#e4ebef']
bar=fig.add_axes([.67,.355,.07,.46]);bar.set_xlim(0,1);bar.set_ylim(0,7);bar.axis('off');z=0
for (key,h),label,color in zip(terms,labels,colors):
 bar.add_patch(Rectangle((0,z),1,h,fc=color,ec='white',lw=.7));z+=h
for i,(label,(_,h)) in enumerate(zip(reversed(labels),reversed(terms))):
 fig.text(.765,.79-i*.048,label,fontsize=10);fig.text(.947,.79-i*.048,f'{h:.2f}',ha='right',fontsize=10)
fig.text(.765,.375,'TOTAL',weight='bold',fontsize=11);fig.text(.947,.375,'7.00 mm',ha='right',weight='bold',fontsize=11)
fig.text(.67,.26,'Core + Display: 0.8 mm boards\nMounted component ceiling: 2.4 mm\nNo stacked board-to-board connector',fontsize=10,linespacing=1.6)
fig.text(.05,.085,'Mechanical partition verified. PCB rerouting, exact parts, supplier tolerances and full fit remain pending.',fontsize=11,weight='bold')
fig.text(.05,.052,'Current native Core-C1 / Display-C1 do not fit this case. Do not fabricate the outline templates.',fontsize=10,color='#637984')
fig.savefig(OUT/'Panda-Thin7-Dimensions.png',dpi=150,facecolor=fig.get_facecolor())
fig.savefig(ROOT/'thin7-dimensions.svg',facecolor=fig.get_facecolor())
