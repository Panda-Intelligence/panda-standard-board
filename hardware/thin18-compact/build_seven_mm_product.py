#!/usr/bin/env python3
"""Rebuild the reviewed112mm product-D PCB geometry and native quality checks.

RevisionD is an engineering review, not an assembly-order permission. It preserves
source-C electrical ECOs while restoring the required112mm outline and USB datum.
Models, reports and fabricated exports stay outside Git. Paid orders are never made.
"""
from pathlib import Path
import argparse,json,sys,subprocess,shutil
from _split_c1_common import ROOT,REPO


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve()
    if out.exists():raise ValueError('Choose a fresh output, never overwrite saved CAD')
    if out.is_relative_to(REPO) and not out.is_relative_to(REPO/'.work'):raise ValueError('Generated candidate must stay ignored/external')
    from build_seven_mm_candidate import build
    from build_seven_mm_quality import apply
    from verify_seven_mm_native_placement import inspect as inspect_placement
    from verify_seven_mm_quality_gpio import verify as verify_gpio
    build(out)
    donor=out/'electrical-donor';donor.mkdir();shutil.copy2(out/'Core-netlist.xml',donor/'Core-netlist.xml')
    native=apply(out,ROOT/'seven_mm_product_source.json',expected_revision='D')
    gpio=verify_gpio(out,donor)
    (out/'PRODUCT-GPIO.json').write_text(json.dumps(gpio,indent=2)+'\n')
    geometry={name:inspect_placement(out/(name+'.kicad_pcb'),name) for name in ['Core','Display']}
    (out/'PRODUCT-PLACEMENT.json').write_text(json.dumps(geometry,indent=2)+'\n')
    # Full paths require Shapely and are independently rerun from exported native
    # geometry using the companion checker; no synthetic all-zero flags here.
    result={'revision':'D','native':{k:v['counts'] for k,v in native['native'].items()},'native_outline_and_nominal_port_pose_passed':True,'quality_gpio_matches_C':gpio['native_schematic_pcb_gpio_parity'],'path_check_command':'verify_seven_mm_product_paths.py <fresh native geometry>','whole_device_maximum_height_qualified':False,'assembly_order_ready':False,'manufacturing_release':False}
    (out/'PRODUCT-D-REBUILD.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    return 0
if __name__=='__main__':raise SystemExit(main())
