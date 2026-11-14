"""Checks for held-out validation and the biological lesion direction."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import scipy.sparse as sp
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pipeline'))
import birmingham_validate as bv
from flybrain import Brain


def test_giant_fibre_lesion_cuts_inputs_and_preserves_other_columns():
    brain = Brain.__new__(Brain)
    brain.N = 3
    brain.W = sp.csr_matrix([[0, 4, -2], [3, 0, 5], [1, 6, 0]])
    brain.groups = {'giant_fibre': np.array([1])}
    brain._lesions = {}
    cut = brain.lesioned('giant_fibre').toarray()
    assert np.all(cut[:, 1] == 0)
    np.testing.assert_array_equal(cut[:, [0, 2]], brain.W.toarray()[:, [0, 2]])
    assert cut[1, 0] == 3  # output row is not the lesion target


def test_birmingham_chronology_matched_baseline_and_no_hidden_targets(monkeypatch):
    monkeypatch.setattr(bv, 'PCTS', [0, 25, 100])
    monkeypatch.setattr(bv, 'DRAWS', 12)
    matrix, capacity = bv.load_synth()
    result, _ = bv.run(matrix, capacity)
    assert result['n_train_days'] > result['n_test_days']
    assert result['mae_none_matched'][0] == result['mae_spill'][0]
    assert result['mae_spill'][-1] is None
    assert result['mae_none_matched'][-1] is None
    assert all(np.isfinite(x) for x in result['mae_spill'][:-1])
    assert result['provenance']['baseline'].startswith('training hour x day-of-week')


def test_birmingham_cleaning_converts_counts_and_rounds_grid(tmp_path):
    import zipfile
    rows = pd.DataFrame({'SystemCodeNumber':['A']*4, 'Capacity':[100]*4,
                         'Occupancy':[20, 40, -1, 200],
                         'LastUpdated':['2016-11-01 08:16','2016-11-01 08:32',
                                        '2016-11-01 09:00','2016-11-01 09:30']})
    path = tmp_path / 'parking.zip'
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('parking.csv', rows.to_csv(index=False))
    data, capacity = bv.load_real(str(path))
    assert len(data) == 1
    assert data.index[0].minute == 30
    assert abs(data.iloc[0,0] - .3) < 1e-12
    assert capacity['A'] == 100
