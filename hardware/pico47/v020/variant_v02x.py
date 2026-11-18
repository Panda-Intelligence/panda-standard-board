"""Board variant of the v0.2.x scripts, chosen by PANDA47_VARIANT (default v020).

v020 is the L-shaped v0.2.0 / E03 board; v021 is the 63 x 42 mm rectangular v0.2.1 / E04 board;
v022 is the 63 x 43 mm v0.2.2 / E05 board (R4 bottom corners, SD on the left edge, WSON-8 flash);
v030 is the v0.2.4 board with the 4.26-inch SPI panel circuit (v0.3.0 / E08);
v023 is the v0.2.3 / E06 re-layout of v0.2.2 with hand-laid power stages, crystal, RF and charge-current trunks.
"""
import os

VARIANTS = {
    'v020': dict(stem='Panda47-v020', version='v0.2.0', revision='E03', date='2026-11-10',
                 board='63 x 111 mm L, 4-layer 0.8 mm'),
    'v021': dict(stem='Panda47-v021', version='v0.2.1', revision='E04', date='2026-11-11',
                 board='63 x 42 mm, 4-layer 0.8 mm'),
    'v022': dict(stem='Panda47-v022', version='v0.2.2', revision='E05', date='2026-11-12',
                 board='63 x 43 mm, R4 bottom corners, 4-layer 0.8 mm'),
    'v023': dict(stem='Panda47-v023', version='v0.2.3', revision='E06', date='2026-11-13',
                 board='63 x 43 mm, R4 bottom corners, 4-layer 0.8 mm'),
    'v024': dict(stem='Panda47-v024', version='v0.2.4', revision='E07', date='2026-11-13',
                 board='63 x 48 mm, speaker notch, R4 bottom corners, 4-layer 0.8 mm'),
    'v025': dict(stem='Panda47-v025', version='v0.2.5', revision='E09', date='2026-11-17',
                 board='63 x 48 mm, speaker notch, R4 bottom corners, 4-layer 0.8 mm'),
    'v026': dict(stem='Panda47-v026', version='v0.2.6', revision='E10', date='2026-11-17',
                 board='63 x 48 mm, speaker notch, R4 bottom corners, 4-layer 0.8 mm'),
    'v027': dict(stem='Panda47-v027', version='v0.2.7', revision='E11', date='2026-11-17',
                 board='63 x 48 mm, speaker notch, R4 bottom corners, 4-layer 0.8 mm'),
    'v028': dict(stem='Panda47-v028', version='v0.2.8', revision='E12', date='2026-11-17',
                 board='63 x 48 mm, speaker notch, R4 bottom corners, 4-layer 0.8 mm'),
    'v030': dict(stem='Panda426-v030', version='v0.3.0', revision='E08', date='2026-11-17',
                 board='63 x 48 mm, speaker notch, R4 bottom corners, 4-layer 0.8 mm; 4.26-inch SPI panel'),
    'v029': dict(stem='Panda47-v029', version='v0.2.9', revision='E14', date='2026-11-18',
                 board='63 x 48 mm, speaker notch, R4 bottom corners, 4-layer 0.8 mm; E0470A03 34-pin panel, two front-light drivers'),
    'v031': dict(stem='Panda426-v031', version='v0.3.1', revision='E13', date='2026-11-18',
                 board='63 x 48 mm, speaker notch, R4 bottom corners, 4-layer 0.8 mm; 4.26-inch SPI panel with front light and touch'),
}
V = VARIANTS[os.environ.get('PANDA47_VARIANT', 'v020')]
STEM, VERSION, REVISION, DATE, BOARD = V['stem'], V['version'], V['revision'], V['date'], V['board']
