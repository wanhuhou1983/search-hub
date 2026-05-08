"""
统一搜索中心 - 配置

所有认证信息集中管理。
"""

from pathlib import Path

# ========== 本地搜索 ==========
ES_BIN = r"C:\Users\linhu\.workbuddy\binaries\es.exe"

# ========== Obsidian Vault ==========
OBSIDIAN_VAULT = Path(r"C:\Users\linhu\Documents\GitHub\wanhuhou_vault")
OBSIDIAN_VAULT2 = Path(r"C:\Users\linhu\Documents\GitHub\infohub")

# ========== 百度网盘 ==========
BAIDU_ACCESS_TOKEN = "123.c20c8814deb06f9733dc4b24dfd34003.Y7Wub9ay1msjpbKemnyj-EECKvy56-MSB6wpkHT.Vett3g"

# ========== 115网盘 ==========
P115_COOKIE = (
    "UID=99999320_A1_1778115175; "
    "CID=3ee3a513f8a7d06ccbf7548b378de379; "
    "SEID=eb005e98e5f1b33e63a806e272c72e0eb8b9c244b4d2aa6b00abe3a4c38f1072103d8eb635bb3a975d545995a38be101b354d7e32c306bb925aef822; "
    "KID=45d3dfdaa9d1e87de11c0ce9b13e59d1"
)

# ========== 夸克网盘 ==========
QUARK_COOKIE_FILE = Path(r"C:\Users\linhu\.workbuddy\skills\quark-storage\quark_cookies.json")

# ========== Z-Library ==========
ZLIB_SEARCH_URL = "https://1lib.s/s/{}"

# ========== 搜索配置 ==========
SEARCH_TIMEOUT = 60         # 每个源超时（秒，115较慢设大些）
MAX_RESULTS_PER_SOURCE = 100  # 每个源最多返回
