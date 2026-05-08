"""
xvideos handler — 解析与下载
依赖: ffmpeg, Python requests
"""

import asyncio
import os
import re
from pathlib import Path

FFMPEG = r"C:\Users\linhu\WorkBuddy\20260328095145\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
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
            # 解码 HTML 实体
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
    """解析 xvideos URL，返回 HLS 地址和标题"""
    if "xvideos" not in video_url.lower():
        return {"error": "无效的 xvideos URL"}

    try:
        html = await _fetch_url(video_url)
    except asyncio.TimeoutError:
        return {"error": "抓取超时"}
    except Exception as e:
        return {"error": str(e)}

    hls_url = _extract_hls(html)
    if not hls_url:
        return {"error": "未找到 HLS 流地址（页面可能需登录或已失效）"}

    title = _extract_title(html)

    return {
        "success": True,
        "hls_url": hls_url,
        "title": title,
        "url": video_url,
    }


async def download_video(video_url: str) -> dict:
    """下载 xvideos 视频到本地"""
    parsed = await parse_url(video_url)
    if "error" in parsed:
        return parsed

    os.makedirs(str(DOWNLOAD_DIR), exist_ok=True)
    output_path = DOWNLOAD_DIR / f"{parsed['title']}.mp4"

    cmd = [
        FFMPEG,
        "-headers", "Referer: https://www.xvideos.com/",
        "-user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "-i", parsed["hls_url"],
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        str(output_path), "-y",
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
        return {"error": "ffmpeg 未找到"}
    except Exception as e:
        return {"error": str(e)}

    if proc.returncode != 0:
        return {"error": f"ffmpeg 退出码 {proc.returncode}", "log": log[:500]}

    if output_path.exists():
        size = output_path.stat().st_size
        return {
            "success": True,
            "file": str(output_path),
            "size": size,
            "size_mb": round(size / 1024 / 1024, 2),
        }
    return {"error": "下载完成但未找到输出文件"}
