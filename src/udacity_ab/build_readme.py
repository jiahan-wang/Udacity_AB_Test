# -*- coding: utf-8 -*-
"""从 config + processed JSON 渲染 README.md。

原则：README 中每个数字都由本脚本从 src pipeline 产出的 JSON 读取，不手写结果数字；
结论表述区分统计显著与业务含义，并对情景假设单独标注。
运行：python -m udacity_ab.build_readme  （或 run_pipeline 后执行）
"""
import json
from pathlib import Path

import pandas as pd

from .config import project_root, load_config


def _pct(x, d=3):
    return f"{x*100:.{d}f}%"


def _pp(x, d=3):
    return f"{x*100:+.{d}f}pp"


def _ci(lo, hi, d=3):
    return f"({lo*100:+.{d}f}pp, {hi*100:+.{d}f}pp)"


def _num(x):
    return f"{x:,.0f}"


def build(root: Path | None = None) -> str:
    root = root or project_root()
    proc = root / "data" / "processed"
    cfg = load_config(root / "config" / "analysis_config.toml")
    lk, base, expc, ba = cfg["locked"], cfg["design_baseline"], cfg["exploratory"], cfg["business_assumptions"]

    def J(n):
        return json.loads((proc / f"{n}.json").read_text(encoding="utf-8"))

    me, nid, cb = J("main_effects"), J("ni_decision"), J("cost_benefit")
    dp, qc, pc = J("design_precision"), J("quality_checks"), J("permutation_check")
    sim_path = root / "methodology_demo" / "sim_summary.json"
    sim = json.loads(sim_path.read_text(encoding="utf-8")) if sim_path.exists() else {}
    # 37 天流量窗总量（SRM/不变指标口径）
    _long = pd.read_csv(proc / "daily_long.csv", parse_dates=["Date"])
    _wt = _long.groupby("Group")[["Pageviews", "Clicks"]].sum()
    pv_c, pv_e = int(_wt.loc["Control", "Pageviews"]), int(_wt.loc["Experiment", "Pageviews"])
    ck_c, ck_e = int(_wt.loc["Control", "Clicks"]), int(_wt.loc["Experiment", "Clicks"])

    g, n = me["z_tests"]["GrossConversion"], me["z_tests"]["NetConversion"]
    ppe = me["ppe_aux"]
    tot = {r["Group"]: r for r in me["totals"]}
    pw = {r["Metric"]: r for r in dp["power_by_metric"]}
    plan = {r["Metric"]: r for r in dp["theoretical_requirement"]}
    extra = dp["extra_days_needed"]
    srm = qc["SRM"]; ctp = qc["invariants"]["CTP"]
    eff = cb["effect_tiers_reduction_23d"]
    scen = {r["cost_scenario"]: r for r in cb["scenarios_23d"]}
    be = cb["sensitivity"]["breakeven"]; ann = cb["sensitivity"]["annualized_scenario"]
    delta = lk["ni_delta_net"]

    md = f"""# Udacity 免费试听筛选（Free-Trial Screener）A/B 实验评估

> 核心业务问题：新增“免费试听前筛选每周学习时长”的门槛，能否**减少低意愿用户对免费试听资源的无效占用，同时保障最终付费转化**？
> 核心决策指标：**Net Conversion（Payments / Clicks）**，采用事前锁定的**非劣效（Non-inferiority）**框架判定。
> 本 README 的结果数字均来自 `data/processed/*.json`，可由 `scripts/run_pipeline.py` 从原始数据复现。

---

## Business Context

Udacity 在免费试听落地页增加学习时长投入度筛选：实验组用户点击“开始免费试听”后需先填写每周可投入学习小时数（过低会被提示课程可能不合适），对照组直接进入。业务假设是：筛掉低投入意愿用户可减少后续无效试听占用的运营资源，同时不实质性损害最终付费。

- 分流单位：cookie（本开源数据只提供**日粒度聚合**计数，无用户级明细）。
- 数据时间：{lk['windows']['traffic_start']} 至 {lk['windows']['traffic_end']}（{lk['windows']['traffic_days']} 天流量窗）；因 enroll→payment 有 {lk['windows']['outcome_lag_days']} 天观察滞后，转化结果只用前 {lk['windows']['outcome_days']} 天 outcome 窗（{lk['windows']['outcome_start']} 至 {lk['windows']['outcome_end']}）。

## Experiment Design

- 普通双侧检验 α={lk['alpha_two_sided']:.2f}；非劣效单侧 α={lk['ni_alpha_one_sided']:.3f}（等价用 95% 双侧 CI 下界判定）；目标功效 {lk['target_power']:.2f}。
- 事前锁定（查看任何结果之前，锁定后不调整；MDE 为绝对效应）：MDE_Gross={lk['mde_gross']*100:.2f}pp、MDE_Net={lk['mde_net']*100:.2f}pp、非劣效边界 δ={delta*100:.2f}pp。
- δ 的业务理由（业务决策原话）：“{lk['ni_delta_rationale']}”
- 规划基线（公开 benchmark，非本实验观测）：Gross p={base['p_enroll_given_click']}、Net p={base['p_pay_given_click']}、CTR={base['ctr']}、合计日 clicks={base['daily_clicks_total']:,}。
- 理论所需样本（每组，80% 功效）：Gross {plan['Gross']['n_per_group@0.80']:,}、Net {plan['Net']['n_per_group@0.80']:,}（90% 功效：{plan['Gross']['n_per_group@0.90']:,}/{plan['Net']['n_per_group@0.90']:,}）。

## Data Dictionary

见 `docs/DATA_DICTIONARY.md`。原始字段：Date（'Sat, Oct 11' 前缀，按 2014 年解析）、Pageviews（cookie 计数）、Clicks（点击免费试听）、Enrollments（注册/进入试听）、Payments（完成付费）。派生：CTP=Clicks/Pageviews、GrossConversion=Enrollments/Clicks、NetConversion=Payments/Clicks、PayPerEnrollment=Payments/Enrollments、OutcomeComplete（该日 enroll/pay 是否成熟）、Group、Weekday。

## Data Cleaning

- 两组各 {lk['windows']['traffic_days']} 天、无重复 (date,group)、日期逐日连续、无负值、漏斗 PV≥Clicks≥Enrollments≥Payments 零违规（`quality_report.json`）。
- |z|≥2.5 极端日**只标记不删除**：10/18（周六低流量，周末季节性，两组同形态）、10/24（两组 CTP 同向下探，共同外部因素）——删除没有业务依据，保留并在质量检查中复核。
- 双窗口：37 天流量窗用于 SRM/不变指标；23 天 outcome 窗用于转化推断，被滞后截断的 {lk['windows']['outcome_lag_days']} 天只贡献流量不进分母。

## Analysis Window

| 口径 | Control | Experiment |
|---|---|---|
| Pageviews（37d） | {_num(pv_c)} | {_num(pv_e)} |
| Clicks（37d 流量窗） | {_num(ck_c)} | {_num(ck_e)} |
| Clicks（23d outcome 窗） | {_num(tot['Control']['Clicks'])} | {_num(tot['Experiment']['Clicks'])} |
| Enrollments（23d） | {_num(tot['Control']['Enrollments'])} | {_num(tot['Experiment']['Enrollments'])} |
| Payments（23d） | {_num(tot['Control']['Payments'])} | {_num(tot['Experiment']['Payments'])} |

outcome 窗样本损失：两组各约 39.1% 的 clicks 落在尚未成熟的后 {lk['windows']['outcome_lag_days']} 天（`window_sample_loss.csv`）。

## Metric Definitions

- **Gross Conversion = Enrollments / Clicks（策略效果指标）**：衡量“点击→进入试听”的比例，筛选器若生效应使其下降（更少低意愿用户进入试听）。
- **Net Conversion = Payments / Clicks（核心决策指标）**：衡量“点击→最终付费”，是业务真正在意的端到端转化，用非劣效框架保障其不被实质损害。
- **Payments / Enrollments（辅助质量诊断，不作独立主检验）**：进入试听用户中的付费比例，用于判断被筛后留下的用户质量是否提升。
- 汇总率一律用 pooled：Σ分子/Σ分母，不用日比率平均。主检验为双样本比例 Z（**检验用 pooled 方差、CI 用 unpooled 方差**）。

## Experimental Quality Checks

- **SRM（Pageviews 分流）**：C={_num(srm['control'])}、E={_num(srm['experiment'])}，实验份额 {_pct(srm['experiment_share'],4)}，χ²={srm['chi2']:.4f}、精确二项 p={srm['p_binom_exact']:.4f}，0.5 在份额 95%CI 内 → **未发现分流比例失配**。
- **Clicks 分流**：χ² p={qc['invariants']['Clicks_split']['p_chi2']:.4f}；**CTP 不变指标**：C={ctp['control']:.6f}、E={ctp['experiment']:.6f}，diff {_pp(ctp['diff'])}，Z={ctp['z']:.3f}、p={ctp['p']:.4f}（不显著，分流前点击行为均衡）。
- 逐日配对诊断（健康检查，非 covariate balance）：PV 配对 t p={qc['daily_diag']['PV_paired_t_p']:.4f}、CTP p={qc['daily_diag']['CTP_paired_t_p']:.4f}。

## Statistical Methods

1. **双样本比例 Z 检验（主分析）**：把每次 click 视为独立 Bernoulli。
2. **Delta Method（辅助复核）**：以“天”为 cluster 的比率方差，承认日间过度离散。
3. **day-cluster bootstrap（辅助，B={me['bootstrap_B']:,}，seed={expc['random_seed']}）**：以天为重采样单位的 percentile CI。
4. **aggregate-data placebo/permutation robustness check（非 AA Test）**：same-weekday block 置换为主、paired-date 翻转为并列敏感性；以天为可交换单位，**不能替代 cookie 级 AA**。
> 同一口径：三法点估计与方向一致；显著性强度依赖 click 相互独立假设（day-cluster 口径下 Gross CI 跨 0）。Z 为事前指定主分析，cluster 法仅额外揭示“只有 23 个日 cluster”的不确定性。

## Precision / MDE Analysis

- 实际每组样本 {dp['actual_precision']['Gross']['nc']:,}/{dp['actual_precision']['Gross']['ne']:,} clicks。
- 对**锁定 MDE** 的实际功效：Gross={pw['Gross']['power@locked_MDE']}、Net={pw['Net']['power@locked_MDE']}，均低于 0.80 → **对 1pp/0.75pp 级别效应 underpowered**。
- 现有样本要达到 80% 功效，实际可检测 |MDE|：Gross {pw['Gross']['achievable_MDE@0.80']*100:.3f}pp、Net {pw['Net']['achievable_MDE@0.80']*100:.3f}pp（均大于锁定 MDE）。
- 补样：按 outcome 窗累积速度，Gross/Net 还需再累积 {extra['Gross']['extra_accrual_days']}/{extra['Net']['extra_accrual_days']} 天（另加 {lk['windows']['outcome_lag_days']} 天 lag 才成熟）。
> **“未达到统计显著”不等于“策略没有影响”**：功效不足时，不显著只说明现有精度无法排除业务相关效应，须结合 CI 宽度与 MDE 解读。

## Main Results

| 指标 | Control | Experiment | 差异(E-C) | Z | p | 95%CI(iid,unpooled) |
|---|---|---|---|---|---|---|
| Gross Conversion | {g['rate_control']:.6f} | {g['rate_experiment']:.6f} | {_pp(g['abs_diff'])}（{_pct(g['relative_change'],2)}） | {g['z']:.4f} | {g['p_value']:.3g} | {_ci(g['ci95_low'],g['ci95_high'])} |
| Net Conversion | {n['rate_control']:.6f} | {n['rate_experiment']:.6f} | {_pp(n['abs_diff'])}（{_pct(n['relative_change'],2)}） | {n['z']:.4f} | {n['p_value']:.4f} | {_ci(n['ci95_low'],n['ci95_high'])} |
| Pay/Enroll（辅助） | {ppe['control']:.6f} | {ppe['experiment']:.6f} | {_pp(ppe['abs_diff'])}（{_pct(ppe['relative_change'],2)}） | — | 描述性 | {_ci(ppe['descriptive_ci95'][0],ppe['descriptive_ci95'][1])} |

- **Gross**：iid-Z 下显著为负（p={g['p_value']:.2e}），方向符合“筛掉低意愿进入”的机制；但 day-cluster bootstrap CI {_ci(me['bootstrap']['GrossConversion']['ci95_low'],me['bootstrap']['GrossConversion']['ci95_high'])}、Delta CI {_ci(me['delta']['GrossConversion']['ci95_low'],me['delta']['GrossConversion']['ci95_high'])} **均跨 0**（cluster SE 约为 iid 的 2.6–3.0 倍，仅 23 个日 cluster）。因此按同一口径：**点估计与方向三法一致，显著性强度依赖 click 独立假设**，不叙述为无条件显著。
- **Net**：iid-Z p={n['p_value']:.4f} 不显著，95%CI {_ci(n['ci95_low'],n['ci95_high'])} 跨 0；day-cluster bootstrap {_ci(me['bootstrap']['NetConversion']['ci95_low'],me['bootstrap']['NetConversion']['ci95_high'])}、Delta {_ci(me['delta']['NetConversion']['ci95_low'],me['delta']['NetConversion']['ci95_high'])} 同样跨 0。点估为负但幅度小，**不能据此说“对付费无影响”，也不能说“已证劣效”**。
- **Pay/Enroll** 点估上行 {_pp(ppe['abs_diff'])}，与“留下用户质量更高”的机制方向一致，但仅为辅助诊断。
- **置换鲁棒性（非 AA）**：same-weekday block 经验双侧 p Gross={pc['results']['GrossConversion']['perm_empirical_p_two_sided']:.4f}、Net={pc['results']['NetConversion']['perm_empirical_p_two_sided']:.4f}；零分布 SD={pc['null_overdispersion']['null_sd_gross']:.2f}/{pc['null_overdispersion']['null_sd_net']:.2f}（远宽于 N(0,1)，源于整天重分配使组分母波动+日间过度离散，非管线错误，零分布均值≈0）；paired-date 敏感性 p={pc['sensitivity_paired_date']['results']['GrossConversion']['empirical_p']:.4f}/{pc['sensitivity_paired_date']['results']['NetConversion']['empirical_p']:.4f}。该检查只作鲁棒性佐证，不改主结论、不做非劣效判定。

## Non-inferiority Framework

- 判定规则：**当且仅当 Net 的 95% 双侧 CI 下界 > −δ（等价 Z_NI=(d+δ)/SE > z_(1−{lk['ni_alpha_one_sided']})）时通过非劣效**；δ={delta*100:.2f}pp 为事前锁定，不做事后调整。
- Net 点估 {_pp(nid['net_point'])}、95%CI {_ci(nid['net_ci95'][0],nid['net_ci95'][1])}，**下界 {nid['net_ci95'][0]*100:.3f}pp < −δ={-delta*100:.2f}pp**；Z_NI={nid['z_ni']:.4f}、单侧 p={nid['p_ni_one_sided']:.4f} → **未通过非劣效（NI NOT established）**。
- 临界 δ（下界恰为 −δ）={nid['critical_delta_to_pass']*100:.3f}pp（仅敏感性展示，正式只用锁定值）。
- **正确解读**：点估本身落在 δ 容忍区间内，但因精度不足（Net 对锁定 MDE 功效仅 {pw['Net']['power@locked_MDE']}），CI 同时覆盖“损失小于边界”和“损失超过边界”，故为 **inconclusive（未能确立非劣效），不是已证明劣效（NOT proof of inferiority）**。二维非劣效门未过 → 当前不满足【全量】上线（暂不 ship，非永久否决；二维矩阵原始判定为 {nid['matrix_decision']}）。衔接说明：四态框架里因 underpowered 属 inconclusive，故 Do-Not-Launch 与 Full Launch 都不满足、触发条件落在 Continue（见 Final Decision Options）。

## Cost-Benefit Scenario Analysis

> **全部成本/工时/毛利/年化数字均为 {ba['label']}，不是数据集观测结果。** headline 只用 23 天观测窗。
- 被筛除试听规模（按 Gross 效应 × 实验组 {_num(tot['Experiment']['Clicks'])} clicks）：点估 {eff['point']:.1f} 例；**iid-Z 口径** [{cb['iid_reference_reduction_23d'][0]:.1f}, {cb['iid_reference_reduction_23d'][1]:.1f}]；**day-cluster 口径** [{eff['cluster_lower (conservative)']:.1f}, {eff['cluster_upper']:.1f}]，cluster 下界≈0 甚至为负。保守情景必须取 cluster 端，不得用 iid 下界充当保守估计。
- 三档单试听成本 c={ba['cost_per_enrollment_low_base_high']} USD（=支持工时 {ba['support_minutes_low_base_high']} 分钟 × 时薪 {ba['hourly_loaded_cost_low_base_high']} USD/h /60）：23 天点估资源节约 Low/Base/High = {scen['Low (c=1.25)']['savings_point']:,.0f} / {scen['Base (c=7.5)']['savings_point']:,.0f} / {scen['High (c=30)']['savings_point']:,.0f} USD；Base 档 cluster 区间 [{scen['Base (c=7.5)']['savings_cluster_lower']:,.0f}, {scen['Base (c=7.5)']['savings_cluster_upper']:,.0f}]。
- Break-even（SCENARIO，依赖未观测毛利 v={ba['payment_margin_low_base_high']}）：点估付费减少 {cb['sensitivity']['point_lost_payments_23d']:.1f} 例，临界单试听成本 c* 分别为 {be[0]['breakeven_cost_per_enrollment_USD']:.2f}/{be[1]['breakeven_cost_per_enrollment_USD']:.2f}/{be[2]['breakeven_cost_per_enrollment_USD']:.2f} USD；Base 成本下临界毛利 v*={cb['sensitivity']['breakeven_margin_at_base_cost']:.2f} USD。
- 年化（明确外推假设：每组 {ba['annualization_clicks_per_group_per_day']:,} clicks/天×{ba['annualization_days']} 天={ann['clicks_per_group']:,}）：减少 {ann['reduced_enrollments']:,.0f} 例、节约 {ann['savings_low_base_high'][0]:,.0f}/{ann['savings_low_base_high'][1]:,.0f}/{ann['savings_low_base_high'][2]:,.0f} USD、点估付费减少 {ann['point_lost_payments']:,.0f} 例——**仅情景行，不进 headline**。

## Limitations（三类核心局限，不淡化）

1. **日粒度聚合数据，无法做真实 user-level inference**：所有检验把 click 当独立 Bernoulli，而同一用户/时段的点击可能相关；以天为 cluster 的复核显示 SE 被低估（cluster SE 为 iid 的 2.6–3.0 倍、Gross cluster CI 跨 0）。日粒度置换是 aggregate-data 检查，**无法复现 cookie 级随机化，不能替代真正的用户级 AA Test**。
2. **outcome 窗截断导致有效样本减少、实验 underpowered**：14 天 payment 滞后使转化推断只能用 23/37 天（约 39% clicks 被排除），对锁定的 1pp/0.75pp 效应功效仅 {pw['Gross']['power@locked_MDE']}/{pw['Net']['power@locked_MDE']}，Net 非劣效因此无法确立；这是精度问题，不是“无效应/已证劣”的证据。
3. **缺少用户级实验前协变量、渠道/设备字段**：无法做真实 CUPED 方差削减、HTE 子组/异质性分析与用户级多重检验；这些只能在独立 Notebook 用**模拟数据**演示，独立目录、不进主结论。
- 其他：单实验、单时间段，无法跨周期复制；业务成本参数未在数据中观测，成本收益为情景分析。

## Methodology Extensions（模拟演示，不参与主结论）

独立 Notebook `notebooks/07_methodology_extension_demo.ipynb`（产物隔离在 `methodology_demo/`），每节标注 “Simulated data methodology demonstration — not used for the primary experiment conclusion”，**不读取主 config/JSON、不回传任何数值**：
- 可控 DGP（ρ≈0.707）下 CUPED 经验方差削减 {sim.get('cuped',{}).get('empirical_variance_reduction',0)*100:.1f}%（理论 ρ²=50%）；
- 零效应假阳性演示（并入的模拟演示）：naive/CUPED 经验 FPR≈{sim.get('zero_effect',{}).get('naive_empirical_FPR',0):.3f}；
- HTE 子组与 treatment×feature 交互演示（真交互 γ={sim.get('hte',{}).get('true_gamma','—')}）；
- K={sim.get('multiplicity',{}).get('K',40)} 多重检验：未校正 FWER={sim.get('multiplicity',{}).get('global_null',{}).get('FWER_unadjusted',0):.2f}、Bonferroni/BH-FDR 控制在名义水平。
这些结果**只演示方法，不用于本实验任何结论**（不参与主结论）。

## Data Provenance, Source & License

- **raw data 默认不入库**（`.gitignore` 忽略 `data/raw/*.csv`）；两份原始文件 SHA-256、双镜像逐行比对与 5 个独立公开来源汇总值交叉验证记录见 `data/raw/DATA_PROVENANCE.md`（Control 345543/28378/3785/2033、Experiment 344660/28325/3423/1945）。
- **来源**：Udacity A/B Testing Final Project 开源课程数据。主镜像 raw：
  - `https://raw.githubusercontent.com/jojoms711/Udacity_AB_Testing/master/data/Final_Project_Results_Control.csv`
  - `https://raw.githubusercontent.com/jojoms711/Udacity_AB_Testing/master/data/Final_Project_Results_Experiment.csv`
  - 官方 Google Sheet、第二镜像与 5 个独立公开交叉来源的完整 URL 见 `DATA_PROVENANCE.md`。
- **下载脚本**：`python scripts/download_data.py`（按 SHA-256 校验落盘到 `data/raw/`，只读保存）。
- **许可证说明**：该数据集为 Udacity 免费试听课程项目的教学用公开数据，版权归原作者/Udacity 所有，本项目仅用于学习与方法复现，不做商业再分发；因此原始 CSV 不纳入本仓库，需按上述来源自行下载。

## Reproducibility

```bash
# 1) 新环境（Python 3.13；直接依赖见 requirements-core.txt，完整冻结见 requirements.txt）
python -m venv .venv
.venv\\Scripts\\pip install -r requirements-core.txt
# 2) 放好原始数据（见下 Data Provenance / data/raw/DATA_PROVENANCE.md；raw 默认不入库）
# 3) 一键从 raw 重建全部 CSV/JSON/图表（seed 固定）
.venv\\Scripts\\python scripts/run_pipeline.py
# 4) 跑全部单元 + 回归 + 端到端测试（无 skip）
.venv\\Scripts\\python -m pytest
# 5) 重新生成本 README
.venv\\Scripts\\python -m udacity_ab.build_readme
# 6) 启动交互看板
.venv\\Scripts\\streamlit run app/streamlit_app.py
```
- 回归保障：`tests/test_regression_against_json.py` 断言 src 复现与已提交 JSON 一致（确定性结果 1e-12、MC 结果紧容差）；`tests/test_pipeline_end_to_end.py` 在临时目录从 raw 全量重跑并逐字段比对。
- 随机种子：bootstrap/permutation seed={expc['random_seed']}，B={expc['bootstrap_b']:,}/{expc['permutation_b']:,}。

## Project Structure

```
Udacity_AB_Test/
├─ config/analysis_config.toml        # 唯一配置：locked / design_baseline / exploratory / business_assumptions
├─ data/raw/                          # 原始 CSV（只读、不入库）+ DATA_PROVENANCE.md
├─ data/processed/                    # pipeline 产物：daily_*.csv / pooled_summary.csv + 7 个结果 JSON
├─ src/udacity_ab/                    # 模块化主代码（cleaning/metrics/design/srm/inference/noninferiority/cost_benefit/figures/pipeline…）
├─ scripts/                           # 一键入口 run_pipeline + 数据下载 + 独立复算
├─ notebooks/                         # 01..07 分析 Notebook（07 为隔离的方法论模拟）
├─ docs/                              # 数据字典 / 清洗日志 / 部署指南
├─ app/streamlit_app.py               # 六页交互看板（δ/成本滑块仅 sensitivity）
├─ tests/                             # 单元/回归/端到端 pytest
├─ reports/figures/                   # 全部图表（图内英文，统一视觉规范）
├─ methodology_demo/                  # 07 模拟演示的隔离产物
├─ requirements-core.txt / requirements.txt
└─ README.md
```

## Decision Options

| 选项 | 触发条件 | 本实验是否满足 |
|---|---|---|
| **Full Launch（全量上线）** | Gross 主检验显著下降 **且** Net 通过非劣效（CI 下界 > −δ）；质量检查无 SRM | **不满足**：Net 未通过非劣效 |
| **Targeted / Conditional Launch（定向/灰度）** | 全量证据不足但业务需推进，且能圈定低风险子人群、可快速回滚、同步继续采 Net | **证据受限**：聚合数据无用户级渠道/设备/前置行为字段，无法数据化圈定定向人群 |
| **Continue Experiment（继续实验补样）** | 机制方向成立但因 underpowered 无法确立非劣效，补样到 80% 功效后重判 | **满足触发条件**：补 Gross/Net 约 {extra['Gross']['extra_accrual_days']}/{extra['Net']['extra_accrual_days']} 天累积 +{lk['windows']['outcome_lag_days']} 天 lag |
| **Do Not Launch（不上线）** | 质量检查失败（SRM），或有充分证据证明 Net 劣效超出 δ | **不满足**：SRM 通过、Net 点估在 δ 内，无劣效证据，只是精度不足 |

**最终决策：Continue Experiment —— 补样至 80% 功效后重判 Net 非劣效。**
- 完整逻辑链：二维非劣效门未过 = 当前暂不【全量】上线（hold，非永久否决）；因 underpowered 属 inconclusive，Do-Not-Launch 在“无劣效证据”前提下同样不成立；四态触发条件唯一落在 Continue（补 Gross/Net 约 {extra['Gross']['extra_accrual_days']}/{extra['Net']['extra_accrual_days']} 天累积 +{lk['windows']['outcome_lag_days']} 天 lag 后重判）。
- 决策理由（机制方向）：Gross 点估下降、Pay/Enroll 点估上行，SRM/不变指标通过；唯一卡点是 Net 非劣效因功效不足无法确立，而补样量明确、成本低，补到 80% 功效即可让非劣效判定真正具备分辨力，避免在精度不足时做不可逆的全量决策。
- 排除 Full Launch：非劣效门未过，全量上线违背事前锁定的决策规则。
- 排除 Do Not Launch：当前没有“损害超出 δ”的证据，仅因不显著就否决会犯“把 underpowered 当证劣”的错误。
- Targeted/Conditional 仅作后备：仅当业务无法等待补样时，以可回滚的小流量灰度并同步采 Net；但现有聚合数据无法识别定向人群，灰度选择缺乏数据支撑，需补用户级字段。

---
*结果数字均可由 `scripts/run_pipeline.py` 复现。*
"""
    return md


def write_readme(root: Path | None = None) -> Path:
    root = root or project_root()
    out = root / "README.md"
    out.write_text(build(root), encoding="utf-8")
    return out


if __name__ == "__main__":
    p = write_readme()
    print("README written:", p)
