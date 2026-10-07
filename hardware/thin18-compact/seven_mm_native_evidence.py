"""Fresh native evidence for a routing checkpoint; no CAD or rule edits."""
from pathlib import Path
import hashlib,json,subprocess,tempfile
from _split_c1_common import kicad_cli


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked_counts(drc,erc):
    for key in ['violations','unconnected_items','schematic_parity']:
        if key not in drc or not isinstance(drc[key],list):
            raise ValueError('Incomplete native DRC/parity evidence: '+key)
    if not isinstance(erc.get('sheets'),list) or not erc['sheets']:
        raise ValueError('Missing native ERC sheets')
    if any(not isinstance(s.get('violations'),list) for s in erc['sheets']):
        raise ValueError('Incomplete native ERC violations')
    counts={'drc':len(drc['violations']),'open':len(drc['unconnected_items']),
            'parity':len(drc['schematic_parity']),
            'erc':sum(len(s['violations']) for s in erc['sheets'])}
    if any(counts.values()):
        raise ValueError('Cannot freeze incomplete native routing: '+str(counts))
    return counts

def verify_native_clean(pcb):
    pcb=Path(pcb).resolve()
    required=[pcb,pcb.with_suffix('.kicad_sch'),pcb.with_suffix('.kicad_pro')]
    for path in required:
        if not path.is_file():raise ValueError('Missing matching native project: '+str(path))
    ancillary=list(pcb.parent.glob('*.kicad_sym'))+list(pcb.parent.glob('*.kicad_dru'))
    ancillary+=[p for p in [pcb.parent/'fp-lib-table',pcb.parent/'sym-lib-table'] if p.is_file()]
    ancillary+=list(pcb.parent.glob('*.pretty/*.kicad_mod'))
    observed={str(path):sha(path) for path in required+ancillary}
    with tempfile.TemporaryDirectory(prefix='panda-seven-mm-native-') as tmp:
        tmp=Path(tmp)
        drc_command=[kicad_cli(),'pcb','drc','--refill-zones','--severity-all','--schematic-parity','--format','json','--output',str(tmp/'drc.json'),str(pcb)]
        erc_command=[kicad_cli(),'sch','erc','--severity-all','--format','json','--output',str(tmp/'erc.json'),str(pcb.with_suffix('.kicad_sch'))]
        for command,name in [(drc_command,'drc'),(erc_command,'erc')]:
            with (tmp/(name+'.log')).open('w') as log:
                subprocess.run(command,cwd=pcb.parent,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
        counts=checked_counts(json.loads((tmp/'drc.json').read_text()),json.loads((tmp/'erc.json').read_text()))
        result={'counts':counts,'pcb_sha256':observed[str(pcb)],
                'schematic_sha256':observed[str(pcb.with_suffix('.kicad_sch'))],
                'project_sha256':observed[str(pcb.with_suffix('.kicad_pro'))],
                'design_rules_sha256':sha(pcb.with_suffix('.kicad_dru')) if pcb.with_suffix('.kicad_dru').exists() else None,
                'local_library_inputs_checked':len(ancillary),
                'refill_before_drc':True,'severity_all':True,'schematic_parity_requested':True,
                'drc_report_sha256':sha(tmp/'drc.json'),'erc_report_sha256':sha(tmp/'erc.json'),
                'physical_qualification_passed':False,'manufacturing_release':False}
    if any(sha(path)!=expected for path,expected in observed.items()):
        raise ValueError('Native inputs changed during evidence collection')
    return result
