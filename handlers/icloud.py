"""
iCloud Drive 搜索 - 通过 pyicloud SDK
"""

import os
import socket
import requests
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
from config import ICLOUD_ACCOUNT, ICLOUD_PASSWORD, ICLOUD_USERNAME, MAX_RESULTS_PER_SOURCE

_ICLOUD_COOKIE_DIR = str(Path.home() / ".workbuddy" / "icloud_cookies")


def _run_with_timeout(func, timeout=15):
    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(func)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            return None, "iCloud 连接超时"


def _get_api(timeout: int):
    try:
        from pyicloud import PyiCloudService
    except ImportError:
        return None, "pyicloud 未安装"

    if not ICLOUD_ACCOUNT or not ICLOUD_PASSWORD:
        return None, "iCloud 账号未配置"

    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)

    try:
        if ICLOUD_USERNAME:
            os.environ.setdefault("USERNAME", ICLOUD_USERNAME)
            os.environ.setdefault("USER", ICLOUD_USERNAME)
        api = PyiCloudService(ICLOUD_ACCOUNT, ICLOUD_PASSWORD,
                              cookie_directory=_ICLOUD_COOKIE_DIR)

        if api.requires_2fa:
            return None, "iCloud 需要两步验证"

        # 检查 iCloud Drive 是否可用
        if not api.data or not api.data.get("apps", {}).get("iclouddrive"):
            return None, "该账号未启用 iCloud Drive（或服务不可用）"

        return api, None
    except Exception as e:
        return None, str(e)[:100]
    finally:
        socket.setdefaulttimeout(old_timeout)


def search(q: str, timeout: int = 30):
    if not q.strip():
        return {"source": "icloud", "results": [], "total": 0}

    return {
        "source": "icloud",
        "error": "iCloud Drive 搜索暂不支持该账号（pyicloud 无法获取 Drive 认证 cookie），"
                 "可在设置页查看账号连接状态",
        "results": [],
    }
