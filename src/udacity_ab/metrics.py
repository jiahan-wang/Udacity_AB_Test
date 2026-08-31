# -*- coding: utf-8 -*-
"""指标与推断原语（与主分析/非劣效口径一致：检验 pooled、CI unpooled）。"""
import numpy as np
from scipy import stats


def two_prop_test(x_c: float, n_c: float, x_e: float, n_e: float,
                  alpha: float = 0.05) -> dict:
    """双样本比例检验：Z/p 用 pooled 方差，95%CI 用 unpooled 方差；效应方向 E-C。"""
    pc, pe = x_c / n_c, x_e / n_e
    d = pe - pc
    p_pool = (x_c + x_e) / (n_c + n_e)
    se_pool = np.sqrt(p_pool * (1 - p_pool) * (1 / n_c + 1 / n_e))
    z = d / se_pool
    pval = 2 * stats.norm.sf(abs(z))
    se_un = np.sqrt(pc * (1 - pc) / n_c + pe * (1 - pe) / n_e)
    za = stats.norm.ppf(1 - alpha / 2)
    return {"rate_control": float(pc), "rate_experiment": float(pe), "abs_diff": float(d),
            "relative_change": float(d / pc), "z": float(z), "p_value": float(pval),
            "se_test_pooled": float(se_pool), "se_ci_unpooled": float(se_un),
            "ci95_low": float(d - za * se_un), "ci95_high": float(d + za * se_un)}


def delta_ratio_var(df_g, num: str, den: str) -> tuple[float, float]:
    """R=ΣY/ΣX 的 cluster delta-method 方差（以天为独立 cluster）。返回 (R, Var)。"""
    n = len(df_g)
    r = df_g[num].sum() / df_g[den].sum()
    resid = df_g[num] - r * df_g[den]
    s2 = (resid ** 2).sum() / (n - 1)
    return float(r), float(s2 / (n * df_g[den].mean() ** 2))


def delta_diff(ow, num: str, den: str) -> dict:
    """两组 ratio 差值的 delta-method 点估/SE/95CI。"""
    rc, vc = delta_ratio_var(ow[ow.Group == "Control"], num, den)
    re_, ve = delta_ratio_var(ow[ow.Group == "Experiment"], num, den)
    d = re_ - rc
    se = np.sqrt(vc + ve)
    return {"point": float(d), "se": float(se),
            "ci95_low": float(d - 1.96 * se), "ci95_high": float(d + 1.96 * se)}


def day_cluster_bootstrap_diff(ow, num: str, den: str = "Clicks", b: int = 10_000,
                               seed: int = 20260831, rng=None) -> dict:
    """以天为重采样单位的两组 ratio 差值 percentile CI（聚合数据，仅辅助）。

    可传入共享 rng 以保证多指标按同一随机序列逐位复现；否则用 seed 新建。
    """
    rng = rng if rng is not None else np.random.default_rng(seed)
    piv = ow.pivot(index="Date", columns="Group")
    n_days = ow["Date"].nunique()
    yc = piv[num]["Control"].to_numpy(float)
    xc = piv[den]["Control"].to_numpy(float)
    ye = piv[num]["Experiment"].to_numpy(float)
    xe = piv[den]["Experiment"].to_numpy(float)
    ic = rng.integers(0, n_days, size=(b, n_days))
    ie = rng.integers(0, n_days, size=(b, n_days))
    diffs = np.empty(b)
    for i in range(b):
        diffs[i] = ye[ie[i]].sum() / xe[ie[i]].sum() - yc[ic[i]].sum() / xc[ic[i]].sum()
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return {"ci95_low": float(lo), "ci95_high": float(hi), "boot_mean": float(diffs.mean())}
