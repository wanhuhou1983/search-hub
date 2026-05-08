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
BAIDU_ACCESS_TOKEN = os.environ.get("BAIDU_ACCESS_TOKEN", "")

# ========== 115网盘 Cookie ==========
# 安全提示：建议通过环境变量 P115_COOKIE 设置
P115_COOKIE = os.environ.get("P115_COOKIE", "")

# ========== 夸克网盘 ==========
QUARK_COOKIE_FILE = Path(
    os.environ.get("QUARK_COOKIE_FILE",
                   str(Path.home() / ".workbuddy" / "skills" / "quark-storage" / "quark_cookies.json"))
)

# ========== Z-Library ==========
ZLIB_SEARCH_URL = os.environ.get("ZLIB_SEARCH_URL", "https://1lib.s/s/{}")

# ========== 搜索配置 ==========
SEARCH_TIMEOUT = int(os.environ.get("SEARCH_TIMEOUT", "60"))
MAX_RESULTS_PER_SOURCE = int(os.environ.get("MAX_RESULTS_PER_SOURCE", "100"))
