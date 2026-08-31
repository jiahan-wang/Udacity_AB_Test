# -*- coding: utf-8 -*-
"""原始数据加载（只读，不修改 data/raw 下文件）。"""
from pathlib import Path

import pandas as pd

RAW_FILES = {
    "Control": "Final_Project_Results_Control.csv",
    "Experiment": "Final_Project_Results_Experiment.csv",
}


def load_raw(raw_dir: Path | str | None = None) -> dict[str, pd.DataFrame]:
    """返回 {'Control': df, 'Experiment': df} 原始 DataFrame（未做日期解析）。"""
    from .config import project_root
    raw_dir = Path(raw_dir) if raw_dir else project_root() / "data" / "raw"
    return {g: pd.read_csv(raw_dir / fname) for g, fname in RAW_FILES.items()}
