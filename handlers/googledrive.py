"""
Google Drive 搜索 - 通过 Google Drive API v3 (Python SDK)
"""

import json
import os
import pickle
from pathlib import Path
from config import (
    GOOGLE_DRIVE_CLIENT_ID,
    GOOGLE_DRIVE_CLIENT_SECRET,
    GOOGLE_DRIVE_SEARCH_ENABLED,
    MAX_RESULTS_PER_SOURCE,
)

_TOKEN_PATH = Path.home() / ".workbuddy" / "googledrive_token.json"
_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def _get_credentials():
    """读取已保存的 token，自动刷新过期的"""
    if not _TOKEN_PATH.exists():
        return None

    try:
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(str(_TOKEN_PATH), _SCOPES)
        if creds and creds.valid:
            return creds
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            with open(_TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
            return creds
    except Exception:
        pass
    return None


def search(q: str, timeout: int = 30):
    if not q.strip():
        return {"source": "googledrive", "results": [], "total": 0}

    if not GOOGLE_DRIVE_SEARCH_ENABLED:
        return {"source": "googledrive", "error": "Google Drive 搜索已禁用", "results": []}

    if not GOOGLE_DRIVE_CLIENT_ID or not GOOGLE_DRIVE_CLIENT_SECRET:
        return {
            "source": "googledrive",
            "error": "Google OAuth 凭据未配置，请在 config.py 中设置 GOOGLE_DRIVE_CLIENT_ID 和 GOOGLE_DRIVE_CLIENT_SECRET",
            "results": [],
        }

    creds = _get_credentials()
    if not creds:
        return {
            "source": "googledrive",
            "error": "Google Drive 未授权。请运行一次授权脚本：\n"
                     f"  cd search-hub && python scripts/googledrive_auth.py\n"
                     "浏览器会弹出，授权后即可使用",
            "results": [],
        }

    try:
        from googleapiclient.discovery import build
        service = build("drive", "v3", credentials=creds, cache_discovery=False)

        page_size = min(MAX_RESULTS_PER_SOURCE, 100)
        results = []
        page_token = None

        while len(results) < MAX_RESULTS_PER_SOURCE:
            resp = service.files().list(
                q=f"name contains '{q}' and trashed=false",
                pageSize=page_size,
                fields="nextPageToken, files(id, name, mimeType, size, parents)",
                pageToken=page_token,
                orderBy="modifiedTime desc",
            ).execute()

            for item in resp.get("files", []):
                name = item.get("name", "")
                fid = item.get("id", "")
                mime = item.get("mimeType", "")
                is_dir = mime == "application/vnd.google-apps.folder"
                size = int(item.get("size", 0))
                results.append({
                    "name": name,
                    "path": name,
                    "is_dir": is_dir,
                    "size": size,
                    "id": fid,
                    "mimeType": mime,
                    "source": "googledrive",
                })
                if len(results) >= MAX_RESULTS_PER_SOURCE:
                    break

            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        return {"source": "googledrive", "results": results, "total": len(results)}

    except Exception as e:
        emsg = str(e)
        if "quota" in emsg.lower():
            return {"source": "googledrive", "error": "Google Drive API 配额不足，请稍后再试", "results": []}
        if "invalid_grant" in emsg or "token_expired" in emsg:
            # Token 失效，删除重试
            _TOKEN_PATH.unlink(missing_ok=True)
            return {"source": "googledrive", "error": "Token 已失效，请重新运行授权脚本", "results": []}
        return {"source": "googledrive", "error": f"Google Drive 搜索失败: {emsg[:200]}", "results": []}
