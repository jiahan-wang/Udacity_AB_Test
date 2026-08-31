# -*- coding: utf-8 -*-
"""分流质量：SRM 卡方/精确二项、两比例比较、逐日配对诊断。"""
import numpy as np
import pandas as pd
from scipy import stats


def srm_check(c: int, e: int, expected: float = 0.5) -> dict:
    """计数分流 SRM：chi2(df=1) + 精确二项双侧 + 实验份额 95%CI。"""
    n = c + e
    chi2 = ((np.array([c, e]) - n * np.array([1 - expected, expected])) ** 2
            / (n * np.array([1 - expected, expected]))).sum()
    bt = stats.binomtest(e, n, expected)
    lo, hi = bt.proportion_ci(0.95)
    return {"control": int(c), "experiment": int(e), "total": int(n),
            "experiment_share": float(e / n), "chi2": float(chi2),
            "p_chi2": float(stats.chi2.sf(chi2, df=1)), "p_binom_exact": float(bt.pvalue),
            "share_95CI": [float(lo), float(hi)]}


def two_proportion(c_num, c_den, e_num, e_den, alpha: float = 0.05) -> dict:
    """两比例比较（如 CTP）：检验 pooled、CI unpooled。"""
    pc, pe = c_num / c_den, e_num / e_den
    d = pe - pc
    pp = (c_num + e_num) / (c_den + e_den)
    sep = np.sqrt(pp * (1 - pp) * (1 / c_den + 1 / e_den))
    z = d / sep
    seu = np.sqrt(pc * (1 - pc) / c_den + pe * (1 - pe) / e_den)
    za = stats.norm.ppf(1 - alpha / 2)
    return {"control": float(pc), "experiment": float(pe), "diff": float(d),
            "z": float(z), "p": float(2 * stats.norm.sf(abs(z))),
            "diff_95CI": [float(d - za * seu), float(d + za * seu)]}


def daily_paired_diag(long: pd.DataFrame) -> dict:
    """逐日配对诊断（健康检查，不称 covariate balance）：PV/CTP 的 E-C 配对 t/Wilcoxon。"""
    piv = long.pivot(index="Date", columns="Group")
    w = pd.DataFrame({
        "PV_C": piv["Pageviews"]["Control"], "PV_E": piv["Pageviews"]["Experiment"],
        "CK_C": piv["Clicks"]["Control"], "CK_E": piv["Clicks"]["Experiment"]})
    w["CTP_C"] = w["CK_C"] / w["PV_C"]
    w["CTP_E"] = w["CK_E"] / w["PV_E"]
    w["PV_diff"] = w["PV_E"] - w["PV_C"]
    w["CTP_diff"] = w["CTP_E"] - w["CTP_C"]
    t_pv = stats.ttest_rel(w["PV_E"], w["PV_C"])
    w_pv = stats.wilcoxon(w["PV_E"], w["PV_C"])
    t_ctp = stats.ttest_rel(w["CTP_E"], w["CTP_C"])
    w_ctp = stats.wilcoxon(w["CTP_E"], w["CTP_C"])
    return {"PV_mean_daily_diff": float(w["PV_diff"].mean()),
            "PV_paired_t_p": float(t_pv.pvalue), "PV_wilcoxon_p": float(w_pv.pvalue),
            "CTP_mean_daily_diff": float(w["CTP_diff"].mean()),
            "CTP_paired_t_p": float(t_ctp.pvalue), "CTP_wilcoxon_p": float(w_ctp.pvalue)}
