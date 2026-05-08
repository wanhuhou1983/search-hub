"""
115网盘搜索 - 优先本地索引，回退轻量 API
"""

import time
from p115client import P115Client
from config import P115_COOKIE, MAX_RESULTS_PER_SOURCE
from handlers.disk_common import load_index, search_local

ROOT_FOLDERS = [
    ("2783096189510179553", "最近接收"),
    ("2566616380224789265", "手机相册"),
    ("159844195371266227", "云下载"),
    ("2783096190340651748", "欧美剧_45T"),
    ("2240909338279410738", "手机备份"),
    ("1896619827959692686", "世界数学奥林匹克解题大辞典(南开大学数学系) 全5卷"),
    ("1882445498506280614", "视频"),
    ("1469398062080773950", "每天听本书"),
    ("1421152633686118382", "看过的电影"),
    ("1376249784921804161", "书籍·杂志·论文·研报"),
    ("1376249411570027762", "CS技术相关"),
    ("1322455683529494089", "stockData"),
    ("1133703177607218176", "电影"),
    ("635810142797071851", "动画"),
    ("634591039491048792", "电视剧"),
    ("519722610041", "软件·驱动程序"),
]


def search(q: str, timeout: int = 60):
    if not q.strip():
        return {"source": "p115", "results": [], "total": 0}

    # 优先本地索引
    cached = load_index("p115")
    if cached is not None:
        results = search_local(cached, q, MAX_RESULTS_PER_SOURCE)
        return {
            "source": "p115",
            "results": results[:MAX_RESULTS_PER_SOURCE],
            "total": len(results),
            "cached": True,
        }

    # 回退：轻量 API 搜索（只搜根目录+第一层）
    try:
        client = P115Client(P115_COOKIE)
        q_lower = q.lower()
        results = []

        for cid, name in ROOT_FOLDERS:
            if q_lower in name.lower():
                results.append({
                    "name": name, "path": name,
                    "is_dir": True, "size": 0, "id": cid, "source": "p115",
                })
                if len(results) >= MAX_RESULTS_PER_SOURCE:
                    return {"source": "p115", "results": results, "total": len(results)}

        for root_cid, root_name in ROOT_FOLDERS:
            try:
                resp = client.request(
                    "https://webapi.115.com/files",
                    params={"cid": root_cid, "show_dir": 1, "offset": 0, "limit": 200, "aid": 1},
                )
            except Exception:
                continue
            if not resp.get("state"):
                continue
            for item in resp.get("data", []):
                name = item.get("n", "")
                if q_lower not in name.lower():
                    continue
                item_cid = str(item.get("cid", ""))
                results.append({
                    "name": name,
                    "path": f"{root_name}/{name}",
                    "is_dir": item.get("fc", 0) > 0,
                    "size": item.get("s") or item.get("p", 0),
                    "id": item_cid,
                    "source": "p115",
                })
                if len(results) >= MAX_RESULTS_PER_SOURCE:
                    return {"source": "p115", "results": results, "total": len(results)}
            time.sleep(0.1)

        return {"source": "p115", "results": results, "total": len(results)}

    except Exception as e:
        return {"source": "p115", "error": str(e), "results": []}
