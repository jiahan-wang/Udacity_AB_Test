# -*- coding: utf-8 -*-
"""配置集中化：唯一从 config/analysis_config.toml 读取参数的入口。"""
import tomllib
from pathlib import Path


def project_root() -> Path:
    """项目根目录（src/udacity_ab/config.py 向上三级）。"""
    return Path(__file__).resolve().parents[2]


def load_config(path: Path | None = None) -> dict:
    """读取集中配置；返回完整 dict。locked=事前锁定，exploratory/business_assumptions=敏感性。"""
    cfg_path = path or (project_root() / "config" / "analysis_config.toml")
    with open(cfg_path, "rb") as f:
        return tomllib.load(f)
