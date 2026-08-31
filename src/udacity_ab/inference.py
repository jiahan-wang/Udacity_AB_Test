# -*- coding: utf-8 -*-
"""aggregate-data placebo/permutation robustness check。

严格命名：aggregate-data placebo/permutation robustness check。
以天为可交换单位；same-weekday block 为主，paired-date 为并列敏感性。
不能替代 cookie 级 AA Test。
"""
import numpy as np
import pandas as pd

ZCRIT_05 = 1.959963984540054


def pooled_z(x_c: float, n_c: float, x_e: float, n_e: float) -> float:
    """pooled 两比例 Z（与主检验管线同一统计量）。"""
    pc, pe = x_c / n_c, x_e / n_e
    p = (x_c + x_e) / (n_c + n_e)
    return float((pe - pc) / np.sqrt(p * (1 - p) * (1 / n_c + 1 / n_e)))


def _z_from_sums(num, den, is_e: np.ndarray) -> float:
    xc, nc = num[~is_e].sum(), den[~is_e].sum()
    xe, ne = num[is_e].sum(), den[is_e].sum()
    return pooled_z(xc, nc, xe, ne)


def same_weekday_block_perm(ow: pd.DataFrame, num_col: str, b: int = 10_000,
                            seed: int = 20260831, observed_z: float | None = None,
                            rng=None) -> dict:
    """同星期几块内置换组标签（块内两组行数对称），返回零分布统计与经验 p。"""
    rng = rng if rng is not None else np.random.default_rng(seed)
    d = ow.sort_values(["Weekday", "Group", "Date"]).reset_index(drop=True)
    num, den = d[num_col].to_numpy(float), d["Clicks"].to_numpy(float)
    base = (d["Group"] == "Experiment").to_numpy()
    blocks = {w: np.where(d["Weekday"].to_numpy() == w)[0] for w in d["Weekday"].unique()}
    null_z = np.empty(b)
    for i in range(b):
        is_e = base.copy()
        for idx in blocks.values():
            is_e[idx] = rng.permutation(is_e[idx])
        null_z[i] = _z_from_sums(num, den, is_e)
    out = {"null_mean": float(null_z.mean()), "null_sd": float(null_z.std(ddof=1)),
           "fpr_at_05": float(np.mean(np.abs(null_z) > ZCRIT_05))}
    if observed_z is not None:
        out["observed_z"] = float(observed_z)
        out["empirical_p_two_sided"] = float(
            (1 + np.sum(np.abs(null_z) >= abs(observed_z))) / (b + 1))
    out["null_z"] = null_z
    return out


def paired_date_perm(ow: pd.DataFrame, num_col: str, b: int = 10_000,
                     seed: int = 20260831, observed_z: float | None = None,
                     rng=None) -> dict:
    """同日配对翻转（fixed daily margins，SENSITIVITY）：每个日期以 0.5 交换 C/E 标签。"""
    rng = rng if rng is not None else np.random.default_rng(seed)
    d = ow.sort_values(["Date", "Group"]).reset_index(drop=True)
    num, den = d[num_col].to_numpy(float), d["Clicks"].to_numpy(float)
    dates, grp = d["Date"].to_numpy(), d["Group"].to_numpy()
    pos_c = np.array([np.where((dates == t) & (grp == "Control"))[0][0] for t in np.unique(dates)])
    pos_e = np.array([np.where((dates == t) & (grp == "Experiment"))[0][0] for t in np.unique(dates)])
    n_dates = len(pos_c)
    null_z = np.empty(b)
    for i in range(b):
        flip = rng.random(n_dates) < 0.5
        is_e = np.zeros(len(d), bool)
        is_e[pos_e] = ~flip
        is_e[pos_c] = flip
        null_z[i] = _z_from_sums(num, den, is_e)
    out = {"null_sd": float(null_z.std(ddof=1)), "fpr_at_05": float(np.mean(np.abs(null_z) > ZCRIT_05))}
    if observed_z is not None:
        out["observed_z"] = float(observed_z)
        out["empirical_p_two_sided"] = float(
            (1 + np.sum(np.abs(null_z) >= abs(observed_z))) / (b + 1))
    out["null_z"] = null_z
    return out
