#!/usr/bin/env python3
import json, sys, xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NETLIST = ROOT / "c1-96x68-battery-ring/verification/netlist.xml"
OUT = ROOT / "c2-j802-compatibility.json"

expected = {
  1: ("NC", lambda n: n.startswith("unconnected-")),
  2: ("GDR", lambda n: n=="EPD16_GDR"),
  3: ("RESE", lambda n: n=="EPD16_RESE"),
  4: ("NC", lambda n: n.startswith("unconnected-")),
  5: ("VSH2", lambda n: n=="EPD16_VSH2"),
  6: ("NC", lambda n: n.startswith("unconnected-")),
  7: ("NC", lambda n: n.startswith("unconnected-")),
  8: ("BS1 low / 4-wire SPI", lambda n: n=="GND"),
  9: ("BUSY", lambda n: n=="EPD16_BUSY"),
 10: ("RES#", lambda n: n=="EPD16_RESET"),
 11: ("D/C#", lambda n: n=="EPD16_DC"),
 12: ("CS#", lambda n: n=="EPD16_CS"),
 13: ("SCL", lambda n: n=="EPD16_SCLK"),
 14: ("SDA", lambda n: n=="EPD16_MOSI"),
 15: ("VDDIO", lambda n: n=="3V3_EPD_LOGIC"),
 16: ("VCI", lambda n: n=="3V3_EPD_LOGIC"),
 17: ("VSS", lambda n: n=="GND"),
 18: ("VDD", lambda n: n=="EPD16_VDD1V5"),
 19: ("VPP NC in application", lambda n: n.startswith("unconnected-")),
 20: ("VSH1", lambda n: n=="EPD16_VSH1"),
 21: ("VGH", lambda n: n=="EPD16_VGH"),
 22: ("VSL", lambda n: n=="EPD16_VSL"),
 23: ("VGL", lambda n: n=="EPD16_VGL"),
 24: ("VCOM", lambda n: n=="EPD16_VCOM"),
}
root=ET.parse(NETLIST).getroot()
pins={}
for net in root.findall("nets/net"):
    name=net.get("name","")
    for node in net.findall("node"):
        if node.get("ref")=="J802":
            pins[int(node.get("pin"))]=name
rows=[]
for pin in range(1,25):
    target,pred=expected[pin]
    actual=pins.get(pin,"<no-net>")
    ok=pred(actual)
    rows.append({"pin":pin,"target":target,"current_net":actual,"compatible":ok,
                 "action":"NONE" if ok else ("DISCONNECT_GND_AND_MARK_NC" if pin in (6,7) else "REVIEW")})
report={
  "source_netlist":str(NETLIST.relative_to(ROOT)),
  "panel":"GDEQ0426T82-FT01C / base GDEY0426T82",
  "pins_checked":24,
  "compatible_without_change":sum(r["compatible"] for r in rows),
  "eco_required":sum(not r["compatible"] for r in rows),
  "eco_pins":[r["pin"] for r in rows if not r["compatible"]],
  "rows":rows,
  "result":"PASS_WITH_2_PIN_NC_ECO" if [r["pin"] for r in rows if not r["compatible"]]==[6,7] else "REVIEW_REQUIRED",
  "production_release":False
}
OUT.write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
sys.exit(0 if report["result"]=="PASS_WITH_2_PIN_NC_ECO" else 2)
