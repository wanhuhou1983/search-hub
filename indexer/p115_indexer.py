"""
115网盘索引器 - 全量递归扫描
注意：115 API 有限流，扫描较慢（可能10-20分钟）
"""

import time
import json
from datetime import datetime
from pathlib import Path

# 已知根目录
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


def _list_dir(client, cid, offset=0, limit=200):
    try:
        resp = client.request(
            "https://webapi.115.com/files",
            params={"cid": cid, "show_dir": 1, "offset": offset, "limit": limit, "aid": 1},
        )
    except Exception:
        return [], 0
    if not resp.get("state"):
        return [], 0
    return resp.get("data", []), resp.get("count", 0)


def _walk(client, cid, path, visited, files, depth=0, max_depth=3, max_total=2000):
    """递归遍历（受限深度和总数）"""
    if cid in visited or depth > max_depth or len(files) >= max_total:
        return
    visited.add(cid)

    items, total = _list_dir(client, cid)
    if not items:
        return

    for item in items:
        if len(files) >= max_total:
            return
        name = item.get("n", "")
        item_cid = str(item.get("cid", ""))
        full_path = f"{path}/{name}" if path else name

        # 检查是否为目录
        time.sleep(0.1)
        sub_items, sub_total = _list_dir(client, item_cid, 0, 1)
        is_dir = sub_total > 0

        files.append({
            "name": name,
            "path": full_path,
            "is_dir": is_dir,
            "size": item.get("s") or item.get("p", 0),
            "id": item_cid,
            "source": "p115",
            "mtime": item.get("te") or item.get("t", 0),
        })

        if is_dir:
            _walk(client, item_cid, full_path, visited, files, depth + 1)


def build_index(cookie_str: str, output_path: Path) -> dict:
    from p115client import P115Client

    print("[115] 开始全量扫描，预计 5-15 分钟...", flush=True)
    client = P115Client(cookie_str)
    all_files = []

    for root_cid, root_name in ROOT_FOLDERS:
        print(f"[115]  扫描目录: {root_name}...", flush=True)
        visited = set()
        visited.add("0")  # 忽略根
        _walk(client, root_cid, root_name, visited, all_files, 0, 3, 2000)
        print(f"[115]  累计 {len(all_files)} 条", flush=True)
        if len(all_files) >= 2000:
            break

    index = {
        "source": "p115",
        "built_at": datetime.now().isoformat(),
        "total": len(all_files),
        "files": all_files,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"[115] 完成：{len(all_files)} 个文件/文件夹，已保存到 {output_path}", flush=True)
    return index
