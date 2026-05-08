"""
本地文件搜索 - Everything CLI
"""

import subprocess
import os
import shlex
from config import ES_BIN, MAX_RESULTS_PER_SOURCE


def _check_everything_running() -> bool:
    """检查 Everything 进程是否在运行"""
    try:
        tasks = subprocess.run(
            ["tasklist", "/NH", "/FI", "IMAGENAME eq Everything.exe"],
            capture_output=True, text=True, timeout=5,
        )
        return "Everything.exe" in tasks.stdout
    except Exception:
        return False


def search(q: str, timeout: int = 10):
    """使用 es.exe 搜索本地文件"""
    if not q.strip():
        return {"source": "local", "results": [], "total": 0}

    # 先检查 Everything 是否在运行
    if not _check_everything_running():
        return {
            "source": "local", "error": "Everything 服务未运行，请先打开 Everything 客户端",
            "results": [],
        }

    cmd = [ES_BIN, "-n", str(max(1, min(MAX_RESULTS_PER_SOURCE, 1000))), q]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )

        # es.exe 返回非零退出码但可能有结果
        lines = [l.strip() for l in result.stdout.split("\n") if l.strip()]
        if result.returncode != 0 and not lines:
            err_msg = result.stderr.strip() or "es.exe 执行异常（退出码 {})".format(result.returncode)
            return {"source": "local", "error": err_msg, "results": []}

        items = []
        for raw_path in lines:
            # 修复盘符路径格式：E:图书馆 → E:\图书馆
            path = raw_path
            if len(path) >= 2 and path[1] == ':' and path[2:3] != '\\':
                path = path[:2] + '\\' + path[2:]
            items.append({
                "name": path.split("\\")[-1] or path,
                "path": path,
                "type": "file",
            })

        return {"source": "local", "results": items, "total": len(items)}

    except subprocess.TimeoutExpired:
        return {"source": "local", "error": "es.exe 搜索超时（{}s），请缩小搜索范围".format(timeout), "results": []}
    except FileNotFoundError:
        return {"source": "local", "error": "es.exe 未找到（{}），请检查 config.py 中 ES_BIN 路径".format(ES_BIN), "results": []}
    except Exception as e:
        return {"source": "local", "error": "本地搜索异常: {}".format(str(e)), "results": []}
