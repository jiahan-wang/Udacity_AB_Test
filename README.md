# Udacity 免费试听筛选（Free-Trial Screener）A/B 实验评估

> 核心业务问题：新增“免费试听前筛选每周学习时长”的门槛，能否**减少低意愿用户对免费试听资源的无效占用，同时保障最终付费转化**？
> 核心决策指标：**Net Conversion（Payments / Clicks）**，采用事前锁定的**非劣效（Non-inferiority）**框架判定。
> 本 README 的结果数字均来自 `data/processed/*.json`，可由 `scripts/run_pipeline.py` 从原始数据复现。

---

## Business Context

Udacity 在免费试听落地页增加学习时长投入度筛选：实验组用户点击“开始免费试听”后需先填写每周可投入学习小时数（过低会被提示课程可能不合适），对照组直接进入。业务假设是：筛掉低投入意愿用户可减少后续无效试听占用的运营资源，同时不实质性损害最终付费。

- 分流单位：cookie（本开源数据只提供**日粒度聚合**计数，无用户级明细）。
- 数据时间：2014-10-11 至 2014-11-16（37 天流量窗）；因 enroll→payment 有 14 天观察滞后，转化结果只用前 23 天 outcome 窗（2014-10-11 至 2014-11-02）。

## Experiment Design

- 普通双侧检验 α=0.05；非劣效单侧 α=0.025（等价用 95% 双侧 CI 下界判定）；目标功效 0.80。
- 事前锁定（查看任何结果之前，锁定后不调整；MDE 为绝对效应）：MDE_Gross=1.00pp、MDE_Net=0.75pp、非劣效边界 δ=0.75pp。
- δ 的业务理由（业务决策原话）：“免费试听筛选器目标是过滤低投入意愿用户、降低运营成本；只要最终付费转化率下降不超过 0.75 个百分点，成本节约的价值就超过可接受的收入损失，因此 0.75pp 是本次实验的业务容忍边界。”
- 规划基线（公开 benchmark，非本实验观测）：Gross p=0.20625、Net p=0.1093125、CTR=0.08、合计日 clicks=3,200。
- 理论所需样本（每组，80% 功效）：Gross 25,233、Net 26,348（90% 功效：33,779/35,273）。

## Data Dictionary

见 `docs/DATA_DICTIONARY.md`。原始字段：Date（'Sat, Oct 11' 前缀，按 2014 年解析）、Pageviews（cookie 计数）、Clicks（点击免费试听）、Enrollments（注册/进入试听）、Payments（完成付费）。派生：CTP=Clicks/Pageviews、GrossConversion=Enrollments/Clicks、NetConversion=Payments/Clicks、PayPerEnrollment=Payments/Enrollments、OutcomeComplete（该日 enroll/pay 是否成熟）、Group、Weekday。

## Data Cleaning

- 两组各 37 天、无重复 (date,group)、日期逐日连续、无负值、漏斗 PV≥Clicks≥Enrollments≥Payments 零违规（`quality_report.json`）。
- |z|≥2.5 极端日**只标记不删除**：10/18（周六低流量，周末季节性，两组同形态）、10/24（两组 CTP 同向下探，共同外部因素）——删除没有业务依据，保留并在质量检查中复核。
- 双窗口：37 天流量窗用于 SRM/不变指标；23 天 outcome 窗用于转化推断，被滞后截断的 14 天只贡献流量不进分母。

## Analysis Window

| 口径 | Control | Experiment |
|---|---|---|
| Pageviews（37d） | 345,543 | 344,660 |
| Clicks（37d 流量窗） | 28,378 | 28,325 |
| Clicks（23d outcome 窗） | 17,293 | 17,260 |
| Enrollments（23d） | 3,785 | 3,423 |
| Payments（23d） | 2,033 | 1,945 |

outcome 窗样本损失：两组各约 39.1% 的 clicks 落在尚未成熟的后 14 天（`window_sample_loss.csv`）。

## Metric Definitions

