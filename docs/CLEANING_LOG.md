# 清洗日志（Cleaning Log）

> 原则：原始只读、所有处理可复现（见 notebooks/01_data_cleaning.ipynb）、不做无依据的删除/插补。

## 1. 加载与解析
- 读取两个只读 CSV（SHA-256 见 data/raw/DATA_PROVENANCE.md，与 quality_report.json 内一致）。
- Date：原始 "Weekday, Mon DD" 无年份 → 结合"星期前缀 × 2014 年历 100% 吻合"验证，按 **2014** 解析为真实日期；新增 Weekday。
- 新增组标签 Group（Control/Experiment），纵向拼接为 74 行长表。

## 2. 数据质量体检结果
| 检查项 | 结果 |
|---|---|
| 每组行数 | 各 37 行 |
| (Date, Group) 重复 | 0 |
| 日期连续性 | 两组均 2014-10-11→11-16 逐日连续，无缺口（断言通过） |
| 缺失 | Pageviews/Clicks 0 缺失；Enrollments/Payments 各缺 14 天×2 组=28 个，且都集中在最后 14 天（11/03–11/16），为观察窗未成熟 |
| 负值 | 四个计数字段负值数均为 0 |
| 漏斗单调（outcome 日 PV≥Clicks≥Enrollments≥Payments） | 违例 0 |
| 极端波动日（组内 \|z\|≥2.5，仅标记不删除） | ① Control 10/18（周六）Pageviews=7434，z=−2.57，周末低流量季节性，两组同形态；② 10/24 两组 CTP 同向下探：Control 0.07134（z=−3.34）、Experiment 0.07413（z=−2.59），属两组共同外部因素，**保留全部数据**，留待分流质量检查复核 |

## 3. 观察窗截断处理
- 判定规则：Enrollments 与 Payments 均非空的日期记 OutcomeComplete=True。
- 流量窗：37 天全部用于 SRM/invariant metrics。
- outcome 窗：前 23 天（10/11–11/02）用于转化分析，转化率分母只取这 23 天 Clicks。
- **被排除日期（14 天，不插补、不填 0）**：2014-11-03、11-04、11-05、11-06、11-07、11-08、11-09、11-10、11-11、11-12、11-13、11-14、11-15、11-16。
- 样本损失量化：Control 点击 28,378 → outcome 窗 17,293，排除 11,085（39.06%）；Experiment 28,325 → 17,260，排除 11,065（39.06%）。该损失将在精度分析中量化。

## 4. 派生与落盘
- 派生 CTP、GrossConversion、NetConversion、PayPerEnrollment（公式与分母见 DATA_DICTIONARY.md）。
- 产出 daily_long.csv（74×12）、daily_wide.csv（37×21）、pooled_summary.csv、window_sample_loss.csv、quality_report.json。
- 汇总方式：pooled（合计相除），未对日比率取平均。

## 5. 描述性结果
| 指标 | Control | Experiment | 差值(E−C) |
|---|---|---|---|
| CTP（37d） | 0.082126 | 0.082182 | +0.000056 |
| Gross Conversion（23d） | 0.218875 | 0.198320 | −0.020555（−2.06pp） |
| Net Conversion（23d） | 0.117562 | 0.112688 | −0.004874（−0.49pp） |
| Payments/Enrollment（23d） | 0.537120 | 0.568215 | +0.031095（+3.11pp） |

显著性、置信区间、非劣效判定不在本步，留待后续推断分析进行。

## 6. 自查记录
- Notebook 8 个代码单元从头执行 0 错误；
- 落盘后独立回读：long 74 行（每组 37）、wide 37 行；
- 从 long 独立重算 pooled 三率，与 pooled_summary.csv 完全一致；
- 总量经数据核验、与 5 个公开来源一致（PV 345543/344660；outcome Clicks 17293/17260；Enr 3785/3423；Pay 2033/1945）。
