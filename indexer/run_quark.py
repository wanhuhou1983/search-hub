#!/usr/bin/env python3
"""夸克网盘索引器 - 全量扫描"""
import sys, json, time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, r"C:\Users\linhu\.workbuddy\binaries\python\envs\default\Lib\site-packages")

DATA_DIR = Path(r"C:\Users\linhu\WorkBuddy\2026-05-06-task-2\search-hub\data")
cookie_file = Path.home() / ".workbuddy" / "skills" / "quark-storage" / "quark_cookies.json"

with open(cookie_file) as f:
    data = json.load(f)
cookie = data.get("cookie", "")

from quark_client import QuarkClient
client = QuarkClient(cookies=cookie, auto_login=False)

all_files = []
visited = set()


def walk(fid, path, depth=0):
    if fid in visited:
        return
    visited.add(fid)
    page = 1
    while True:
        try:
            resp = client.list_files(fid, page=page, size=100)
        except Exception as e:
            return
        if resp.get("status") != 200:
            return
        d = resp.get("data")
        if not isinstance(d, dict):
            return
        items = d.get("list")
        if not items:
            return
        for item in items:
            name = item.get("file_name", "")
            item_fid = item.get("fid", "")
            is_dir = bool(item.get("dir", False) or item.get("file_type") == 0)
            full_path = f"{path}/{name}" if path else name
            all_files.append({
                "name": name, "path": full_path, "is_dir": is_dir,
                "size": item.get("size", 0), "id": item_fid, "source": "quark",
                "mtime": (item.get("l_updated_at", 0) // 1000) if item.get("l_updated_at") else 0,
            })
            if is_dir and name:
                time.sleep(0.1)
                walk(item_fid, full_path, depth + 1)
        page += 1
        if len(items) < 100:
            return


try:
    print("[夸克] 索引中...", flush=True)
    walk("0", "")
    index = {"source": "quark", "built_at": datetime.now().isoformat(), "total": len(all_files), "files": all_files}
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / "quark.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"[夸克] 完成: {len(all_files)} 条", flush=True)
except Exception as e:
    print(f"[夸克] 失败: {e}", flush=True)
