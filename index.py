"""
统一索引脚本
用法:
  python index.py                  # 索引全部网盘
  python index.py --source baidu    # 只索引指定源 (baidu/p115/quark)
  python index.py --source p115    # 只索引115
  python index.py --source quark    # 只索引夸克
"""

import argparse
import sys
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"
sys.path.insert(0, str(PROJECT_DIR))

from config import BAIDU_ACCESS_TOKEN, P115_COOKIE


def _get_quark_cookie():
    """读取夸克 cookie"""
    cookie_file = Path.home() / ".workbuddy" / "skills" / "quark-storage" / "quark_cookies.json"
    if not cookie_file.exists():
        # 另一个可能位置
        cookie_file = PROJECT_DIR / ".." / ".." / ".workbuddy" / "skills" / "quark-storage" / "quark_cookies.json"
    if not cookie_file.exists():
        print("[夸克] ❌ 未找到夸克 cookie 文件")
        return None
    import json
    with open(cookie_file) as f:
        data = json.load(f)
    return data.get("cookie", "")


def index_baidu():
    print("=" * 60, flush=True)
    print("📡 百度网盘索引", flush=True)
    from indexer.baidu_indexer import build_index
    build_index(BAIDU_ACCESS_TOKEN, DATA_DIR / "baidu.json")


def index_p115():
    print("=" * 60, flush=True)
    print("📡 115网盘索引（较慢，预计5-15分钟）", flush=True)
    from indexer.p115_indexer import build_index
    build_index(P115_COOKIE, DATA_DIR / "p115.json")


def index_quark():
    print("=" * 60, flush=True)
    print("📡 夸克网盘索引", flush=True)
    cookie = _get_quark_cookie()
    if not cookie:
        print("[夸克] ⏭ 跳过（无 cookie）", flush=True)
        return
    from indexer.quark_indexer import build_index
    build_index(cookie, DATA_DIR / "quark.json")


def main():
    parser = argparse.ArgumentParser(description="网盘全量索引工具")
    parser.add_argument("--source", "-s", default="all",
                        help="索引目标: baidu/p115/quark/all (默认全部)")
    args = parser.parse_args()

    start = time.time()

    src = args.source
    if src in ("all", "baidu"):
        index_baidu()
    if src in ("all", "p115"):
        index_p115()
    if src in ("all", "quark"):
        index_quark()

    elapsed = time.time() - start
    print("=" * 60, flush=True)
    print(f"✅ 全部完成！耗时 {elapsed:.0f} 秒", flush=True)
    print(f"   索引文件位于: {DATA_DIR}/", flush=True)


if __name__ == "__main__":
    main()
