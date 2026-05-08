#!/usr/bin/env python3
"""
token_check.py - 网盘 Token/Cookie 有效性检查

检查四个网盘的认证凭据状态：
- 百度网盘: access_token (依赖环境变量)
- 115网盘: cookie (依赖环境变量)
- 夸克网盘: cookie (依赖文件)
- 阿里云盘: refresh_token (自动续期)

用法:
  python token_check.py [--json]
"""

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path

# ── 配置 ──
SEARCH_HUB_DIR = Path(__file__).parent.parent
DATA_DIR = SEARCH_HUB_DIR / "data"

# 从 config.py 读取凭据（优先环境变量）
sys.path.insert(0, str(SEARCH_HUB_DIR))
try:
    import config as _cfg
    BAIDU_TOKEN = getattr(_cfg, 'BAIDU_ACCESS_TOKEN', os.environ.get('BAIDU_ACCESS_TOKEN', ''))
    P115_COOKIE_VAL = getattr(_cfg, 'P115_COOKIE', os.environ.get('P115_COOKIE', ''))
except Exception:
    BAIDU_TOKEN = os.environ.get('BAIDU_ACCESS_TOKEN', '')
    P115_COOKIE_VAL = os.environ.get('P115_COOKIE', '')


def check_baidu() -> dict:
    """检查百度网盘 access_token"""
    token = BAIDU_TOKEN
    if not token:
        return {
            "name": "百度网盘",
            "status": "NONE",
            "detail": "缺少 BAIDU_ACCESS_TOKEN 环境变量",
            "expires": "—",
            "fix": "设置环境变量或更新 config.py",
        }

    try:
        import requests
    except ImportError:
        return {
            "name": "百度网盘",
            "status": "FAIL",
            "detail": "缺少 requests 库",
            "expires": "—",
            "fix": "pip install requests",
        }
    try:
        r = requests.get(
            "https://pan.baidu.com/rest/2.0/xpan/file?method=search",
            params={
                "access_token": token,
                "key": "test",
                "num": 1,
                "path": "/",
                "recursion": 1,
            },
            timeout=10,
        )
        data = r.json()
        if data.get("errno") == 0:
            return {
                "name": "百度网盘",
                "status": "OK",
                "detail": f"用户: {data.get('baidu_name', 'N/A')}",
                "expires": "约1-3天（可自动续期30天）",
                "fix": "无需操作",
            }
        elif data.get("errno") == -6:
            return {
                "name": "百度网盘",
                "status": "EXPIRED",
                "detail": "access_token 已失效 (errno=-6)",
                "expires": "已过期",
                "fix": "重新获取 refresh_token → 换新的 access_token",
            }
        else:
            return {
                "name": "百度网盘",
                "status": "WARN",
                "detail": f"errno={data.get('errno')}: {data.get('errmsg', '')}",
                "expires": "—",
                "fix": "检查 Token 是否正确",
            }
    except requests.Timeout:
        return {
            "name": "百度网盘",
            "status": "TIMEOUT",
            "detail": "API 请求超时",
            "expires": "—",
            "fix": "稍后重试",
        }
    except Exception as e:
        return {
            "name": "百度网盘",
            "status": "ERR",
            "detail": str(e),
            "expires": "—",
            "fix": "检查网络或 Token",
        }


def check_p115() -> dict:
    """检查115网盘 cookie"""
    cookie = P115_COOKIE_VAL
    if not cookie:
        return {
            "name": "115网盘",
            "status": "NONE",
            "detail": "缺少 P115_COOKIE 环境变量",
            "expires": "—",
            "fix": "设置环境变量 P115_COOKIE",
        }

    try:
        import requests
        headers = {
            "Cookie": cookie,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": "https://115.com",
            "Referer": "https://115.com/",
        }
        r = requests.get(
            "https://webapi.115.com/files/index_info?count_space_nums=1",
            headers=headers,
            timeout=10,
        )
        data = r.json()
        if data.get("state"):
            info = data.get("data", {}).get("space_info", {})
            total = info.get("all_total", {}).get("size_format", "N/A")
            return {
                "name": "115网盘",
                "status": "OK",
                "detail": f"空间: {total}",
                "expires": "通常3-6个月，取决于活跃度",
                "fix": "无需操作",
            }
        else:
            return {
                "name": "115网盘",
                "status": "INVALID",
                "detail": data.get("msg", "cookie 无效"),
                "expires": "已过期",
                "fix": "重新从浏览器复制 cookie",
            }
    except Exception as e:
        return {
            "name": "115网盘",
            "status": "ERR",
            "detail": str(e),
            "expires": "—",
            "fix": "检查网络或 Cookie",
        }


