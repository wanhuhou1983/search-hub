"""
MissAV 视频解析与下载 - 调用 Node.js 脚本
"""

import asyncio
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

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


async def search(keyword: str) -> list:
    """搜索 MissAV 视频，返回视频页面 URL 列表"""
    encoded = keyword.replace(" ", "+")
    search_url = f"https://missav.live/cn/search/{encoded}"
    html = await _fetch_url(search_url)

    seen = set()
    urls = []
    kw_lower = keyword.lower()

    for m in re.finditer(r'href="(https://missav\.live[^"]+)"', html):
        url = m.group(1)
        # 只保留包含搜索关键词的视频页链接
        if kw_lower not in url.lower():
            continue
        # 排除非视频页
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


async def parse_url(missav_url: str) -> dict:
    """调用 extract_uuid.js 解析 MissAV URL"""
    if not missav_url or "missav" not in missav_url.lower():
        return {"error": "无效的 MissAV URL"}
    if not EXTRACT_SCRIPT.exists():
        return {"error": f"脚本不存在: {EXTRACT_SCRIPT}"}

    try:
        proc = await asyncio.create_subprocess_exec(
            "node", str(EXTRACT_SCRIPT), missav_url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        out = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")
    except asyncio.TimeoutError:
        return {"error": "解析超时"}
    except FileNotFoundError:
        return {"error": "Node.js 未安装"}
    except Exception as e:
        return {"error": str(e)}

    if proc.returncode != 0:
        return {"error": err or "解析失败"}

    # 解析输出：UUID / Playlist / 可用流
    uuid = ""
    qualities = []
    for line in out.split("\n"):
        m = re.search(r"UUID:\s*([a-f0-9-]+)", line)
        if m:
            uuid = m.group(1)
        m = re.search(r"可用流:\s*(.+)", line)
        if m:
            # 解析流列表: 1080p, 720p, 480p, 360p
            for q in ["360p", "480p", "720p", "1080p"]:
                if q in line:
                    qualities.append(q)

    if not uuid:
        return {"error": "未能提取视频 UUID"}

    # 提取 DVD ID 和标题
    dvd_id = ""
    m = re.search(r"/([a-z]+-\d+)", missav_url)
    if m:
        dvd_id = m.group(1)

    return {
        "uuid": uuid,
        "qualities": qualities,
        "dvd_id": dvd_id,
        "url": missav_url,
    }


async def download_video(uuid: str, quality: str) -> dict:
    """调用 download_missav.js 下载视频"""
    if quality not in ["360p", "480p", "720p", "1080p"]:
        return {"error": f"无效清晰度: {quality}"}
    if not DOWNLOAD_SCRIPT.exists():
        return {"error": f"脚本不存在: {DOWNLOAD_SCRIPT}"}

    os.makedirs(str(DOWNLOAD_DIR), exist_ok=True)

    try:
        proc = await asyncio.create_subprocess_exec(
            "node", str(DOWNLOAD_SCRIPT), uuid, quality, str(DOWNLOAD_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
        out = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")
    except asyncio.TimeoutError:
        return {"error": "下载超时（超过10分钟）"}
    except FileNotFoundError:
        return {"error": "Node.js 未安装"}
    except Exception as e:
        return {"error": str(e)}

    if proc.returncode != 0:
        return {"error": err[:200], "log": out}

    # 找输出文件
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
    return {"error": "下载完成但未找到输出文件", "log": out}
