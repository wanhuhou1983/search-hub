"""
pornhub handler — 解析与下载
依赖: yt-dlp, ffmpeg
"""

import asyncio
import json
import os
import re
from pathlib import Path

YTDLP = r"C:\Users\linhu\.workbuddy\binaries\python\versions\3.13.12\Scripts\yt-dlp.exe"
DOWNLOAD_DIR = Path.home() / "Downloads" / "pornhub"

QUALITY_MAP = {
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p":  "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p":  "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "240p":  "worstvideo+worstaudio/worst",
}


async def parse_url(video_url: str) -> dict:
    """解析 pornhub URL，返回标题、时长、可用格式"""
    if "pornhub" not in video_url.lower():
        return {"error": "无效的 pornhub URL"}

    try:
        proc = await asyncio.create_subprocess_exec(
            YTDLP, "--dump-json", "--no-playlist", video_url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    except asyncio.TimeoutError:
        return {"error": "解析超时"}
    except FileNotFoundError:
        return {"error": "yt-dlp 未找到"}
    except Exception as e:
        return {"error": str(e)}

    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="replace")
        return {"error": err[:300]}

    info = json.loads(stdout.decode("utf-8", errors="replace"))
    title = info.get("title", "video")
    duration = info.get("duration", 0)

    return {
        "success": True,
        "title": re.sub(r'[\\/:*?"<>|]', '_', title)[:60],
        "duration": duration,
        "duration_str": f"{duration//60}分{duration%60}秒" if duration else "未知",
        "url": video_url,
    }


async def download_video(video_url: str, quality: str = "720p") -> dict:
    """用 yt-dlp 下载 pornhub 视频"""
    parsed = await parse_url(video_url)
    if "error" in parsed:
        return parsed

    fmt = QUALITY_MAP.get(quality, "bestvideo+bestaudio/best")
    os.makedirs(str(DOWNLOAD_DIR), exist_ok=True)

    out_tpl = str(DOWNLOAD_DIR / f"{parsed['title']}.%(ext)s")

    cmd = [
        YTDLP,
        "-f", fmt,
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--no-check-certificate",
        "-o", out_tpl,
        video_url,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=600)
        log = stdout.decode("utf-8", errors="replace")
    except asyncio.TimeoutError:
        return {"error": "下载超时（超过10分钟）"}
    except FileNotFoundError:
        return {"error": "yt-dlp 未找到"}
    except Exception as e:
        return {"error": str(e)}

    if proc.returncode != 0:
        return {"error": f"yt-dlp 退出码 {proc.returncode}", "log": log[:500]}

    # 找输出文件
    output_path = DOWNLOAD_DIR / f"{parsed['title']}.mp4"
    if output_path.exists():
        size = output_path.stat().st_size
        return {
            "success": True,
            "file": str(output_path),
            "size": size,
            "size_mb": round(size / 1024 / 1024, 2),
        }

    # 如果文件名不对，扫描目录
    existing = list(DOWNLOAD_DIR.glob(f"{parsed['title']}.*"))
    existing += list(DOWNLOAD_DIR.glob("*.mp4"))
    for f in existing:
        if f.name.startswith(parsed['title'][:10]) or f.suffix == ".mp4":
            size = f.stat().st_size
            return {
                "success": True,
                "file": str(f),
                "size": size,
                "size_mb": round(size / 1024 / 1024, 2),
            }

    return {"error": "下载完成但未找到输出文件", "log": log[:300]}
