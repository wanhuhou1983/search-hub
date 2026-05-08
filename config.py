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
BAIDU_ACCESS_TOKEN = os.environ.get("BAIDU_ACCESS_TOKEN", "121.477a6b445387c78b8e82efb34c8edf63.YGRPeo3N4EJg1um7rPBS9Ix45tXLV7HpIg2_2rT.qgS5rA")
BAIDU_REFRESH_TOKEN = os.environ.get("BAIDU_REFRESH_TOKEN", "122.ef742939faedb10e85c20255f9ccab40.YH5fvZDRg9-eD-oLAjJOPtRR6U8sY4rRbRrg1pp.7RDw-Q")
BAIDU_APP_KEY = os.environ.get("BAIDU_APP_KEY", "uraMTdgEEtwfShXL3G2drGBaghJoCzOk")
BAIDU_SECRET_KEY = os.environ.get("BAIDU_SECRET_KEY", "aOmlTXNgTpULDzhaRSFFxCZFAj4opqMM")

# ========== 115网盘 Cookie ==========
# 安全提示：建议通过环境变量 P115_COOKIE 设置
# 通过 Chrome MCP 从 115.com 自动提取
P115_COOKIE = os.environ.get("P115_COOKIE", "USERSESSIONID=582b56c6e3e0d0bae9c28784f412975dd86a68aa8c642df44c8e6d56d406bf18; 115_lang=zh; GST=2ca6cd466a1cbc316ec3159e4114b1af; UID=99999320_A1_1778241706; CID=04fdea0f43fccf533e8bcc60aac4c450; SEID=1364c5729fb1cfeabca426cb4e67b364103b3ac3211d039d17530aee061fb61c8faeedeb80ef66b4177f10f187959591b682bb2ec01c5d4968e15451; KID=84bb60e1149491067f91775cd18c9c0f; acw_tc=784e2ca117782417092954531e6218b06b15659e3c996c1ae6f34ecd38d5b1")

# ========== 夸克网盘 ==========
QUARK_COOKIE_FILE = Path(
    os.environ.get("QUARK_COOKIE_FILE",
                   str(Path.home() / ".workbuddy" / "skills" / "quark-storage" / "quark_cookies.json"))
)

# ========== Z-Library ==========
ZLIB_SEARCH_URL = os.environ.get("ZLIB_SEARCH_URL", "https://1lib.s/s/{}")

# ========== Google Drive ==========
# gws CLI 认证：在命令行执行 gws auth login
GOOGLE_DRIVE_SEARCH_ENABLED = os.environ.get("GOOGLE_DRIVE_SEARCH_ENABLED", "true").lower() == "true"

# ========== iCloud Drive ==========
# 安全提示：建议通过环境变量 ICONUT_CLOUD_ACCOUNT / ICONUT_CLOUD_PASSWORD 设置
# 如果启用两步验证，请使用 App-Specific Password
ICLOUD_ACCOUNT = os.environ.get("ICLOUD_ACCOUNT", "linhu50115@hotmail.com")
ICLOUD_PASSWORD = os.environ.get("ICLOUD_PASSWORD", "17512039Bb")

# ========== 搜索配置 ==========
SEARCH_TIMEOUT = int(os.environ.get("SEARCH_TIMEOUT", "60"))
MAX_RESULTS_PER_SOURCE = int(os.environ.get("MAX_RESULTS_PER_SOURCE", "100"))
