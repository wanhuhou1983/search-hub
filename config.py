"""
统一搜索中心 - 配置

敏感信息通过环境变量注入，优先读取环境变量，无环境变量时使用默认值。
本地路径配置可直接修改。
"""

import os
from pathlib import Path

# ========== 本地搜索 ==========
# es.exe (Everything CLI) 路径
ES_BIN = os.environ.get(
    "ES_BIN",
    r"C:\Users\linhu\.workbuddy\binaries\es.exe"
)

# ========== Obsidian Vault ==========
OBSIDIAN_VAULT = Path(
    os.environ.get("OBSIDIAN_VAULT",
                   r"C:\Users\linhu\Documents\GitHub\wanhuhou_vault")
)
OBSIDIAN_VAULT2 = Path(
    os.environ.get("OBSIDIAN_VAULT2",
                   r"C:\Users\linhu\Documents\GitHub\infohub")
)

# ========== 百度网盘 Access Token ==========
# 安全提示：建议通过环境变量 BAIDU_ACCESS_TOKEN 设置
# 有效期30天，可用 scripts/baidu_token_refresh.py 自动续期
BAIDU_ACCESS_TOKEN = os.environ.get("BAIDU_ACCESS_TOKEN", "")
BAIDU_REFRESH_TOKEN = os.environ.get("BAIDU_REFRESH_TOKEN", "")
BAIDU_APP_KEY = os.environ.get("BAIDU_APP_KEY", "")
BAIDU_SECRET_KEY = os.environ.get("BAIDU_SECRET_KEY", "")

# ========== 115网盘 Cookie ==========
# 安全提示：建议通过环境变量 P115_COOKIE 设置
# 通过 Chrome MCP 从 115.com 自动提取
P115_COOKIE = os.environ.get("P115_COOKIE", "")

# ========== 夸克网盘 ==========
QUARK_COOKIE_FILE = Path(
    os.environ.get("QUARK_COOKIE_FILE",
                   str(Path.home() / ".workbuddy" / "skills" / "quark-storage" / "quark_cookies.json"))
)

# ========== Z-Library ==========
ZLIB_SEARCH_URL = os.environ.get("ZLIB_SEARCH_URL", "https://1lib.s/s/{}")

# ========== Google Drive ==========
# 先运行 scripts/googledrive_auth.py 进行一次浏览器授权
# Token 自动保存到 ~/.workbuddy/googledrive_token.json
GOOGLE_DRIVE_SEARCH_ENABLED = os.environ.get("GOOGLE_DRIVE_SEARCH_ENABLED", "true").lower() == "true"
GOOGLE_DRIVE_CLIENT_ID = os.environ.get("GOOGLE_DRIVE_CLIENT_ID", "")
GOOGLE_DRIVE_CLIENT_SECRET = os.environ.get("GOOGLE_DRIVE_CLIENT_SECRET", "")

# ========== iCloud Drive ==========
# 安全提示：建议通过环境变量 ICONUT_CLOUD_ACCOUNT / ICONUT_CLOUD_PASSWORD 设置
# 如果启用两步验证，请使用 App-Specific Password
ICLOUD_ACCOUNT = os.environ.get("ICLOUD_ACCOUNT", "")
ICLOUD_PASSWORD = os.environ.get("ICLOUD_PASSWORD", "")

# ========== VPS 视频中转 ==========
# 本地被 block 时通过 VPS 中转下载视频
VPS_RELAY_URL = os.environ.get("VPS_RELAY_URL", "http://107.175.49.215:18081")
VPS_RELAY_ENABLED = os.environ.get("VPS_RELAY_ENABLED", "auto").lower()  # auto/always/off

# ========== 搜索配置 ==========
SEARCH_TIMEOUT = int(os.environ.get("SEARCH_TIMEOUT", "60"))
MAX_RESULTS_PER_SOURCE = int(os.environ.get("MAX_RESULTS_PER_SOURCE", "100"))
