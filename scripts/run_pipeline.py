# -*- coding: utf-8 -*-
"""一键复现入口。

新环境：
    python -m venv .venv
    .venv\\Scripts\\pip install -r requirements-core.txt
    .venv\\Scripts\\python scripts/run_pipeline.py
即从 data/raw 重建 data/processed 全部 CSV/JSON 与 reports/figures 全部图表（seed 固定）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from udacity_ab.pipeline import run_all  # noqa: E402

if __name__ == "__main__":
    run_all(Path(__file__).resolve().parents[1])
