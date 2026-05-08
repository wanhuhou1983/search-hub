"""
夸克网盘索引器 - 全量递归扫描
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# 确保 quark_client 可导入
SITE_PACKAGES = Path(r"C:\Users\linhu\.workbuddy\binaries\python\envs\default\Lib\site-packages")
if str(SITE_PACKAGES) not in sys.path:
    sys.path.insert(0, str(SITE_PACKAGES))


def _list_dir(client, fid, page=1, size=200):
    try:
        resp = client.list_files(fid, page=page, size=size)
        if resp.get("status") != 200:
            return [], 0
        data = resp.get("data", {})
        files = data.get("list", [])
        total = data.get("total", 0) or len(files)
        return files, total
    except Exception:
        return [], 0


def _walk(client, fid, path, visited, files, depth=0):
    if fid in visited:
        return
    visited.add(fid)

    page = 1
    while True:
        items, total = _list_dir(client, fid, page, 200)
        if not items:
            break

        for item in items:
            name = item.get("file_name", "")
            item_fid = item.get("fid", "")
            is_dir = item.get("dir", False) or item.get("file_type") == 0
            full_path = f"{path}/{name}" if path else name

            files.append({
                "name": name,
                "path": full_path,
                "is_dir": is_dir,
                "size": item.get("size", 0),
                "id": item_fid,
                "source": "quark",
                "mtime": item.get("l_updated_at", 0) // 1000 if item.get("l_updated_at") else 0,
            })

            if is_dir:
                time.sleep(0.1)
                _walk(client, item_fid, full_path, visited, files, depth + 1)

        page += 1
        if len(items) < 200:
            break


def build_index(cookie_str: str, output_path: Path) -> dict:
    from quark_client import QuarkClient

    print("[夸克] 开始全量扫描...", flush=True)
    client = QuarkClient(cookies=cookie_str, auto_login=False)
    all_files = []
    visited = set()

    _walk(client, "0", "", visited, all_files)

    index = {
        "source": "quark",
        "built_at": datetime.now().isoformat(),
        "total": len(all_files),
        "files": all_files,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"[夸克] 完成：{len(all_files)} 个文件/文件夹，已保存到 {output_path}", flush=True)
    return index
