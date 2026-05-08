"""
百度网盘索引器 - 递归全量扫描
"""

import requests
import json
from datetime import datetime
from pathlib import Path

API_BASE = "https://pan.baidu.com/rest/2.0/xpan/file"

def build_index(access_token: str, output_path: Path) -> dict:
    print("[百度] 正在全量扫描...", flush=True)
    base_url = f"{API_BASE}?method=list"
    all_files = []
    start_page = 0
    limit = 2000

    while True:
        r = requests.get(base_url, params={
            "access_token": access_token,
            "dir": "/",
            "recursion": 1,
            "num": limit,
            "start": start_page,
        }, timeout=60)
        if r.status_code != 200:
            raise Exception(f"HTTP {r.status_code}")
        data = r.json()
        if data.get("errno") != 0:
            raise Exception(f"errno={data.get('errno')}: {data.get('errmsg', '')}")

        items = data.get("list", [])
        if not items:
            break

        for f in items:
            all_files.append({
                "name": f.get("server_filename", ""),
                "path": f.get("path", ""),
                "is_dir": f.get("isdir") == 1,
                "size": f.get("size", 0),
                "id": str(f.get("fs_id", "")),
                "source": "baidu",
                "mtime": f.get("server_mtime", 0),
            })

        if len(items) < limit:
            break
        start_page += limit
        print(f"[百度]  已获取 {len(all_files)} 条...", flush=True)

    index = {
        "source": "baidu",
        "built_at": datetime.now().isoformat(),
        "total": len(all_files),
        "files": all_files,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"[百度] 完成：{len(all_files)} 个文件/文件夹，已保存到 {output_path}", flush=True)
    return index
