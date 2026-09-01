# -*- coding: utf-8 -*-
"""样本量/功效公式测试。"""
import numpy as np
from scipy.stats import norm

from udacity_ab import design


def test_n_per_group_matches_closed_form():
    p1, d, alpha, power = 0.20625, -0.01, 0.05, 0.80
    n = design.n_per_group(p1, d, alpha, power)
    p2 = p1 + d
    pbar = (p1 + p2) / 2
    za, zb = norm.ppf(0.975), norm.ppf(0.8)
    n_hand = ((za * np.sqrt(2 * pbar * (1 - pbar))
               + zb * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2) / (p1 - p2) ** 2
    assert abs(n - n_hand) < 1e-9
    assert n > 0


def test_power_increases_with_sample_and_effect():
    p = 0.11
    pw_small = design.power_two_prop(p, -0.005, 5000, 5000)
    pw_big_n = design.power_two_prop(p, -0.005, 20000, 20000)
    pw_big_eff = design.power_two_prop(p, -0.02, 5000, 5000)
    assert pw_small < pw_big_n and pw_small < pw_big_eff


def test_achievable_mde_shrinks_with_n():
    p = 0.11
    m1 = design.achievable_mde(p, 10000, 10000, 0.8)
    m2 = design.achievable_mde(p, 30000, 30000, 0.8)
    assert m2 < m1
    # 在该样本量下，achievable MDE 的功效应回到 0.8
    assert abs(design.power_two_prop(p, -m1, 10000, 10000) - 0.8) < 1e-4
