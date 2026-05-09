"""
统一搜索中心 - FastAPI 后端

设计原则：
  1. 所有 handler 采用 LAZY IMPORT（请求时加载，启动时不加载）
     确保某个 handler 缺失/异常不会拖垮整个服务
  2. 视频下载端点（missav/xvideos/pornhub）同样懒加载
  3. 启动极快，不联网、不检查外部依赖
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger("search-hub")

app = FastAPI(title="统一搜索中心")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Pydantic Request Schemas ────────────────────────

class MissavDownloadReq(BaseModel):
    uuid: str
    quality: str = "720p"

class XvideosDownloadReq(BaseModel):
    url: str

class PornhubDownloadReq(BaseModel):
    url: str
    quality: str = "720p"

class MissavRelayDownloadReq(BaseModel):
    m3u8_url: str
    filename: str
    quality: str = "720p"

# ─── 搜索源注册（存模块名/函数名，不 import） ───────────
SEARCH_SOURCES = {
    "local":      {"module": "handlers.local",      "name": "本地文件"},
    "obsidian":   {"module": "handlers.obsidian",   "name": "Obsidian"},
    "baidu":      {"module": "handlers.baidu",      "name": "百度网盘"},
    "p115":       {"module": "handlers.p115",       "name": "115网盘"},
    "quark":      {"module": "handlers.quark",      "name": "夸克网盘"},
    "aliyun":     {"module": "handlers.aliyun",     "name": "阿里云盘"},
    "zlib":       {"module": "handlers.zlib",        "name": "Z-Library"},
    "googledrive":{"module": "handlers.googledrive", "name": "Google Drive"},
    "icloud":     {"module": "handlers.icloud",      "name": "iCloud Drive"},
}

# ─── 下载源注册 ──────────────────────────────────────
DOWNLOAD_SOURCES = {
    "baidu": {"module": "handlers.disk_common", "func": "baidu_download_url"},
    "p115":  {"module": "handlers.disk_common", "func": "p115_download_url"},
    "quark": {"module": "handlers.disk_common", "func": "quark_download_url"},
    "aliyun": {"module": "handlers.aliyun", "func": "download_url"},
}


# ─── 懒加载工具 ──────────────────────────────────────
def _load_module(module_path: str):
    """安全导入模块，失败返回 None"""
    try:
        import importlib
        return importlib.import_module(module_path)
    except Exception as e:
        logger.warning("lazy import failed: %s — %s", module_path, e)
        return None


def _load_config():
    """懒加载 config（只在需要 token/cookie 时）"""
    mod = _load_module("config")
    if mod is None:
        return {}
    return {
        "SEARCH_TIMEOUT": getattr(mod, "SEARCH_TIMEOUT", 60),
        "MAX_RESULTS": getattr(mod, "MAX_RESULTS_PER_SOURCE", 100),
        "BAIDU_TOKEN": getattr(mod, "BAIDU_ACCESS_TOKEN", ""),
        "P115_COOKIE": getattr(mod, "P115_COOKIE", ""),
    }


# ═══════════════════════════════════════════════════════
#  搜索 API
# ═══════════════════════════════════════════════════════

async def _run_search(source_key: str, q: str, timeout: int):
    """在 executor 中运行同步搜索函数"""
    info = SEARCH_SOURCES.get(source_key)
    if not info:
        return {"source": source_key, "error": "未知数据源", "results": []}

    mod = _load_module(info["module"])
    if mod is None:
        return {"source": source_key, "error": f"handler 加载失败", "results": []}

    if not hasattr(mod, "search"):
        return {"source": source_key, "error": "handler 无 search 函数", "results": []}

    loop = asyncio.get_running_loop()

    def _search():
        try:
            return mod.search(q, timeout)
        except Exception as e:
            return {"source": source_key, "error": str(e), "results": []}

    return await loop.run_in_executor(None, _search)


@app.get("/api/search")
async def api_search(
    q: str = Query("", description="搜索关键词"),
    sources: str = Query("all", description="数据源，逗号分隔"),
):
    if not q.strip():
        return {"q": q, "results": {}}

    cfg = _load_config()
    timeout = cfg.get("SEARCH_TIMEOUT", 60)

    if sources == "all":
        keys = list(SEARCH_SOURCES.keys())
    else:
        keys = [s.strip() for s in sources.split(",") if s.strip() in SEARCH_SOURCES]

    if not keys:
        return JSONResponse({"q": q, "error": "无效的 source 参数"}, status_code=400)

    start = time.time()
    tasks = {key: _run_search(key, q, timeout) for key in keys}
    results = {}

    for key, task in tasks.items():
        try:
            results[key] = await asyncio.wait_for(task, timeout=timeout + 2)
        except asyncio.TimeoutError:
            results[key] = {"source": key, "error": "超时", "results": []}

    total = sum(r.get("total", len(r.get("results", []))) for r in results.values())

    return {
        "q": q,
        "sources": keys,
        "total": total,
        "elapsed": round(time.time() - start, 2),
        "results": results,
    }


@app.get("/api/sources")
async def list_sources():
    return {
        "sources": [
            {"key": k, "name": v["name"]}
            for k, v in SEARCH_SOURCES.items()
        ]
    }


# ═══════════════════════════════════════════════════════
#  网盘 Token 状态检查
# ═══════════════════════════════════════════════════════


@app.get("/api/token/status")
async def token_status():
    """检查各网盘 token/cookie 状态"""
    results = []
    script_path = Path(__file__).parent / "scripts" / "token_check.py"
    try:
        r = subprocess.run(
            [sys.executable, str(script_path), "--json"],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
        if r.returncode == 0 and r.stdout.strip():
            results = json.loads(r.stdout)
        else:
            error_msg = r.stderr[:200] if r.stderr else f"exit code {r.returncode}"
            results = [{"name": "错误", "status": "🔴 检查失败", "detail": error_msg}]
    except Exception as e:
        results = [{"name": "错误", "status": "🔴 检查失败", "detail": str(e)}]
    return {"checks": results, "time": datetime.now().isoformat()}


# ═══════════════════════════════════════════════════════
#  打开文件路径（仅本地）
# ═══════════════════════════════════════════════════════


@app.get("/api/open-path")
async def open_path(path: str = Query("", description="要打开的本地文件/文件夹路径")):
    """在文件管理器中定位文件或打开文件夹"""
    if not path.strip():
        return JSONResponse({"error": "缺少 path"}, status_code=400)

    path = path.strip().strip('"').strip("'")
    # 修复盘符路径格式：E:图书馆 → E:\图书馆
    if len(path) >= 2 and path[1] == ':' and path[2:3] != '\\':
        path = path[:2] + '\\' + path[2:]
    if not os.path.exists(path):
        return JSONResponse({"error": f"路径不存在: {path}"}, status_code=404)

    try:
        if os.path.isfile(path):
            subprocess.Popen(["explorer", "/select,", path])
        else:
            subprocess.Popen(["explorer", path])
        return {"success": True, "path": path}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════
#  网盘下载 API
# ═══════════════════════════════════════════════════════

@app.get("/api/download")
async def download_file(
    source: str = Query("", description="数据源: baidu/p115/quark/aliyun"),
    id: str = Query("", description="文件ID"),
    name: str = Query("", description="文件名（用于生成App链接）"),
    pickcode: str = Query("", description="115 pickcode（用于视频播放）"),
):
    if not source or not id:
        return JSONResponse({"error": "缺少参数 source 或 id"}, status_code=400)

    info = DOWNLOAD_SOURCES.get(source)
    if not info:
        return JSONResponse({"error": f"不支持的下载源: {source}"}, status_code=400)

    mod = _load_module(info["module"])
    if mod is None:
        return JSONResponse({"error": f"handler 加载失败"}, status_code=500)

    func = getattr(mod, info["func"], None)
    if func is None:
        return JSONResponse({"error": f"未找到下载函数"}, status_code=500)

    try:
        cfg = _load_config()
        url = None

        # 115网盘：直接跳转115网页，不尝试获取直链
        if source == "p115":
            return {
                "url": "https://115.com/",
                "source": source,
                "tip": "请在115网盘中找到对应文件下载",
                "actions": [
                    {"type": "web", "label": "打开115网盘", "url": "https://115.com/"},
                ],
            }

        if source == "baidu":
            url = func(id, cfg.get("BAIDU_TOKEN", ""))
        elif source == "quark":
            url = func(id)
        elif source == "aliyun":
            url = func(id)
        else:
            return JSONResponse({"error": f"不支持的下载源: {source}"}, status_code=400)

        if not url:
            return JSONResponse({"error": "获取下载链接失败"}, status_code=500)

        result = {
            "url": url,
            "source": source,
            "actions": [],
        }

        # 生成跳转App链接和Web链接
        if source == "baidu":
            result["actions"] = [
                {"type": "app", "label": "打开百度网盘客户端", "url": f"https://pan.baidu.com/disk/main?from=web"},
                {"type": "web", "label": "浏览器下载", "url": url},
            ]
        elif source == "aliyun":
            result["actions"] = [
                {"type": "app", "label": "打开阿里云盘客户端", "url": "https://www.alipan.com/"},
                {"type": "web", "label": "浏览器下载", "url": url},
            ]
        elif source == "quark":
            result["tip"] = "夸克链接需浏览器登录夸克后打开"
            result["actions"] = [
                {"type": "app", "label": "打开夸克网盘客户端", "url": "https://pan.quark.cn/"},
                {"type": "web", "label": "浏览器下载", "url": url},
            ]

        return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════
#  115 视频在线播放 API
# ═══════════════════════════════════════════════════════

@app.get("/api/p115/play")
async def p115_play_video(
    pickcode: str = Query("", description="115视频文件 pickcode"),
    definition: int = Query(0, description="画质: 0=全部, 1=标清, 3=超清, 4=1080P, 5=4K, 100=原画"),
):
    """获取115网盘视频的播放链接，前端通过HLS.js播放"""
    if not pickcode:
        return JSONResponse({"error": "缺少 pickcode 参数"}, status_code=400)

    cfg = _load_config()
    cookie = cfg.get("P115_COOKIE", "")
    if not cookie:
        return JSONResponse({"error": "115 Cookie 未配置"}, status_code=500)

    # 使用代理的m3u8 URL，后端代理115的m3u8请求
    proxy_m3u8 = f"/api/p115/proxy-m3u8?pickcode={pickcode}&definition={definition}"
    return {
        "url": proxy_m3u8,
        "original_url": f"https://115.com/api/video/m3u8/{pickcode}.m3u8",
        "title": "",
        "qualities": [],
        "type": "hls_proxy",
    }


@app.get("/api/p115/proxy-m3u8")
async def p115_proxy_m3u8(
    request: Request,
    pickcode: str = Query("", description="115视频文件 pickcode"),
    definition: int = Query(0, description="画质"),
):
    """代理115 m3u8请求，重写URL让ts分片也走代理"""
    import httpx
    from urllib.parse import quote

    cfg = _load_config()
    cookie = cfg.get("P115_COOKIE", "")
    if not cookie:
        return JSONResponse({"error": "115 Cookie 未配置"}, status_code=500)

    headers = {
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Referer": "https://115.com/",
    }

    m3u8_url = f"https://115.com/api/video/m3u8/{pickcode}.m3u8"

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            # 获取 master m3u8
            resp = await client.get(m3u8_url, headers=headers, follow_redirects=True)
            if resp.status_code != 200:
                return JSONResponse({"error": f"获取m3u8失败: HTTP {resp.status_code}"}, status_code=500)

            content = resp.text

            # 如果是master m3u8（包含子流URL），请求子流并重写ts路径
            import re
            sub_m3u8_urls = re.findall(r'(https?://[^\s]+\.m3u8[^\s]*)', content)

            if sub_m3u8_urls:
                # Master m3u8: 请求第一个子流并代理
                sub_url = sub_m3u8_urls[0]
                sub_resp = await client.get(sub_url, headers=headers, follow_redirects=True)
                if sub_resp.status_code != 200:
                    return JSONResponse({"error": f"获取子流m3u8失败: HTTP {sub_resp.status_code}"}, status_code=500)

                sub_content = sub_resp.text
                base_domain = sub_url.split("/")[2]  # cpats01.115.com
                scheme = sub_url.split("/")[0]  # https:

                # 重写ts分片的相对路径为代理URL
                def rewrite_ts(match):
                    ts_path = match.group(1)
                    if ts_path.startswith("/"):
                        full_url = f"{scheme}//{base_domain}{ts_path}"
                    else:
                        full_url = ts_path
                    return f"/api/p115/proxy-ts?url={quote(full_url, safe='')}"

                rewritten = re.sub(r'(/[^\s]+\.ts[^\s]*)', rewrite_ts, sub_content)
                return HTMLResponse(rewritten, media_type="application/vnd.apple.mpegurl")
            else:
                # 单层m3u8（没有子流），直接代理
                return HTMLResponse(content, media_type="application/vnd.apple.mpegurl")

    except Exception as e:
        logger.error("proxy-m3u8 error: %s", e)
        return JSONResponse({"error": f"代理m3u8失败: {e}"}, status_code=500)


@app.get("/api/p115/proxy-ts")
async def p115_proxy_ts(
    request: Request,
    url: str = Query("", description="115 TS分片URL"),
):
    """代理115视频TS分片请求"""
    import httpx

    cfg = _load_config()
    cookie = cfg.get("P115_COOKIE", "")
    if not cookie:
        return JSONResponse({"error": "115 Cookie 未配置"}, status_code=500)

    headers = {
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Referer": "https://115.com/",
    }

    async def stream():
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            async with client.stream("GET", url, headers=headers, follow_redirects=True) as resp:
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    yield chunk

    return StreamingResponse(stream(), media_type="video/mp2t")


# ═══════════════════════════════════════════════════════
#  视频下载 API
# ═══════════════════════════════════════════════════════

@app.get("/api/missav/search")
async def missav_search(q: str = Query("", description="搜索关键词")):
    if not q.strip():
        return JSONResponse({"error": "请输入关键词"}, status_code=400)
    mod = _load_module("handlers.missav")
    if mod is None:
        return JSONResponse({"error": "MissAV handler 加载失败"}, status_code=500)
    urls = await mod.search(q)
    return {"q": q, "urls": urls, "total": len(urls)}


@app.get("/api/missav/parse")
async def missav_parse(url: str = Query("", description="MissAV 视频页面 URL")):
    if not url.strip():
        return JSONResponse({"error": "请输入 URL"}, status_code=400)
    mod = _load_module("handlers.missav")
    if mod is None:
        return JSONResponse({"error": "MissAV handler 加载失败"}, status_code=500)
    result = await mod.parse_url(url)
    if "error" in result:
        return JSONResponse(result, status_code=400)
    return result


@app.post("/api/missav/download")
async def missav_download(data: MissavDownloadReq):
    if not data.uuid:
        return JSONResponse({"error": "缺少 uuid"}, status_code=400)
    mod = _load_module("handlers.missav")
    if mod is None:
        return JSONResponse({"error": "MissAV handler 加载失败"}, status_code=500)
    result = await mod.download_video(data.uuid, data.quality)
    if "error" in result:
        return JSONResponse(result, status_code=500)
    return result


@app.get("/api/xvideos/parse")
async def xvideos_parse(url: str = Query("", description="XVideos 视频页面 URL")):
    if not url.strip():
        return JSONResponse({"error": "请输入 URL"}, status_code=400)
    mod = _load_module("handlers.xvideos")
    if mod is None:
        return JSONResponse({"error": "XVideos handler 加载失败"}, status_code=500)
    result = await mod.parse_url(url)
    if "error" in result:
        return JSONResponse(result, status_code=400)
    return result


@app.post("/api/xvideos/download")
async def xvideos_download(data: XvideosDownloadReq):
    if not data.url:
        return JSONResponse({"error": "缺少 url"}, status_code=400)
    mod = _load_module("handlers.xvideos")
    if mod is None:
        return JSONResponse({"error": "XVideos handler 加载失败"}, status_code=500)
    result = await mod.download_video(data.url)
    if "error" in result:
        return JSONResponse(result, status_code=500)
    return result


@app.get("/api/pornhub/parse")
async def pornhub_parse(url: str = Query("", description="PornHub 视频页面 URL")):
    if not url.strip():
        return JSONResponse({"error": "请输入 URL"}, status_code=400)
    mod = _load_module("handlers.pornhub")
    if mod is None:
        return JSONResponse({"error": "PornHub handler 加载失败"}, status_code=500)
    result = await mod.parse_url(url)
    if "error" in result:
        return JSONResponse(result, status_code=400)
    return result


@app.post("/api/pornhub/download")
async def pornhub_download(data: PornhubDownloadReq):
    if not data.url:
        return JSONResponse({"error": "缺少 url"}, status_code=400)
    mod = _load_module("handlers.pornhub")
    if mod is None:
        return JSONResponse({"error": "PornHub handler 加载失败"}, status_code=500)
    result = await mod.download_video(data.url, data.quality)
    if "error" in result:
        return JSONResponse(result, status_code=500)
    return result


# ─── VPS 中转状态检查 ─────────────────────────────

@app.get("/api/relay/status")
async def relay_status():
    """检查 VPS 中转服务状态"""
    mod = _load_module("handlers.vps_relay")
    if mod is None:
        return {"available": False, "error": "vps_relay 模块加载失败"}
    ok = await mod.check_vps_relay()
    cfg = _load_config()
    relay_url = getattr(mod, "VPS_RELAY_URL", "unknown")
    return {"available": ok, "url": relay_url}


# ─── MissAV VPS 中转下载 ──────────────────────────

@app.post("/api/missav/relay-download")
async def missav_relay_download(data: MissavRelayDownloadReq):
    """通过 VPS 中转下载 MissAV 视频"""
    mod = _load_module("handlers.missav")
    if mod is None:
        return JSONResponse({"error": "MissAV handler 加载失败"}, status_code=500)
    result = await mod.download_via_relay(data.m3u8_url, data.filename, data.quality)
    if "error" in result:
        return JSONResponse(result, status_code=500)
    return result


# ═══════════════════════════════════════════════════════
#  前端
# ═══════════════════════════════════════════════════════

_INDEX_CACHE = None
_INDEX_LOCK = asyncio.Lock()


@app.get("/", response_class=HTMLResponse)
async def index():
    global _INDEX_CACHE
    if _INDEX_CACHE is None:
        async with _INDEX_LOCK:
            # double-check 模式
            if _INDEX_CACHE is None:
                html_path = Path(__file__).parent / "index.html"
                if html_path.exists():
                    _INDEX_CACHE = html_path.read_text(encoding="utf-8")
                else:
                    _INDEX_CACHE = "<h1>index.html not found</h1>"
    return _INDEX_CACHE
