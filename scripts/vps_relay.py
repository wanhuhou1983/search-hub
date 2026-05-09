"""
VPS 视频中转服务 — 部署在 107.175.49.215
功能：代理视频页抓取 + HLS/视频下载
端口：18081（避免与本地 search-hub 冲突）
"""

import asyncio
import json
import os
import re
import subprocess
import tempfile
import urllib.parse
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

app = FastAPI(title="VPS Video Relay")

DOWNLOAD_DIR = Path("/tmp/video_relay")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# ─── 通用页面抓取 ─────────────────────────────────

@app.get("/api/fetch")
async def fetch_page(url: str = Query(..., description="要抓取的URL")):
    """代理 curl 抓取页面，返回 HTML 内容"""
    try:
        proc = await asyncio.create_subprocess_exec(
            "curl", "-s", "-L", "-m", "30",
            "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "-H", f"Referer: {urllib.parse.urlparse(url).scheme}://{urllib.parse.urlparse(url).netloc}/",
            url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=35)
        html = stdout.decode("utf-8", errors="replace")
        if proc.returncode != 0:
            return JSONResponse({"error": stderr.decode("utf-8", errors="replace")[:300]}, status_code=502)
        return {"html": html, "length": len(html)}
    except asyncio.TimeoutError:
        return JSONResponse({"error": "抓取超时"}, status_code=504)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ─── MissAV 搜索 ──────────────────────────────────

@app.get("/api/missav/search")
async def missav_search(q: str = Query(..., description="搜索关键词")):
    """在VPS端搜索 MissAV"""
    encoded = q.replace(" ", "+")
    search_url = f"https://missav.live/cn/search/{encoded}"
    
    proc = await asyncio.create_subprocess_exec(
        "curl", "-s", "-L", "-m", "30",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "-H", "Referer: https://missav.live/",
        search_url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=35)
    html = stdout.decode("utf-8", errors="replace")
    
    seen = set()
    urls = []
    kw_lower = q.lower()
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
    
    return {"q": q, "urls": urls[:30], "total": len(urls)}


# ─── MissAV 解析（调用 Node.js） ──────────────────

@app.get("/api/missav/parse")
async def missav_parse(url: str = Query(..., description="MissAV URL")):
    """在VPS端解析 MissAV UUID"""
    extract_script = Path.home() / ".workbuddy" / "skills" / "missav-video-download" / "scripts" / "extract_uuid.js"
    
    # 如果没有 extract_uuid.js，用 curl + 正则提取
    proc = await asyncio.create_subprocess_exec(
        "curl", "-s", "-L", "-m", "30",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "-H", "Referer: https://missav.live/",
        url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=35)
    html = stdout.decode("utf-8", errors="replace")
    
    # 从页面提取 UUID
    uuid = ""
    m = re.search(r'/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', url)
    if not m:
        m = re.search(r'"id"\s*:\s*"([a-f0-9-]{36})"', html)
    if m:
        uuid = m.group(1)
    
    # 尝试提取 m3u8 地址
    m3u8 = ""
    for pattern in [
        r'(https?://[^"\']+\.m3u8[^"\']*)',
        r'setVideoUrl(?:High|Low|HLS)?\(\s*["\']([^"\']+)["\']',
        r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
    ]:
        mm = re.search(pattern, html)
        if mm:
            m3u8 = mm.group(1).replace("&amp;", "&")
            break
    
    dvd_id = ""
    mm = re.search(r"/([a-z]+-\d+)", url)
    if mm:
        dvd_id = mm.group(1)
    
    return {"uuid": uuid, "m3u8": m3u8, "dvd_id": dvd_id, "url": url}


# ─── MissAV 下载（ffmpeg） ────────────────────────

class MissavDownloadReq(BaseModel):
    m3u8_url: str
    filename: str = "video"
    quality: str = "720p"

@app.post("/api/missav/download")
async def missav_download(data: MissavDownloadReq):
    """在VPS端下载 MissAV 视频，返回文件供本地拉取"""
    output_path = DOWNLOAD_DIR / f"{data.filename}.ts"
    
    cmd = [
        "ffmpeg", "-y",
        "-headers", "Referer: https://missav.live/\r\nUser-Agent: Mozilla/5.0",
        "-i", data.m3u8_url,
        "-c", "copy",
        str(output_path),
    ]
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=600)
    except asyncio.TimeoutError:
        return JSONResponse({"error": "下载超时"}, status_code=504)
    
    if not output_path.exists() or output_path.stat().st_size < 1024:
        return JSONResponse({"error": "下载失败"}, status_code=500)
    
    size = output_path.stat().st_size
    return {
        "success": True,
        "file": str(output_path),
        "size": size,
        "size_mb": round(size / 1024 / 1024, 2),
        "download_url": f"/api/file/{output_path.name}",
    }


# ─── XVideos 解析 + 下载 ──────────────────────────

