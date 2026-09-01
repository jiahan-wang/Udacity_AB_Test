# -*- coding: utf-8 -*-
"""SRM 平衡/失配与两比例不变指标测试。"""
from udacity_ab import srm


def test_srm_perfectly_balanced():
    r = srm.srm_check(10000, 10000)
    assert abs(r["chi2"]) < 1e-12
    assert abs(r["p_chi2"] - 1.0) < 1e-12
    assert abs(r["experiment_share"] - 0.5) < 1e-12
    lo, hi = r["share_95CI"]
    assert lo <= 0.5 <= hi


def test_srm_detects_mismatch():
    # 55:45 严重失配 -> 两个 p 值都极小
    r = srm.srm_check(55000, 45000)
    assert r["p_chi2"] < 1e-10 and r["p_binom_exact"] < 1e-10
    assert not (r["share_95CI"][0] <= 0.5 <= r["share_95CI"][1])


def test_two_proportion_known_answer():
    r = srm.two_proportion(800, 10000, 820, 10000)  # 0.08 vs 0.082
    assert abs(r["control"] - 0.08) < 1e-12
    assert abs(r["diff"] - 0.002) < 1e-12
    assert r["diff_95CI"][0] < 0.002 < r["diff_95CI"][1]
