"""
Obsidian Vault 搜索 - 按文件名 + 内容 grep
"""

from pathlib import Path
import subprocess
from config import OBSIDIAN_VAULT, OBSIDIAN_VAULT2, MAX_RESULTS_PER_SOURCE

def _search_vault(vault_path: Path, q: str, limit: int):
    if not vault_path.exists():
        return []

    items = []

    # 1. 文件名搜索 (快速)
    for f in vault_path.rglob(f"*{q}*"):
        if f.is_file() and f.suffix == ".md":
            rel = f.relative_to(vault_path)
            items.append({
                "name": f.name,
                "path": str(rel),
                "vault": vault_path.name,
                "type": "obsidian_note",
                "match": "filename",
            })
            if len(items) >= limit:
                return items

    return items


def _search_vault_content(vault_path: Path, q: str, limit: int):
    """用 grep 搜索笔记内容"""
    if not vault_path.exists():
        return []

    try:
        cmd = ["grep", "-r", "-l", "-i", q, str(vault_path), "--include=*.md"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode not in (0, 1):  # 0=match, 1=no match
            return []

        lines = [l.strip() for l in result.stdout.split("\n") if l.strip()]
        items = []
        for path in lines[:limit]:
            p = Path(path)
            if p.is_file():
                rel = p.relative_to(vault_path)
                items.append({
                    "name": p.name,
                    "path": str(rel),
                    "vault": vault_path.name,
                    "type": "obsidian_note",
                    "match": "content",
                })
        return items
    except Exception:
        return []


def search(q: str, timeout: int = 10):
    if not q.strip():
        return {"source": "obsidian", "results": [], "total": 0}

    results = []

    # 先按文件名搜
    for vault in [OBSIDIAN_VAULT, OBSIDIAN_VAULT2]:
        results += _search_vault(vault, q, MAX_RESULTS_PER_SOURCE // 2)

    # 再按内容搜（补足不足的部分）
    if len(results) < MAX_RESULTS_PER_SOURCE:
        for vault in [OBSIDIAN_VAULT, OBSIDIAN_VAULT2]:
            content_results = _search_vault_content(
                vault, q, MAX_RESULTS_PER_SOURCE - len(results)
            )
            existing_paths = {r["path"] for r in results}
            for r in content_results:
                if r["path"] not in existing_paths:
                    results.append(r)
                    existing_paths.add(r["path"])

    return {"source": "obsidian", "results": results[:MAX_RESULTS_PER_SOURCE], "total": len(results)}
