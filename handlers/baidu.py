"""
百度网盘搜索 - 优先本地索引，回退 API
"""

import requests
from config import BAIDU_ACCESS_TOKEN, MAX_RESULTS_PER_SOURCE
from handlers.disk_common import load_index, search_local

API_BASE = "https://pan.baidu.com/rest/2.0/xpan/file"


def _load_or_fallback():
    """尝试加载本地索引"""
    files = load_index("baidu")
    return files  # None 表示需要 API 回退


def search(q: str, timeout: int = 10):
    if not q.strip():
        return {"source": "baidu", "results": [], "total": 0}

    # 优先本地索引
    cached = _load_or_fallback()
    if cached is not None:
        results = search_local(cached, q, MAX_RESULTS_PER_SOURCE)
        if results:  # 有结果才用缓存
            return {
                "source": "baidu",
                "results": results[:MAX_RESULTS_PER_SOURCE],
                "total": len(results),
                "cached": True,
            }

    # 回退：实时 API
    try:
        r = requests.get(
            f"{API_BASE}?method=search",
            params={
                "access_token": BAIDU_ACCESS_TOKEN,
                "key": q,
                "num": MAX_RESULTS_PER_SOURCE,
                "path": "/",
                "recursion": 1,
            },
            timeout=timeout,
        )
        if r.status_code != 200:
            return {"source": "baidu", "error": f"HTTP {r.status_code}", "results": []}

        data = r.json()
        if data.get("errno") != 0:
            return {"source": "baidu", "error": f"errno={data.get('errno')}", "results": []}

        items = []
        for f in data.get("list", []):
            items.append({
                "name": f.get("server_filename", ""),
                "path": f.get("path", ""),
                "is_dir": f.get("isdir") == 1,
                "size": f.get("size", 0),
                "id": str(f.get("fs_id", "")),
                "source": "baidu",
                "mtime": f.get("server_mtime", 0),
            })

        return {"source": "baidu", "results": items, "total": len(items)}

    except requests.Timeout:
        return {"source": "baidu", "error": "超时", "results": []}
    except Exception as e:
        return {"source": "baidu", "error": str(e), "results": []}
