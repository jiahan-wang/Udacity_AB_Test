# -*- coding: utf-8 -*-
"""known-answer toy 数据集验证清洗与 pooled 汇总逻辑。"""
import pandas as pd

from udacity_ab import cleaning


def _toy_raw():
    # 两组各 3 天；后 1 天无 enroll/pay（outcome 未成熟）
    ctrl = pd.DataFrame({
        "Date": ["Sat, Oct 11", "Sun, Oct 12", "Mon, Oct 13"],
        "Pageviews": [1000, 800, 1000], "Clicks": [80, 64, 80],
        "Enrollments": [20.0, 16.0, None], "Payments": [10.0, 8.0, None]})
    exp = pd.DataFrame({
        "Date": ["Sat, Oct 11", "Sun, Oct 12", "Mon, Oct 13"],
        "Pageviews": [1000, 800, 1000], "Clicks": [80, 64, 80],
        "Enrollments": [16.0, 12.0, None], "Payments": [8.0, 6.0, None]})
    return {"Control": ctrl, "Experiment": exp}


def test_prep_parses_date_and_weekday():
    daily = cleaning.build_daily(_toy_raw())
    assert len(daily) == 6
    row0 = daily.iloc[0]
    assert str(row0["Date"].date()) == "2014-10-11" and row0["Weekday"] == "Sat"
    # outcome 窗仅前两天
    assert int(daily["OutcomeComplete"].sum()) == 4


def test_pooled_summary_known_answer():
    daily = cleaning.build_daily(_toy_raw())
    pool = cleaning.pooled_summary(daily).set_index("Group")
    # Control outcome clicks=144, enroll=36, pay=18
    assert int(pool.loc["Control", "Clicks_23d"]) == 144
    assert abs(pool.loc["Control", "GrossConversion"] - 36 / 144) < 1e-12
    assert abs(pool.loc["Control", "NetConversion"] - 18 / 144) < 1e-12
    assert abs(pool.loc["Control", "PayPerEnrollment"] - 0.5) < 1e-12
    # 37 天 clicks=224
    assert int(pool.loc["Control", "Clicks_37d"]) == 224


def test_window_loss_known_answer():
    daily = cleaning.build_daily(_toy_raw())
    loss = cleaning.window_sample_loss(daily).set_index("Group")
    assert int(loss.loc["Control", "Clicks_excluded"]) == 80
    assert int(loss.loc["Control", "Outcome_days"]) == 2
    assert int(loss.loc["Control", "Excluded_days"]) == 1


def test_structural_qc_detects_funnel_violation():
    raw = _toy_raw()
    raw["Control"].loc[0, "Clicks"] = 5  # Pageviews(1000)>=Clicks OK; make Clicks<Enrollments
    raw["Control"].loc[0, "Enrollments"] = 99  # Clicks 5 < Enroll 99 -> violation
    daily = cleaning.build_daily(raw)
    qc = cleaning.structural_qc(daily)
    assert qc["funnel_violations"]["Clicks_lt_Enrollments"] == 1
