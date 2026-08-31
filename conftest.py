"""pytest 全局：把 src 加入导入路径（无需 editable install）。"""
import sys
from pathlib import Path

SRC = Path(__file__).parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
