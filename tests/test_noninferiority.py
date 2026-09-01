# -*- coding: utf-8 -*-
"""非劣效边界逻辑测试（CI 下界 > -δ 才通过；单侧 α=0.025）。"""
from scipy.stats import norm

from udacity_ab import noninferiority as ni

Z975 = norm.ppf(0.975)


def test_boundary_exactly_at_minus_delta_fails():
    # d=-δ, SE=0.01：z_ni=0，CI 下界恰为 -δ，不满足严格大于 -> 不通过
    d, se, delta = -0.0075, 0.01, 0.0075
    ci_low = d - 1.96 * se
    r = ni.ni_decision(d, se, delta, ci_low=ci_low)
    assert abs(r["z_ni"]) < 1e-12
    assert r["ni_pass"] is False
    assert abs(r["p_ni_one_sided"] - 0.5) < 1e-12


def test_well_inside_margin_passes():
    # d=-0.001, SE=0.002, δ=0.0075：下界 -0.00492 > -0.0075 -> 通过
    d, se, delta = -0.001, 0.002, 0.0075
    ci_low = d - 1.96 * se
    r = ni.ni_decision(d, se, delta, ci_low=ci_low)
    assert r["ni_pass"] is True and r["z_ni"] > 1.96
    assert r["p_ni_one_sided"] < 0.025


def test_critical_delta_is_minus_ci_low():
    d, se = -0.004874, 0.003434
    r = ni.ni_decision(d, se, 0.0075)
    # 临界 δ = -CI 下界 = -(d - 1.96se)
    assert abs(r["critical_delta_to_pass"] - (-(d - Z975 * se))) < 1e-12
