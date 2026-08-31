# -*- coding: utf-8 -*-
"""一键复现主流程。

raw -> cleaning -> quality checks -> effect estimation -> non-inferiority
    -> cost-benefit -> figures -> final tables

所有锁定参数从 config 注入；随机种子固定（exploratory.random_seed）。
用法：python scripts/run_pipeline.py   或   python -m udacity_ab.pipeline
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from . import cleaning, metrics, design, srm, noninferiority as nim
from . import inference, figures, data_loader
from .config import project_root, load_config
from .data_loader import RAW_FILES


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _write_json(obj, path: Path) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=float), encoding="utf-8")


# ---------------- stage 1: cleaning ----------------
def stage_cleaning(root: Path, cfg) -> pd.DataFrame:
    raw_dir, proc = root / "data" / "raw", root / "data" / "processed"
    daily = cleaning.build_daily(data_loader.load_raw(raw_dir))
    daily.to_csv(proc / "daily_long.csv", index=False, encoding="utf-8")
    cleaning.wide_table(daily).to_csv(proc / "daily_wide.csv", index=False, encoding="utf-8")
    loss = cleaning.window_sample_loss(daily)
    loss.to_csv(proc / "window_sample_loss.csv", index=False, encoding="utf-8")
    pool = cleaning.pooled_summary(daily)
    pool.to_csv(proc / "pooled_summary.csv", index=False, encoding="utf-8")

    qc = cleaning.structural_qc(daily)
    flags = cleaning.extreme_day_flags(daily)
    win = cfg["locked"]["windows"]
    report = {
        "generated_by": "data cleaning, computed from raw",
        "source_sha256": {
            "control": _sha256(raw_dir / RAW_FILES["Control"]),
            "experiment": _sha256(raw_dir / RAW_FILES["Experiment"])},
        "rows_per_group": qc["rows_per_group"],
        "duplicated_date_group": qc["duplicated_date_group"],
        "date_range": qc["date_range"],
        "date_continuous": True,
        "missing_long": {k: int(v) for k, v in daily.isna().sum().items()},
        "negatives": qc["negatives"],
        "funnel_violations_on_outcome_days": qc["funnel_violations"],
        "extreme_days_z_abs_ge_2_5": [
            {"Group": r["Group"], "Date": r["Date"], "Metric": r["Metric"],
             "value": r["Value"], "z": r["z"]} for _, r in flags.iterrows()],
        "windows": {"traffic_window_days": win["traffic_days"],
                    "outcome_window_days": win["outcome_days"],
                    "outcome_start": win["outcome_start"], "outcome_end": win["outcome_end"],
                    "excluded_dates": win["excluded_dates"],
                    "sample_loss": loss.to_dict(orient="records")},
        "pooled_summary": pool.to_dict(orient="records")}
    _write_json(report, proc / "quality_report.json")
    return daily


# ---------------- stage 2: design precision ----------------
def stage_design(root: Path, cfg, daily: pd.DataFrame):
    lk, base, proc = cfg["locked"], cfg["design_baseline"], root / "data" / "processed"
    a, pw = lk["alpha_two_sided"], lk["target_power"]
    ow = daily[daily["OutcomeComplete"]]
    plan = []
    for name, p1, mde in [("Gross", base["p_enroll_given_click"], lk["mde_gross"]),
                          ("Net", base["p_pay_given_click"], lk["mde_net"])]:
        n8 = design.n_per_group(p1, -mde, a, pw)
        n9 = design.n_per_group(p1, -mde, a, 0.90)
        plan.append({"Metric": name, "planning_p": p1, "target_MDE": mde,
                     "n_per_group@0.80": round(n8), "n_per_group@0.90": round(n9),
                     "total_PV@0.80": round(2 * n8 / base["ctr"]),
                     "accrual_days": round(2 * n8 / base["daily_clicks_total"], 1),
                     "calendar_days_with_14d_lag": round(2 * n8 / base["daily_clicks_total"]
                                                         + lk["windows"]["outcome_lag_days"], 1)})
    actual = {}
    for name, num in [("Gross", "Enrollments"), ("Net", "Payments")]:
        d = ow.groupby("Group").apply(
            lambda x: pd.Series({"n": int(x["Clicks"].sum()), "x": int(x[num].sum()),
                                 "p": x[num].sum() / x["Clicks"].sum()}), include_groups=False)
        nc, ne, pc, pe = (d.loc["Control", "n"], d.loc["Experiment", "n"],
                          d.loc["Control", "p"], d.loc["Experiment", "p"])
        se = np.sqrt(pc * (1 - pc) / nc + pe * (1 - pe) / ne)
        from scipy.stats import norm
        hw = norm.ppf(1 - a / 2) * se
        actual[name] = dict(nc=int(nc), ne=int(ne), pc=float(pc), pe=float(pe), se=float(se),
                            ci_halfwidth=float(hw), ci_fullwidth=float(2 * hw))
    power_rows, extra = [], {}
    for name, p1, mde in [("Gross", base["p_enroll_given_click"], lk["mde_gross"]),
                          ("Net", base["p_pay_given_click"], lk["mde_net"])]:
        nc, ne = actual[name]["nc"], actual[name]["ne"]
        p_lock = design.power_two_prop(p1, -mde, nc, ne)
        mde80 = design.achievable_mde(p1, nc, ne, pw)
        req = design.n_per_group(p1, -mde, a, pw)
        power_rows.append({"Metric": name, "power@locked_MDE": round(p_lock, 4),
                           "achievable_MDE@0.80": round(mde80, 5), "locked_MDE": mde,
                           "n_coverage": round((nc + ne) / 2 / req, 3)})
        days = lk["windows"]["outcome_days"]
        rate = ((nc + ne) / 2) / days
        need = (req - (nc + ne) / 2) / rate
        extra[name] = dict(required_per_group=round(req), achieved_per_group=round((nc + ne) / 2),
                           clicks_per_group_day=round(rate, 1), extra_accrual_days=round(need, 1),
                           extra_calendar_days_with_lag=round(need + lk["windows"]["outcome_lag_days"], 1))
    out = {"locked": {k: lk[k] for k in ["alpha_two_sided", "ni_alpha_one_sided", "target_power",
                                         "mde_gross", "mde_net", "ni_delta_net"]},
           "theoretical_requirement": plan, "actual_precision": actual,
           "power_by_metric": power_rows, "extra_days_needed": extra}
    _write_json(out, proc / "design_precision.json")
    fig_dir = root / "reports" / "figures"; fig_dir.mkdir(parents=True, exist_ok=True)
    figures.fig_power_vs_effect(actual, base, lk, fig_dir / "fig_power_vs_effect.png")
    figures.fig_mde_vs_sample(actual, base, lk, pw, fig_dir / "fig_mde_vs_sample.png")
    return out


# ---------------- stage 3: quality ----------------
def stage_quality(root: Path, cfg, daily: pd.DataFrame):
    proc = root / "data" / "processed"
    traffic = daily.sort_values(["Date", "Group"])
    tot = traffic.groupby("Group")[["Pageviews", "Clicks"]].sum()
    pv_c, pv_e = int(tot.loc["Control", "Pageviews"]), int(tot.loc["Experiment", "Pageviews"])
    ck_c, ck_e = int(tot.loc["Control", "Clicks"]), int(tot.loc["Experiment", "Clicks"])
    srm_pv = srm.srm_check(pv_c, pv_e)
    srm_out = {"metric": "Pageviews", "control": srm_pv["control"], "experiment": srm_pv["experiment"],
               "total": srm_pv["total"], "expected_ratio": "50:50",
               "experiment_share": srm_pv["experiment_share"], "chi2": srm_pv["chi2"],
               "p_chi2": srm_pv["p_chi2"], "p_binom_exact": srm_pv["p_binom_exact"],
               "share_95CI": srm_pv["share_95CI"]}
    srm_ck = srm.srm_check(ck_c, ck_e)
    ctp = srm.two_proportion(ck_c, pv_c, ck_e, pv_e)
    invariants = {
        "Clicks_split": {"control": ck_c, "experiment": ck_e, "experiment_share": srm_ck["experiment_share"],
                         "share_95CI": srm_ck["share_95CI"], "chi2": srm_ck["chi2"],
                         "p_chi2": srm_ck["p_chi2"], "p_binom_exact": srm_ck["p_binom_exact"]},
        "CTP": {"control": ctp["control"], "experiment": ctp["experiment"], "diff": ctp["diff"],
                "z": ctp["z"], "p": ctp["p"], "diff_95CI": ctp["diff_95CI"]}}
    diag = srm.daily_paired_diag(traffic)
    quality = {"window": "37-day traffic window (2014-10-11..2014-11-16)",
               "SRM": srm_out, "invariants": invariants, "daily_diag": diag}
    _write_json(quality, proc / "quality_checks.json")
    fig_dir = root / "reports" / "figures"
    figures.fig_pageviews_ts(traffic, fig_dir / "fig_pageviews_ts.png")
    figures.fig_ctp_ts(traffic, fig_dir / "fig_ctp_ts.png")
    return quality


# ---------------- stage 4: main effects ----------------
def stage_effects(root: Path, cfg, daily: pd.DataFrame):
    lk, exp_cfg, proc = cfg["locked"], cfg["exploratory"], root / "data" / "processed"
    ow = daily[daily["OutcomeComplete"]].copy()
    assert ow["Date"].nunique() == lk["windows"]["outcome_days"] == 23
    B, seed = exp_cfg["bootstrap_b"], exp_cfg["random_seed"]
    tot = ow.groupby("Group")[["Clicks", "Enrollments", "Payments"]].sum().astype(int)
    tot["GrossConversion"] = tot["Enrollments"] / tot["Clicks"]
    tot["NetConversion"] = tot["Payments"] / tot["Clicks"]
    tot["PayPerEnrollment"] = tot["Payments"] / tot["Enrollments"]
    z_results = {}
    for name, num in [("GrossConversion", "Enrollments"), ("NetConversion", "Payments")]:
        z_results[name] = metrics.two_prop_test(
            int(tot.loc["Control", num]), int(tot.loc["Control", "Clicks"]),
            int(tot.loc["Experiment", num]), int(tot.loc["Experiment", "Clicks"]),
            alpha=lk["alpha_two_sided"])
    ppe_c = tot.loc["Control", "Payments"] / tot.loc["Control", "Enrollments"]
    ppe_e = tot.loc["Experiment", "Payments"] / tot.loc["Experiment", "Enrollments"]
    se_ppe = np.sqrt(ppe_c * (1 - ppe_c) / tot.loc["Control", "Enrollments"]
                     + ppe_e * (1 - ppe_e) / tot.loc["Experiment", "Enrollments"])
    d_ppe = ppe_e - ppe_c
    ppe_aux = {"control": float(ppe_c), "experiment": float(ppe_e), "abs_diff": float(d_ppe),
               "relative_change": float(d_ppe / ppe_c), "direction": "up" if d_ppe > 0 else "down",
               "descriptive_ci95": [float(d_ppe - 1.96 * se_ppe), float(d_ppe + 1.96 * se_ppe)],
               "note": "auxiliary business diagnostic only; NOT an independent primary hypothesis test"}
    rng = np.random.default_rng(seed)
    boot = {}
    bg = metrics.day_cluster_bootstrap_diff(ow, "Enrollments", b=B, rng=rng)
    bn = metrics.day_cluster_bootstrap_diff(ow, "Payments", b=B, rng=rng)
    bp = metrics.day_cluster_bootstrap_diff(ow, "Payments", den="Enrollments", b=B, rng=rng)
    boot["GrossConversion"], boot["NetConversion"], boot["PayPerEnrollment"] = bg, bn, bp
    delta = {}
    for name, num, den in [("GrossConversion", "Enrollments", "Clicks"),
                           ("NetConversion", "Payments", "Clicks"),
                           ("PayPerEnrollment", "Payments", "Enrollments")]:
        delta[name] = metrics.delta_diff(ow, num, den)
    out = {"window": "23-day outcome window",
           "totals": tot.reset_index().to_dict(orient="records"),
           "z_tests": z_results, "ppe_aux": ppe_aux,
           "bootstrap_B": B, "bootstrap": boot, "delta": delta}
    _write_json(out, proc / "main_effects.json")
    figures.fig_forest(z_results, ppe_aux, lk["ni_delta_net"],
                       root / "reports" / "figures" / "fig_forest_effects.png")
    return out


# ---------------- permutation robustness ----------------
def stage_permutation(root: Path, cfg, daily: pd.DataFrame, main: dict):
    exp_cfg, proc = cfg["exploratory"], root / "data" / "processed"
    B, seed = exp_cfg["permutation_b"], exp_cfg["random_seed"]
    ow = (daily[daily["OutcomeComplete"]].copy()
          .sort_values(["Weekday", "Group", "Date"]).reset_index(drop=True))
    wc = ow.groupby(["Weekday", "Group"]).size().unstack()
    assert (wc["Control"] == wc["Experiment"]).all()
    z_obs = {k: main["z_tests"][k]["z"] for k in ["GrossConversion", "NetConversion"]}
    rng = np.random.default_rng(seed)
    pg = inference.same_weekday_block_perm(ow, "Enrollments", b=B, observed_z=z_obs["GrossConversion"], rng=rng)
    pn = inference.same_weekday_block_perm(ow, "Payments", b=B, observed_z=z_obs["NetConversion"], rng=rng)
    null_g, null_n = pg.pop("null_z"), pn.pop("null_z")
    results = {}
    for name, r in [("GrossConversion", pg), ("NetConversion", pn)]:
        results[name] = {"observed_z": r["observed_z"],
                         "perm_empirical_p_two_sided": r["empirical_p_two_sided"],
                         "null_mean": r["null_mean"], "null_sd": r["null_sd"],
                         "empirical_rejection_rate_at_alpha05": r["fpr_at_05"],
                         "z_pipeline_p": main["z_tests"][name]["p_value"]}
    # 置换后组分母波动诊断（Gross）
    grp = (ow["Group"] == "Experiment").to_numpy()
    den = ow["Clicks"].to_numpy(float)
    blocks = {w: np.where(ow["Weekday"].to_numpy() == w)[0] for w in ow["Weekday"].unique()}
    rng_diag = np.random.default_rng(seed)
    ne_arr = np.empty(B)
    num = ow["Enrollments"].to_numpy(float)
    for b in range(B):
        is_e = grp.copy()
        for idx in blocks.values():
            is_e[idx] = rng_diag.permutation(is_e[idx])
        ne_arr[b] = den[is_e].sum()
    rng2 = np.random.default_rng(seed + 1)
    dg = inference.paired_date_perm(ow, "Enrollments", b=B, observed_z=z_obs["GrossConversion"], rng=rng2)
    dn = inference.paired_date_perm(ow, "Payments", b=B, observed_z=z_obs["NetConversion"], rng=rng2)
    pair_g, pair_n = dg.pop("null_z"), dn.pop("null_z")
    paired = {}
    for name, r in [("GrossConversion", dg), ("NetConversion", dn)]:
        paired[name] = {"empirical_p": r["empirical_p_two_sided"], "null_sd": r["null_sd"],
                        "fpr_at_05": r["fpr_at_05"]}
    rows3 = []
    for name in ["GrossConversion", "NetConversion"]:
        rows3 += [
            {"metric": name, "method": "iid-Z (phase-4 primary test)", "obs_Z": z_obs[name],
             "empirical_p": results[name]["z_pipeline_p"], "null_sd": 1.0, "fpr_at_05": 0.05},
            {"metric": name, "method": "same-weekday block (primary permutation)", "obs_Z": z_obs[name],
             "empirical_p": results[name]["perm_empirical_p_two_sided"],
             "null_sd": results[name]["null_sd"],
             "fpr_at_05": results[name]["empirical_rejection_rate_at_alpha05"]},
            {"metric": name, "method": "paired-date swap (SENSITIVITY)", "obs_Z": z_obs[name],
             "empirical_p": paired[name]["empirical_p"], "null_sd": paired[name]["null_sd"],
             "fpr_at_05": paired[name]["fpr_at_05"]}]
    out = {"name": "aggregate-data placebo/permutation robustness check", "not_aa_test": True,
           "method": "same-weekday block permutation of group labels within weekday (balanced blocks)",
           "exchangeability_note": "controls weekday seasonality; cannot replicate cookie-level randomization; 23 day-clusters only",
           "B": B, "seed": seed, "window": "23-day outcome window",
           "statistic": "two-sample pooled two-proportion Z (identical to phase-4 pipeline)",
           "null_overdispersion": {
               "null_sd_gross": float(null_g.std(ddof=1)), "null_sd_net": float(null_n.std(ddof=1)),
               "cause": "whole-day reassignment fluctuates group click margins and folds day-level overdispersion into null; not a pipeline bug (null mean ~0)",
               "permuted_experiment_clicks_mean": float(ne_arr.mean()),
               "permuted_experiment_clicks_sd": float(ne_arr.std(ddof=1))},
           "sensitivity_paired_date": {"label": "SENSITIVITY ONLY - not primary, not an AA test",
                                       "seed": seed + 1, "B": B, "results": paired},
           "three_method_table": rows3, "results": results}
    _write_json(out, proc / "permutation_check.json")
    fig_dir = root / "reports" / "figures"
    figures.fig_permutation_null(null_g, null_n, z_obs, fig_dir / "fig_permutation_null.png")
    figures.fig_sensitivity_comparison(null_g, null_n, pair_g, pair_n, z_obs,
                                       fig_dir / "fig_permutation_sensitivity.png")
    return out


# ---------------- stage 6: non-inferiority ----------------
def stage_ni(root: Path, cfg, main: dict):
    lk, proc = cfg["locked"], root / "data" / "processed"
    delta, ni_alpha = lk["ni_delta_net"], lk["ni_alpha_one_sided"]
    net, gross = main["z_tests"]["NetConversion"], main["z_tests"]["GrossConversion"]
    d, lo, hi, se = net["abs_diff"], net["ci95_low"], net["ci95_high"], net["se_ci_unpooled"]
    crit = -lo
    grid_d = [0.005, delta, 0.010, crit, 0.0125, 0.015]
    rows = [{"delta_pp": round(x * 100, 3), "lower_bound > -delta": bool(lo > -x),
             "NI_verdict": "pass" if lo > -x else "fail"} for x in grid_d]
    dec = nim.ni_decision(d, se, delta, ci_low=lo, ni_alpha=ni_alpha)
    ni_pass = dec["ni_pass"]
    gross_sig = gross["p_value"] < lk["alpha_two_sided"] and gross["ci95_high"] < 0
    g_label = "显著下降" if gross_sig else "未显著下降"
    n_label = "满足非劣效" if ni_pass else "不满足非劣效"
    matrix = [
        ["显著下降", "满足非劣效", "支持上线"], ["显著下降", "不满足非劣效", "拒绝上线"],
        ["未显著下降", "满足非劣效", "策略价值证据不足，考虑继续实验"],
        ["未显著下降", "不满足非劣效", "不建议上线"]]
    decision = {row[2] for row in matrix if row[0] == g_label and row[1] == n_label}.pop()
    out = {"locked_delta": delta, "ni_alpha_one_sided": ni_alpha,
           "rule": "NI pass iff 95% two-sided CI lower bound > -delta (equivalent to one-sided alpha=0.025)",
           "net_point": float(d), "net_ci95": [float(lo), float(hi)],
           "z_ni": dec["z_ni"], "p_ni_one_sided": dec["p_ni_one_sided"],
           "ni_pass": ni_pass, "critical_delta_to_pass": float(crit),
           "gross_verdict_primary_ztest": g_label, "matrix_decision": decision,
           "delta_sensitivity": rows}
    _write_json(out, proc / "ni_decision.json")
    figures.fig_noninferiority(d, lo, hi, delta, ni_pass,
                               root / "reports" / "figures" / "fig_noninferiority.png")
    return out


# ---------------- stage 7: cost-benefit ----------------
def stage_cost(root: Path, cfg, main: dict):
    ba, proc = cfg["business_assumptions"], root / "data" / "processed"
    g, gb = main["z_tests"]["GrossConversion"], main["bootstrap"]["GrossConversion"]
    net = main["z_tests"]["NetConversion"]
    d = g["abs_diff"]
    iid_lo, iid_hi = g["ci95_low"], g["ci95_high"]
    clu_lo, clu_hi = gb["ci95_low"], gb["ci95_high"]
    tot = {r["Group"]: r for r in main["totals"]}
    n_e = int(tot["Experiment"]["Clicks"])

    def rng_(n, lo_, hi_):
        return -n * d, -n * hi_, -n * lo_
    scale = []
    for tag, n in [("observed outcome window (23d)", n_e),
                   ("37d traffic window (SCENARIO: lag days same effect)", 28325)]:
        p_i, l_i, h_i = rng_(n, iid_lo, iid_hi)
        p_c, l_c, h_c = rng_(n, clu_lo, clu_hi)
        scale.append({"scale": tag, "clicks": n, "iid_point": p_i, "iid_low": l_i, "iid_high": h_i,
                      "cluster_point": p_c, "cluster_low": l_c, "cluster_high": h_c})
    c_low, c_base, c_high = ba["cost_per_enrollment_low_base_high"]
    v_low, v_base, v_high = ba["payment_margin_low_base_high"]
    pt = -n_e * d
    eff = {"cluster_lower (conservative)": -n_e * clu_hi, "point": pt, "cluster_upper": -n_e * clu_lo}
    iid_ref = (-n_e * iid_hi, -n_e * iid_lo)
    scen = []
    for cname, c in zip(["Low (c=1.25)", "Base (c=7.5)", "High (c=30)"], [c_low, c_base, c_high]):
        scen.append({"cost_scenario": cname, "cost_per_enrollment_USD": c,
                     "savings_cluster_lower": eff["cluster_lower (conservative)"] * c,
                     "savings_point": eff["point"] * c,
                     "savings_cluster_upper": eff["cluster_upper"] * c,
                     "iid_reference_range": f"[{iid_ref[0]*c:,.0f}, {iid_ref[1]*c:,.0f}]"})
    out = {"screened_scale": scale,
           "assumptions": {**ba},
           "scenarios_23d": scen, "effect_tiers_reduction_23d": eff,
           "iid_reference_reduction_23d": list(iid_ref),
           "unified_wording": "point/direction agree across Z/delta/bootstrap; strength depends on iid-click assumption; day-cluster Gross CI contains 0"}
    fig_dir = root / "reports" / "figures"
    grid_df = figures.fig_savings_grid(eff, fig_dir / "fig_savings_grid.png")
    base_saving, tor = figures.fig_tornado(eff, iid_ref, c_low, c_base, c_high, fig_dir / "fig_tornado.png")
    lost_pt = -net["abs_diff"] * n_e
    be = []
    for vname, v in zip(["Low v=50", "Base v=150", "High v=400"], [v_low, v_base, v_high]):
        loss = lost_pt * v
        be.append({"margin_scenario": vname, "v_USD": v, "point_revenue_loss_USD": loss,
                   "breakeven_cost_per_enrollment_USD": loss / eff["point"]})
    v_star = base_saving / lost_pt
    figures.fig_breakeven(eff["point"], lost_pt, [v_low, v_base, v_high], fig_dir / "fig_breakeven.png")
    apd = ba["annualization_clicks_per_group_per_day"] * ba["annualization_days"]
    ann_red, ann_pay = -d * apd, -net["abs_diff"] * apd
    out["sensitivity"] = {"savings_grid": grid_df.reset_index().to_dict(orient="records"),
                     "tornado_base": base_saving, "tornado": tor.to_dict(orient="records"),
                     "breakeven": be, "breakeven_margin_at_base_cost": float(v_star),
                     "point_lost_payments_23d": float(lost_pt),
                     "annualized_scenario": {"clicks_per_group": int(apd), "reduced_enrollments": float(ann_red),
                                             "savings_low_base_high": [float(ann_red * c_low), float(ann_red * c_base),
                                                                       float(ann_red * c_high)],
                                             "point_lost_payments": float(ann_pay),
                                             "label": "Assumption - not observed in dataset"}}
    _write_json(out, proc / "cost_benefit.json")
    return out


def run_all(root: Path | None = None, verbose: bool = True) -> dict:
    root = root or project_root()
    cfg = load_config(root / "config" / "analysis_config.toml")
    (root / "data" / "processed").mkdir(parents=True, exist_ok=True)
    (root / "reports" / "figures").mkdir(parents=True, exist_ok=True)

    def log(msg):
        if verbose:
            print("[pipeline]", msg, flush=True)

    log("1/7 cleaning ..."); daily = stage_cleaning(root, cfg)
    log("2/7 design precision ..."); design_out = stage_design(root, cfg, daily)
    log("3/7 experiment quality ..."); quality = stage_quality(root, cfg, daily)
    log("4/7 main effects ..."); main = stage_effects(root, cfg, daily)
    log("5/7 permutation robustness ..."); perm = stage_permutation(root, cfg, daily, main)
    log("6/7 non-inferiority ..."); ni = stage_ni(root, cfg, main)
    log("7/7 cost-benefit ..."); cost = stage_cost(root, cfg, main)
    log("DONE. artifacts under data/processed and reports/figures")
    return {"design": design_out, "quality": quality, "main": main,
            "permutation": perm, "ni": ni, "cost": cost}


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else project_root()
    run_all(root)
