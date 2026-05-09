"""
夸克网盘搜索 - 优先本地索引，回退 API
"""

import json
import os
import sys
from config import MAX_RESULTS_PER_SOURCE, QUARK_EXTRA_SITE_PACKAGES
from handlers.disk_common import load_index, search_local

if QUARK_EXTRA_SITE_PACKAGES and QUARK_EXTRA_SITE_PACKAGES not in sys.path:
    sys.path.insert(0, QUARK_EXTRA_SITE_PACKAGES)


def _get_cookie():
    cookie_file = os.path.join(
        os.path.expanduser("~"),
        ".workbuddy", "skills", "quark-storage", "quark_cookies.json"
    )
    if not os.path.exists(cookie_file):
        return None
    with open(cookie_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("cookie", "")


def search(q: str, timeout: int = 10):
    if not q.strip():
        return {"source": "quark", "results": [], "total": 0}

    # 优先本地索引
    cached = load_index("quark")
    if cached is not None:
        results = search_local(cached, q, MAX_RESULTS_PER_SOURCE)
        return {
            "source": "quark",
            "results": results[:MAX_RESULTS_PER_SOURCE],
            "total": len(results),
            "cached": True,
        }

    # 回退：实时 API
    try:
        from quark_client import QuarkClient

        cookie = _get_cookie()
        if not cookie:
            return {"source": "quark", "error": "未找到夸克cookie", "results": []}

        client = QuarkClient(cookies=cookie, auto_login=False)
        resp = client.search_files(q)
        if resp.get("status") != 200:
            return {"source": "quark", "error": resp.get("message", "搜索失败"), "results": []}

        items = []
        for f in resp.get("data", {}).get("list", []):
            is_dir = f.get("file_type") == 0 or f.get("dir", False)
            items.append({
                "name": f.get("file_name", ""),
                "path": f.get("file_name", ""),
                "is_dir": is_dir,
                "size": f.get("size", 0),
                "id": f.get("fid", ""),
                "source": "quark",
            })

        return {"source": "quark", "results": items, "total": len(items)}

    except ImportError:
        return {"source": "quark", "error": "quark_client 未安装", "results": []}
    except Exception as e:
        return {"source": "quark", "error": str(e), "results": []}
