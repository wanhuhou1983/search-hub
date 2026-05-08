#!/usr/bin/env python3
"""
search-hub 启动入口

功能：
  - 自动检测端口占用并提示
  - 支持 DEBUG 模式（自动 reload）
  - 支持自定义端口（环境变量 PORT）
  - 支持自定义 host（环境变量 HOST）
  - Docker 友好

用法：
  python run.py                    # 生产模式
  python run.py --debug            # 开发模式（热重载）
  PORT=19080 python run.py         # 自定义端口
  python run.py --help             # 查看所有选项
"""

import os
import sys
import socket
import argparse

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18080


def port_in_use(host: str, port: int) -> bool:
    """检测端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def find_free_port(host: str, start: int, max_attempts: int = 20) -> int:
    """从 start 开始找空闲端口"""
    for port in range(start, start + max_attempts):
        if not port_in_use(host, port):
            return port
    return 0


def main():
    parser = argparse.ArgumentParser(description="统一搜索中心 — 启动入口")
    parser.add_argument("--host", default=os.environ.get("HOST", DEFAULT_HOST),
                        help=f"监听地址 (默认 {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", str(DEFAULT_PORT))),
                        help=f"监听端口 (默认 {DEFAULT_PORT})")
    parser.add_argument("--debug", action="store_true",
                        help="开发模式 (uvicorn --reload)")
    parser.add_argument("--auto-port", action="store_true",
                        help="端口被占用时自动找空闲端口")
    args = parser.parse_args()

    host = args.host
    port = args.port

    # ── 端口检测 ──
    if port_in_use(host, port):
        if args.auto_port:
            new_port = find_free_port(host, port + 1)
            if new_port:
                print(f"⚠️  端口 {port} 被占用，自动切换到 {new_port}")
                port = new_port
            else:
                print(f"❌ 端口 {port} 被占用，且未找到空闲端口")
                sys.exit(1)
        else:
            print(f"❌ 端口 {port} 已被占用！")
            print(f"   可用方案：")
            print(f"     1. 杀掉旧进程后重试")
            print(f"     2. 使用 --auto-port 自动找空闲端口")
            print(f"     3. 使用 --port 指定其他端口")
            sys.exit(1)

    # ── 启动 ──
    print(f"🚀 统一搜索中心启动")
    print(f"   地址: http://{host}:{port}")
    print(f"   模式: {'开发 (hot-reload)' if args.debug else '生产'}")

    # 把 port 注入 main.py 的全局变量，让 __main__ 块读到
    os.environ["SEARCH_HUB_PORT"] = str(port)
    os.environ["SEARCH_HUB_HOST"] = host

    # 启动 uvicorn
    import uvicorn
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=args.debug,
        log_level="info" if not args.debug else "debug",
    )


if __name__ == "__main__":
    main()