def check_quark() -> dict:
    """检查夸克网盘 cookie"""
    cookie_file = Path(os.environ.get(
        "QUARK_COOKIE_FILE",
        str(Path.home() / ".workbuddy" / "skills" / "quark-storage" / "quark_cookies.json"),
    ))

    if not cookie_file.exists():
        return {
            "name": "夸克网盘",
            "status": "NONE",
            "detail": f"Cookie 文件不存在: {cookie_file}",
            "expires": "—",
            "fix": "先登录夸克：运行 quark login",
        }

    try:
        import json
        with open(cookie_file) as f:
            content = f.read().strip()
            if not content:
                raise ValueError("空文件")
            data = json.loads(content)

        cookie_str = data.get("cookie", data.get("Cookie", ""))
        if not cookie_str:
            return {
                "name": "夸克网盘",
                "status": "CFG_ERR",
                "detail": "Cookie 文件格式不正确",
                "expires": "—",
                "fix": "检查 quark_cookies.json 格式",
            }

        # 尝试访问夸克
        import requests
        r = requests.get(
            "https://drive-pc.quark.cn/1/clouddrive/auth/pc/flush?pr=ucpro&fr=pc&uc_param_str=",
            headers={
                "Cookie": cookie_str,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
            timeout=10,
        )
        data = r.json()
        if data.get("code") == 0:
            return {"name": "夸克网盘", "status": "OK", "detail": "登录正常", "expires": "约30天", "fix": "无需操作"}
        elif data.get("code") == 40100:
            return {"name": "夸克网盘", "status": "EXPIRED", "detail": "cookie 已失效 (40100)", "expires": "已过期", "fix": "重新登录夸克"}
        else:
            return {"name": "夸克网盘", "status": "WARN", "detail": f"code={data.get('code')}", "expires": "—", "fix": "检查 Cookie"}
    except Exception as e:
        return {"name": "夸克网盘", "status": "ERR", "detail": str(e), "expires": "—", "fix": "检查 Cookie 文件"}


def check_aliyun() -> dict:
    """检查阿里云盘 refresh_token"""
    # 抑制 aligo stdout 日志（走 stderr）
    import os, sys
    _old_out = sys.stdout
    sys.stdout = sys.stderr
    try:
        from aligo import Aligo
    finally:
        sys.stdout = _old_out

    config_dir = Path.home() / ".aligo"
    config_file = config_dir / "aligo.json"

    if not config_file.exists():
        return {
            "name": "阿里云盘",
            "status": "NOLOGIN",
            "detail": f"配置文件不存在: {config_file}",
            "expires": "—",
            "fix": "运行 aliyun login --token <refresh_token>",
        }

    try:
        # 抑制 aligo 运行时日志
        _old_out = sys.stdout
        sys.stdout = sys.stderr
        try:
            cli = Aligo(show=False)
            user = cli.get_user()
            cap = cli.get_user_capacity_info()
        finally:
            sys.stdout = _old_out

        used_gb = cap.drive_capacity_details.drive_used_size / (1024 ** 3)
        total_gb = cap.drive_capacity_details.drive_total_size / (1024 ** 3)
        return {
            "name": "阿里云盘",
            "status": "OK",
            "detail": f"用户: {user.user_name} | {used_gb:.1f}/{total_gb:.0f} GB",
            "expires": "refresh_token 长期有效（SDK 自动续期）",
            "fix": "无需操作",
        }
    except Exception as e:
        return {
            "name": "阿里云盘",
            "status": "ERR",
            "detail": str(e),
            "expires": "—",
            "fix": "重新运行 login",
        }


def main():
    use_json = "--json" in sys.argv

    checks = [
        check_baidu(),
        check_p115(),
        check_quark(),
        check_aliyun(),
    ]

    if use_json:
        print(json.dumps(checks, ensure_ascii=False, indent=2))
        return

    # 表格输出
    print(f"\n{'='*70}")
    print(f"  网盘 Token/Cookie 状态检查  ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    print(f"{'='*70}")
    print()
    print(f"{'网盘':<12} {'状态':<20} {'详情':<30}")
    print(f"{'-'*62}")
    for c in checks:
        print(f"{c['name']:<12} {c['status']:<20} {c['detail']:<30}")
    print(f"{'-'*62}")
    print()
    for c in checks:
        if c['status'] not in ('OK', '—'):
            print(f"  ⚠️  {c['name']}: {c['fix']}")
    print()

    valid = sum(1 for c in checks if c['status'] == 'OK')
    total = len(checks)
    print(f"  摘要: {valid}/{total} 个网盘认证正常")
    print()


if __name__ == "__main__":
    main()
