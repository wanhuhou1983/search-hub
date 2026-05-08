"""
115网盘搜索 - 调用 115 文件搜索 API
"""

import json
import urllib.request
from config import P115_COOKIE, MAX_RESULTS_PER_SOURCE

SEARCH_URL = "https://webapi.115.com/files/search?search_value={q}&aid=1&offset=0&limit=100"


def _api_search(q: str, max_results: int) -> list:
    """调用 115 官方搜索 API"""
    if not P115_COOKIE:
        return []
    url = SEARCH_URL.format(q=urllib.request.quote(q))
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Cookie": P115_COOKIE,
        "Origin": "https://115.com",
        "Referer": "https://115.com/",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
    except Exception:
        return []

    if not data.get("state"):
        return []

    results = []
    for item in data.get("data") or []:
        name = item.get("n", "")
        cid = str(item.get("cid", ""))
        pid = str(item.get("pid", ""))
        results.append({
            "name": name,
            "path": name,
            "is_dir": item.get("fc", 0) > 0,
            "size": item.get("s") or item.get("p", 0),
            "id": cid,
            "parent_id": pid,
            "source": "p115",
        })
        if len(results) >= max_results:
            break

    return results


def search(q: str, timeout: int = 60):
    if not q.strip():
        return {"source": "p115", "results": [], "total": 0}

    results = _api_search(q, MAX_RESULTS_PER_SOURCE)

    return {
        "source": "p115",
        "results": results,
        "total": len(results),
    }
