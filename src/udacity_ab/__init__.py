"""Udacity free-trial screener A/B test —— 模块化主分析代码。

模块划分（按分析流程）：
- data_loader      原始 CSV 读取
- cleaning         日期解析、窗口标记、质检、长/宽表与 pooled 汇总
- metrics          比率指标、双样本比例 Z 检验、Delta Method、day-cluster bootstrap
- design           样本量/功效/可检测 MDE
- srm              SRM 卡方/精确二项、CTP 不变指标、逐日配对诊断
- inference        置换鲁棒性检查（aggregate-data，非 AA Test）
- noninferiority   Net 非劣效判定
- cost_benefit     筛除规模/情景/break-even
- visualization    统一视觉规范
- pipeline         一键复现入口

方法论扩展（CUPED/HTE/零效应模拟）独立目录在 notebooks/07 + methodology_demo/，不进入本包。
"""

__version__ = "1.0.0"
