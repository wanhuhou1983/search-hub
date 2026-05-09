"""
MissAV 视频解析与下载 - 支持本地 + VPS 中转
"""

import asyncio
import json
import logging
import os
import re
from pathlib import Path

logger = logging.getLogger("search-hub.missav")

SKILL_DIR = Path.home() / ".workbuddy" / "skills" / "missav-video-download"
EXTRACT_SCRIPT = SKILL_DIR / "scripts" / "extract_uuid.js"
DOWNLOAD_SCRIPT = SKILL_DIR / "scripts" / "download_missav.js"
DOWNLOAD_DIR = Path.home() / "Downloads" / "missav"


async def _fetch_url(url: str, timeout: int = 15) -> str:
    """通用页面抓取"""
    proc = await asyncio.create_subprocess_exec(
        "curl", "-s", "-L",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "-H", "Referer: https://missav.live/",
        url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    return stdout.decode("utf-8", errors="replace")


def _parse_search_results(html: str, keyword: str) -> list:
    """从 HTML 中解析搜索结果"""
    seen = set()
    urls = []
    kw_lower = keyword.lower()

    for m in re.finditer(r'href="(https://missav\.live[^"]+)"', html):
        url = m.group(1)
        if kw_lower not in url.lower():
            continue
        if any(x in url for x in ['/search/', '/actresses', '/ads', '/contact',
                                   '/terms', '/upload', '/articles', '/saved',
                                   '/playlists', '/history', '/new', '/release',
                                   '/uncensored', '/chinese-subtitle', '/genres',
                                   '/makers', '/klive', '/clive', '/vip']):
            continue
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls[:30]


async def search(keyword: str) -> list:
    """搜索 MissAV 视频，本地失败走 VPS 中转"""
    # 1) 先尝试本地
    try:
        encoded = keyword.replace(" ", "+")
        search_url = f"https://missav.live/cn/search/{encoded}"
        html = await _fetch_url(search_url)
        urls = _parse_search_results(html, keyword)
        if urls:
            return urls
        # 页面抓到了但没结果，可能真没结果
        if len(html) > 5000:
            return urls
    except Exception as e:
        logger.info(f"MissAV 本地搜索失败，尝试 VPS 中转: {e}")

    # 2) VPS 中转
    try:
        from handlers.vps_relay import relay_get_json
        data = await relay_get_json("/api/missav/search", {"q": keyword})
        if "error" in data:
            logger.warning(f"VPS MissAV 搜索也失败: {data['error']}")
            return []
        return data.get("urls", [])
    except Exception as e:
        logger.warning(f"VPS MissAV 搜索异常: {e}")
        return []


async def parse_url(missav_url: str) -> dict:
    """解析 MissAV URL，本地失败走 VPS"""
    if not missav_url or "missav" not in missav_url.lower():
        return {"error": "无效的 MissAV URL"}

    # 1) 本地解析
    local_ok = False
    if EXTRACT_SCRIPT.exists():
        try:
            proc = await asyncio.create_subprocess_exec(
                "node", str(EXTRACT_SCRIPT), missav_url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            out = stdout.decode("utf-8", errors="replace")
            err = stderr.decode("utf-8", errors="replace")

            if proc.returncode == 0:
                uuid = ""
                qualities = []
                for line in out.split("\n"):
                    m = re.search(r"UUID:\s*([a-f0-9-]+)", line)
                    if m:
                        uuid = m.group(1)
                    m = re.search(r"可用流:\s*(.+)", line)
                    if m:
                        for q in ["360p", "480p", "720p", "1080p"]:
                            if q in line:
                                qualities.append(q)

                if uuid:
                    dvd_id = ""
                    m = re.search(r"/([a-z]+-\d+)", missav_url)
                    if m:
                        dvd_id = m.group(1)
                    result = {
                        "uuid": uuid,
                        "qualities": qualities,
                        "dvd_id": dvd_id,
                        "url": missav_url,
                    }
                    local_ok = True
        except Exception as e:
            logger.info(f"MissAV 本地解析失败: {e}")

    if local_ok:
        return result

    # 2) VPS 中转解析
    try:
        from handlers.vps_relay import relay_get_json
        data = await relay_get_json("/api/missav/parse", {"url": missav_url})
        if "error" in data:
            return {"error": f"本地和VPS解析均失败: {data.get('error', '未知')}"}

        result = {
            "uuid": data.get("uuid", ""),
            "qualities": ["720p"],  # VPS解析默认返回720p
            "dvd_id": data.get("dvd_id", ""),
            "url": missav_url,
            "m3u8": data.get("m3u8", ""),
            "relay": True,  # 标记走的中转
        }
        if not result["uuid"] and not result["m3u8"]:
            return {"error": "VPS 解析也未获取到有效信息"}
        return result
    except Exception as e:
        return {"error": f"本地和VPS解析均失败: {e}"}


async def download_video(uuid: str, quality: str) -> dict:
    """下载 MissAV 视频，本地失败走 VPS"""
    if quality not in ["360p", "480p", "720p", "1080p"]:
        return {"error": f"无效清晰度: {quality}"}

    # 1) 本地下载
    if DOWNLOAD_SCRIPT.exists():
        try:
            os.makedirs(str(DOWNLOAD_DIR), exist_ok=True)
            proc = await asyncio.create_subprocess_exec(
                "node", str(DOWNLOAD_SCRIPT), uuid, quality, str(DOWNLOAD_DIR),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
            out = stdout.decode("utf-8", errors="replace")
            err = stderr.decode("utf-8", errors="replace")

            if proc.returncode == 0:
                output_file = DOWNLOAD_DIR / f"{uuid}_{quality}.ts"
                if output_file.exists():
                    size = output_file.stat().st_size
                    return {
                        "success": True,
                        "file": str(output_file),
                        "size": size,
                        "size_mb": round(size / 1024 / 1024, 2),
                        "log": out,
                    }
        except Exception as e:
            logger.info(f"MissAV 本地下载失败: {e}")

    # 2) VPS 中转下载
    try:
        from handlers.vps_relay import relay_post_json, relay_download_file

        # 先解析获取 m3u8
        # VPS上的下载需要 m3u8 URL
        # 尝试从 VPS 解析获取 m3u8
        return {"error": "VPS 中转下载需要先通过 VPS 解析获取 m3u8 地址，请使用 VPS 中转模式解析后再下载"}
    except Exception as e:
        return {"error": f"本地和VPS下载均失败: {e}"}


async def download_via_relay(m3u8_url: str, filename: str, quality: str = "720p") -> dict:
    """通过 VPS 中转下载（需要 m3u8 地址）"""
    try:
        from handlers.vps_relay import relay_post_json, relay_download_file

        # 发送下载请求到 VPS
        data = await relay_post_json("/api/missav/download", {
            "m3u8_url": m3u8_url,
            "filename": filename,
            "quality": quality,
        })

        if "error" in data:
            return data

        # 从 VPS 拉取文件到本地
        download_url = data.get("download_url", "")
        if not download_url:
            return {"error": "VPS 下载成功但未返回下载链接"}

        local_path = DOWNLOAD_DIR / f"{filename}.ts"
        result = await relay_download_file(download_url, local_path)

        return result
    except Exception as e:
        return {"error": f"VPS 中转下载失败: {e}"}
