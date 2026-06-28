import numpy as np
from backend.workers.drift_watcher import calculate_psi, calc_covariance_shift
import pandas as pd

def test_calculate_psi_identical_distributions():
    expected = np.random.normal(100, 10, 1000)
    actual = expected.copy()
    
    psi = calculate_psi(expected, actual, buckets=10)
    assert psi < 0.01

def test_calculate_psi_drifted_distributions():
    expected = np.random.normal(100, 10, 1000)
    actual = np.random.normal(150, 20, 1000) 
    
    psi = calculate_psi(expected, actual, buckets=10)
    assert psi > 0.25 
def test_calc_covariance_shift():
    df_ref = pd.DataFrame({"rev": [10, 20, 30], "vis": [100, 200, 300]})
    df_cur = pd.DataFrame({"rev": [10, 20, 30], "vis": [100, 200, 300]})
    
    shift = calc_covariance_shift(df_ref, df_cur)
    assert shift < 0.01 # 