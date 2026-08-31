# -*- coding: utf-8 -*-
"""原始数据下载与 SHA-256 校验（raw 不入库，需自行下载）。

用法：python scripts/download_data.py
仅用标准库；下载后逐字节校验，哈希不符则非零退出并提示。
"""
import hashlib
import sys
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/jojoms711/Udacity_AB_Testing/master/data"
FILES = {
    "Final_Project_Results_Control.csv": (
        f"{BASE}/Final_Project_Results_Control.csv",
        "64e3d23e25449188d7e65391c9642d991865550ee77d13887248af0f9224a86b"),
    "Final_Project_Results_Experiment.csv": (
        f"{BASE}/Final_Project_Results_Experiment.csv",
        "7d49095e7146bead42babf9358da435a9869389c4269230d76492cb33d755056"),
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main(root: Path) -> int:
    raw_dir = root / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    ok = True
    for fname, (url, expected) in FILES.items():
        dst = raw_dir / fname
        if dst.exists() and sha256_bytes(dst.read_bytes()) == expected:
            print(f"[skip] {fname} already present and SHA-256 matches.")
            continue
        print(f"[download] {url}")
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                data = resp.read()
        except Exception as exc:  # noqa: BLE001
            print(f"  FAILED: {exc}")
            ok = False
            continue
        got = sha256_bytes(data)
        if got != expected:
            print(f"  SHA-256 MISMATCH: expected {expected}, got {got} -> not saved")
            ok = False
            continue
        dst.write_bytes(data)
        try:
            dst.chmod(0o444)  # 只读，防止误改原始数据
        except OSError:
            pass
        print(f"  saved {fname} ({len(data):,} bytes), SHA-256 OK")
    return 0 if ok else 1


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]
    sys.exit(main(project_root))
