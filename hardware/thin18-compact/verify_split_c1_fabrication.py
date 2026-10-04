#!/usr/bin/env python3
"""Verify frozen factory package identities; never infer supplier acceptance."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from _split_c1_common import ROOT, REPO, repo_entry, sha
from _split_c1_fabrication import (require,load_contract,validate_archive,geometry_payload,verify_cap_drill_export)


def verify():
    contract=load_contract();out=ROOT/'production/jlc-prototype-orderpack'
    archive=ROOT/'production/Panda-Split-C1-JLC-Prototype.zip'
    status=json.loads((out/'prototype-status.json').read_text())
    require(status['ready_for_cam_review'] is True and status['cam_accepted'] is False,'Wrong CAM state')
    require(status['automatic_fabrication_order_ready'] is False and status['assembly_request_ready'] is False,'Unproven order approval')
    require(status['manufacturing_release'] is False,'Unproven physical release')
    sums={}
    for line in (out/'SHA256SUMS').read_text().splitlines():
        digest,name=line.split('  ',1)
        require(name not in sums and not Path(name).is_absolute() and '..' not in Path(name).parts,'Unsafe/duplicate checksum path')
        require(sha(out/name)==digest,'Changed package file: '+name);sums[name]=digest
    actual={p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file() and p.name!='SHA256SUMS'}
    require(set(sums)==actual,'Checksum manifest is not complete')
    with zipfile.ZipFile(archive) as z:
        require(z.testzip() is None,'Combined archive CRC failed')
        require(len(z.namelist())==len(set(z.namelist())),'Duplicate combined archive entries')
        require(set(z.namelist())==actual|{'SHA256SUMS'},'Combined archive contents differ')
        for name in z.namelist():
            require(z.read(name)==(out/name).read_bytes(),'Archive stale: '+name)
    from audit_split_c1_assembly_process import REPORT as PROCESS_REPORT, verify_fresh as verify_process, contact_csv, drill_coverage
    process=json.loads((out/'assembly-process.json').read_text());verify_process(process)
    require((out/'assembly-process.json').read_bytes()==PROCESS_REPORT.read_bytes(),'Stale copied assembly process record')
    require('ASSEMBLY-PROCESS.md' in sums,'Missing process handoff')
    boards={}
    for board,folder in [('Core-C1','core-c1-96x68'),('Display-C1','display-c1-45x36')]:
        prod=ROOT/'production'/folder;m=json.loads((prod/'production-manifest.json').read_text());f=m['files']
        require(not any(m['native_checks'].values()),'Native checks not zero')
        for entry in f.values():require(sha(REPO/entry['path'])==entry['sha256'],'Stale production input: '+entry['path'])
        fab=json.loads((REPO/f['fabrication_record']['path']).read_text())
        for key in ['contract','normalizer','raw_kicad_job','gerber_job','native_pcb']:
            item=fab[key];require(sha(REPO/item['path'])==item['sha256'],'Stale fabrication evidence: '+key)
        require(fab['native_pcb']==f['pcb'],'Wrong PCB source')
        require(fab['selection']==contract['boards'][board],'Wrong order selection')
        zippath=out/board/(board+'-Gerber-Drill.zip')
        require(sha(zippath)==f['gerber_zip']['sha256'],'Copied bare-board ZIP differs')
        drills=validate_archive(zippath,contract['boards'][board],board,f['pcb']['sha256'])
        if board=='Core-C1':verify_cap_drill_export(drills)
        process_board=process['boards'][board]
        require(process_board['pcb']==f['pcb'],'Process audit covers another PCB')
        drill_coverage(process_board,drills)
        selection=status['assembly_process'][board]
        require(selection['cam_accepted'] is False,'Process acceptance incorrectly enabled')
        require(selection['pcb_sha256']==f['pcb']['sha256'] and selection['via_count']==process_board['via_count'] and selection['land_overlap_hole_count']==process_board['land_overlap_hole_count'],'Process count/source differs')
        require(selection['required_via_treatment']==process_board['required_via_treatment'],'Fill/cap requirement lost')
        csv_path=out/board/'VIA-IN-PAD.csv'
        require(selection['location_csv']==board+'/VIA-IN-PAD.csv' and sha(csv_path)==selection['location_csv_sha256'],'Process location list hash differs')
        require(csv_path.read_text()==contact_csv(process_board),'Process coordinate list differs')
        with zipfile.ZipFile(zippath) as z:
            for name,digest in fab['layer_drawing_sha256'].items():
                require(hashlib.sha256(geometry_payload(z.read(name).decode()).encode()).hexdigest()==digest,'Gerber drawing changed: '+name)
        require(status['boards'][board]['native_rule_dfm_passed'] is True,'Native-rule DFM missing')
        require(status['boards'][board]['standard_fabrication_ready'] is False,'Unaccepted process advertised as ready')
        require(status['boards'][board]['cam_acceptance_required'] is True,'CAM questions hidden')
        boards[board]={'native_checks':m['native_checks'],'pcb_sha256':f['pcb']['sha256'],
                       'gerber_zip_sha256':sha(zippath),'drills':drills,
                       'assembly_process_hole_count':process_board['land_overlap_hole_count'],
                       'via_drill_inventory_verified':True,'metadata_consistent':True,'gerber_geometry_digest_verified':True,
                       'native_rule_dfm_passed':True,'cam_accepted':False}
    return {'schema':'panda-split-c1-fabrication-verification-v1',
            'source_git_commit_observed':status['source_git_commit_observed'],
            'native_pcbs_match_observed_commit':status['native_pcbs_match_observed_commit'],
            'contract':repo_entry(ROOT/'split-c1-fabrication-contract.json'),
            'checker':repo_entry(Path(__file__)),'archive':repo_entry(archive),
            'entry':repo_entry(out/'START-HERE.md'),'boards':boards,
            'all_packet_hashes_verified':True,'ready_for_cam_review':True,
            'cam_accepted':False,'automatic_fabrication_order_ready':False,
            'assembly_order_ready':False,'manufacturing_release':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-cam-accepted',action='store_true')
    args=parser.parse_args();report=verify()
    (ROOT/'production/split-c1-fabrication-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['source_git_commit_observed','native_pcbs_match_observed_commit','all_packet_hashes_verified','ready_for_cam_review','cam_accepted','automatic_fabrication_order_ready']},indent=2))
    return 2 if args.require_cam_accepted and not report['cam_accepted'] else 0


if __name__=='__main__':raise SystemExit(main())
