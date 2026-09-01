# -*- coding: utf-8 -*-
"""成本收益情景算术（全部为 Assumption 情景，非观测）。"""
from udacity_ab import cost_benefit as cb


def test_reduction_scale_sign_and_scale():
    # 效应 -0.02、1000 clicks -> 减少 20；CI 效应 [-0.03,-0.01] -> 减少区间 [10,30]
    r = cb.reduction_scale(1000, -0.02, -0.03, -0.01)
    assert abs(r["point"] - 20) < 1e-12
    assert abs(r["low"] - 10) < 1e-12 and abs(r["high"] - 30) < 1e-12


def test_savings_grid_known_answer():
    red = {"low": 10.0, "point": 20.0, "high": 30.0}
    g = cb.savings_grid(red, [1.25, 7.5, 30.0]).set_index("cost_per_enrollment")
    assert abs(g.loc[7.5, "savings_point"] - 150.0) < 1e-12
    assert abs(g.loc[1.25, "savings_cluster_lower"] - 12.5) < 1e-12
    assert abs(g.loc[30.0, "savings_cluster_upper"] - 900.0) < 1e-12


def test_breakeven_cost_known_answer():
    # 点估付费减少 10 例、试听减少 20 例、毛利 v=50 -> 收入损失 500 -> c*=25
    be = cb.breakeven_cost(10.0, 20.0, [50, 150, 400]).set_index("margin_v")
    assert abs(be.loc[50, "breakeven_cost_per_enrollment"] - 25.0) < 1e-12
    assert abs(be.loc[150, "point_revenue_loss"] - 1500.0) < 1e-12
