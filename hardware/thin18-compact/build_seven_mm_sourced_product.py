#!/usr/bin/env python3
"""Build current Product-D routing plus the reviewed 20-reference sourcing ECO.

Use KiCad Python. Outputs must be fresh and ignored/external. Catalog-resolved
parts, pending JLC registration and post-SMT cell supply remain distinct; no paid
order or blanket production acceptance is performed by this builder.
"""
from pathlib import Path
import argparse, subprocess, sys
from _split_c1_common import ROOT, REPO
from seven_mm_sourcing import apply


def build(output):
    output=Path(output).resolve()
    if output.exists():raise ValueError('Choose a new output directory')
    if output.is_relative_to(REPO) and not output.is_relative_to(REPO/'.work'):
        raise ValueError('Generated candidates cannot enter source directories')
    subprocess.run([sys.executable,str(ROOT/'build_seven_mm_product.py'),'--output',str(output),'--routing-only'],check=True)
    return apply(output)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();build(args.output)
