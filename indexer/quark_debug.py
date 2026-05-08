#!/usr/bin/env python3
"""夸克网盘索引器 - 调试版"""
import sys, json, time, traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, r"C:\Users\linhu\.workbuddy\binaries\python\envs\default\Lib\site-packages")
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(r"C:\Users\linhu\WorkBuddy\2026-05-06-task-2\search-hub\data")
cookie_file = Path.home() / ".workbuddy" / "skills" / "quark-storage" / "quark_cookies.json"

with open(cookie_file) as f:
    data = json.load(f)
cookie = data.get("cookie", "")

from quark_client import QuarkClient

client = QuarkClient(cookies=cookie, auto_login=False)

print("step1: listing root...", flush=True)
resp = client.list_files("0", page=1, size=5)
print(f"step2: status={resp.get('status')}", flush=True)
print(f"step3: data={json.dumps(resp, ensure_ascii=False)[:500]}", flush=True)
