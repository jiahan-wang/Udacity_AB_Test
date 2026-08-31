# -*- coding: utf-8 -*-
"""成本收益情景。所有业务参数均为 Assumption — not observed in dataset。"""
import numpy as np
import pandas as pd


def reduction_scale(n_clicks: int, point: float, ci_low: float, ci_high: float) -> dict:
    """反事实减少量 = -n×效应；返回 point 与 [low,high]（效应 CI 同乘）。"""
    return {"clicks": int(n_clicks), "point": -n_clicks * point,
            "low": -n_clicks * ci_high, "high": -n_clicks * ci_low}


def savings_grid(reductions: dict, costs: np.ndarray) -> pd.DataFrame:
    """cost × {cluster_lower, point, cluster_upper} 节约网格（USD）。"""
    rows = []
    for c in costs:
        rows.append({"cost_per_enrollment": float(c),
                     "savings_cluster_lower": reductions["low"] * c,
                     "savings_point": reductions["point"] * c,
                     "savings_cluster_upper": reductions["high"] * c})
    return pd.DataFrame(rows)


def breakeven_cost(lost_payments_point: float, reduced_point: float,
                   margins: list[float]) -> pd.DataFrame:
    """临界单试听成本 c*：运营节约=点估收入下行时；依赖未观测毛利 v（scenario）。"""
    rows = []
    for v in margins:
        loss = lost_payments_point * v
        rows.append({"margin_v": float(v), "point_revenue_loss": float(loss),
                     "breakeven_cost_per_enrollment": float(loss / reduced_point)})
    return pd.DataFrame(rows)
