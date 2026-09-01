# 部署与运行指南

环境要求：Python 3.11–3.13；依赖见 `requirements-core.txt`（直接依赖）或 `requirements.txt`（完整冻结）。

## 本地安装

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements-core.txt      # Windows；*nix 用 .venv/bin/pip
```

## 数据

原始 CSV 不随仓库分发（许可口径见 `data/raw/DATA_PROVENANCE.md`）。需要复现完整流程时：

```bash
.venv/Scripts/python scripts/download_data.py           # 下载并做 SHA-256 校验到 data/raw/
.venv/Scripts/python scripts/run_pipeline.py            # 从 raw 重建 data/processed 全部产物与图表
```

## 运行看板

```bash
.venv/Scripts/streamlit run app/streamlit_app.py
```

六个页面：数据概览 / 实验质量 / 核心效果 / 非劣效判断 / 成本收益 / 方法论与局限。δ 与成本滑块仅用于敏感性/情景分析，不改变正式结论。

## 测试

```bash
.venv/Scripts/python -m pytest -q
```

## 部署到 Streamlit Community Cloud

1. 先把仓库推到 GitHub；
2. share.streamlit.io → New app，选本仓库与 `main` 分支；
3. **Main file path** 填 `app/streamlit_app.py`；
4. Python 版本在 Advanced settings 选 3.11 或 3.12；
5. 云端按 `requirements.txt` 安装依赖；看板只读已入库的 `data/processed/*.json|csv` 与 `reports/figures/*.png`，无需 raw CSV、无需跑 pipeline；
6. 代码已用 `parents[1]` 把 `src` 加入路径，云端不依赖 PYTHONPATH。

## 更新与回滚

- 更新：本地提交后 `git push`，Streamlit Cloud 自动重新部署；
- 回滚：在 GitHub 回退到上一 commit，或 `git revert` 后重新推送。
