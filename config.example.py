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
from pathlib import Path

# ========== 本地搜索 ==========
ES_BIN = r"C:\path\to\es.exe"

# ========== Obsidian Vault ==========
OBSIDIAN_VAULT = Path(r"/path/to/your/vault")
OBSIDIAN_VAULT2 = Path(r"/path/to/your/vault2")

# ========== 百度网盘 ==========
BAIDU_ACCESS_TOKEN = os.environ.get("BAIDU_ACCESS_TOKEN", "")

# ========== 115网盘 ==========
P115_COOKIE = os.environ.get("P115_COOKIE", "")

# ========== 夸克网盘 ==========
QUARK_COOKIE_FILE = Path(os.environ.get("QUARK_COOKIE_FILE", ""))

# ========== Z-Library ==========
ZLIB_SEARCH_URL = "https://1lib.s/s/{}"

# ========== 搜索配置 ==========
SEARCH_TIMEOUT = 60
MAX_RESULTS_PER_SOURCE = 100
