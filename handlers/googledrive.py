"""
Google Drive 搜索 - 通过 gws CLI 调用 Google Drive API v3
"""

import json
import os
import subprocess
import shutil
from config import GOOGLE_DRIVE_SEARCH_ENABLED, MAX_RESULTS_PER_SOURCE

_GWS_PATHS = [
    shutil.which("gws"),
    os.path.expanduser(r"~\AppData\Roaming\npm\gws"),
    os.path.expanduser(r"~\AppData\Roaming\npm\gws.cmd"),
    r"C:\Program Files\nodejs\node_modules\@googleworkspace\gws\bin\run.js",
]


def _find_gws() -> str | None:
    """查找 gws CLI 路径"""
    for p in _GWS_PATHS:
        if p and os.path.isfile(p):
            return p
    return None


def _gws_available() -> bool:
    return _find_gws() is not None


def _gws_authenticated() -> tuple[bool, str]:
    """检查 gws 认证状态，返回 (ok, msg)"""
    gws_bin = _find_gws()
    if not gws_bin:
        return False, "gws CLI 未安装"
    try:
        r = subprocess.run(
            [gws_bin, "auth", "status"],
            capture_output=True, text=True, timeout=15,
        )
        out = r.stdout.strip()
        if '"credential_source": "none"' in out:
            return False, "gws 未认证，请运行: gws auth login"
        if '"credential_source"' in out:
            return True, ""
        return False, "gws 认证状态异常"
    except FileNotFoundError:
        return False, "gws CLI 未安装"
    except Exception as e:
        return False, f"gws 检查失败: {e}"


def search(q: str, timeout: int = 30):
    if not q.strip():
        return {"source": "googledrive", "results": [], "total": 0}

    if not GOOGLE_DRIVE_SEARCH_ENABLED:
        return {"source": "googledrive", "error": "Google Drive 搜索已禁用", "results": []}

    gws_bin = _find_gws()
    if not gws_bin:
        return {
            "source": "googledrive",
            "error": "gws CLI 未安装，请 npm install -g @googleworkspace/gws",
            "results": [],
        }

    authed, msg = _gws_authenticated()
    if not authed:
        return {"source": "googledrive", "error": msg, "results": []}

    try:
        params = json.dumps({"q": f"name contains '{q}'", "pageSize": 100})
        cmd = [gws_bin, "drive", "files", "list", "--format", "json", "--params", params]

        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )

        if r.returncode != 0:
            return {
                "source": "googledrive",
                "error": f"gws 调用失败: {r.stderr[:200]}",
                "results": [],
            }

        # 解析 NDJSON 输出（每行一个 JSON）
        files = []
        for line in r.stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            name = item.get("name", "")
            fid = item.get("id", "")
            mime = item.get("mimeType", "")
            is_dir = mime == "application/vnd.google-apps.folder"
            size = int(item.get("size", 0))

            files.append({
                "name": name,
                "path": name,
                "is_dir": is_dir,
                "size": size,
                "id": fid,
                "mimeType": mime,
                "source": "googledrive",
            })
            if len(files) >= MAX_RESULTS_PER_SOURCE:
                break

        return {"source": "googledrive", "results": files, "total": len(files)}

    except subprocess.TimeoutExpired:
        return {"source": "googledrive", "error": "超时", "results": []}
    except Exception as e:
        return {"source": "googledrive", "error": str(e), "results": []}
