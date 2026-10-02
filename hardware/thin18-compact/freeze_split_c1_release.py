#!/usr/bin/env python3
"""Freeze both board packages and verify every recorded digest and archive."""
from pathlib import Path
import hashlib, json, zipfile
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def entry(p):return {"path":str(p.relative_to(REPO)),"sha256":sha(p)}
interface=ROOT/"split-c1-interface.json"
contract=json.loads(interface.read_text())
if not contract["all_60_pins_verified"] or not contract["cad_complete"]:
    raise SystemExit("interface/native CAD gates are not complete")
mechanical_path=ROOT/'split-c1-mechanical-audit.json'
mechanical_inputs=ROOT/'split-c1-mechanical-inputs.json'
sourcing_evidence=ROOT/'split-c1-sourcing-evidence.json'
mechanical=json.loads(mechanical_path.read_text())
if mechanical['pcb_sha256']!=contract['pcb_sha256'] or mechanical['interface_sha256']!=sha(interface):
    raise SystemExit('mechanical audit was checked against other CAD/interface data')
if mechanical['inputs_sha256']!=sha(mechanical_inputs):
    raise SystemExit('mechanical inputs changed since audit')
if not mechanical['component_gap_xy_screen_passed']:
    raise SystemExit('mechanical XY screen failed')
if mechanical['manufacturing_release'] is not False:
    raise SystemExit('mechanical audit incorrectly enabled physical release')
validation_path=ROOT/'split-c1-validation.json'
validation=json.loads(validation_path.read_text())
if validation.get('schema')!='panda-split-c1-validation-v2' or validation['manufacturing_release'] is not False:
    raise SystemExit('CAD validation record is missing or has the wrong release status')
if not validation.get('native_all_60_pin_check_passed') or not validation.get('conflicting_part_id_rejection_checked'):
    raise SystemExit('CAD validation did not verify interface or procurement-ID guards')
for board in ('Core-C1', 'Display-C1'):
    native = validation['files'][board]['native_checks']
    if set(native) != {'current', 'fresh_rebuild'} or any(any(counts.values()) for counts in native.values()):
        raise SystemExit('Both current and rebuilt CAD must pass all native gates')
for label,info in validation['files'].items():
    if 'sha256' in info and sha(REPO/label)!=info['sha256']:
        raise SystemExit('CAD validation source hash is stale: '+label)
    for counts in info.get('native_checks',{}).values():
        if any(counts.values()):raise SystemExit('CAD rebuild validation failed')
from audit_split_c1_domestic import verify_fresh
domestic_path=ROOT/'split-c1-domestic-audit.json'
domestic=json.loads(domestic_path.read_text());verify_fresh(domestic)
if domestic['manufacturing_release'] is not False or domestic['assembly_order_ready'] is not False:
    raise SystemExit('Domestic audit incorrectly releases manufacturing/order')
if not domestic['applied_replacement_identities_verified'] or not domestic['manufacturer_only_relabel_rejected']:
    raise SystemExit('Domestic identity guards did not run')
engineering_files={'mechanical_audit':mechanical_path,'mechanical_inputs':mechanical_inputs,
                   'sourcing_evidence':sourcing_evidence,'cad_validation':validation_path,
                   'domestic_audit':domestic_path,'domestic_policy':ROOT/'split-c1-domestic-policy.json',
                   'domestic_eco':ROOT/'split-c1-domestic-eco.json',
                   'domestic_notes':ROOT/'SPLIT-C1-DOMESTICIZATION.md'}
