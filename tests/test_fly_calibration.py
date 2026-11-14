"""Check measured-surface interpolation and train/test separation for the encoder."""
import json
import sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'pipeline'))
from calibrate_fly import interpolate,choose
from senses import Surface,fly_pick


def test_vectorized_brain_lookup_and_choice_match_existing_scalar_model():
    doc=json.loads((ROOT/'web/data/fly_surface.json').read_text())
    rng=np.random.default_rng(12)
    hz=rng.uniform([0,0,0],[200,200,150],size=(10,6,3))
    for mode in ['intact','lesion_gf']:
        batch=interpolate(doc,mode,hz);scalar=Surface(doc,mode)
        for row in range(len(hz)):
            reads=[scalar.read(*h) for h in hz[row]]
            expected=np.array([[r[k] for k in ['mn9','giant_fibre','mdn']] for r in reads])
            np.testing.assert_allclose(batch[row],expected,atol=1e-10)
            assert int(choose(batch[row:row+1],hz[row:row+1])[0][0])==fly_pick(reads,hz[row])[0]
        if mode=='lesion_gf':assert np.all(batch[...,1]==0)


def test_calibration_keeps_training_and_test_seeds_disjoint_and_reproduces_baseline():
    data=json.loads((ROOT/'web/data/fly_calibration.json').read_text())
    old=json.loads((ROOT/'web/data/results.json').read_text())['decision']
    assert set(data['provenance']['train_seeds']).isdisjoint(data['provenance']['test_seeds'])
    assert data['provenance']['test_decisions_per_pct']==156
    for metric in ['success','minutes']:
        assert data['policies']['original'][metric]==old['policies']['fly'][metric]
    for policy in data['policies'].values():
        lo,mean,hi=map(np.array,[policy['success_lo'],policy['success'],policy['success_hi']])
        assert np.all((lo<=mean+1e-4)&(mean<=hi+1e-4))
        assert np.all((0<=lo)&(hi<=1))