- **Gross Conversion = Enrollments / Clicks（策略效果指标）**：衡量“点击→进入试听”的比例，筛选器若生效应使其下降（更少低意愿用户进入试听）。
- **Net Conversion = Payments / Clicks（核心决策指标）**：衡量“点击→最终付费”，是业务真正在意的端到端转化，用非劣效框架保障其不被实质损害。
- **Payments / Enrollments（辅助质量诊断，不作独立主检验）**：进入试听用户中的付费比例，用于判断被筛后留下的用户质量是否提升。
- 汇总率一律用 pooled：Σ分子/Σ分母，不用日比率平均。主检验为双样本比例 Z（**检验用 pooled 方差、CI 用 unpooled 方差**）。

## Experimental Quality Checks

- **SRM（Pageviews 分流）**：C=345,543、E=344,660，实验份额 49.9360%，χ²=1.1297、精确二项 p=0.2884，0.5 在份额 95%CI 内 → **未发现分流比例失配**。
- **Clicks 分流**：χ² p=0.8239；**CTP 不变指标**：C=0.082126、E=0.082182，diff +0.006pp，Z=0.086、p=0.9317（不显著，分流前点击行为均衡）。
- 逐日配对诊断（健康检查，非 covariate balance）：PV 配对 t p=0.1672、CTP p=0.8409。

## Statistical Methods

1. **双样本比例 Z 检验（主分析）**：把每次 click 视为独立 Bernoulli。
2. **Delta Method（辅助复核）**：以“天”为 cluster 的比率方差，承认日间过度离散。
3. **day-cluster bootstrap（辅助，B=10,000，seed=20260831）**：以天为重采样单位的 percentile CI。
4. **aggregate-data placebo/permutation robustness check（非 AA Test）**：same-weekday block 置换为主、paired-date 翻转为并列敏感性；以天为可交换单位，**不能替代 cookie 级 AA**。
> 同一口径：三法点估计与方向一致；显著性强度依赖 click 相互独立假设（day-cluster 口径下 Gross CI 跨 0）。Z 为事前指定主分析，cluster 法仅额外揭示“只有 23 个日 cluster”的不确定性。

## Precision / MDE Analysis

- 实际每组样本 17,293/17,260 clicks。
- 对**锁定 MDE** 的实际功效：Gross=0.6399、Net=0.6212，均低于 0.80 → **对 1pp/0.75pp 级别效应 underpowered**。
- 现有样本要达到 80% 功效，实际可检测 |MDE|：Gross 1.206pp、Net 0.923pp（均大于锁定 MDE）。
- 补样：按 outcome 窗累积速度，Gross/Net 还需再累积 10.6/12.1 天（另加 14 天 lag 才成熟）。
> **“未达到统计显著”不等于“策略没有影响”**：功效不足时，不显著只说明现有精度无法排除业务相关效应，须结合 CI 宽度与 MDE 解读。

## Main Results

| 指标 | Control | Experiment | 差异(E-C) | Z | p | 95%CI(iid,unpooled) |
|---|---|---|---|---|---|---|
| Gross Conversion | 0.218875 | 0.198320 | -2.055pp（-9.39%） | -4.7018 | 2.58e-06 | (-2.912pp, -1.199pp) |
| Net Conversion | 0.117562 | 0.112688 | -0.487pp（-4.15%） | -1.4192 | 0.1558 | (-1.160pp, +0.186pp) |
| Pay/Enroll（辅助） | 0.537120 | 0.568215 | +3.109pp（5.79%） | — | 描述性 | (+0.812pp, +5.407pp) |

