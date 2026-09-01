# -*- coding: utf-8 -*-
"""README 一致性检查：README 每个关键数字可回指 JSON，且与模板渲染保持同步。

- 用当前 JSON/config 重新渲染 README，必须与已提交 README.md 完全一致（防止数字陈旧）；
- 关键数字字符串必须出现（来自 JSON）；
- 图中不残留硬编码的 δ/下界字面量。
"""
from pathlib import Path

import pytest

from udacity_ab.build_readme import build, project_root

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def text():
    return build(ROOT)


def test_committed_readme_is_fresh(text):
    committed = (ROOT / "README.md").read_text(encoding="utf-8")
    assert text == committed, "README.md 与 JSON 渲染结果不一致，请重跑 python -m udacity_ab.build_readme"


@pytest.mark.parametrize("token", [
    "-4.7018", "0.1558", "-1.160pp", "0.7648", "0.2222",      # Z/p/NI
    "354.8", "2,661", "11.86", "31.63",                       # cost-benefit
    "0.6399", "0.6212", "1.206pp", "0.923pp", "10.6/12.1",    # precision
    "0.1354", "0.5874", "3.14/2.54",                          # permutation
    "345,543", "344,660", "28,378", "28,325", "17,293", "17,260", "3,785", "3,423", "2,033", "1,945",
    "50.6",                                                    # CUPED demo
])
def test_key_numbers_present(text, token):
    assert token in text, f"README 缺少应来自 JSON 的数字 {token}"


def test_no_hardcoded_delta_in_figures():
    src = (ROOT / "src" / "udacity_ab" / "figures.py").read_text(encoding="utf-8")
    assert "0.75pp" not in src and "-1.16pp" not in src, "图中仍有硬编码 δ/下界字面量"
