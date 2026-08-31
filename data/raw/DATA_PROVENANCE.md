# 原始数据来源与核验记录（Data Provenance）

## 数据集
- 名称：Udacity A/B Testing 课程 Final Project Results（免费试听筛选实验，Control / Experiment 两张日粒度表）
- 官方位置：Udacity 课程提供的 Google Sheet「Final Project Results」
  - https://docs.google.com/spreadsheets/d/1uX6xnulothizT-MbIQJ_2jw3IJQ4CczMHmnoXyzdjNk/edit
- 字段：Date, Pageviews, Clicks, Enrollments, Payments

## 获取记录
- 首次获取：2026-08-31（Asia/Shanghai）。
- 来源：经 `curl` 从 GitHub 公开镜像取得数据（HTTP 200 校验）。
- 落盘来源（镜像 A）：https://github.com/jojoms711/Udacity_AB_Testing
  - data/Final_Project_Results_Control.csv
  - data/Final_Project_Results_Experiment.csv

## 交叉核验范围
- **实验组：双镜像逐行比对。** 与独立镜像 B（https://github.com/moggirain/A-B-Testing-for-Udacity 的 data/experiment_data_20190713.csv）逐行比对，37 行完全一致。
- **对照组：单源。** 未取得第二份数据副本做逐行比对；其正确性由以下 **5 个独立公开来源**披露的汇总值交叉验证（Control 345543 / 28378 / 3785 / 2033，Experiment 344660 / 28325 / 3423 / 1945；23 天 outcome 窗 Clicks 17293 / 17260）：
  1. jianru-shi 项目报告（明确列出全部总量）：https://jianru-shi.github.io/ABTest/ABTestFinalProject.pdf
  2. adalee2future 项目报告（明确列出全部总量）：http://adalee2future.github.io/udacity_data_analyst/AB_Test.pdf
  3. Rahul Saxena 项目报告（sanity 区间与派生结果一致）：https://rpalsaxena.github.io/projects/Rahul_UDACITY-AB_Testing.pdf
  4. zyellieyan/AB-Testing-Project（明确列出 PV 总量，派生 CI 一致）：https://github.com/zyellieyan/AB-Testing-Project
  5. YenLinWu/Data_Science_Marathon 解题 Notebook（自带数据副本，表头前 5 行与本数据一致，PV 总量与派生结果一致）：https://github.com/YenLinWu/Data_Science_Marathon
- 本项目复算结果与上述来源全部一致。

## 文件哈希（SHA-256，已设为只读）
| 文件 | SHA-256 |
|---|---|
| Final_Project_Results_Control.csv | 64E3D23E25449188D7E65391C9642D991865550EE77D13887248AF0F9224A86B |
| Final_Project_Results_Experiment.csv | 7D49095E7146BEAD42BABF9358DA435A9869389C4269230D76492CB33D755056 |

## 获取后核验结果（2026-08-31）
1. 两组均为 37 行 × 5 列；日期范围 2014-10-11 至 2014-11-16，逐日连续无缺；
   - 年份 2014 为推断值（原始 Date 无年份），已用"星期前缀与 2014 年历完全一致"做内部一致性验证，全部通过；
2. Enrollments / Payments：前 23 天（10/11–11/2）非空，后 14 天（11/3–11/16）为空，符合 14 天 outcome 观察窗截断的业务解释；
3. 两组日期完全对齐；
4. 汇总值（复算）：
   - 全 37 天流量窗：Control Pageviews 345,543 ｜ Clicks 28,378；Experiment Pageviews 344,660 ｜ Clicks 28,325（用于 SRM / invariant metrics）；
   - 23 天 outcome 窗：Control Clicks 17,293 ｜ Enrollments 3,785 ｜ Payments 2,033；Experiment Clicks 17,260 ｜ Enrollments 3,423 ｜ Payments 1,945（用于转化率分析）；
5. 数据形态确认：**日粒度聚合数据（非用户级）**，主分析按聚合数据路径执行。

## 许可证 / 使用条款
- 该数据为 Udacity 课程教学材料，公开用于教育/学习用途；未取得明确书面授权条款前按最保守口径处理：
  - **raw CSV 默认不进入公开 Git 仓库**（见根目录 .gitignore）；
  - 公开仓库仅提供下载说明与来源记录（见 scripts/download_data.py）；
  - 若后续确认官方许可口径，再决定是否放开。

## 备注
- 原始文件已设置 Windows 只读属性。
