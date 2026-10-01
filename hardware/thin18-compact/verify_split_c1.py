#!/usr/bin/env python3
"""Verify all split-interface pins and the explicit board mating transform."""
from pathlib import Path
import hashlib, json, math, re, sys, subprocess, xml.etree.ElementTree as ET
import wx
APP=wx.App(False)
import pcbnew
from _split_c1_common import git_bytes, kicad_cli
ROOT=Path(__file__).resolve().parent
REL=Path("eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16")
STEM="PANDA-STD-CORE-EVT-quilter-j501-merged"
core=ROOT/"core-c1-96x68-split"
display=ROOT/"display-c1-45x36-production-bom"
pcb_paths=[core/REL/(STEM+".kicad_pcb"),display/"PANDA-EPD0426-SPI-EVT.kicad_pcb"]
boards=[pcbnew.LoadBoard(str(p)) for p in pcb_paths]
from _split_c1_sourcing import blocks, property_value
for path,ref,mpn in zip(pcb_paths,["J601","J1"],["HC-PBB40C-60DS-0.4V-1.5-02","HC-PBB40C-60DP-0.4V-02"]):
    fp=next(b for _,_,b in blocks(path.read_text(),r"\(footprint\s") if property_value(b,"Reference")==ref)
    assert property_value(fp,"Manufacturer")=="HCTL" and property_value(fp,"MPN")==mpn, "mixed or unexpected mating pair"
connectors=[boards[0].FindFootprintByReference("J601"),
    boards[1].FindFootprintByReference("J1")]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def xy(p): return [pcbnew.ToMM(p.x),pcbnew.ToMM(p.y)]
def normal(s): return s.lstrip("/")
def xml_pins(p,ref):
    root=ET.parse(p).getroot()
    return {n.attrib["pin"]:normal(net.attrib["name"])
        for net in root.findall("./nets/net") for n in net.findall("node")
        if n.attrib["ref"]==ref}
signals={1:("EPD_D0","HOST_SCLK"),3:("EPD_D1","HOST_MOSI"),
    5:("EPD_D2","HOST_CS"),7:("EPD_D3","HOST_DC"),
    9:("EPD_D4","HOST_RESET"),11:("EPD_D5","HOST_BUSY")}
grounds=set(range(2,35,2))|set(range(55,61))
power={35,36}
removed=set()
for prefix,first,last in [("C",801,813),("D",801,803),("U",801,803),("R",801,814)]:
    removed.update(f"{prefix}{i}" for i in range(first,last+1))
removed.update({"J802","L801","Q801"}|{f"TP80{i}" for i in range(1,7)})
assert not removed & {f.GetReference() for f in boards[0].GetFootprints()}, "adapter still on Core PCB"
for b,f in zip(boards,connectors):
    assert f is not None
    assert f.GetLayer()==pcbnew.B_Cu, "both connectors must be on B.Cu"
    assert abs(f.GetOrientationDegrees())<1e-6, "mating transform requires 0-degree connectors"
assert xy(connectors[0].GetPosition())==[61.0,62.0]
assert xy(connectors[1].GetPosition())==[23.0,4.0]
K=kicad_cli()
for folder,pcb in zip([core,display],pcb_paths):
    (folder/"verification").mkdir(exist_ok=True)
    sch=pcb.with_suffix(".kicad_sch")
    for command in [
        [K,"pcb","drc","--format","json","--severity-all","--schematic-parity","--output",str(folder/"verification/drc.json"),str(pcb)],
        [K,"sch","erc","--format","json","--severity-all","--output",str(folder/"verification/erc.json"),str(sch)],
        [K,"sch","export","netlist","--format","kicadxml","--output",str(folder/"verification/netlist.xml"),str(sch)]]:
        result=subprocess.run(command,capture_output=True,text=True)
        if result.returncode: raise RuntimeError(result.stderr)
