"""
xvideos handler — 解析与下载，支持本地 + VPS 中转
依赖: ffmpeg, Python requests
"""

import asyncio
import logging
import os
import re
from pathlib import Path

logger = logging.getLogger("search-hub.xvideos")

from config import FFMPEG_BIN, _resolve_tool

FFMPEG = _resolve_tool(FFMPEG_BIN, "ffmpeg")
DOWNLOAD_DIR = Path.home() / "Downloads" / "xvideos"


async def _fetch_url(url: str, timeout: int = 15) -> str:
    """curl 抓取页面"""
    proc = await asyncio.create_subprocess_exec(
        "curl", "-s", "-L",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "-H", "Referer: https://www.xvideos.com/",
        url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    return stdout.decode("utf-8", errors="replace")


def _extract_hls(html: str) -> str | None:
    """从 xvideos 页面 HTML 中提取 HLS URL"""
    patterns = [
        r'setVideoHLS\(\s*["\']([^"\']+)["\']\s*\)',
        r'"hls":\s*["\']([^"\']+)["\']',
    ]
    for p in patterns:
        m = re.search(p, html)
        if m:
            url = m.group(1)
            url = url.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
            return url
    return None


def _extract_title(html: str) -> str:
    """提取视频标题"""
    m = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
    if m:
        title = m.group(1).replace(" - XVIDEOS.COM", "").strip()
        return re.sub(r'[\\/:*?"<>|]', '_', title)[:60]
    return "xv_video"


async def parse_url(video_url: str) -> dict:
    """解析 xvideos URL，本地失败走 VPS"""
    if "xvideos" not in video_url.lower():
        return {"error": "无效的 xvideos URL"}

    # 1) 本地解析
    try:
        html = await _fetch_url(video_url)
        hls_url = _extract_hls(html)
        if hls_url:
            title = _extract_title(html)
            return {
                "success": True,
                "hls_url": hls_url,
                "title": title,
                "url": video_url,
            }
    except Exception as e:
        logger.info(f"XVideos 本地解析失败: {e}")

    # 2) VPS 中转
    try:
        from handlers.vps_relay import relay_get_json
        data = await relay_get_json("/api/xvideos/parse", {"url": video_url})
        if "error" in data:
            return {"error": f"本地和VPS解析均失败: {data.get('error', '未知')}"}
        data["relay"] = True
        return data
    except Exception as e:
        return {"error": f"本地和VPS解析均失败: {e}"}


async def download_video(video_url: str) -> dict:
    """下载 xvideos 视频，本地失败走 VPS"""
    parsed = await parse_url(video_url)
    if "error" in parsed:
        return parsed

    is_relay = parsed.get("relay", False)
    hls_url = parsed["hls_url"]
    title = parsed.get("title", "xv_video")

    # 1) 本地下载（非中转模式）
    if not is_relay and os.path.exists(FFMPEG):
        try:
            os.makedirs(str(DOWNLOAD_DIR), exist_ok=True)
            output_path = DOWNLOAD_DIR / f"{title}.mp4"

            cmd = [
                FFMPEG,
                "-headers", "Referer: https://www.xvideos.com/",
                "-user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "-i", hls_url,
                "-c", "copy",
                "-bsf:a", "aac_adtstoasc",
                str(output_path), "-y",
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=600)
            log = stdout.decode("utf-8", errors="replace")

            if proc.returncode == 0 and output_path.exists():
                size = output_path.stat().st_size
                return {
                    "success": True,
                    "file": str(output_path),
                    "size": size,
                    "size_mb": round(size / 1024 / 1024, 2),
                }
            logger.info(f"XVideos 本地下载失败: ffmpeg exit {proc.returncode}")
        except Exception as e:
            logger.info(f"XVideos 本地下载异常: {e}")

    # 2) VPS 中转下载
    try:
        from handlers.vps_relay import relay_post_json, relay_download_file

        data = await relay_post_json("/api/xvideos/download", {
            "hls_url": hls_url,
            "title": title,
        })

        if "error" in data:
            return data

        download_url = data.get("download_url", "")
        if not download_url:
            return {"error": "VPS 下载成功但未返回下载链接"}

        local_path = DOWNLOAD_DIR / f"{title}.mp4"
        result = await relay_download_file(download_url, local_path)
        result["relay"] = True
        return result
    except Exception as e:
        return {"error": f"本地和VPS下载均失败: {e}"}
