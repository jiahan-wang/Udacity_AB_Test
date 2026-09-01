# -*- coding: utf-8 -*-
"""指标公式与 CI 的 known-answer 测试（手算可复核）。"""
import numpy as np
from scipy import stats

from udacity_ab import metrics


def test_two_prop_known_answer():
    # 50/100 vs 60/100：率 0.5 vs 0.6
    r = metrics.two_prop_test(50, 100, 60, 100)
    assert r["rate_control"] == 0.5 and r["rate_experiment"] == 0.6
    assert abs(r["abs_diff"] - 0.1) < 1e-12
    # pooled 检验 SE = sqrt(0.55*0.45*(1/100+1/100))
    se_pool = np.sqrt(0.55 * 0.45 * 0.02)
    assert abs(r["se_test_pooled"] - se_pool) < 1e-12
    assert abs(r["z"] - 0.1 / se_pool) < 1e-12
    assert abs(r["p_value"] - 2 * stats.norm.sf(0.1 / se_pool)) < 1e-12


def test_ci_uses_unpooled_variance():
    r = metrics.two_prop_test(50, 100, 60, 100)
    # unpooled SE = sqrt(0.25/100 + 0.24/100) = 0.07
    se_un = np.sqrt(0.25 / 100 + 0.24 / 100)
    assert abs(r["se_ci_unpooled"] - se_un) < 1e-12
    hw = stats.norm.ppf(0.975) * se_un
    assert abs(r["ci95_low"] - (0.1 - hw)) < 1e-12
    assert abs(r["ci95_high"] - (0.1 + hw)) < 1e-12
    assert r["ci95_low"] < r["abs_diff"] < r["ci95_high"]


def test_identical_rates_zero_z():
    r = metrics.two_prop_test(30, 100, 300, 1000)
    assert abs(r["z"]) < 1e-12 and abs(r["p_value"] - 1.0) < 1e-12
    assert abs(r["abs_diff"]) < 1e-12


def test_delta_ratio_var_zero_when_constant_ratio():
    import pandas as pd
    # 每天 num/den 恒为 0.5 -> 残差为 0 -> 方差 0
    df = pd.DataFrame({"y": [5, 10, 15], "x": [10, 20, 30]})
    r, v = metrics.delta_ratio_var(df, "y", "x")
    assert abs(r - 0.5) < 1e-12 and abs(v) < 1e-12
