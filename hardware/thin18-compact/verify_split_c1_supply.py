#!/usr/bin/env python3
"""Audit the nine requested supply refs; public stock never substitutes for receipts."""
import argparse, copy, json, re
import xml.etree.ElementTree as ET
from _split_c1_common import ROOT

EXPECTED={"U902","U905","U402","U403","U404","U405","D202","C301","U906"}
SMT_PENDING=EXPECTED-{"D202","C301"}

def integer(v, minimum):
    return isinstance(v,int) and not isinstance(v,bool) and v>=minimum

def cad_fields():
    path=ROOT/"core-c1-96x68-split/verification/netlist.xml"
    return {c.get("ref"):{f.get("name"):f.text or "" for f in c.findall("fields/field")}
            for c in ET.parse(path).findall("components/comp")}

def audit(plan, sets=None):
    fields=cad_fields()
    manifest=json.loads((ROOT/"split-c1-smt-consignment.json").read_text())
    if len(manifest["rows"])!=7 or {r["ref"] for r in manifest["rows"]}!=SMT_PENDING:
        raise ValueError("Wrong seven-SMT consignment scope")
    seen=set()
    count=sets if sets is not None else plan.get("kit_quantity")
    if count is not None and not integer(count,1):
        raise ValueError("Two-board set count must be a positive integer")
    states=[]
    for row in plan["rows"]:
        refs=row["refs"]
        if len(set(refs))!=len(refs) or seen.intersection(refs):
            raise ValueError("Duplicate supply ref")
        seen.update(refs)
        if row["board"]!="Core-C1" or row["quantity_per_two_board_set"]!=len(refs):
            raise ValueError("Wrong board or per-set quantity")
        if row["assembly_route"]!=("CUSTOMER_POST_ASSEMBLY" if refs==["C301"] else "JLC_SMT"):
            raise ValueError("Wrong assembly route; C301 must not enter SMT consignment")
        if "C301" in refs and row.get("jlc_consignment_allowed") is not False:
            raise ValueError("Ultracap consignment incorrectly allowed")
        for ref in refs:
            f=fields[ref]
            for k,name in [("Manufacturer","manufacturer"),("MPN","mpn"),("Footprint","footprint"),("LCSC","catalog_code")]:
                if (f.get(k) or None)!=(row.get(name) or None):
                    raise ValueError("Supply/CAD identity mismatch: "+ref+"/"+k)
            if ref in SMT_PENDING:
                m=next(x for x in manifest["rows"] if x["ref"]==ref)
                if any(m[k]!=row[k] for k in ["manufacturer","mpn","footprint"]):
                    raise ValueError("Stale seven-SMT manifest identity")
        gaps=[]
        if count is None:gaps.append("KIT_QUANTITY_MISSING")
        receipt=row.get("supply_receipt")
        required=len(refs)*count if count is not None else None
        if receipt is None:
            gaps.append("ACTUAL_SUPPLY_RECEIPT_MISSING")
        else:
            for key in ["manufacturer","mpn","footprint","catalog_code"]:
                if (receipt.get(key) or None)!=(row.get(key) or None):gaps.append("RECEIPT_IDENTITY_MISMATCH:"+key)
            if receipt.get("route")!=row["assembly_route"]:gaps.append("RECEIPT_ROUTE_MISMATCH")
            for key in ["acceptance_reference","inventory_reference","lot_reference"]:
                if not isinstance(receipt.get(key),str) or not receipt[key].strip():gaps.append(key.upper()+"_MISSING")
            if receipt.get("packing_accepted") is not True:gaps.append("ACTUAL_PACKING_ACCEPTANCE_MISSING")
            extra=receipt.get("additional_quantity")
            available=receipt.get("usable_quantity")
            if not integer(extra,0):gaps.append("ACCEPTED_ATTRITION_QUANTITY_MISSING")
            if not integer(available,0) or (required is not None and integer(extra,0) and available<required+extra):
                gaps.append("RECEIVED_USABLE_QUANTITY_INSUFFICIENT")
            if row.get("engineering_confirmation_required") and not receipt.get("engineering_confirmation_reference"):
                gaps.append("MANUFACTURER_OR_DRAWING_CONFIRMATION_MISSING")
        if row["assembly_route"]=="JLC_SMT" and not re.fullmatch(r"C[1-9][0-9]*",row.get("catalog_code") or ""):
            gaps.append("EXACT_C_CODE_NOT_APPLIED_TO_CAD")
        states.append({"group":row["group"],"refs":refs,"required_units_excluding_attrition":required,
                       "assembly_route":row["assembly_route"],"supply_closed":not gaps,"gaps":gaps})
    if seen!=EXPECTED or len(plan["rows"])!=6:raise ValueError("Expected six exact groups/nine refs")
    return {"scope":"Only nine requested Core-C1 refs; not full PCBA approval","kit_quantity":count,
            "groups":states,"requested_supply_closed":all(x["supply_closed"] for x in states),
            "assembly_order_released":False,"physical_evt_passed":False}

def controls(plan):
    # Synthetic receipts stay in memory; no purchase/acceptance evidence is written.
    base=copy.deepcopy(plan)
    d=next(r for r in base["rows"] if r["refs"]==["D202"])
    d["supply_receipt"]={k:d[k] for k in ["manufacturer","mpn","footprint","catalog_code"]}
    d["supply_receipt"].update(route="JLC_SMT",acceptance_reference="SYNTHETIC",inventory_reference="SYNTHETIC",
                            lot_reference="SYNTHETIC",packing_accepted=True,usable_quantity=7,additional_quantity=2)
    state=lambda p:next(x for x in audit(p,5)["groups"] if x["group"]=="D202")
    assert state(base)["supply_closed"],"Valid isolated receipt fixture should close D202 only"
    assert not audit(base,5)["requested_supply_closed"],"One receipt cannot close the other eight refs"
    cases=[("mpn","wrong"),("catalog_code","C48260"),("route","CUSTOMER_POST_ASSEMBLY"),
           ("acceptance_reference",None),("inventory_reference",None),("usable_quantity",6),
           ("usable_quantity",True),("additional_quantity",None),("packing_accepted",False)]
    for key,value in cases:
        bad=copy.deepcopy(base);next(r for r in bad["rows"] if r["refs"]==["D202"])["supply_receipt"][key]=value
        assert not state(bad)["supply_closed"],"Invalid receipt accepted: "+key
    for change in ["cap_route","duplicate","cad_identity"]:
        bad=copy.deepcopy(plan)
        if change=="cap_route":next(r for r in bad["rows"] if r["refs"]==["C301"])["assembly_route"]="JLC_SMT"
        elif change=="duplicate":bad["rows"][0]["refs"].append("D202")
        else:bad["rows"][0]["mpn"]="SGM62125BXG/TR"
        try:audit(bad,5)
        except ValueError:pass
        else:raise AssertionError("Invalid supply plan accepted: "+change)
    print("Supply controls: 12 invalid cases rejected; synthetic D202 receipt and partial-scope control passed")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--plan",default=ROOT/"split-c1-supply-plan.json")
    p.add_argument("--sets",type=int)
    p.add_argument("--require-requested-supply",action="store_true")
    p.add_argument("--negative-controls",action="store_true")
    args=p.parse_args()
    plan=json.loads(open(args.plan).read())
    if args.negative_controls:controls(plan)
    result=audit(plan,args.sets)
    print(json.dumps(result,indent=2))
    if args.require_requested_supply and not result["requested_supply_closed"]:raise SystemExit(1)
if __name__=="__main__":main()