boards={}
for name,folder in [("Core-C1","core-c1-96x68"),("Display-C1","display-c1-45x36")]:
    out=ROOT/"production"/folder
    manifest_path=out/"production-manifest.json"
    m=json.loads(manifest_path.read_text())
    if any(m["native_checks"].values()):raise SystemExit("native gate failed")
    if m["manufacturing_release"] is not False:raise SystemExit("physical release incorrectly enabled")
    if not all(m["bom_complete"].values()):raise SystemExit("BOM incomplete")
    jlc=out/"manufacturing/jlcpcb"
    for label,file in [("jlc_bom","BOM_JLCPCB.csv"),("jlc_cpl","CPL_JLCPCB.csv"),
            ("assembly_sourcing","assembly-sourcing.csv"),("jlc_summary","jlc-summary.json")]:
        m["files"][label]=entry(jlc/file)
    review=out/'engineering'; review.mkdir(exist_ok=True)
    for label,source in engineering_files.items():
        target=review/source.name
        target.write_bytes(source.read_bytes())
        m['files'][label]=entry(target)
    summary=json.loads((jlc/"jlc-summary.json").read_text())
    if summary["cpl_refs_missing_from_bom"]:raise SystemExit("BOM/CPL mismatch")
    m["all_domestic_bom_complete"]=domestic["all_domestic_bom_complete"]
    m["domestic_foreign_ref_count"]=domestic["foreign_ref_count"]
    m["assembly_order_ready"]=False
    m["assembly_sourcing_status"]={
        "lcsc_mapped_designators":summary["lcsc_mapped_designators"],
        "mpn_only_designators":summary["mpn_only_designators"],
        "identity_verified_designators":summary["identity_verified_designators"],
        "stock_reserved":False,
        "automatic_jlc_library_mapping_complete":summary["mpn_only_designators"]==0}
    for key,info in m["files"].items():
        p=REPO/info["path"]
        if sha(p)!=info["sha256"]:raise SystemExit("stale artifact hash: "+key)
    if m["files"]["pcb"]["sha256"]!=contract["pcb_sha256"][name]:
        raise SystemExit("interface was checked against another PCB")
    manifest_path.write_text(json.dumps(m,indent=2)+"\n")
    rc={"schema":"panda-board-c1-release-candidate-v1","board_id":name,
        "native_checks":m["native_checks"],"dimensions_mm":m["board_dimensions_mm"],
        "production_data_complete":True,"manufacturing_release":False,
        "all_domestic_bom_complete":domestic["all_domestic_bom_complete"],
        "assembly_request_ready":False,"assembly_order_ready":False,
        "production_manifest":entry(manifest_path),"interface_contract":entry(interface),
        "assembly_sourcing":m["assembly_sourcing_status"],
        "physical_gates":"Physical electrical EVT, enclosure/battery Z-stack, panel fit and actual mating remain unverified."}
    rc_path=out/"release-candidate.json"
    rc_path.write_text(json.dumps(rc,indent=2)+"\n")
    sums=out/"SHA256SUMS"
    sums.write_text("".join(sha(p)+"  "+str(p.relative_to(out))+"\n"
        for p in sorted(out.rglob("*")) if p.is_file() and p!=sums))
    for line in sums.read_text().splitlines():
        digest,path=line.split("  ",1)
        if sha(out/path)!=digest:raise SystemExit("SHA256SUMS mismatch")
    gerber=REPO/m["files"]["gerber_zip"]["path"]
    with zipfile.ZipFile(gerber) as z:
        if z.testzip():raise SystemExit("Gerber ZIP CRC failure")
    boards[name]={"pcb":m["files"]["pcb"],"dimensions_mm":m["board_dimensions_mm"],
        "copper_layers":m["copper_layers"],"native_checks":m["native_checks"],
        "files":m["files"],"production_manifest":entry(manifest_path),
        "release_candidate":entry(rc_path),"sha256_manifest":entry(sums)}
release={"schema":"panda-split-c1-release-v1","architecture":"Core-C1 + Display-C1",
    "cad_manufacturing_data_complete":True,"manufacturing_release":False,
    "all_domestic_bom_complete":domestic["all_domestic_bom_complete"],
    "domestic_audit":entry(domestic_path),"assembly_order_ready":False,
    "interface_contract":entry(interface),"boards":boards,
    "mechanical_audit":entry(mechanical_path),"mechanical_inputs":entry(mechanical_inputs),
    "sourcing_evidence":entry(sourcing_evidence),"cad_validation":entry(validation_path),
    "historical_reference":"c4d20-96x68 integrated production package; not the final architecture",
    "physical_gates":contract["open_physical_gates"]}
p=ROOT/"production/split-c1-release.json"
p.write_text(json.dumps(release,indent=2)+"\n")
identities = {name: board["pcb"] for name,board in boards.items()}
generated_candidate = ROOT/"production/split-c1-qualification.json"
generated_candidate.write_text(json.dumps({
    "schema": "panda-generated-split-c1-qualification-v1",
    "split_release_path": str(p.relative_to(REPO)),
    "split_release_sha256": sha(p),
    "pcb_identities": identities,
    "manufacturing_release": False
},indent=2)+"\n")
qualification = ROOT/'qualification/c4d-evt/release-candidate.json'
qualification.write_text(json.dumps({
    "schema": "thin18-compact-split-release-candidate-v2",
    "checkpoint": "Split-C1 Core-C1 + Display-C1",
    "generated_candidate_path": str(generated_candidate.relative_to(REPO)),
    "pcb_identities": identities,
    "manufacturing_release": False,
    "note": "Generate packages before release verification; physical Q04-Q14 and independent approval remain mandatory."
},indent=2)+"\n")
print(json.dumps({"release":str(p.relative_to(REPO)),
    "boards":{name:{"native_checks":b["native_checks"],"dimensions_mm":b["dimensions_mm"]}
        for name,b in boards.items()},"manufacturing_release":False},indent=2))