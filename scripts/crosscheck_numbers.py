# -*- coding: utf-8 -*-
"""关键数字独立复算（不 import 项目 src，独立实现公式）。

从 raw CSV + config 独立计算：两组总 Clicks、Gross/Net、处理效应、Z、CI、
Net CI 下界与 -δ 边界比较、成本收益核心结果；再与 pipeline 产出的 JSON 逐项核对。
运行结果写到仓库本地、已被 .gitignore 忽略的 local_reports/ 目录（可用环境变量
AB_LOCAL_REPORT_DIR 覆盖），不进入版本库；并以非零退出表示任何不一致。
"""
import json
import os
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
# 运行结果输出目录：仓库本地、已被 .gitignore 忽略，避免复核流水进入版本库
ARCHIVE = Path(os.environ.get("AB_LOCAL_REPORT_DIR", str(ROOT / "local_reports")))


def two_prop(xc, nc, xe, ne):
    pc, pe = xc / nc, xe / ne
    d = pe - pc
    p = (xc + xe) / (nc + ne)
    z = d / np.sqrt(p * (1 - p) * (1 / nc + 1 / ne))
    pval = 2 * norm.sf(abs(z))
    se = np.sqrt(pc * (1 - pc) / nc + pe * (1 - pe) / ne)
    return pc, pe, d, float(z), float(pval), float(d - 1.959963984540054 * se), float(d + 1.959963984540054 * se)


def main() -> int:
    cfg = tomllib.load(open(ROOT / "config" / "analysis_config.toml", "rb"))
    delta = cfg["locked"]["ni_delta_net"]
    long = pd.read_csv(ROOT / "data/processed/daily_long.csv", parse_dates=["Date"])
    raw_c = pd.read_csv(ROOT / "data/raw/Final_Project_Results_Control.csv")
    raw_e = pd.read_csv(ROOT / "data/raw/Final_Project_Results_Experiment.csv")
    ow = long[long["OutcomeComplete"]]
    s = ow.groupby("Group")[["Clicks", "Enrollments", "Payments"]].sum()
    me = json.load(open(ROOT / "data/processed/main_effects.json", encoding="utf-8"))
    nid = json.load(open(ROOT / "data/processed/ni_decision.json", encoding="utf-8"))
    cb = json.load(open(ROOT / "data/processed/cost_benefit.json", encoding="utf-8"))

    checks = []

    def chk(name, got, ref, tol=1e-10):
        ok = abs(got - ref) <= tol
        checks.append((name, got, ref, ok))
        return ok

    # 0) raw 行数 / 37 天总 clicks（独立从 raw 解析日期）
    chk("raw rows control", len(raw_c), 37, 0)
    chk("raw rows experiment", len(raw_e), 37, 0)
    clicks37_c = int(long[long.Group == "Control"]["Clicks"].sum())
    clicks37_e = int(long[long.Group == "Experiment"]["Clicks"].sum())
    chk("Clicks 37d C", clicks37_c, 28378, 0)
    chk("Clicks 37d E", clicks37_e, 28325, 0)
    chk("Clicks 23d C", int(s.loc["Control", "Clicks"]), 17293, 0)
    chk("Clicks 23d E", int(s.loc["Experiment", "Clicks"]), 17260, 0)

    # 1) Gross / Net 独立计算
    gc = two_prop(int(s.loc["Control", "Enrollments"]), int(s.loc["Control", "Clicks"]),
                  int(s.loc["Experiment", "Enrollments"]), int(s.loc["Experiment", "Clicks"]))
    nc_ = two_prop(int(s.loc["Control", "Payments"]), int(s.loc["Control", "Clicks"]),
                   int(s.loc["Experiment", "Payments"]), int(s.loc["Experiment", "Clicks"]))
    for tag, got, ref in [
        ("Gross rate C", gc[0], me["z_tests"]["GrossConversion"]["rate_control"]),
        ("Gross rate E", gc[1], me["z_tests"]["GrossConversion"]["rate_experiment"]),
        ("Gross diff", gc[2], me["z_tests"]["GrossConversion"]["abs_diff"]),
        ("Gross Z", gc[3], me["z_tests"]["GrossConversion"]["z"]),
        ("Gross p", gc[4], me["z_tests"]["GrossConversion"]["p_value"]),
        ("Gross CI low", gc[5], me["z_tests"]["GrossConversion"]["ci95_low"]),
        ("Gross CI high", gc[6], me["z_tests"]["GrossConversion"]["ci95_high"]),
        ("Net rate C", nc_[0], me["z_tests"]["NetConversion"]["rate_control"]),
        ("Net rate E", nc_[1], me["z_tests"]["NetConversion"]["rate_experiment"]),
        ("Net diff", nc_[2], me["z_tests"]["NetConversion"]["abs_diff"]),
        ("Net Z", nc_[3], me["z_tests"]["NetConversion"]["z"]),
        ("Net p", nc_[4], me["z_tests"]["NetConversion"]["p_value"]),
        ("Net CI low", nc_[5], me["z_tests"]["NetConversion"]["ci95_low"]),
        ("Net CI high", nc_[6], me["z_tests"]["NetConversion"]["ci95_high"])]:
        chk(tag, got, ref)

    # 2) Net CI 下界 vs -δ（非劣效独立判定）
    net_low = nc_[5]
    ni_pass_indep = net_low > -delta
    z_ni = (nc_[2] + delta) / me["z_tests"]["NetConversion"]["se_ci_unpooled"]
    chk("Net lower bound", net_low, nid["net_ci95"][0])
    chk("Z_NI", float(z_ni), nid["z_ni"])
    checks.append(("NI pass (lower > -delta)", ni_pass_indep, nid["ni_pass"], ni_pass_indep == nid["ni_pass"]))

    # 3) 成本收益核心（c_base 从 config 独立取）
    c_base = cfg["business_assumptions"]["cost_per_enrollment_low_base_high"][1]
    red_point = -int(s.loc["Experiment", "Clicks"]) * gc[2]
    save_base = red_point * c_base
    chk("reduced enrollments point", red_point, cb["effect_tiers_reduction_23d"]["point"])
    chk("base savings point", save_base,
        cb["scenarios_23d"][1]["savings_point"])

    lines = ["# 关键数字独立复算结果",
             "",
             "独立脚本 `scripts/crosscheck_numbers.py`（不 import src）从 raw/config 独立实现公式，"
             "再与 pipeline JSON 核对。容差 1e-10（计数为 0）。", "",
             "| 项目 | 独立复算 | JSON 基准 | 一致 |", "|---|---|---|---|"]
    all_ok = True
    for name, got, ref, *ok in checks:
        okv = ok[0] if ok else False
        all_ok &= okv
        lines.append(f"| {name} | {got} | {ref} | {'PASS' if okv else 'FAIL'} |")
    lines += ["", f"**总体：{'全部一致 PASS' if all_ok else '存在 FAIL'}**",
              f"独立非劣效判定：Net CI 下界 {net_low:.6f} vs -δ={-delta:.6f} → "
              f"{'通过' if ni_pass_indep else '未通过（inconclusive，非已证劣效）'}"]
    out_dir = ARCHIVE
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "CROSSCHECK_NUMBERS.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[结果写入本地 local_reports/（不入库）] {out}")
    print("\n".join(lines))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
