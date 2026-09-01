# -*- coding: utf-8 -*-
"""回归测试：src 计算结果与已提交 JSON 一致，防止重构引入数值漂移。

- 确定性结果（清洗/检验/设计/SRM/NI）逐位或 1e-12 容差一致；
- bootstrap/permutation 为 MC：Gross 因首个使用共享 RNG 逐位一致，
  Net 按 B=10000 的 MC 尺度给紧容差（CI 2e-3、经验 p 0.015）。
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from udacity_ab import data_loader, cleaning, metrics, design, srm, noninferiority as nim
from udacity_ab import inference

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"


@pytest.fixture(scope="module")
def daily():
    return cleaning.build_daily(data_loader.load_raw(ROOT / "data" / "raw"))


def load(name):
    return json.loads((PROC / name).read_text(encoding="utf-8"))


def test_cleaning_reproduces_tables(daily):
    long = pd.read_csv(PROC / "daily_long.csv", parse_dates=["Date"])
    for c in daily.columns:
        a, b = daily[c], long[c]
        if str(daily[c].dtype) == "float64":
            assert np.allclose(a, b, equal_nan=True, atol=1e-12)
        else:
            assert (a.astype(str).values == b.astype(str).values).all()
    pool = cleaning.pooled_summary(daily)
    old = pd.read_csv(PROC / "pooled_summary.csv")
    assert np.allclose(pool.select_dtypes(float).values,
                       old.select_dtypes(float).values, atol=1e-12)


def test_z_tests_reproduce_main_effects(daily):
    me = load("main_effects.json")
    cases = {"GrossConversion": (3785, 17293, 3423, 17260),
             "NetConversion": (2033, 17293, 1945, 17260)}
    for name, (xc, nc, xe, ne) in cases.items():
        got = metrics.two_prop_test(xc, nc, xe, ne)
        ref = me["z_tests"][name]
        for k in ["rate_control", "rate_experiment", "abs_diff", "z", "p_value",
                  "se_test_pooled", "se_ci_unpooled", "ci95_low", "ci95_high"]:
            assert abs(got[k] - ref[k]) < 1e-12, (name, k)


def test_design_reproduces_precision_json(daily):
    dp = load("design_precision.json")
    # 理论样本
    n_gross = design.n_per_group(0.20625, -0.01, 0.05, 0.80)
    assert round(n_gross) == dp["theoretical_requirement"][0]["n_per_group@0.80"]
    # 锁定 MDE 功效
    ap = {r["Metric"]: r for r in dp["power_by_metric"]}
    pw_g = design.power_two_prop(0.20625, -0.01, 17293, 17260)
    assert abs(round(pw_g, 4) - ap["Gross"]["power@locked_MDE"]) < 1e-9
    pw_n = design.power_two_prop(0.1093125, -0.0075, 17293, 17260)
    assert abs(round(pw_n, 4) - ap["Net"]["power@locked_MDE"]) < 1e-9


def test_srm_reproduces_quality_json():
    qc = load("quality_checks.json")
    s = srm.srm_check(345543, 344660)
    for k in ["chi2", "p_chi2", "p_binom_exact", "experiment_share"]:
        assert abs(s[k] - qc["SRM"][k]) < 1e-12


def test_ni_reproduces_decision_json():
    nid = load("ni_decision.json")
    me = load("main_effects.json")["z_tests"]["NetConversion"]
    r = nim.ni_decision(me["abs_diff"], me["se_ci_unpooled"], 0.0075,
                        ci_low=me["ci95_low"])
    assert abs(r["z_ni"] - nid["z_ni"]) < 1e-12
    assert abs(r["p_ni_one_sided"] - nid["p_ni_one_sided"]) < 1e-12
    assert r["ni_pass"] == nid["ni_pass"]


def test_bootstrap_and_permutation_within_mc(daily):
    me = load("main_effects.json")
    pc = load("permutation_check.json")
    ow = daily[daily["OutcomeComplete"]]
    # bootstrap：共享 RNG 序列（Gross 先、Net 后）逐位复现
    rng = np.random.default_rng(20260831)
    bg = metrics.day_cluster_bootstrap_diff(ow, "Enrollments", b=10000, rng=rng)
    bn = metrics.day_cluster_bootstrap_diff(ow, "Payments", b=10000, rng=rng)
    assert bg == me["bootstrap"]["GrossConversion"]
    for k in ["ci95_low", "ci95_high"]:
        assert abs(bn[k] - me["bootstrap"]["NetConversion"][k]) < 2e-3
    # same-weekday block permutation
    zg = me["z_tests"]["GrossConversion"]["z"]
    zn = me["z_tests"]["NetConversion"]["z"]
    rngp = np.random.default_rng(20260831)
    pg = inference.same_weekday_block_perm(ow, "Enrollments", observed_z=zg, rng=rngp)
    pn = inference.same_weekday_block_perm(ow, "Payments", observed_z=zn, rng=rngp)
    assert abs(pg["empirical_p_two_sided"]
               - pc["results"]["GrossConversion"]["perm_empirical_p_two_sided"]) < 1e-12
    assert abs(pn["empirical_p_two_sided"]
               - pc["results"]["NetConversion"]["perm_empirical_p_two_sided"]) < 0.015
