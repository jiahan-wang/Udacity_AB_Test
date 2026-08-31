# -*- coding: utf-8 -*-
"""实验设计精度。"""
import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm


def n_per_group(p1: float, d: float, alpha: float, power: float) -> float:
    """每组所需样本；d=处理效应(负)，零假设 pooled pbar，备选分组方差。"""
    p2 = p1 + d
    pbar = (p1 + p2) / 2
    za, zb = norm.ppf(1 - alpha / 2), norm.ppf(power)
    return ((za * np.sqrt(2 * pbar * (1 - pbar))
             + zb * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2) / (p1 - p2) ** 2


def power_two_prop(p: float, d: float, nc: float, ne: float, alpha: float = 0.05) -> float:
    """设计式功效（非 observed power）：p=对照真实率，d=真实效应，实际样本量。"""
    p0 = (nc * p + ne * (p + d)) / (nc + ne)
    se0 = np.sqrt(p0 * (1 - p0) * (1 / nc + 1 / ne))
    sea = np.sqrt(p * (1 - p) / nc + (p + d) * (1 - (p + d)) / ne)
    zc = norm.ppf(1 - alpha / 2) * se0
    return float(norm.sf((zc - d) / sea) + norm.cdf((-zc - d) / sea))


def achievable_mde(p: float, nc: float, ne: float, power: float, alpha: float = 0.05) -> float:
    """给定样本达到指定功效可检测的最小绝对效应（brentq；处理后率须为正）。"""
    f = lambda x: power_two_prop(p, -x, nc, ne, alpha) - power
    return float(brentq(f, 1e-6, p - 1e-6))
