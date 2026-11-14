#!/usr/bin/env python3
"""Rebuild the current demo from official cached geography and seeded simulation.

python build_ncstate.py                 # refit simulation, evaluate, select lesion scene, export tastes
python build_ncstate.py --refresh-map   # also re-export official GIS / destination geometry first
python build_ncstate.py --birmingham    # also download and validate real Birmingham observations

Never fabricates SEED facilities or occupancy labeled as live.
"""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent

def run(*args):
    subprocess.run(args, cwd=ROOT, check=True)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--refresh-map', action='store_true')
    ap.add_argument('--birmingham', action='store_true')
    args = ap.parse_args()
    if args.refresh_map or not (ROOT / 'web/data/lots.json').exists():
        run(sys.executable, 'pipeline/ncsu_lots.py')
    run(sys.executable, 'pipeline/simulate_drivers.py')
    run(sys.executable, 'pipeline/evaluate.py')
    run(sys.executable, 'pipeline/calibrate_fly.py')
    run('node', 'pipeline/find_lesion_scene.cjs')
    run(sys.executable, 'pipeline/export_senses.py')
    if args.birmingham:
        run(sys.executable, 'pipeline/birmingham_validate.py')
