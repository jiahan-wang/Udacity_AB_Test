# 数据字典（Data Dictionary）

> 前期产出。所有比率字段均标注分母与分析窗口。

## 一、原始数据（data/raw，只读）

| 文件 | 粒度 | 行×列 | 说明 |
|---|---|---|---|
| Final_Project_Results_Control.csv | 日 | 37×5 | 对照组 |
| Final_Project_Results_Experiment.csv | 日 | 37×5 | 实验组（新增每周学习时长筛选） |

| 原始字段 | 类型 | 口径 |
|---|---|---|
| Date | 字符串（解析为 date） | 原始形如 "Sat, Oct 11"，无年份；按星期前缀核验为 **2014 年**，范围 2014-10-11 至 2014-11-16，共 37 天 |
| Pageviews | int | 当日看到课程概览页的 unique cookies 数（≈ Cookies，分流规模，发生在筛选之前） |
| Clicks | int | 当日点击 Start Free Trial 的 unique cookies 数（发生在筛选之前） |
| Enrollments | float（后 14 天缺失） | 当日完成免费试用注册的 user-id 数；仅前 23 天成熟 |
| Payments | float（后 14 天缺失） | 当日 enroll 且满 14 天仍留存付费的 user-id 数；**日期为 enroll 起始日**；仅前 23 天成熟 |

## 二、分析窗口（双窗口口径）

| 窗口 | 日期 | 天数 | 用途 |
|---|---|---|---|
| 流量窗 traffic window | 2014-10-11 → 2014-11-16 | 37 | SRM、invariant metrics（Pageviews/Clicks/CTP） |
| outcome 窗 | 2014-10-11 → 2014-11-02 | 23 | Gross / Net / PayPerEnrollment 等转化分析（分母 Clicks 也只取这 23 天） |
| 被排除 | 2014-11-03 → 2014-11-16 | 14 | Enrollments/Payments 因 14 天观察期未成熟，缺失，不参与转化分析 |

## 三、processed 产物

### 1) daily_long.csv（74 行 × 12 列；长格式，主分析表）
每天每组一行（37 天 × 2 组）。

| 字段 | 类型 | 口径/公式 | 有效窗口 |
|---|---|---|---|
| Date | date | 解析后的真实日期（2014） | 37d |
| Weekday | str | 星期三字母（Mon…Sun） | 37d |
| Group | str | Control / Experiment | — |
| Pageviews | int | 同原始 | 37d |
| Clicks | int | 同原始 | 37d |
| Enrollments | float | 同原始，后 14 天为空 | 23d 非空 |
| Payments | float | 同原始，后 14 天为空 | 23d 非空 |
| OutcomeComplete | bool | 该日 Enrollments 与 Payments 是否都成熟（True=属于 outcome 窗） | — |
| CTP | float | Clicks / Pageviews，**分母=当日 Pageviews** | 37d |
| GrossConversion | float | Enrollments / Clicks，**分母=当日 Clicks** | 仅 23d 有值 |
| NetConversion | float | Payments / Clicks，**分母=当日 Clicks** | 仅 23d 有值 |
| PayPerEnrollment | float | Payments / Enrollments，**分母=当日 Enrollments** | 仅 23d 有值 |

### 2) daily_wide.csv（37 行 × 21 列；宽格式）
- 每天一行；每个指标按 `Control_*` / `Experiment_*` 成对展开（Pageviews、Clicks、Enrollments、Payments、OutcomeComplete、CTP、GrossConversion、NetConversion、PayPerEnrollment、Weekday）。
- 用途：逐日组间对比、时间序列绘图。

### 3) pooled_summary.csv（2 行；双窗口 pooled 汇总，描述性）
| 字段 | 口径 |
|---|---|
| Group | 组 |
| Pageviews_37d / Clicks_37d | 37 天流量窗合计 |
| CTP_37d | ΣClicks / ΣPageviews（37d） |
| Outcome_days | outcome 窗天数（=23） |
| Clicks_23d / Enrollments_23d / Payments_23d | 23 天 outcome 窗合计（**转化率分母用 Clicks_23d**） |
| GrossConversion | ΣEnrollments / ΣClicks（23d，pooled，非日比率平均） |
| NetConversion | ΣPayments / ΣClicks（23d，pooled） |
| PayPerEnrollment | ΣPayments / ΣEnrollments（23d，pooled） |

### 4) window_sample_loss.csv（2 行；窗口截断的样本损失）
Clicks_37d、Clicks_outcome_23d、Clicks_excluded、Pct_excluded、Outcome_days、Excluded_days。

### 5) quality_report.json
数据质量体检的机器可读结果（结构、缺失、负值、漏斗单调、极端日标记、窗口与汇总），供单元测试与审计使用。

## 四、关键口径提醒（防止后续用错）
1. 转化率一律用 **pooled 合计相除**，不要对日比率取算术平均；
2. Gross/Net 的分母是 **23 天 outcome 窗内的 Clicks（17,293 / 17,260）**，不是全 37 天 Clicks（28,378 / 28,325）；
3. CTP 是不变指标，用全 37 天；
4. 后 14 天的空值是**观察窗未成熟**，不是数据丢失，不做插补、不填 0。
