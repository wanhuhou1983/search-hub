"""
VPS 中转模块 — 本地请求失败时自动走 VPS 中转

VPS 地址: 107.175.49.215:18081
"""

import json
import logging
import os
from pathlib import Path
from urllib.parse import urlparse

import aiohttp

logger = logging.getLogger("search-hub.vps-relay")

# VPS 中转服务地址
VPS_RELAY_URL = os.environ.get("VPS_RELAY_URL", "http://107.175.49.215:18081")

# 下载文件临时目录
LOCAL_DOWNLOAD_DIR = Path.home() / "Downloads"


def get_relay_url(path: str) -> str:
    """拼接 VPS 中转 URL"""
    return f"{VPS_RELAY_URL}{path}"


async def relay_fetch_page(url: str, timeout: int = 35) -> str:
    """通过 VPS 抓取页面 HTML"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            get_relay_url("/api/fetch"),
            params={"url": url},
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            data = await resp.json()
            if "error" in data:
                raise Exception(f"VPS 中转抓取失败: {data['error']}")
            return data.get("html", "")


async def relay_download_file(download_url: str, local_path: Path, timeout: int = 600) -> dict:
    """从 VPS 下载已转存的文件到本地"""
    url = get_relay_url(download_url)
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            if resp.status != 200:
                raise Exception(f"VPS 文件下载失败: HTTP {resp.status}")
            
            local_path.parent.mkdir(parents=True, exist_ok=True)
            size = 0
            with open(local_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(8192):
                    f.write(chunk)
                    size += len(chunk)
            
            return {
                "success": True,
                "file": str(local_path),
                "size": size,
                "size_mb": round(size / 1024 / 1024, 2),
            }


async def relay_post_json(path: str, payload: dict, timeout: int = 600) -> dict:
    """POST JSON 到 VPS 中转服务"""
    url = get_relay_url(path)
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            return await resp.json()


async def relay_get_json(path: str, params: dict = None, timeout: int = 35) -> dict:
    """GET JSON 从 VPS 中转服务"""
    url = get_relay_url(path)
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
            params=params or {},
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            return await resp.json()


async def check_vps_relay() -> bool:
    """检查 VPS 中转服务是否可用"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                get_relay_url("/api/health"),
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                data = await resp.json()
                return data.get("status") == "ok"
    except Exception:
        return False
