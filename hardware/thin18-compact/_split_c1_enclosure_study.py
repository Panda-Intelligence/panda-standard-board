"""Calculate an explicit side-by-side battery study, without fit signoff."""
import math

def side_battery_budget(inputs,display_rect,core_t,gap,display_t):
    s=inputs.get('side_battery_study')
    if s is None:return None
    if s['architecture']!='battery_beside_display_below_core_b':raise ValueError('Unknown side battery architecture')
    r=s['battery_rect_xyxy_mm'];dim=s['maximum_pack_xy_thickness_mm']
    outer=s['proposed_outer_xyz_mm'];v=s['z_parameters_mm']
    numbers=r+dim+outer+list(v.values())
    if any(not isinstance(n,(int,float)) or not math.isfinite(n) for n in numbers):raise ValueError('Non-finite enclosure study dimension')
    if any(n<=0 for n in dim+outer) or any(n<0 for n in v.values()):raise ValueError('Invalid enclosure study allowance')
    if r[0]<0 or r[1]<0 or r[2]>96 or r[3]>68:raise ValueError('Side battery leaves Core XY')
    if abs(r[2]-r[0]-dim[0])>1e-6 or abs(r[3]-r[1]-dim[1])>1e-6:raise ValueError('Pack and cavity XY budget differ')
    separation=display_rect[0]-r[2]
    if separation<s['minimum_display_xy_separation_mm']:raise ValueError('Side battery intersects Display projection')
    panel_back=core_t+v['core_front_component_budget']+v['front_mounted_allowance']+v['panel_clearance']
    front=panel_back+v['panel_thickness_budget']+v['front_wall']
    battery_top=-(v['core_back_component_budget']+v['battery_insulation'])
    battery_bottom=battery_top-dim[2]-v['battery_swelling']
    display_bottom=-(gap+display_t+v['display_front_component_budget'])
    rear=min(battery_bottom,display_bottom)-v['rear_wall']
    required=front-rear+v['manufacturing_reserve']
    if required>outer[2]+1e-6:raise ValueError('Proposed shell is thinner than parameter budget')
    # Supplier pack max dimensions, mounted heights and FPC solids remain unsigned.
    return {
      'status':s['status'],'architecture':s['architecture'],
      'battery_rect_xyxy_mm':r,'maximum_pack_xy_thickness_mm':dim,
      'battery_display_xy_separation_mm':separation,
      'proposed_outer_xyz_mm':outer,'panel_back_core_b_z_mm':round(panel_back,6),
      'outer_front_core_b_z_mm':round(front,6),'battery_top_core_b_z_mm':round(battery_top,6),
      'battery_bottom_with_swelling_core_b_z_mm':round(battery_bottom,6),
      'display_front_extent_core_b_z_mm':round(display_bottom,6),
      'outer_rear_core_b_z_mm':round(rear,6),
      'calculated_outer_thickness_with_reserve_mm':round(required,6),
      'parameter_budget_passed':True,
      'engineering_allowances_are_not_supplier_maxima':True,
      'selected_pack':None,'enclosure_fit_verified':False,'manufacturing_release':False,
      'open_constraints':s['open_constraints'],
      'basis':'Core B plane=0; Core F=+0.8; Display B=-1.5; Display F=-2.3. Pack sits beside Display in XY and below Core backside components.'}

def openscad_study(inputs):
    import json
    b=side_battery_budget(inputs,[38,30,83,66],.8,1.5,.8)
    s=inputs['side_battery_study']
    return '\n'.join([
      '// Review-only space budget: no case ports, supports, exact bodies or fit signoff.',
      '// Source: split-c1-mechanical-inputs.json; Core XY uses native KiCad coordinates.',
      'outer='+json.dumps(s['proposed_outer_xyz_mm'])+';',
      'pack_rect='+json.dumps(s['battery_rect_xyxy_mm'])+';',
      'pack_max='+json.dumps(s['maximum_pack_xy_thickness_mm'])+';',
      'panel_back='+str(b['panel_back_core_b_z_mm'])+';',
      'panel_thickness='+str(s['z_parameters_mm']['panel_thickness_budget'])+';',
      'battery_top='+str(b['battery_top_core_b_z_mm'])+';',
      'swelling='+str(s['z_parameters_mm']['battery_swelling'])+';',
      'rear='+str(b['outer_rear_core_b_z_mm']-.1)+';',
      'module slab(r,z,h){translate([r[0],r[1],z])cube([r[2]-r[0],r[3]-r[1],h]);}',
      'color([0.1,0.5,0.2])slab([0,0,96,68],0,.8); // Core-C1',
      'color([0.1,0.25,0.7])slab([38,30,83,66],-2.3,.8); // Display-C1 mirrored',
      'color([.85,.65,.1])slab(pack_rect,battery_top-pack_max[2],pack_max[2]);',
      'color([1,.6,.2,.25])slab(pack_rect,battery_top-pack_max[2]-swelling,swelling);',
      'color([.15,.15,.15])slab([-4.665,2.815,100.665,65.185],panel_back,panel_thickness);',
      'color([.6,.8,1,.10])translate([48-outer[0]/2,34-outer[1]/2,rear])cube(outer);',
      '// Engineering shell box112x75x19; no fabrication or3D-print approval.',
      '// Component/lead/FPC/tool/antenna/speaker solids and mount bosses omitted.',
      ''])
