"""Board variant of the v0.2.x scripts, chosen by PANDA47_VARIANT (default v020).

v020 is the L-shaped v0.2.0 / E03 board; v021 is the 63 x 42 mm rectangular v0.2.1 / E04 board;
v022 is the 63 x 43 mm v0.2.2 / E05 board (R4 bottom corners, SD on the left edge, WSON-8 flash).
"""
import os

VARIANTS = {
    'v020': dict(stem='Panda47-v020', version='v0.2.0', revision='E03', date='2026-11-10',
                 board='63 x 111 mm L, 4-layer 0.8 mm'),
    'v021': dict(stem='Panda47-v021', version='v0.2.1', revision='E04', date='2026-11-11',
                 board='63 x 42 mm, 4-layer 0.8 mm'),
    'v022': dict(stem='Panda47-v022', version='v0.2.2', revision='E05', date='2026-11-12',
                 board='63 x 43 mm, R4 bottom corners, 4-layer 0.8 mm'),
}
V = VARIANTS[os.environ.get('PANDA47_VARIANT', 'v020')]
STEM, VERSION, REVISION, DATE, BOARD = V['stem'], V['version'], V['revision'], V['date'], V['board']