@app.get("/api/xvideos/parse")
async def xvideos_parse(url: str = Query(..., description="XVideos URL")):
    """在VPS端解析 XVideos"""
    proc = await asyncio.create_subprocess_exec(
        "curl", "-s", "-L", "-m", "30",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "-H", "Referer: https://www.xvideos.com/",
        url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=35)
    html = stdout.decode("utf-8", errors="replace")
    
    hls_url = None
    for p in [
        r'setVideoHLS\(\s*["\']([^"\']+)["\']\s*\)',
        r'"hls":\s*["\']([^"\']+)["\']',
    ]:
        m = re.search(p, html)
        if m:
            hls_url = m.group(1).replace("&amp;", "&")
            break
    
    title = "xv_video"
    m = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
    if m:
        title = re.sub(r'[\\/:*?"<>|]', '_', m.group(1).replace(" - XVIDEOS.COM", "").strip())[:60]
    
    if not hls_url:
        return JSONResponse({"error": "未找到 HLS 地址"}, status_code=400)
    
    return {"success": True, "hls_url": hls_url, "title": title, "url": url}


@app.post("/api/xvideos/download")
async def xvideos_download(data: dict):
    """在VPS端下载 XVideos 视频"""
    hls_url = data.get("hls_url", "")
    title = data.get("title", "xv_video")
    
    output_path = DOWNLOAD_DIR / f"{title}.mp4"
    
    cmd = [
        "ffmpeg", "-y",
        "-headers", "Referer: https://www.xvideos.com/\r\nUser-Agent: Mozilla/5.0",
        "-i", hls_url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        str(output_path),
    ]
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=600)
    except asyncio.TimeoutError:
        return JSONResponse({"error": "下载超时"}, status_code=504)
    
    if not output_path.exists() or output_path.stat().st_size < 1024:
        return JSONResponse({"error": "下载失败"}, status_code=500)
    
    size = output_path.stat().st_size
    return {
        "success": True,
        "file": str(output_path),
        "size": size,
        "size_mb": round(size / 1024 / 1024, 2),
        "download_url": f"/api/file/{output_path.name}",
    }


# ─── PornHub 解析 + 下载（yt-dlp） ────────────────

@app.get("/api/pornhub/parse")
async def pornhub_parse(url: str = Query(..., description="PornHub URL")):
    """在VPS端解析 PornHub"""
    cmd = ["yt-dlp", "--dump-json", "--no-playlist", url]
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    except asyncio.TimeoutError:
        return JSONResponse({"error": "解析超时"}, status_code=504)
    
    if proc.returncode != 0:
        return JSONResponse({"error": stderr.decode("utf-8", errors="replace")[:300]}, status_code=502)
    
    info = json.loads(stdout.decode("utf-8", errors="replace"))
    title = re.sub(r'[\\/:*?"<>|]', '_', info.get("title", "video"))[:60]
    duration = info.get("duration", 0)
    
    return {
        "success": True,
        "title": title,
        "duration": duration,
        "duration_str": f"{duration//60}分{duration%60}秒" if duration else "未知",
        "url": url,
    }


@app.post("/api/pornhub/download")
async def pornhub_download(data: dict):
    """在VPS端下载 PornHub 视频"""
    url = data.get("url", "")
    title = data.get("title", "video")
    quality = data.get("quality", "720p")
    
    quality_map = {
        "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "720p":  "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "480p":  "bestvideo[height<=480]+bestaudio/best[height<=480]",
    }
    fmt = quality_map.get(quality, "bestvideo+bestaudio/best")
    
    out_tpl = str(DOWNLOAD_DIR / f"{title}.%(ext)s")
    
    cmd = [
        "yt-dlp",
        "-f", fmt,
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--no-check-certificate",
        "-o", out_tpl,
        url,
    ]
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=600)
    except asyncio.TimeoutError:
        return JSONResponse({"error": "下载超时"}, status_code=504)
    
    # 找输出文件
    output_path = DOWNLOAD_DIR / f"{title}.mp4"
    if not output_path.exists():
        for f in DOWNLOAD_DIR.glob(f"{title}.*"):
            output_path = f
            break
    
    if not output_path.exists():
        return JSONResponse({"error": "下载完成但未找到文件"}, status_code=500)
    
    size = output_path.stat().st_size
    return {
        "success": True,
        "file": str(output_path),
        "size": size,
        "size_mb": round(size / 1024 / 1024, 2),
        "download_url": f"/api/file/{output_path.name}",
    }


# ─── 文件下载（本地从VPS拉取） ────────────────────

@app.get("/api/file/{filename}")
async def download_file(filename: str):
    """下载VPS上的已下载文件"""
    file_path = DOWNLOAD_DIR / filename
    if not file_path.exists():
        return JSONResponse({"error": "文件不存在"}, status_code=404)
    return FileResponse(
        str(file_path),
        media_type="application/octet-stream",
        filename=filename,
    )


# ─── 健康检查 ─────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "vps-video-relay"}


# ─── 清理旧文件 ──────────────────────────────────

@app.post("/api/cleanup")
async def cleanup(max_age_hours: int = 2):
    """清理超过指定小时数的下载文件"""
    import time
    now = time.time()
    removed = 0
    for f in DOWNLOAD_DIR.iterdir():
        if f.is_file() and (now - f.stat().st_mtime) > max_age_hours * 3600:
            f.unlink()
            removed += 1
    return {"removed": removed}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18081)
