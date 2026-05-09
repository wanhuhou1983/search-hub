"""
统一搜索中心 - 配置模板

用法：
  1. 复制此文件为 config.py
  2. 填写你的认证信息
  3. config.py 已被 .gitignore 排除，不会被提交

或通过环境变量注入（推荐）：
  export BAIDU_ACCESS_TOKEN="your_token"
  export P115_COOKIE="your_cookie"
"""

import os
import shutil
from pathlib import Path

# ========== 本地搜索 ==========
ES_BIN = os.environ.get("ES_BIN", r"C:\path\to\es.exe")

# ========== 外部工具路径（留空则自动从 PATH 查找）==========
YTDLP_BIN = os.environ.get("YTDLP_BIN", "")  # yt-dlp，留空自动 shutil.which
FFMPEG_BIN = os.environ.get("FFMPEG_BIN", "")  # ffmpeg，留空自动 shutil.which

def _resolve_tool(env_val: str, name: str) -> str:
    """解析工具路径：环境变量 > shutil.which > 空字符串"""
    if env_val and os.path.isfile(env_val):
        return env_val
    found = shutil.which(name)
    return found or ""

# ========== 夸克网盘额外 site-packages 路径 ==========
# 如果 quark_client 不在标准路径，设置此值
# 通常在 Docker 或 venv 环境下不需要设置
QUARK_EXTRA_SITE_PACKAGES = os.environ.get("QUARK_EXTRA_SITE_PACKAGES", "")

# ========== Obsidian Vault ==========
OBSIDIAN_VAULT = Path(r"/path/to/your/vault")
OBSIDIAN_VAULT2 = Path(r"/path/to/your/vault2")

# ========== 百度网盘 ==========
BAIDU_ACCESS_TOKEN = os.environ.get("BAIDU_ACCESS_TOKEN", "")
BAIDU_REFRESH_TOKEN = os.environ.get("BAIDU_REFRESH_TOKEN", "")
BAIDU_APP_KEY = os.environ.get("BAIDU_APP_KEY", "")
BAIDU_SECRET_KEY = os.environ.get("BAIDU_SECRET_KEY", "")

# ========== 115网盘 ==========
P115_COOKIE = os.environ.get("P115_COOKIE", "")

# ========== 夸克网盘 ==========
QUARK_COOKIE_FILE = Path(os.environ.get("QUARK_COOKIE_FILE",
    str(Path.home() / ".workbuddy" / "skills" / "quark-storage" / "quark_cookies.json")))

# ========== Z-Library ==========
ZLIB_SEARCH_URL = "https://1lib.s/s/{}"

# ========== Google Drive ==========
GOOGLE_DRIVE_SEARCH_ENABLED = os.environ.get("GOOGLE_DRIVE_SEARCH_ENABLED", "true").lower() == "true"
GOOGLE_DRIVE_CLIENT_ID = os.environ.get("GOOGLE_DRIVE_CLIENT_ID", "")
GOOGLE_DRIVE_CLIENT_SECRET = os.environ.get("GOOGLE_DRIVE_CLIENT_SECRET", "")

# ========== iCloud Drive ==========
ICLOUD_ACCOUNT = os.environ.get("ICLOUD_ACCOUNT", "")
ICLOUD_PASSWORD = os.environ.get("ICLOUD_PASSWORD", "")

# ========== VPS 视频中转 ==========
VPS_RELAY_URL = os.environ.get("VPS_RELAY_URL", "http://your-vps:18081")
VPS_RELAY_ENABLED = os.environ.get("VPS_RELAY_ENABLED", "auto").lower()

# ========== iCloud Drive ==========
ICLOUD_ACCOUNT = os.environ.get("ICLOUD_ACCOUNT", "")
ICLOUD_PASSWORD = os.environ.get("ICLOUD_PASSWORD", "")
# pyicloud 需要 USERNAME 环境变量，留空则使用当前用户
ICLOUD_USERNAME = os.environ.get("ICLOUD_USERNAME", "")

# ========== VPS 视频中转 ==========
VPS_RELAY_URL = os.environ.get("VPS_RELAY_URL", "http://your-vps:18081")
VPS_RELAY_ENABLED = os.environ.get("VPS_RELAY_ENABLED", "auto").lower()
# 设为 "true" 则跳过本地直连，始终走 VPS 中转（适合墙内环境）
USE_VPS_RELAY_BY_DEFAULT = os.environ.get("USE_VPS_RELAY_BY_DEFAULT", "false").lower() == "true"

# ========== 搜索配置 ==========
SEARCH_TIMEOUT = 60
MAX_RESULTS_PER_SOURCE = 100
