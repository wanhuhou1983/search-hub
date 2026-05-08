"""
本地文件搜索 - Everything CLI
"""

import subprocess
import shlex
from config import ES_BIN, MAX_RESULTS_PER_SOURCE

def search(q: str, timeout: int = 10):
    """使用 es.exe 搜索本地文件"""
    if not q.strip():
        return []

    cmd = [ES_BIN, "-n", str(MAX_RESULTS_PER_SOURCE), q]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            return {"error": f"es.exe error: {result.stderr.strip()}", "results": []}

        lines = [l.strip() for l in result.stdout.split("\n") if l.strip()]
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
        return {"source": "local", "error": "超时", "results": []}
    except FileNotFoundError:
        return {"source": "local", "error": "es.exe 未找到，请检查路径", "results": []}
    except Exception as e:
        return {"source": "local", "error": str(e), "results": []}
