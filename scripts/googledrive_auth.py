"""
Google Drive 授权脚本 - 一次性运行，打开浏览器授权后即可使用
"""
import json
import sys
from pathlib import Path

# 确保能导入项目的 config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import GOOGLE_DRIVE_CLIENT_ID, GOOGLE_DRIVE_CLIENT_SECRET

if not GOOGLE_DRIVE_CLIENT_ID or not GOOGLE_DRIVE_CLIENT_SECRET:
    print("❌ 错误：config.py 中未配置 GOOGLE_DRIVE_CLIENT_ID 和 GOOGLE_DRIVE_CLIENT_SECRET")
    sys.exit(1)

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
TOKEN_PATH = Path.home() / ".workbuddy" / "googledrive_token.json"

flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": GOOGLE_DRIVE_CLIENT_ID,
            "client_secret": GOOGLE_DRIVE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    },
    SCOPES,
)

print("🔐 正在打开浏览器进行 Google 授权...")
creds = flow.run_local_server(port=0, open_browser=True)

with open(TOKEN_PATH, "w") as f:
    f.write(creds.to_json())

print(f"✅ 授权成功！Token 已保存到 {TOKEN_PATH}")
print("   现在可以重启 search-hub 搜索 Google Drive 了")
