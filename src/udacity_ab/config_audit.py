# -*- coding: utf-8 -*-
"""配置集中化核对。

- 校验 [locked] / [exploratory] / [business_assumptions] 三区结构与必备键；
- 扫描 src/udacity_ab 源码，锁定参数（α/MDE/δ/power）应统一由 config 提供
  （统计函数允许保留约定默认值，但 pipeline 必须由 config 注入）；
- 业务假设必须带 Assumption 标签。
"""
import re
from pathlib import Path

LOCKED_KEYS = ["alpha_two_sided", "ni_alpha_one_sided", "target_power",
               "mde_gross", "mde_net", "ni_delta_net", "windows"]
EXPLORATORY_KEYS = ["random_seed", "bootstrap_b", "permutation_b"]
# 锁定值字面量（白名单文件除外）
LOCKED_LITERALS = {"0.0075": "mde_net/ni_delta", "0.20625": "baseline p_gross",
                   "0.1093125": "baseline p_net"}
WHITELIST = {"config_audit.py", "config.py"}


def audit_config(cfg: dict) -> list[str]:
    """返回问题列表；空列表表示通过。"""
    problems: list[str] = []
    for k in LOCKED_KEYS:
        if k not in cfg.get("locked", {}):
            problems.append(f"[locked] 缺少必备键 {k}")
    for k in EXPLORATORY_KEYS:
        if k not in cfg.get("exploratory", {}):
            problems.append(f"[exploratory] 缺少必备键 {k}")
    ba = cfg.get("business_assumptions", {})
    if "Assumption" not in ba.get("label", ""):
        problems.append("business_assumptions.label 必须包含 Assumption 标注")
    # 锁定值一致性
    if cfg["locked"]["mde_net"] != cfg["locked"]["ni_delta_net"]:
        problems.append("mde_net 与 ni_delta_net 应同为事前锁定 0.0075")
    return problems


def scan_hardcoded_literals(pkg_dir: Path | None = None) -> list[str]:
    pkg_dir = pkg_dir or Path(__file__).parent
    hits = []
    for py in pkg_dir.glob("*.py"):
        if py.name in WHITELIST:
            continue
        text = py.read_text(encoding="utf-8")
        for lit, meaning in LOCKED_LITERALS.items():
            if re.search(rf"(?<![\d.]){re.escape(lit)}(?![\d])", text):
                hits.append(f"{py.name}: 硬编码锁定值 {lit}（{meaning}），应从 config 注入")
    return hits


def run_audit(cfg: dict) -> tuple[bool, list[str]]:
    problems = audit_config(cfg)
    problems += scan_hardcoded_literals()
    return (len(problems) == 0, problems)
