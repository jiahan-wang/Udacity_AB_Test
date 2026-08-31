# -*- coding: utf-8 -*-
"""数据清洗。"""
import numpy as np
import pandas as pd

COUNT_COLS = ["Pageviews", "Clicks", "Enrollments", "Payments"]


def prep_group(df: pd.DataFrame, group: str, year: int = 2014) -> pd.DataFrame:
    """'Sat, Oct 11' 前缀日期 -> 指定年份 Timestamp；加 Group/Weekday。"""
    df = df.copy()
    md = df["Date"].str.split(",").str[1].str.strip()
    df["Date"] = pd.to_datetime(f"{year} " + md, format="%Y %b %d")
    df["Group"] = group
    df["Weekday"] = df["Date"].dt.day_name().str[:3]
    return df


def build_daily(raw: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """两组原始表 -> 日粒度长表（含派生指标与 OutcomeComplete 窗口标记），按 Date,Group 排序。"""
    parts = [prep_group(raw[g], g) for g in ("Control", "Experiment")]
    daily = pd.concat(parts, ignore_index=True)
    daily["OutcomeComplete"] = daily["Enrollments"].notna() & daily["Payments"].notna()
    daily["CTP"] = daily["Clicks"] / daily["Pageviews"]
    daily["GrossConversion"] = daily["Enrollments"] / daily["Clicks"]
    daily["NetConversion"] = daily["Payments"] / daily["Clicks"]
    daily["PayPerEnrollment"] = daily["Payments"] / daily["Enrollments"]
    cols = ["Date", "Weekday", "Group"] + COUNT_COLS + [
        "OutcomeComplete", "CTP", "GrossConversion", "NetConversion", "PayPerEnrollment"]
    return daily[cols].sort_values(["Date", "Group"]).reset_index(drop=True)


def structural_qc(daily: pd.DataFrame) -> dict:
    """结构质检：行数/重复/连续/缺失/负值/漏斗单调（对应 01 notebook cell 6）。"""
    qc: dict = {}
    qc["rows_per_group"] = daily.groupby("Group").size().to_dict()
    qc["duplicated_date_group"] = int(daily.duplicated(["Date", "Group"]).sum())
    qc["date_range"] = {}
    for g, d in daily.groupby("Group"):
        gaps = d["Date"].sort_values().diff().dropna().dt.days
        if not (gaps == 1).all():
            raise AssertionError(f"{g} 日期不连续")
        qc["date_range"][g] = [str(d["Date"].min().date()), str(d["Date"].max().date()), len(d)]
    qc["missing"] = {k: int(v) for k, v in daily.isna().sum().items()}
    qc["negatives"] = {c: int((daily[c] < 0).sum()) for c in COUNT_COLS}
    od = daily[daily["Enrollments"].notna()]
    qc["funnel_violations"] = {
        "Pageviews_lt_Clicks": int((od["Pageviews"] < od["Clicks"]).sum()),
        "Clicks_lt_Enrollments": int((od["Clicks"] < od["Enrollments"]).sum()),
        "Enrollments_lt_Payments": int((od["Enrollments"] < od["Payments"]).sum()),
    }
    return qc


def extreme_day_flags(daily: pd.DataFrame, z_thresh: float = 2.5) -> pd.DataFrame:
    """组内 |z|>=2.5 的极端日（Pageviews/Clicks/CTP），只标记不删除。"""
    flags = []
    for g, d in daily.groupby("Group"):
        for col in ["Pageviews", "Clicks", "CTP"]:
            z = (d[col] - d[col].mean()) / d[col].std(ddof=1)
            for idx in d.index[z.abs() >= z_thresh]:
                flags.append({"Group": g, "Date": d.loc[idx, "Date"].date().isoformat(),
                              "Metric": col, "Value": float(d.loc[idx, col]),
                              "z": float(z.loc[idx])})
    return pd.DataFrame(flags)


def window_sample_loss(daily: pd.DataFrame) -> pd.DataFrame:
    """37 天流量窗 vs 23 天 outcome 窗的样本损失量化。"""
    rows = []
    for g, d in daily.groupby("Group"):
        full_clicks = int(d["Clicks"].sum())
        out_clicks = int(d.loc[d["OutcomeComplete"], "Clicks"].sum())
        rows.append({"Group": g, "Clicks_37d": full_clicks, "Clicks_outcome_23d": out_clicks,
                     "Clicks_excluded": full_clicks - out_clicks,
                     "Pct_excluded": (full_clicks - out_clicks) / full_clicks,
                     "Outcome_days": int(d["OutcomeComplete"].sum()),
                     "Excluded_days": int((~d["OutcomeComplete"]).sum())})
    return pd.DataFrame(rows)


def wide_table(daily: pd.DataFrame) -> pd.DataFrame:
    """同一日期两组并排的宽表。"""
    piv = daily.pivot(index="Date", columns="Group")
    wide = piv.swaplevel(axis=1).sort_index(axis=1, level=0)
    wide.columns = [f"{g}_{m}" for g, m in wide.columns]
    return wide.reset_index()


def pooled_summary(daily: pd.DataFrame) -> pd.DataFrame:
    """双窗口 pooled 汇总（Σ分子/Σ分母，不用日比率平均）。"""
    rows = []
    for g, d in daily.groupby("Group"):
        ow = d[d["OutcomeComplete"]]
        rows.append({
            "Group": g,
            "Pageviews_37d": int(d["Pageviews"].sum()),
            "Clicks_37d": int(d["Clicks"].sum()),
            "CTP_37d": d["Clicks"].sum() / d["Pageviews"].sum(),
            "Outcome_days": int(ow.shape[0]),
            "Clicks_23d": int(ow["Clicks"].sum()),
            "Enrollments_23d": int(ow["Enrollments"].sum()),
            "Payments_23d": int(ow["Payments"].sum()),
            "GrossConversion": ow["Enrollments"].sum() / ow["Clicks"].sum(),
            "NetConversion": ow["Payments"].sum() / ow["Clicks"].sum(),
            "PayPerEnrollment": ow["Payments"].sum() / ow["Enrollments"].sum(),
        })
    return pd.DataFrame(rows)
