"""
iCloud Drive 搜索 - 通过 pyicloud SDK
"""

import os
import socket
import requests
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
from config import ICLOUD_ACCOUNT, ICLOUD_PASSWORD, MAX_RESULTS_PER_SOURCE

# pyicloud 依赖 getpass.getuser()，sandbox 环境可能取不到用户名
# 确保 USERNAME 环境变量可用，同时指定 cookie 目录避免权限问题
_ICLOUD_COOKIE_DIR = str(Path.home() / ".workbuddy" / "icloud_cookies")


def _run_with_timeout(func, timeout=15):
    """在线程中运行函数，超时自动中断"""
    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(func)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            return None, "iCloud 连接超时，请检查网络"


def _get_api(timeout: int):
    """懒加载并初始化 PyiCloudService"""
    try:
        from pyicloud import PyiCloudService
    except ImportError:
        return None, "pyicloud 未安装，请 pip install pyicloud"

    if not ICLOUD_ACCOUNT or not ICLOUD_PASSWORD:
        return None, "iCloud 账号或密码未配置"

    # 设置 socket 全局超时（防止 hang 住）
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)

    try:
        os.environ.setdefault("USERNAME", "linhu")
        os.environ.setdefault("USER", "linhu")
        api = PyiCloudService(
            ICLOUD_ACCOUNT, ICLOUD_PASSWORD,
            cookie_directory=_ICLOUD_COOKIE_DIR,
        )

        if api.requires_2fa:
            return None, "iCloud 需要两步验证，请在浏览器登录 Apple ID 后重新授权"

        return api, None
    except requests.exceptions.ConnectionError:
        return None, "iCloud 服务不可达（网络连接失败），请检查网络"
    except Exception as e:
        emsg = str(e)
        if "Invalid email/password" in emsg:
            return None, "iCloud 账号或密码错误"
        if "Authentication required" in emsg:
            return None, "iCloud 认证失败，请检查密码或网络连接"
        return None, f"iCloud 登录失败: {emsg[:200]}"
    finally:
        socket.setdefaulttimeout(old_timeout)


def _walk_dir(node, path: str = "", max_results: int = 100) -> list:
    """递归遍历 iCloud Drive 目录"""
    results = []
    try:
        items = node.dir() if hasattr(node, "dir") else node
    except Exception:
        return results

    for item in items:
        name = item.name if hasattr(item, "name") else str(item)
        item_path = f"{path}/{name}" if path else name

        is_dir = item.type == "folder" if hasattr(item, "type") else False

        if is_dir:
            try:
                results.extend(_walk_dir(item, item_path, max_results - len(results)))
            except Exception:
                pass
        else:
            size = item.size if hasattr(item, "size") else 0
            item_id = getattr(item, "id", "") or getattr(item, "driverId", "") or name
            results.append({
                "name": name,
                "path": item_path,
                "is_dir": False,
                "size": size,
                "id": str(item_id),
                "source": "icloud",
            })

        if len(results) >= max_results:
            break

    return results


def search(q: str, timeout: int = 30):
    if not q.strip():
        return {"source": "icloud", "results": [], "total": 0}

    api, err = _get_api(timeout)
    if err:
        return {"source": "icloud", "error": err, "results": []}

    # 搜索阶段也加 socket 超时
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
        drive = api.drive
        q_lower = q.lower()
        results = []

        def _do_search():
            try:
                sr = drive.search(q)
                return list(sr)
            except (AttributeError, TypeError):
                return None

        search_items = _run_with_timeout(_do_search, timeout)
        if isinstance(search_items, tuple) and search_items[0] is None:
            return {"source": "icloud", "error": "iCloud 搜索超时", "results": []}

        if search_items is None:
            # search 方法不可用，回退到递归遍历
            all_items = _run_with_timeout(
                lambda: _walk_dir(drive, max_results=MAX_RESULTS_PER_SOURCE),
                timeout,
            )
            if isinstance(all_items, tuple) and all_items[0] is None:
                return {"source": "icloud", "error": "iCloud 遍历超时", "results": []}
            results = [r for r in (all_items or []) if q_lower in r["name"].lower()]
        else:
            for item in search_items:
                name = item.name if hasattr(item, "name") else str(item)
                is_dir = item.type == "folder" if hasattr(item, "type") else False
                size = item.size if hasattr(item, "size") else 0
                item_id = getattr(item, "id", "") or name
                results.append({
                    "name": name,
                    "path": name,
                    "is_dir": is_dir,
                    "size": size,
                    "id": str(item_id),
                    "source": "icloud",
                })
                if len(results) >= MAX_RESULTS_PER_SOURCE:
                    break

        return {"source": "icloud", "results": results, "total": len(results)}

    except requests.exceptions.ConnectionError:
        return {"source": "icloud", "error": "iCloud 服务不可达", "results": []}
    except Exception as e:
        return {"source": "icloud", "error": str(e)[:200], "results": []}
    finally:
        socket.setdefaulttimeout(old_timeout)
