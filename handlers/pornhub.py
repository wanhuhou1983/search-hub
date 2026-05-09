"""
pornhub handler — 解析与下载，支持本地 + VPS 中转
依赖: yt-dlp, ffmpeg
"""

import asyncio
import json
import logging
import os
import re
from pathlib import Path

logger = logging.getLogger("search-hub.pornhub")

from config import YTDLP_BIN, _resolve_tool

YTDLP = _resolve_tool(YTDLP_BIN, "yt-dlp")
DOWNLOAD_DIR = Path.home() / "Downloads" / "pornhub"

QUALITY_MAP = {
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p":  "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p":  "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "240p":  "worstvideo+worstaudio/worst",
}


async def parse_url(video_url: str) -> dict:
    """解析 pornhub URL，本地失败走 VPS"""
    if "pornhub" not in video_url.lower():
        return {"error": "无效的 pornhub URL"}

    # 1) 本地解析
    if os.path.exists(YTDLP):
        try:
            proc = await asyncio.create_subprocess_exec(
                YTDLP, "--dump-json", "--no-playlist", video_url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

            if proc.returncode == 0:
                info = json.loads(stdout.decode("utf-8", errors="replace"))
                title = re.sub(r'[\\/:*?"<>|]', '_', info.get("title", "video"))[:60]
                duration = info.get("duration", 0)
                return {
                    "success": True,
                    "title": title,
                    "duration": duration,
                    "duration_str": f"{duration//60}分{duration%60}秒" if duration else "未知",
                    "url": video_url,
                }
            else:
                err = stderr.decode("utf-8", errors="replace")
                logger.info(f"PornHub 本地解析失败: {err[:200]}")
        except Exception as e:
            logger.info(f"PornHub 本地解析异常: {e}")

    # 2) VPS 中转
    try:
        from handlers.vps_relay import relay_get_json
        data = await relay_get_json("/api/pornhub/parse", {"url": video_url})
        if "error" in data:
            return {"error": f"本地和VPS解析均失败: {data.get('error', '未知')}"}
        data["relay"] = True
        return data
    except Exception as e:
        return {"error": f"本地和VPS解析均失败: {e}"}


async def download_video(video_url: str, quality: str = "720p") -> dict:
    """下载 pornhub 视频，本地失败走 VPS"""
    parsed = await parse_url(video_url)
    if "error" in parsed:
        return parsed

    is_relay = parsed.get("relay", False)
    title = parsed.get("title", "video")

    # 1) 本地下载
    if not is_relay and os.path.exists(YTDLP):
        try:
            fmt = QUALITY_MAP.get(quality, "bestvideo+bestaudio/best")
            os.makedirs(str(DOWNLOAD_DIR), exist_ok=True)
            out_tpl = str(DOWNLOAD_DIR / f"{title}.%(ext)s")

            cmd = [
                YTDLP,
                "-f", fmt,
                "--merge-output-format", "mp4",
                "--no-playlist",
                "--no-check-certificate",
                "-o", out_tpl,
                video_url,
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=600)
            log = stdout.decode("utf-8", errors="replace")

            if proc.returncode == 0:
                # 找输出文件
                output_path = DOWNLOAD_DIR / f"{title}.mp4"
                if output_path.exists():
                    size = output_path.stat().st_size
                    return {
                        "success": True,
                        "file": str(output_path),
                        "size": size,
                        "size_mb": round(size / 1024 / 1024, 2),
                    }
                # 搜索目录
                for f in DOWNLOAD_DIR.glob(f"{title}.*"):
                    if f.suffix in (".mp4", ".mkv", ".webm"):
                        size = f.stat().st_size
                        return {
                            "success": True,
                            "file": str(f),
                            "size": size,
                            "size_mb": round(size / 1024 / 1024, 2),
                        }
            logger.info(f"PornHub 本地下载失败: yt-dlp exit {proc.returncode}")
        except Exception as e:
            logger.info(f"PornHub 本地下载异常: {e}")

    # 2) VPS 中转下载
    try:
        from handlers.vps_relay import relay_post_json, relay_download_file

        data = await relay_post_json("/api/pornhub/download", {
            "url": video_url,
            "title": title,
            "quality": quality,
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
