# -*- coding: utf-8 -*-
"""Net 非劣效判定。单侧 α=0.025 等价 95% 双侧 CI 下界 > -δ。"""
from scipy import stats


def ni_decision(d: float, se_unpooled: float, delta: float,
                ci_low: float | None = None, ci_high: float | None = None,
                ni_alpha: float = 0.025) -> dict:
    """返回 Z_NI、单侧 p、是否通过、临界 δ（CI 下界恰为 -δ）。

    判定式：95% 双侧 CI 下界 > -δ  <=>  Z_NI=(d+δ)/SE > z_{1-α}。
    """
    z_ni = (d + delta) / se_unpooled
    p_ni = float(stats.norm.sf(z_ni))
    zcrit = stats.norm.ppf(1 - ni_alpha)
    if ci_low is None:
        ci_low = d - zcrit * se_unpooled
    ni_pass = bool(ci_low > -delta)
    assert (z_ni > zcrit) == ni_pass
    return {"z_ni": float(z_ni), "p_ni_one_sided": p_ni, "ni_pass": ni_pass,
            "critical_delta_to_pass": float(-ci_low)}
