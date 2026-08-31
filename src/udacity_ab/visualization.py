# -*- coding: utf-8 -*-
"""统一视觉规范——字体、数字精度、千分位、标题/轴标签、中英文格式。

规则：图内文字一律英文（避免中文字体 tofu）；正文表格可用中文。
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 统一配色
COLOR_CONTROL = "#1f77b4"
COLOR_TREATMENT = "#d62728"
COLOR_PRIMARY = "#1f4e79"
COLOR_AUX = "#7f7f7f"
COLOR_NI = "#d62728"
COLOR_OK = "#2ca02c"
COLOR_WARN = "#e69f00"
DPI = 150


def apply_style() -> None:
    """全局 rcParams 统一。"""
    plt.rcParams.update({
        "figure.dpi": DPI, "savefig.dpi": DPI,
        "font.size": 11, "axes.titlesize": 13, "axes.labelsize": 11,
        "axes.grid": True, "grid.alpha": 0.3, "legend.fontsize": 9,
        "axes.spines.top": False, "axes.spines.right": False,
        "figure.constrained_layout.use": False,
    })


def fmt_pp(x: float, digits: int = 2) -> str:
    """百分点：-0.00487 -> '-0.49pp'。"""
    return f"{x*100:+.{digits}f}pp"


def fmt_int(x: float) -> str:
    """千分位整数。"""
    return f"{x:,.0f}"


def fmt_p(p: float) -> str:
    """p 值：小值科学计数。"""
    return f"{p:.3g}" if 0 < p < 1e-3 else f"{p:.4f}"
