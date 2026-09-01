# -*- coding: utf-8 -*-
"""Udacity 免费试听筛选 A/B 实验交互式看板（Streamlit）。

启动：streamlit run app/streamlit_app.py
六页：数据概览 / 实验质量 / 核心效果 / 非劣效判断 / 成本收益 / 方法论与局限。
硬约束：δ 滑块默认=事前锁定 0.75pp，仅用于 sensitivity，不改变正式结论；
成本/工时滑块只驱动明确标注 Assumption 的情景，不代表数据集观测结果。
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]  # app/ 的上一级 = 项目根[1]
sys.path.insert(0, str(ROOT / "src"))
from udacity_ab.config import load_config  # noqa: E402
from udacity_ab import noninferiority as nim  # noqa: E402

st.set_page_config(page_title="Udacity Free-Trial Screener A/B Test", layout="wide")
CFG = load_config(ROOT / "config" / "analysis_config.toml")
LK, PROC, FIG = CFG["locked"], ROOT / "data" / "processed", ROOT / "reports" / "figures"


@st.cache_data
def _json(name):
    import json
    return json.loads((PROC / f"{name}.json").read_text(encoding="utf-8"))


@st.cache_data
def _csv(name):
    return pd.read_csv(PROC / f"{name}.csv")


def pp(x, d=3):
    return f"{x*100:+.{d}f}pp"


st.sidebar.title("A/B Test Dashboard")
page = st.sidebar.radio("页面", ["1. 数据概览", "2. 实验质量", "3. 核心效果",
                                "4. 非劣效判断", "5. 成本收益", "6. 方法论与局限"])
st.sidebar.info(
    f"事前锁定：α={LK['alpha_two_sided']}（双侧），NI 单侧 α={LK['ni_alpha_one_sided']}，"
    f"MDE Gross={LK['mde_gross']*100:.2f}pp / Net={LK['mde_net']*100:.2f}pp，"
    f"非劣效边界 δ={LK['ni_delta_net']*100:.2f}pp。锁定参数不随滑块改变。")

# ---------------- 1 数据概览 ----------------
if page.startswith("1"):
    st.title("数据概览")
    qr = _json("quality_report")
    pool = _csv("pooled_summary")
    loss = _csv("window_sample_loss")
    c1, c2, c3 = st.columns(3)
    c1.metric("流量窗天数", qr["windows"]["traffic_window_days"])
    c2.metric("outcome 窗天数", qr["windows"]["outcome_window_days"])
    c3.metric("重复日期-组", qr["duplicated_date_group"])
    st.subheader("双窗口 pooled 汇总（Σ分子/Σ分母）")
    st.dataframe(pool.style.format({c: "{:.6f}" for c in pool.columns if pool[c].dtype == float}),
                 width="stretch")
    st.subheader("outcome 窗样本损失（14 天 Payment 滞后）")
    st.dataframe(loss.style.format({"Pct_excluded": "{:.4f}"}), width="stretch")
    st.caption("结构质检：负值/漏斗违规均为 0；|z|≥2.5 极端日仅标记不删除（10/18 周末低流量、10/24 两组 CTP 同向下探）。")

# ---------------- 2 实验质量 ----------------
elif page.startswith("2"):
    st.title("实验质量（37 天流量窗）")
    q = _json("quality_checks")
    srm_, inv, diag = q["SRM"], q["invariants"], q["daily_diag"]
    c1, c2 = st.columns(2)
    c1.subheader("SRM（Pageviews 分流）")
    c1.write({k: srm_[k] for k in ["control", "experiment", "experiment_share",
                                   "p_chi2", "p_binom_exact"]})
    c1.success("未发现分流比例失配（p≫0.05，0.5 在份额 95%CI 内）")
    c2.subheader("不变指标")
    c2.write(pd.DataFrame({
        "Clicks_split": inv["Clicks_split"], "CTP": inv["CTP"]}).T)
    st.write("逐日配对诊断（健康检查，非 covariate balance）：", diag)
    st.image(str(FIG / "fig_pageviews_ts.png"), width="stretch")
    st.image(str(FIG / "fig_ctp_ts.png"), width="stretch")

# ---------------- 3 核心效果 ----------------
elif page.startswith("3"):
    st.title("核心效果（23 天 outcome 窗，Z 检验为主）")
    me = _json("main_effects")
    rows = []
    for name in ["GrossConversion", "NetConversion"]:
        z = me["z_tests"][name]
        rows.append({"指标": name, "Control": z["rate_control"], "Experiment": z["rate_experiment"],
                     "差异(E-C)": z["abs_diff"], "Z": z["z"], "p": z["p_value"],
                     "95%CI 下界": z["ci95_low"], "95%CI 上界": z["ci95_high"]})
    st.dataframe(pd.DataFrame(rows).style.format(
        {"Control": "{:.6f}", "Experiment": "{:.6f}", "差异(E-C)": "{:.6f}",
         "Z": "{:.4f}", "p": "{:.4g}", "95%CI 下界": "{:.6f}", "95%CI 上界": "{:.6f}"}),
        width="stretch")
    st.warning("同一口径：三法点估计与方向一致；显著性强度依赖 click 相互独立假设"
               "（day-cluster 口径下 Gross CI 跨 0），不把 Gross 下降叙述为无条件显著。")
    st.image(str(FIG / "fig_forest_effects.png"), width="stretch")
    pc = _json("permutation_check")
    st.subheader("aggregate-data placebo/permutation robustness check（非 AA Test）")
    st.dataframe(pd.DataFrame(pc["three_method_table"]).style.format(
        {"obs_Z": "{:.4f}", "empirical_p": "{:.4f}", "null_sd": "{:.3f}", "fpr_at_05": "{:.3f}"}),
        width="stretch")
    st.image(str(FIG / "fig_permutation_null.png"), width="stretch")
    st.image(str(FIG / "fig_permutation_sensitivity.png"), width="stretch")

# ---------------- 4 非劣效 ----------------
elif page.startswith("4"):
    st.title("Net Conversion 非劣效判断")
    nid = _json("ni_decision")
    me = _json("main_effects")["z_tests"]["NetConversion"]
    st.write(f"**正式结论（锁定 δ={LK['ni_delta_net']*100:.2f}pp，不随滑块变化）**")
    st.write({k: nid[k] for k in ["net_point", "net_ci95", "z_ni", "p_ni_one_sided",
                                  "ni_pass", "critical_delta_to_pass", "matrix_decision"]})
    if not nid["ni_pass"]:
        _lo = nid["net_ci95"][0]
        st.error(f"未通过非劣效：95%CI 下界 {_lo*100:.3f}pp < -{LK['ni_delta_net']*100:.2f}pp；"
                 "属精度不足导致的 inconclusive，非已证劣效。")
    st.image(str(FIG / "fig_noninferiority.png"), width="stretch")

    st.divider()
    st.subheader("Sensitivity：拖动 δ 仅作敏感性展示，不改变上面的正式结论")
    d_slider = st.slider("假设非劣效边界 δ（pp）", min_value=0.0, max_value=2.0,
                         value=float(LK["ni_delta_net"] * 100), step=0.05,
                         format="%.2f pp") / 100
    r = nim.ni_decision(me["abs_diff"], me["se_ci_unpooled"], d_slider, ni_alpha=LK["ni_alpha_one_sided"])
    st.write(f"在 δ={d_slider*100:.2f}pp 下：Z_NI={r['z_ni']:.4f}，单侧 p={r['p_ni_one_sided']:.4f}，"
             f"是否通过={'是' if r['ni_pass'] else '否'}（临界 δ={r['critical_delta_to_pass']*100:.3f}pp）")
    st.caption("正式决策只使用事前锁定的 0.75pp；本滑块不回写任何结果文件。")

# ---------------- 5 成本收益 ----------------
elif page.startswith("5"):
    st.title("成本收益情景（全部为 Assumption — not observed in dataset）")
    cb = _json("cost_benefit")
    eff = cb["effect_tiers_reduction_23d"]
    st.caption(cb["assumptions"]["label"] + "；headline 只用 23 天观测窗，年化为标注外推情景。")
    st.subheader("Sensitivity：单试听支持工时 × 综合时薪 → 单试听成本")
    c1, c2 = st.columns(2)
    minutes = c1.slider("单试听运营支持工时（分钟）", 1, 60, 15)
    hourly = c2.slider("综合人力时薪（USD/小时）", 5, 100, 30)
    c = minutes * hourly / 60
    red_pt, red_lo, red_hi = eff["point"], eff["cluster_lower (conservative)"], eff["cluster_upper"]
    st.write(f"推导单试听成本 c = {minutes}×{hourly}/60 = **{c:.2f} USD**（Assumption）")
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("点估资源节约", f"{red_pt*c:,.0f} USD")
    sc2.metric("cluster 保守端", f"{red_lo*c:,.0f} USD")
    sc3.metric("cluster 上端", f"{red_hi*c:,.0f} USD")
    st.caption("同一口径：减少试听的点估计与方向三法一致；显著性强度依赖 click 独立假设，"
               "cluster 保守端≈0（甚至可为负），避免只报有利窄区间。")
    st.subheader("批准的三档情景（c=1.25/7.5/30）")
    st.dataframe(pd.DataFrame(cb["scenarios_23d"]), width="stretch")
    st.image(str(FIG / "fig_savings_grid.png"), width="stretch")
    st.image(str(FIG / "fig_tornado.png"), width="stretch")
    st.image(str(FIG / "fig_breakeven.png"), width="stretch")
    be = pd.DataFrame(cb["sensitivity"]["breakeven"])
    st.write("Break-even（SCENARIO，依赖未观测毛利 v）：")
    st.dataframe(be.style.format({"v_USD": "{:.0f}", "point_revenue_loss_USD": "{:.1f}",
                                  "breakeven_cost_per_enrollment_USD": "{:.2f}"}),
                 width="stretch")

# ---------------- 6 方法论与局限 ----------------
else:
    st.title("方法论与局限")
    st.markdown("""
**统计方法**：主分析为双样本比例 Z 检验（检验 pooled、CI unpooled）；Delta Method 与
day-cluster bootstrap（B=10,000，seed 固定）仅作辅助；置换为 aggregate-data
placebo/permutation robustness check（same-weekday block 为主、paired-date 为敏感性），
**不是 AA Test，不能替代 cookie 级 AA**。

**三类核心局限**：
1. 日粒度聚合数据，无法做真实 user-level inference，click 相互独立假设可能不成立；
2. outcome 窗截断（14 天 Payment 滞后）使有效样本从 37 天降到 23 天，对 0.75–1pp 效应 underpowered；
3. 缺少用户级实验前协变量、渠道/设备字段，CUPED/HTE/多重检验只能在独立 Notebook 用模拟数据演示，
   不参与主结论（见 `notebooks/07_methodology_extension_demo.ipynb`，标签 Simulated methodology demonstration）。

**业务参数**：成本/工时/毛利/年化全部为 Assumption — not observed in dataset，仅情景分析。

**复现**：`python scripts/run_pipeline.py` 从 raw 重建全部 CSV/JSON/图表；`pytest` 含 src↔JSON 回归断言。
""")