- **Gross**：iid-Z 下显著为负（p=2.58e-06），方向符合“筛掉低意愿进入”的机制；但 day-cluster bootstrap CI (-4.587pp, +0.477pp)、Delta CI (-4.651pp, +0.540pp) **均跨 0**（cluster SE 约为 iid 的 2.6–3.0 倍，仅 23 个日 cluster）。因此按同一口径：**点估计与方向三法一致，显著性强度依赖 click 独立假设**，不叙述为无条件显著。
- **Net**：iid-Z p=0.1558 不显著，95%CI (-1.160pp, +0.186pp) 跨 0；day-cluster bootstrap (-2.256pp, +1.182pp)、Delta (-2.224pp, +1.249pp) 同样跨 0。点估为负但幅度小，**不能据此说“对付费无影响”，也不能说“已证劣效”**。
- **Pay/Enroll** 点估上行 +3.109pp，与“留下用户质量更高”的机制方向一致，但仅为辅助诊断。
- **置换鲁棒性（非 AA）**：same-weekday block 经验双侧 p Gross=0.1354、Net=0.5874；零分布 SD=3.14/2.54（远宽于 N(0,1)，源于整天重分配使组分母波动+日间过度离散，非管线错误，零分布均值≈0）；paired-date 敏感性 p=0.0015/0.4469。该检查只作鲁棒性佐证，不改主结论、不做非劣效判定。

## Non-inferiority Framework

- 判定规则：**当且仅当 Net 的 95% 双侧 CI 下界 > −δ（等价 Z_NI=(d+δ)/SE > z_(1−0.025)）时通过非劣效**；δ=0.75pp 为事前锁定，不做事后调整。
- Net 点估 -0.487pp、95%CI (-1.160pp, +0.186pp)，**下界 -1.160pp < −δ=-0.75pp**；Z_NI=0.7648、单侧 p=0.2222 → **未通过非劣效（NI NOT established）**。
- 临界 δ（下界恰为 −δ）=1.160pp（仅敏感性展示，正式只用锁定值）。
- **正确解读**：点估本身落在 δ 容忍区间内，但因精度不足（Net 对锁定 MDE 功效仅 0.6212），CI 同时覆盖“损失小于边界”和“损失超过边界”，故为 **inconclusive（未能确立非劣效），不是已证明劣效（NOT proof of inferiority）**。二维非劣效门未过 → 当前不满足【全量】上线（暂不 ship，非永久否决；二维矩阵原始判定为 拒绝上线）。衔接说明：四态框架里因 underpowered 属 inconclusive，故 Do-Not-Launch 与 Full Launch 都不满足、触发条件落在 Continue（见 Final Decision Options）。

## Cost-Benefit Scenario Analysis

> **全部成本/工时/毛利/年化数字均为 Assumption - not observed in dataset; scenario analysis only，不是数据集观测结果。** headline 只用 23 天观测窗。
- 被筛除试听规模（按 Gross 效应 × 实验组 17,260 clicks）：点估 354.8 例；**iid-Z 口径** [206.9, 502.6]；**day-cluster 口径** [-82.3, 791.7]，cluster 下界≈0 甚至为负。保守情景必须取 cluster 端，不得用 iid 下界充当保守估计。
- 三档单试听成本 c=[1.25, 7.5, 30] USD（=支持工时 [5, 15, 30] 分钟 × 时薪 [15, 30, 60] USD/h /60）：23 天点估资源节约 Low/Base/High = 443 / 2,661 / 10,643 USD；Base 档 cluster 区间 [-617, 5,938]。
- Break-even（SCENARIO，依赖未观测毛利 v=[50, 150, 400]）：点估付费减少 84.1 例，临界单试听成本 c* 分别为 11.86/35.57/94.84 USD；Base 成本下临界毛利 v*=31.63 USD。
- 年化（明确外推假设：每组 1,600 clicks/天×365 天=584,000）：减少 12,004 例、节约 15,005/90,030/360,121 USD、点估付费减少 2,846 例——**仅情景行，不进 headline**。

## Limitations（三类核心局限，不淡化）

1. **日粒度聚合数据，无法做真实 user-level inference**：所有检验把 click 当独立 Bernoulli，而同一用户/时段的点击可能相关；以天为 cluster 的复核显示 SE 被低估（cluster SE 为 iid 的 2.6–3.0 倍、Gross cluster CI 跨 0）。日粒度置换是 aggregate-data 检查，**无法复现 cookie 级随机化，不能替代真正的用户级 AA Test**。
2. **outcome 窗截断导致有效样本减少、实验 underpowered**：14 天 payment 滞后使转化推断只能用 23/37 天（约 39% clicks 被排除），对锁定的 1pp/0.75pp 效应功效仅 0.6399/0.6212，Net 非劣效因此无法确立；这是精度问题，不是“无效应/已证劣”的证据。
3. **缺少用户级实验前协变量、渠道/设备字段**：无法做真实 CUPED 方差削减、HTE 子组/异质性分析与用户级多重检验；这些只能在独立 Notebook 用**模拟数据**演示，独立目录、不进主结论。
- 其他：单实验、单时间段，无法跨周期复制；业务成本参数未在数据中观测，成本收益为情景分析。

