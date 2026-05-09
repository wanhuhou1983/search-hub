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
    from config import QUARK_EXTRA_SITE_PACKAGES
    if QUARK_EXTRA_SITE_PACKAGES:
        sys.path.insert(0, QUARK_EXTRA_SITE_PACKAGES)

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


# ========== 115 网盘视频在线播放 ==========


def p115_video_play_url(pickcode: str, cookie_str: str, definition: int = 0) -> dict:
    """获取115网盘视频的播放链接

    115 CDN有防盗链，所有URL需要通过后端代理访问。
    优先使用 download_url（mp4直链），回退到 m3u8。

    Args:
        pickcode: 视频文件的 pickcode
        cookie_str: 115 cookie 字符串
        definition: 画质 (0=全部, 1=标清, 3=超清, 4=1080P, 5=4K, 100=原画)

    Returns:
        dict: {url: str, title: str, qualities: list} 或 {error: str}
    """
    try:
        from p115client import P115Client
        client = P115Client(cookie_str)
        title = ""
        qualities = []

        # 策略1：通过 download_url 获取 mp4 直链（最可靠，浏览器原生播放）
        try:
            dl_url = str(client.download_url(pickcode))
            if dl_url and dl_url.startswith("http"):
                qualities.append({"label": "原画直链", "url": dl_url, "key": "direct"})
        except Exception:
            pass

        # 策略2：通过 fs_video 获取视频信息和额外链接
        try:
            video_info = client.fs_video({"pickcode": pickcode})
            if isinstance(video_info, dict):
                title = video_info.get("file_name", "")
                # origin_file_url 是另一个直链
                origin_url = video_info.get("origin_file_url", "")
                if origin_url and origin_url.startswith("http"):
                    if not qualities:
                        qualities.append({"label": "原画", "url": origin_url, "key": "origin"})
        except Exception:
            pass

        # 策略3：通过 fs_video_m3u8 获取 m3u8（最后备选，需要代理m3u8+ts片段）
        if not qualities:
            try:
                m3u8_data = client.fs_video_m3u8(pickcode=pickcode, definition=definition)
                if m3u8_data:
                    import re
                    if isinstance(m3u8_data, bytes):
                        m3u8_text = m3u8_data.decode("utf-8", errors="ignore")
                    else:
                        m3u8_text = str(m3u8_data)

                    stream_urls = re.findall(r'(https?://[^\s]+\.m3u8[^\s]*)', m3u8_text)
                    if stream_urls:
                        for i, u in enumerate(stream_urls):
                            label = "原画" if i == 0 else f"流{i+1}"
                            qualities.append({"label": label, "url": u, "key": f"m3u8_{i}"})
                    elif m3u8_text.strip().startswith("#EXTM3U"):
                        base_url = f"https://115.com/api/video/m3u8/{pickcode}.m3u8"
                        qualities.append({"label": "自动", "url": base_url, "key": "m3u8_auto"})
            except Exception:
                pass

        if not qualities:
            return {"error": "未找到可用的播放链接，文件可能已损坏或未上传完成"}

        best = qualities[0]
        return {
            "url": best["url"],
            "qualities": qualities,
            "title": title,
        }
    except Exception as e:
        return {"error": f"获取播放链接失败: {e}"}
