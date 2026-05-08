"""
Z-Library 搜索 - opencli web scraping
"""

import subprocess
import re
from config import MAX_RESULTS_PER_SOURCE


def search(q: str, timeout: int = 15):
    if not q.strip():
        return {"source": "zlib", "results": [], "total": 0}

    try:
        import urllib.parse
        encoded_q = urllib.parse.quote(q)
        url = f"https://1lib.s/s/{encoded_q}"

        cmd = ["opencli", "web", "read", "--url", url]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )

        if result.returncode != 0:
            return {"source": "zlib", "error": result.stderr.strip()[:200], "results": []}

        html = result.stdout

        # 尝试提取书籍条目
        items = []
        # 匹配书名、作者等
        # 模式1: 书名在 h3 标签内
        titles = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL)[:MAX_RESULTS_PER_SOURCE]
        authors = re.findall(r'<div class="authors"[^>]*>(.*?)</div>', html, re.DOTALL)
        sizes = re.findall(r'(\d[\d.]*\s*(?:MB|KB|GB))', html)

        if not titles:
            # 尝试 markdown.new 格式输出
            lines = html.strip().split("\n")
            current_title = ""
            for line in lines:
                line = line.strip()
                # 找书名模式: 可能是 markdown 列表项
                if line.startswith("- ") or line.startswith("* "):
                    if current_title:
                        items.append({
                            "name": current_title,
                            "path": current_title,
                            "type": "book",
                            "author": "",
                            "size": "",
                        })
                    current_title = line.lstrip("- *").strip()
                elif "[📥" in line or "下载" in line:
                    pass

            if current_title:
                items.append({
                    "name": current_title,
                    "path": current_title,
                    "type": "book",
                    "author": "",
                    "size": "",
                })

            # 如果什么也没解析出来，把原始输出当搜索结果
            if not items and html.strip():
                items.append({
                    "name": f"Z-Lib 搜索结果（关键词：{q}）",
                    "path": url,
                    "type": "zlib_result",
                    "snippet": html[:500],
                })
        else:
            for i, title in enumerate(titles):
                clean_title = re.sub(r'<[^>]+>', '', title).strip()
                author = ""
                if i < len(authors):
                    author = re.sub(r'<[^>]+>', '', authors[i]).strip()
                size = ""
                if i < len(sizes):
                    size = sizes[i]
                items.append({
                    "name": clean_title,
                    "path": clean_title,
                    "author": author,
                    "size": size,
                    "type": "book",
                })

        return {"source": "zlib", "results": items[:MAX_RESULTS_PER_SOURCE], "total": len(items)}

    except subprocess.TimeoutExpired:
        return {"source": "zlib", "error": "超时", "results": []}
    except FileNotFoundError:
        return {"source": "zlib", "error": "opencli not found", "results": []}
    except Exception as e:
        return {"source": "zlib", "error": str(e), "results": []}
