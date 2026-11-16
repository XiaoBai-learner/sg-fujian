"""参考引擎测试只在该测试树内加入 PoC 包路径，不污染正式应用。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
