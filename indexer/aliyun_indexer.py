"""
阿里云盘索引器 - 基于 aligo SDK 递归全量扫描
"""

import json
from datetime import datetime
from pathlib import Path


def _parse_mtime(updated_at) -> int:
    """将 aligo 返回的 update_at（ISO 字符串或 datetime）转为 unix 时间戳"""
    if not updated_at:
        return 0
    if isinstance(updated_at, str):
        try:
            return int(datetime.fromisoformat(updated_at).timestamp())
        except (ValueError, TypeError):
            return 0
    if hasattr(updated_at, "timestamp"):
        return int(updated_at.timestamp())
    return 0


def _scan_dir(cli, parent_id: str = "root", all_files: list = None, depth: int = 0):
    """递归扫描单目录"""
    if all_files is None:
        all_files = []

    try:
        files = cli.get_file_list(parent_file_id=parent_id)
    except Exception as e:
        print(f"[阿里云盘]  扫描目录 {parent_id} 失败: {e}", flush=True)
        return all_files

    if not files:
        return all_files

    for f in files:
        entry = {
            "name": f.name,
            "path": f.name,
            "is_dir": f.type == "folder",
            "size": f.size or 0,
            "id": f.file_id,
            "parent_id": f.parent_file_id,
            "source": "aliyun",
            "mtime": _parse_mtime(f.updated_at),
        }
        all_files.append(entry)

        # 递归子目录
        if entry["is_dir"]:
            if depth > 0 and depth % 2 == 0:
                print(f"[阿里云盘]  深度 {depth}，已扫描 {len(all_files)} 项...", flush=True)
            _scan_dir(cli, f.file_id, all_files, depth + 1)

    return all_files


def build_index(output_path: Path) -> dict:
    """全量扫描阿里云盘，生成索引文件"""
    print("[阿里云盘] 正在全量扫描...", flush=True)

    try:
        from aligo import Aligo
        cli = Aligo(show=False)
        print("[阿里云盘] 登录成功", flush=True)
    except Exception as e:
        raise RuntimeError(f"阿里云盘登录失败: {e}") from e

    all_files = _scan_dir(cli, "root", [], 0)

    index = {
        "source": "aliyun",
        "built_at": datetime.now().isoformat(),
        "total": len(all_files),
        "files": all_files,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"[阿里云盘] 完成：{len(all_files)} 个文件/文件夹，已保存到 {output_path}", flush=True)
    return index


if __name__ == "__main__":
    output = Path(__file__).parent.parent / "data" / "aliyun.json"
    build_index(output)
