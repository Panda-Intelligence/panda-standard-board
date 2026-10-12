"""Manifest mutation tests, not fabricated native/supplier acceptance evidence."""
import copy
import unittest
from pico47_checkpoint import validate_manifest


def synthetic_manifest():
    row={key:'a'*64 for key in ['pcb_sha256','schematic_sha256','project_sha256',
                               'rules_sha256','geometry_sha256']}
    row['counts']={'drc_errors':0,'drc_warnings':3,'open':10,'parity':0,'erc':0}
    return {'schema':'panda47-external-routing-checkpoint-v1','source_design_sha256':'b'*64,
            'source_layout_sha256':'c'*64,'boards':{'Core':copy.deepcopy(row),
            'Display':copy.deepcopy(row)},'manufacturing_release':False}


class CheckpointTests(unittest.TestCase):
    def test_partial_work_may_be_recorded_but_is_not_release(self):
        self.assertTrue(validate_manifest(synthetic_manifest()))

    def test_zero_counts_do_not_automatically_mark_release(self):
        data=synthetic_manifest()
        for row in data['boards'].values():
            row['counts']={k:0 for k in row['counts']}
        self.assertTrue(validate_manifest(data))
        self.assertFalse(data['manufacturing_release'])


def mutation(path,value):
    def run(self):
        data=synthetic_manifest()
        target=data
        for key in path[:-1]:
            target=target[key]
        target[path[-1]]=value
        with self.assertRaises(ValueError):
            validate_manifest(data)
    return run


CASES=[
    (['schema'],'old-checkpoint'),
    (['manufacturing_release'],True),
    (['boards'],{}),
    (['source_design_sha256'],'g'*64),
    (['source_layout_sha256'],None),
    (['boards','Core','pcb_sha256'],'a'*63),
    (['boards','Display','schematic_sha256'],'wrong'),
    (['boards','Core','counts','drc_errors'],1),
    (['boards','Display','counts','parity'],1),
    (['boards','Core','counts','erc'],1),
    (['boards','Core','counts','open'],-1),
    (['boards','Core','counts','drc_warnings'],False),
    (['boards','Core','counts','open'],1.5),
    (['boards','Display','counts'],{'drc_errors':0}),
]
for index,(path,value) in enumerate(CASES):
    setattr(CheckpointTests,f'test_reject_mutation_{index:02d}',mutation(path,value))

if __name__=='__main__':
    unittest.main(verbosity=2)
