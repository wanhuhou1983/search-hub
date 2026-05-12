"""
本地文件搜索 - Everything CLI (主) + 文件系统搜索 (降级)
"""
import subprocess
import httpx
import os
from pathlib import Path
from config import ES_BIN, EVERYTHING_HTTP_URL, MAX_RESULTS_PER_SOURCE


def _check_everything_running() -> bool:
    """检查 Everything 进程是否在运行"""
    try:
        tasks = subprocess.run(
            ["tasklist", "/NH", "/FI", "IMAGENAME eq Everything.exe"],
            capture_output=True, text=True, timeout=5,
        )
        return "Everything.exe" in tasks.stdout
    except Exception:
        return False


def _filesystem_fallback(q: str) -> dict:
    """降级方案：通过 Python Path.rglob() 搜索文件系统"""
    search_dirs = []
    try:
        from config import OBSIDIAN_VAULT, OBSIDIAN_VAULT2
        if OBSIDIAN_VAULT and OBSIDIAN_VAULT.exists():
            search_dirs.append(OBSIDIAN_VAULT)
        if OBSIDIAN_VAULT2 and OBSIDIAN_VAULT2.exists():
            search_dirs.append(OBSIDIAN_VAULT2)
    except (ImportError, AttributeError):
        pass
    
    # 默认搜索路径
    search_dirs.append(Path.home() / "Downloads")
    search_dirs.append(Path.home() / "Documents")
    
    items = []
    max_results = max(1, min(MAX_RESULTS_PER_SOURCE, 200))
    
    q_lower = q.lower()
    for d in search_dirs:
        if not d.exists():
            continue
        try:
            for f in d.rglob("*"):
                if not f.is_file():
                    continue
                # 文件名匹配
                if q_lower in f.name.lower():
                    items.append({
                        "name": f.name,
                        "path": str(f),
                        "type": "file",
                        "size": f.stat().st_size if f.exists() else 0,
                    })
                    if len(items) >= max_results:
                        break
        except PermissionError:
            continue
        except Exception:
            continue
        if len(items) >= max_results:
            break

    return {"source": "local", "results": items, "total": len(items)}




def _everything_http_search(q: str, timeout: int = 10) -> dict | None:
    """Search via Everything HTTP Server API."""
    if not EVERYTHING_HTTP_URL:
        return None
    try:
        # Fetch HTML results, parse paths from <a href="/X%3A/...">
        resp = httpx.get(EVERYTHING_HTTP_URL, params={"s": q}, timeout=timeout)
        if resp.status_code != 200:
            return None

        import re as _re
        import urllib.parse as _up
        items = []
        seen = set()

        # Everything HTTP result table links look like:
        # <a href="/C%3A/Users/linhu/file.txt"><img...>file.txt</a>
        # Extract href starting with /X%3A/ and decode to real Windows path
        for m in _re.finditer(r'<a href="/([A-Z]%3[Aa][^"]+)"[^>]*>', resp.text):
            href = m.group(1)
            # URL-decode: C%3A -> C:, %20 -> space, etc.
            path = _up.unquote(href)
            # Convert C:/ to C:\ (Windows path format)
            path = path.replace("/", "\\")
            # Make sure it has drive letter:
            if len(path) >= 2 and path[1] == ":" and path[2] != "\\":
                path = path[:2] + "\\" + path[2:]

            if path in seen:
                continue
            seen.add(path)

            name = path.rsplit("\\", 1)[-1] if "\\" in path else path
            items.append({"name": name, "path": path, "type": "file"})
            if len(items) >= MAX_RESULTS_PER_SOURCE:
                break

        if items:
            return {"source": "local", "results": items, "total": len(items)}

        return None
    except Exception as e:
        print(f"[local search] HTTP Everything error: {e}")
        return None

def search(q: str, timeout: int = 10):
    """搜索本地文件：优先 Everything CLI，降级到文件系统搜索"""
    if not q.strip():
        return {"source": "local", "results": [], "total": 0}

    # 尝试 Everything HTTP 服务（优先）
    result = _everything_http_search(q, timeout)
    if result:
        return result

    # 尝试 Everything CLI（降级）
    es_available = ES_BIN and os.path.isfile(ES_BIN)
    if es_available and _check_everything_running():
        cmd = [ES_BIN, "-n", str(max(1, min(MAX_RESULTS_PER_SOURCE, 1000))), q]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            lines = [l.strip() for l in result.stdout.split("\n") if l.strip()]
            if result.returncode == 0 or lines:
                items = []
                for raw_path in lines:
                    path = raw_path
                    if len(path) >= 2 and path[1] == ':' and path[2:3] != '\\':
                        path = path[:2] + '\\' + path[2:]
                    items.append({
                        "name": path.split("\\")[-1] or path,
                        "path": path,
                        "type": "file",
                    })
                return {"source": "local", "results": items, "total": len(items)}
        except FileNotFoundError:
            pass  # 降级
        except subprocess.TimeoutExpired:
            pass  # 降级
        except Exception:
            pass  # 降级

    # 降级到文件系统搜索
    return _filesystem_fallback(q)