## Methodology Extensions（模拟演示，不参与主结论）

独立 Notebook `notebooks/07_methodology_extension_demo.ipynb`（产物隔离在 `methodology_demo/`），每节标注 “Simulated data methodology demonstration — not used for the primary experiment conclusion”，**不读取主 config/JSON、不回传任何数值**：
- 可控 DGP（ρ≈0.707）下 CUPED 经验方差削减 50.6%（理论 ρ²=50%）；
- 零效应假阳性演示（并入的模拟演示）：naive/CUPED 经验 FPR≈0.052；
- HTE 子组与 treatment×feature 交互演示（真交互 γ=0.08）；
- K=40 多重检验：未校正 FWER=0.86、Bonferroni/BH-FDR 控制在名义水平。
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
.venv\Scripts\pip install -r requirements-core.txt
# 2) 放好原始数据（见下 Data Provenance / data/raw/DATA_PROVENANCE.md；raw 默认不入库）
# 3) 一键从 raw 重建全部 CSV/JSON/图表（seed 固定）
.venv\Scripts\python scripts/run_pipeline.py
# 4) 跑全部单元 + 回归 + 端到端测试（无 skip）
.venv\Scripts\python -m pytest
# 5) 重新生成本 README
.venv\Scripts\python -m udacity_ab.build_readme
# 6) 启动交互看板
.venv\Scripts\streamlit run app/streamlit_app.py
```
- 回归保障：`tests/test_regression_against_json.py` 断言 src 复现与已提交 JSON 一致（确定性结果 1e-12、MC 结果紧容差）；`tests/test_pipeline_end_to_end.py` 在临时目录从 raw 全量重跑并逐字段比对。
- 随机种子：bootstrap/permutation seed=20260831，B=10,000/10,000。

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
| **Continue Experiment（继续实验补样）** | 机制方向成立但因 underpowered 无法确立非劣效，补样到 80% 功效后重判 | **满足触发条件**：补 Gross/Net 约 10.6/12.1 天累积 +14 天 lag |
| **Do Not Launch（不上线）** | 质量检查失败（SRM），或有充分证据证明 Net 劣效超出 δ | **不满足**：SRM 通过、Net 点估在 δ 内，无劣效证据，只是精度不足 |

**最终决策：Continue Experiment —— 补样至 80% 功效后重判 Net 非劣效。**
- 完整逻辑链：二维非劣效门未过 = 当前暂不【全量】上线（hold，非永久否决）；因 underpowered 属 inconclusive，Do-Not-Launch 在“无劣效证据”前提下同样不成立；四态触发条件唯一落在 Continue（补 Gross/Net 约 10.6/12.1 天累积 +14 天 lag 后重判）。
- 决策理由（机制方向）：Gross 点估下降、Pay/Enroll 点估上行，SRM/不变指标通过；唯一卡点是 Net 非劣效因功效不足无法确立，而补样量明确、成本低，补到 80% 功效即可让非劣效判定真正具备分辨力，避免在精度不足时做不可逆的全量决策。
- 排除 Full Launch：非劣效门未过，全量上线违背事前锁定的决策规则。
- 排除 Do Not Launch：当前没有“损害超出 δ”的证据，仅因不显著就否决会犯“把 underpowered 当证劣”的错误。
- Targeted/Conditional 仅作后备：仅当业务无法等待补样时，以可回滚的小流量灰度并同步采 Net；但现有聚合数据无法识别定向人群，灰度选择缺乏数据支撑，需补用户级字段。

---
*结果数字均可由 `scripts/run_pipeline.py` 复现。*
