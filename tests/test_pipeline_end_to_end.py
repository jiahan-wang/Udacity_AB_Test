# -*- coding: utf-8 -*-
"""一键复现端到端测试。

在临时根目录复制 raw + config，运行 run_all（raw->...->figures/tables），
再与仓库已提交的 7 个 JSON 逐字段比对（确定性结果 1e-12；MC 结果因共享 RNG 序列逐位一致）。
不修改仓库 canonical 产物；不 skip。
"""
import json
import math
import shutil
from pathlib import Path

import pytest

from udacity_ab.pipeline import run_all

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"

JSONS = ["design_precision", "quality_checks", "quality_report", "main_effects",
         "permutation_check", "ni_decision", "cost_benefit"]


def _flatten(o, pre=""):
    out = {}
    if isinstance(o, dict):
        for k, v in o.items():
            out.update(_flatten(v, f"{pre}.{k}"))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            out.update(_flatten(v, f"{pre}[{i}]"))
    else:
        out[pre] = o
    return out


@pytest.mark.slow
def test_pipeline_reproduces_committed_json(tmp_path):
    # 组装临时根：raw + config（pipeline 自建 processed/figures）
    shutil.copytree(ROOT / "data" / "raw", tmp_path / "data" / "raw")
    shutil.copytree(ROOT / "config", tmp_path / "config")
    run_all(tmp_path, verbose=False)

    for name in JSONS:
        new = json.loads((tmp_path / "data" / "processed" / f"{name}.json").read_text(encoding="utf-8"))
        old = json.loads((PROC / f"{name}.json").read_text(encoding="utf-8"))
        fn, fo = _flatten(new), _flatten(old)
        assert set(fn) == set(fo), f"{name}: 键结构不一致 {set(fn) ^ set(fo)}"
        for k in fn:
            x, y = fn[k], fo[k]
            if isinstance(x, float) or isinstance(y, float):
                assert math.isclose(float(x), float(y), rel_tol=1e-10, abs_tol=1e-12), (name, k, x, y)
            else:
                assert x == y, (name, k, x, y)

    # 图表全部生成
    fig_dir = tmp_path / "reports" / "figures"
    expected = ["fig_power_vs_effect.png", "fig_mde_vs_sample.png", "fig_pageviews_ts.png",
                "fig_ctp_ts.png", "fig_forest_effects.png", "fig_permutation_null.png",
                "fig_permutation_sensitivity.png", "fig_noninferiority.png",
                "fig_savings_grid.png", "fig_tornado.png", "fig_breakeven.png"]
    for f in expected:
        assert (fig_dir / f).exists() and (fig_dir / f).stat().st_size > 1000, f
