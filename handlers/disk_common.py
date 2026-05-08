"""
网盘搜索通用模块 - 本地索引读取 + 下载功能
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def load_index(source: str):
    """读取本地索引文件，返回 files 列表或 None"""
    index_file = DATA_DIR / f"{source}.json"
    if not index_file.exists():
        return None
    try:
        with open(index_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("files", [])
    except Exception:
        return None


def search_local(files: list, q: str, max_results: int = 100):
    """在已加载的索引列表中搜索"""
    if not files:
        return []
    q_lower = q.lower()
    results = []
    for f in files:
        if q_lower in f["name"].lower():
            results.append(f)
            if len(results) >= max_results:
                break
    return results


# ========== 下载功能 ==========


def baidu_download_url(fs_id: str, access_token: str) -> str:
    """获取百度网盘文件下载直链（两步：filemetas 拿 path → download 拿直链）"""
    import requests
    r = requests.get(
        "https://pan.baidu.com/rest/2.0/xpan/file?method=filemetas",
        params={"access_token": access_token, "fsids": f"[{fs_id}]"},
        timeout=15,
    )
    if r.status_code != 200:
        return None
    data = r.json()
    items = data.get("info", [])
    if not items:
        return None
    file_path = items[0].get("path", "")
    if not file_path:
        return None

    r2 = requests.get(
        "https://pan.baidu.com/rest/2.0/xpan/file?method=download",
        params={"access_token": access_token, "path": file_path},
        timeout=15, allow_redirects=False,
    )
    if r2.status_code == 302:
        return r2.headers.get("Location", "")
    return None


def p115_download_url(cid: str, cookie_str: str) -> str:
    """获取115网盘文件下载直链"""
    from p115client import P115Client
    client = P115Client(cookie_str)
    try:
        url = client.download_url(cid, headers={"Cookie": cookie_str})
        return url
    except Exception:
        return None


def _read_quark_cookie() -> dict:
    """读取夸克 cookie 和初始化 client"""
    import sys
    sys.path.insert(0, r"C:\Users\linhu\.workbuddy\binaries\python\envs\default\Lib\site-packages")

    cookie_file = None
    for p in [
        Path.home() / ".workbuddy" / "skills" / "quark-storage" / "quark_cookies.json",
        Path(__file__).parent.parent.parent / ".workbuddy" / "skills" / "quark-storage" / "quark_cookies.json",
    ]:
        if p.exists():
            cookie_file = p
            break
    if not cookie_file:
        return None

    from quark_client import QuarkClient
    with open(cookie_file) as f:
        raw = json.load(f)
    cookie = raw.get("cookie", "")
    if not cookie:
        return None

    return {"cookie": cookie, "client": QuarkClient(cookies=cookie, auto_login=False)}


def quark_download_url(fid: str) -> str:
    """获取夸克网盘文件下载直链（浏览器打开可能需要登录）"""
    info = _read_quark_cookie()
    if not info:
        return None
    try:
        from quark_client.services.file_download_service import FileDownloadService
        svc = FileDownloadService(info["client"].api_client)
        url = svc.get_download_url(fid)
        return url if url and url.startswith("http") else None
    except Exception:
        return None
