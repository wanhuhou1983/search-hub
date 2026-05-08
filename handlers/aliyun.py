"""
阿里云盘搜索与下载 - 优先本地索引，回退 aligo SDK

首次使用需要扫码登录，token 会缓存到 ~/.aligo/ 目录。
"""

import os
import threading
from pathlib import Path
from config import MAX_RESULTS_PER_SOURCE
from handlers.disk_common import load_index, search_local

_ali = None
_ali_lock = threading.Lock()


def _get_ali():
    """懒加载 aligo 客户端（线程安全）"""
    global _ali
    if _ali is None:
        with _ali_lock:
            if _ali is None:
                try:
                    from aligo import Aligo
                    # 静默初始化，失败时抛异常
                    _ali = Aligo(show=False)
                except Exception as e:
                    raise RuntimeError(f"阿里云盘登录失败: {e}，请先扫码登录") from e
    return _ali


def _load_or_fallback():
    """尝试加载本地索引"""
    files = load_index("aliyun")
    return files


def search(q: str, timeout: int = 30) -> dict:
    """搜索阿里云盘文件"""
    if not q.strip():
        return {"source": "aliyun", "results": [], "total": 0}

    # 优先本地索引
    cached = _load_or_fallback()
    if cached is not None:
        results = search_local(cached, q, MAX_RESULTS_PER_SOURCE)
        if results:  # 有结果才用缓存
            return {
                "source": "aliyun",
                "results": results[:MAX_RESULTS_PER_SOURCE],
                "total": len(results),
                "cached": True,
            }

    # 回退：实时 aligo API 搜索
    try:
        ali = _get_ali()
        from aligo import BaseFile
        results = ali.search_files(name=q, limit=MAX_RESULTS_PER_SOURCE)
        items = []
        for f in (results or []):
            items.append({
                "name": f.name,
                "path": f.name,
                "id": f.file_id,
                "is_dir": f.type == "folder",
                "size": f.size or 0,
                "parent_id": f.parent_file_id,
                "source": "aliyun",
            })
        return {"source": "aliyun", "results": items, "total": len(items)}
    except RuntimeError as e:
        return {"source": "aliyun", "error": str(e), "results": []}
    except Exception as e:
        return {"source": "aliyun", "error": str(e), "results": []}


def download_url(file_id: str, _=None) -> str | None:
    """获取阿里云盘文件下载链接"""
    try:
        ali = _get_ali()
        dl = ali.get_download_url(file_id)
        if dl and dl.url:
            return dl.url
        return None
    except Exception:
        return None