cp=xml_pins(core/"verification/netlist.xml","J601")
dp=xml_pins(display/"verification/netlist.xml","J1")
mapping=[]
for n in range(1,61):
    if n in signals: cn,dn=signals[n];role="signal"
    elif n in grounds: cn=dn="GND";role="ground"
    elif n in power: cn,dn="3V3_EPD_LOGIC","EPD_3V3";role="power"
    else: cn=dn=None;role="reserved_no_connect"
    pads=[f.FindPadByNumber(str(n)) for f in connectors]
    assert all(p is not None for p in pads)
    names=[normal(p.GetNetname()) for p in pads]
    for actual,expected,xpins in zip(names,[cn,dn],[cp,dp]):
        if expected is None:
            assert actual.startswith("unconnected-"), (n,actual)
            assert str(n) not in xpins or xpins[str(n)].startswith("unconnected-")
        else:
            assert actual==expected, (n,actual,expected)
            assert xpins.get(str(n))==expected, (n,xpins.get(str(n)),expected)
    c,d=map(lambda p:xy(p.GetPosition()),pads)
    world=[d[0]+38.,66.-d[1]]
    assert abs(c[0]-world[0])<1e-6, "pin columns reversed"
    assert (c[1]-62)*(world[1]-62)>0, "odd/even rows swapped"
    assert abs(abs(c[1]-world[1])-0.185)<1e-6, "land-pattern row geometry differs"
    mapping.append({"pin":n,"role":role,"core_net":cn,"display_net":dn,
        "core_pad_mm":c,"display_pad_mm":d,"display_pad_world_mm":world})
# Native rules are inherited intact; no new suppressions or minimum reductions.
rules={}
for ext in [".kicad_pro",".kicad_dru"]:
    p=core/REL/(STEM+ext)
    expected=hashlib.sha256(git_bytes(str(REL/(STEM+ext)))).hexdigest()
    assert sha(p)==expected,"routing rules changed"
    rules[ext]=sha(p)
counts={}
for name,folder in [("Core-C1",core),("Display-C1",display)]:
    d=json.loads((folder/"verification/drc.json").read_text())
    e=json.loads((folder/"verification/erc.json").read_text())
    counts[name]={"drc":len(d["violations"]),"open":len(d["unconnected_items"]),
        "parity":len(d["schematic_parity"]),
        "erc":sum(len(s["violations"]) for s in e["sheets"])}
cad_complete=all(not any(c.values()) for c in counts.values())
if not cad_complete: raise RuntimeError("Native CAD gates failed: "+str(counts))
report={"schema":"panda-split-c1-interface-v1","logical_pin_mapping_verified":True,
    "same_number_mating":True,"all_60_pins_verified":True,
    "signals":6,"ground_pins":len(grounds),"power_pins":2,"reserved_pins":29,
    "core_connector":{"ref":"J601","mpn":"HC-PBB40C-60DS-0.4V-1.5-02",
        "type":"receptacle","layer":"B.Cu","rotation_deg":0,"center_mm":[61,62]},
    "display_connector":{"ref":"J1","mpn":"HC-PBB40C-60DP-0.4V-02",
        "type":"plug","layer":"B.Cu","rotation_deg":0,"center_mm":[23,4]},
    "assembly":{"coordinates":"Core B.Cu mounting plane z=0; mounting faces oppose",
        "display_to_core_matrix":[[1,0,0,38],[0,-1,0,66],[0,0,-1,-1.5],[0,0,0,1]],
        "mated_board_gap_mm":1.5,"display_xy_bounds_on_core_mm":[[38,30],[83,66]],
        "within_core_nominal_outline":True,
        "land_center_row_offset_mm":0.185,
        "land_offset_note":"Socket and plug solder lands differ; contacts mate by numbered rows, not coincident solder centers.",
        "core_thickness_mm":pcbnew.ToMM(boards[0].GetDesignSettings().GetBoardThickness()),
        "display_thickness_mm":pcbnew.ToMM(boards[1].GetDesignSettings().GetBoardThickness()),
        "enclosure_z_stack_verified":False,
        "battery_stack_verified":False,
        "physical_mating_verified":False},
    "adapter_removed_from_core":True,"unchanged_native_rule_hashes":rules,
    "native_checks":counts,"cad_complete":cad_complete,"manufacturing_release":False,
    "pcb_sha256":{"Core-C1":sha(pcb_paths[0]),"Display-C1":sha(pcb_paths[1])},
    "mapping":mapping,
    "sources":[
        "https://atta.szlcsc.com/upload/public/pdf/source/20240919/9AC60CBEB0CC244F18C3CAA79B732E7D.pdf",
        "https://atta.szlcsc.com/upload/public/pdf/source/20250421/1D7BA14108151E8660428C4797015DB7.pdf"],
    "open_physical_gates":["enclosure and component Z-clearance within 1.5-mm gap",
        "rear battery envelope overlaps display XY projection; final battery layer/swelling clearance",
        "panel FPC insertion/access and actual alignment","all existing calibrated physical EVT gates"]}
(ROOT/"split-c1-interface.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({k:report[k] for k in ["all_60_pins_verified","adapter_removed_from_core",
    "native_checks","cad_complete","manufacturing_release"]},indent=2))
