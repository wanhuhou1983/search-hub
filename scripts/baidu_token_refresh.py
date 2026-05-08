#!/usr/bin/env python3
"""
百度网盘 access_token 自动续期脚本

用法：
  python scripts/baidu_token_refresh.py                   # 刷新并打印新 token
  python scripts/baidu_token_refresh.py --write-config     # 刷新并写入 config.py

配合 WorkBuddy 自动化：
  设置每25天运行一次，自动刷新即将过期的 token
"""

import json
import os
import re
import sys
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.py"

# 从环境变量或 config.py 读取凭据
def read_config_value(key: str) -> str:
    val = os.environ.get(key, "")
    if val:
        return val
    if CONFIG_PATH.exists():
        text = CONFIG_PATH.read_text(encoding="utf-8")
        m = re.search(rf'^{key}\s*=\s*os\.environ\.get\(.*?,\s*"([^"]*)"\s*\)', text, re.M)
        if m:
            return m.group(1)
        m = re.search(rf'^{key}\s*=\s*"([^"]*)"', text, re.M)
        if m:
            return m.group(1)
    return ""


def write_config(key: str, value: str):
    """写入 config.py"""
    if not CONFIG_PATH.exists():
        print(f"❌ config.py 不存在: {CONFIG_PATH}")
        return False
    text = CONFIG_PATH.read_text(encoding="utf-8")
    # 更新 BAIDU_REFRESH_TOKEN 或 BAIDU_ACCESS_TOKEN
    pattern = rf'^{key}\s*=\s*os\.environ\.get\(".*?", ".*?"\)'
    replacement = f'{key} = os.environ.get("{key}", "{value}")'
    if re.search(pattern, text, re.M):
        text = re.sub(pattern, replacement, text, flags=re.M)
    else:
        pattern2 = rf'^{key}\s*=\s*".*?"'
        replacement2 = f'{key} = "{value}"'
        if re.search(pattern2, text, re.M):
            text = re.sub(pattern2, replacement2, text, flags=re.M)
        else:
            print(f"⚠️ 未找到 {key} 配置项")
            return False
    CONFIG_PATH.write_text(text, encoding="utf-8")
    return True


def refresh_token():
    refresh_token = read_config_value("BAIDU_REFRESH_TOKEN")
    app_key = read_config_value("BAIDU_APP_KEY")
    secret_key = read_config_value("BAIDU_SECRET_KEY")

    if not refresh_token:
        print("❌ BAIDU_REFRESH_TOKEN 未配置")
        sys.exit(1)

    # 用 Python requests 发送 POST
    import requests
    r = requests.post("https://openapi.baidu.com/oauth/2.0/token", data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": app_key,
        "client_secret": secret_key,
    })
    data = r.json()

    if "access_token" not in data:
        print(f"❌ 刷新失败: {json.dumps(data, ensure_ascii=False)}")
        sys.exit(1)

    return data


if __name__ == "__main__":
    write_config = "--write-config" in sys.argv
    data = refresh_token()

    new_at = data["access_token"]
    new_rt = data.get("refresh_token", "")

    if write_config:
        ok1 = write_config("BAIDU_ACCESS_TOKEN", new_at)
        ok2 = write_config("BAIDU_REFRESH_TOKEN", new_rt) if new_rt else True
        if ok1 and ok2:
            print(f"✅ 已更新 config.py")
            print(f"   access_token:  {new_at[:40]}...")
            print(f"   refresh_token: {new_rt[:40]}...")
            print(f"   有效期: {data.get('expires_in', '?')} 秒 (~30天)")
        else:
            print("⚠️ 部分写入失败")
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))

    # 也输出给环境变量
    print(f"\nexport BAIDU_ACCESS_TOKEN={new_at}")
    if new_rt:
        print(f"export BAIDU_REFRESH_TOKEN={new_rt}")
