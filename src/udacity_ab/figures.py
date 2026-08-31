# -*- coding: utf-8 -*-
"""全部图表的绘制函数（从各分析 Notebook 逐行移植，图内文字一律英文）。"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy import stats

from . import visualization as viz


def _weekly_ticks(fig, *axes):
    for ax in axes:
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.SU))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    fig.autofmt_xdate(rotation=0, ha="center")


# ---------- 设计精度 ----------
def fig_power_vs_effect(actual: dict, baseline: dict, locked: dict, path):
    viz.apply_style()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    xs = np.linspace(0.001, 0.02, 200)
    from .design import power_two_prop
    for name, p1, mde, color in [("Gross", baseline["p_enroll_given_click"], locked["mde_gross"], viz.COLOR_CONTROL),
                                 ("Net", baseline["p_pay_given_click"], locked["mde_net"], viz.COLOR_TREATMENT)]:
        nc, ne = actual[name]["nc"], actual[name]["ne"]
        ax.plot(xs * 100, [power_two_prop(p1, -x, nc, ne) for x in xs], color=color, label=name)
        ax.axvline(mde * 100, color=color, ls="--", lw=1)
    ax.axhline(0.8, color="gray", ls=":", lw=1.2)
    ax.text(xs[-1] * 100, 0.81, "target power 0.80", ha="right", color="gray")
    ax.set_xlabel("Hypothesized true absolute effect (percentage points)")
    ax.set_ylabel("Power (two-sided, alpha=0.05)")
    ax.set_title("Power vs effect size at achieved sample size")
    ax.legend()
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def fig_mde_vs_sample(actual: dict, baseline: dict, locked: dict, target_power: float, path):
    viz.apply_style()
    from .design import achievable_mde
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ns = np.arange(8000, 40001, 500)
    for name, p1, mde, color in [("Gross", baseline["p_enroll_given_click"], locked["mde_gross"], viz.COLOR_CONTROL),
                                 ("Net", baseline["p_pay_given_click"], locked["mde_net"], viz.COLOR_TREATMENT)]:
        ax.plot(ns, [achievable_mde(p1, n, n, target_power) * 100 for n in ns], color=color, label=name)
        ax.axhline(mde * 100, color=color, ls="--", lw=1)
    n_act = int((actual["Gross"]["nc"] + actual["Gross"]["ne"]) / 2)
    ax.axvline(n_act, color="black", ls=":", lw=1.2)
    ax.text(n_act + 300, ax.get_ylim()[1] * 0.9, f"achieved ~{n_act:,}/group", rotation=90, va="top")
    ax.set_xlabel("Clicks per group"); ax.set_ylabel("Detectable |MDE| at 80% power (pp)")
    ax.set_title("Precision (achievable MDE) vs sample size")
    ax.legend()
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


# ---------- 质量 ----------
def _daily_wide(traffic: pd.DataFrame) -> pd.DataFrame:
    daily = traffic.pivot(index="Date", columns="Group")
    w = pd.DataFrame({
        "Weekday": traffic.pivot(index="Date", columns="Group")["Weekday"]["Control"],
        "PV_C": daily["Pageviews"]["Control"], "PV_E": daily["Pageviews"]["Experiment"],
        "CK_C": daily["Clicks"]["Control"], "CK_E": daily["Clicks"]["Experiment"]})
    w["CTP_C"] = w["CK_C"] / w["PV_C"]; w["CTP_E"] = w["CK_E"] / w["PV_E"]
    w["PV_diff"] = w["PV_E"] - w["PV_C"]; w["CTP_diff"] = w["CTP_E"] - w["CTP_C"]
    return w


def fig_pageviews_ts(traffic: pd.DataFrame, path):
    viz.apply_style(); w = _daily_wide(traffic)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True,
                                 gridspec_kw={"height_ratios": [2, 1]})
    a1.plot(w.index, w["PV_C"], label="Control", color=viz.COLOR_CONTROL)
    a1.plot(w.index, w["PV_E"], label="Experiment", color=viz.COLOR_TREATMENT, ls="--")
    a1.set_ylabel("Daily Pageviews"); a1.set_title("Daily Pageviews by group (37-day traffic window)")
    a1.legend()
    a2.bar(w.index, w["PV_diff"], color=[viz.COLOR_TREATMENT if x < 0 else viz.COLOR_CONTROL for x in w["PV_diff"]], width=1.0)
    a2.axhline(0, color="black", lw=.8); a2.set_ylabel("E - C Pageviews")
    _weekly_ticks(fig, a1, a2)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def fig_ctp_ts(traffic: pd.DataFrame, path):
    viz.apply_style(); w = _daily_wide(traffic)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True,
                                 gridspec_kw={"height_ratios": [2, 1]})
    a1.plot(w.index, w["CTP_C"], label="Control", color=viz.COLOR_CONTROL)
    a1.plot(w.index, w["CTP_E"], label="Experiment", color=viz.COLOR_TREATMENT, ls="--")
    a1.set_ylabel("Daily CTP"); a1.set_title("Daily Click-Through-Probability by group")
    a1.legend()
    a2.bar(w.index, w["CTP_diff"], color="gray", width=1.0)
    a2.axhline(0, color="black", lw=.8); a2.set_ylabel("E - C CTP")
    _weekly_ticks(fig, a1, a2)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


# ---------- 森林图 ----------
def fig_forest(z_results: dict, ppe_aux: dict, delta: float, path):
    viz.apply_style()
    fig, ax = plt.subplots(figsize=(9, 4.2))
    order = ["GrossConversion", "NetConversion", "PayPerEnrollment"]
    labels = {"GrossConversion": "Gross Conversion (Enr/Click)",
              "NetConversion": "Net Conversion (Pay/Click) [core]",
              "PayPerEnrollment": "Pay/Enrollment (auxiliary)"}
    for i, name in enumerate(order):
        a = ppe_aux if name == "PayPerEnrollment" else z_results[name]
        pt = a["abs_diff"]
        lo = a["descriptive_ci95"][0] if name == "PayPerEnrollment" else a["ci95_low"]
        hi = a["descriptive_ci95"][1] if name == "PayPerEnrollment" else a["ci95_high"]
        color = viz.COLOR_AUX if name == "PayPerEnrollment" else viz.COLOR_CONTROL
        ax.errorbar(pt * 100, i, xerr=[[(pt - lo) * 100], [(hi - pt) * 100]],
                    fmt="o", color=color, capsize=5, lw=2)
        ax.text(hi * 100 + 0.08, i, f"{pt*100:+.2f}pp [{lo*100:+.2f}, {hi*100:+.2f}]", va="center", fontsize=9)
    ax.axvline(0, color="black", lw=1.2)
    ax.axvline(-delta * 100, color=viz.COLOR_TREATMENT, ls="--", lw=1.2)
    ax.text(-delta * 100 + 0.05, 0.35, f"-delta=-{delta*100:.2f}pp (NI boundary)",
            color=viz.COLOR_TREATMENT, fontsize=8, ha="left")
    ax.set_yticks(range(len(order))); ax.set_yticklabels([labels[n] for n in order])
    ax.invert_yaxis(); ax.set_xlabel("Absolute difference (Experiment - Control), percentage points")
    ax.set_title("Main effect estimates with 95% CI (Z-test primary; Pay/Enr descriptive)")
    ax.grid(axis="x", alpha=.3)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


# ---------- 置换 ----------
def fig_permutation_null(null_g, null_n, z_obs: dict, path):
    viz.apply_style()
    grid = np.linspace(-6, 6, 400)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, name, nz in zip(axes, ["GrossConversion", "NetConversion"], [null_g, null_n]):
        ax.hist(nz, bins=60, color="#4c78a8", alpha=.75, density=True, label="same-weekday-block null")
        ax.plot(grid, stats.norm.pdf(grid), color="black", lw=1.3, label="N(0,1) iid reference")
        zc = 1.959963984540054
        ax.axvline(-zc, color="gray", ls=":", lw=1.2); ax.axvline(zc, color="gray", ls=":", lw=1.2)
        ax.axvline(z_obs[name], color=viz.COLOR_TREATMENT, lw=1.6, label=f"observed Z={z_obs[name]:.2f}")
        ax.set_title(f"{name} (null sd={nz.std(ddof=1):.2f})")
        ax.set_xlabel("permutation null Z"); ax.legend(fontsize=7)
    axes[0].set_ylabel("density")
    fig.suptitle("Aggregate-data same-weekday-block permutation null (B=10,000; not an AA test)")
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def fig_sensitivity_comparison(null_g, null_n, pair_g, pair_n, z_obs: dict, path):
    viz.apply_style()
    grid = np.linspace(-6, 6, 400)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, name, blk, pr in zip(axes, ["GrossConversion", "NetConversion"], [null_g, null_n], [pair_g, pair_n]):
        ax.hist(blk, bins=60, density=True, alpha=.55, color="#4c78a8", label="same-weekday block (primary)")
        ax.hist(pr, bins=60, density=True, histtype="step", color="#e69f00", lw=1.6, label="paired-date (sensitivity)")
        ax.plot(grid, stats.norm.pdf(grid), color="black", lw=1.2, label="N(0,1) iid")
        ax.axvline(z_obs[name], color=viz.COLOR_TREATMENT, lw=1.5, label=f"obs Z={z_obs[name]:.2f}")
        ax.set_title(name); ax.set_xlabel("null Z"); ax.legend(fontsize=7)
    axes[0].set_ylabel("density")
    fig.suptitle("Exchangeability assumption vs null width (aggregate-data check; not an AA test)")
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


# ---------- 非劣效 ----------
def fig_noninferiority(d, lo, hi, delta: float, ni_pass: bool, path):
    viz.apply_style()
    fig, ax = plt.subplots(figsize=(9.2, 3.6))
    ax.axvspan(-delta * 100, 1.2, color=viz.COLOR_OK, alpha=.10)
    ax.axvline(0, color="black", lw=1.3)
    ax.axvline(-delta * 100, color=viz.COLOR_NI, ls="--", lw=1.6)
    ax.errorbar(d * 100, 0, xerr=[[(d - lo) * 100], [(hi - d) * 100]], fmt="o",
                color=viz.COLOR_PRIMARY, capsize=6, lw=2.4, markersize=9)
    ax.text(d * 100, 0.22, f"point={d*100:+.2f}pp", ha="center", fontsize=9)
    ax.text(lo * 100, -0.30, f"lower={lo*100:+.2f}pp", ha="center", fontsize=9, color=viz.COLOR_PRIMARY)
    ax.text(-delta * 100, 0.42, f"-delta = -{delta*100:.2f}pp (NI boundary)",
            color=viz.COLOR_NI, fontsize=9, ha="center")
    ax.text(0, 0.42, "zero effect", color="black", fontsize=9, ha="center")
    verdict = ("NI established" if ni_pass else
               f"NI NOT established: lower bound {lo*100:+.2f}pp < -{delta*100:.2f}pp "
               f"(one-sided alpha=0.025)\n"
               "inconclusive due to limited precision - NOT proof of inferiority")
    ax.text(0.5, -0.72, verdict, fontsize=9.5, ha="center",
            bbox=dict(boxstyle="round", fc="#fff3cd", ec=viz.COLOR_NI))
    ax.set_ylim(-1, 0.8); ax.set_xlim(-2.2, 1.2); ax.set_yticks([])
    ax.set_xlabel("Net Conversion absolute difference (Experiment - Control), pp")
    ax.set_title(f"Non-inferiority assessment of Net Conversion (locked delta={delta*100:.2f}pp)")
    ax.grid(axis="x", alpha=.3)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


# ---------- 成本收益 ----------
def fig_savings_grid(eff: dict, path):
    viz.apply_style()
    cost_grid = np.array([1.25, 2.5, 5, 7.5, 10, 15, 20, 30])
    tiers = {"cluster_lower": eff["cluster_lower (conservative)"], "point": eff["point"],
             "cluster_upper": eff["cluster_upper"]}
    grid_df = pd.DataFrame({k: np.round(cost_grid * red, 1) for k, red in tiers.items()},
                           index=pd.Index(cost_grid, name="cost_USD_per_enrollment"))
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    im = ax.imshow(grid_df.to_numpy(), aspect="auto", cmap="RdYlGn", vmin=-3000, vmax=24000)
    ax.set_xticks(range(3), ["cluster lower", "point", "cluster upper"])
    ax.set_yticks(range(len(cost_grid)), [f"{c:.2f}" for c in cost_grid])
    ax.set_xlabel("Gross effect tier (day-cluster conservative)")
    ax.set_ylabel("Assumed cost per enrollment (USD)")
    for i in range(grid_df.shape[0]):
        for j in range(grid_df.shape[1]):
            ax.text(j, i, f"{grid_df.iloc[i, j]:,.0f}", ha="center", va="center", fontsize=7)
    ax.set_title("23d operational savings (USD): cost x effect grid [Assumption]")
    fig.colorbar(im, ax=ax, label="USD", shrink=.8)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)
    return grid_df


def fig_tornado(eff, iid_ref, c_low, c_base, c_high, path):
    viz.apply_style()
    base_saving = eff["point"] * c_base
    swing_effect = (eff["cluster_lower (conservative)"] * c_base, eff["cluster_upper"] * c_base)
    swing_cost = (eff["point"] * c_low, eff["point"] * c_high)
    iid_swing = (iid_ref[0] * c_base, iid_ref[1] * c_base)
    tor = pd.DataFrame([["unit cost c (1.25..30)", *swing_cost],
                        ["Gross effect (cluster CI)", *swing_effect],
                        ["Gross effect (iid CI, ref.)", *iid_swing]], columns=["driver", "low", "high"])
    fig, ax = plt.subplots(figsize=(8, 3.6))
    for y, (_, row) in zip(range(len(tor)), tor.iterrows()):
        ax.barh(y, row["high"] - base_saving, left=base_saving, color=viz.COLOR_OK, alpha=.75)
        ax.barh(y, row["low"] - base_saving, left=base_saving, color=viz.COLOR_TREATMENT, alpha=.75)
    ax.axvline(base_saving, color="black", lw=1.3, label=f"Base={base_saving:,.0f}")
    ax.set_yticks(list(range(len(tor))), tor["driver"]); ax.invert_yaxis()
    ax.set_xlabel("23d operational savings (USD) [Assumption]")
    ax.set_title("Tornado: drivers of savings uncertainty (23d window)")
    ax.legend(fontsize=8); ax.grid(axis="x", alpha=.3)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)
    return base_saving, tor


def fig_breakeven(red_pt, lost_payments_pt, margins, path):
    viz.apply_style()
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    xs = np.linspace(0, 35, 200)
    ax.plot(xs, red_pt * xs, color=viz.COLOR_PRIMARY, lw=2, label="Operational savings (point)")
    for v, col in zip(margins, [viz.COLOR_OK, viz.COLOR_WARN, viz.COLOR_TREATMENT]):
        ax.axhline(lost_payments_pt * v, ls="--", color=col, lw=1.3,
                   label=f"Revenue downside v={v} (break-even c*={lost_payments_pt*v/red_pt:.1f})")
    ax.set_xlabel("Assumed cost per screened enrollment (USD) [Assumption]")
    ax.set_ylabel("USD over 23d outcome window")
    ax.set_title("Break-even: operational savings vs Net revenue downside [SCENARIO]")
    ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)
