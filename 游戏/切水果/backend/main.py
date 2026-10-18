# -*- coding: utf-8 -*-
"""
手势切水果 - 后端入口。

职责：
1. 组装 MediaPipe 手势引擎 + WebSocket 推流 + 前端静态托管
2. 启动 aiohttp 服务并自动打开浏览器

用法：
    python backend/main.py [--port 8000] [--camera 0]
"""
import argparse
import os
import sys
import threading
import time
import webbrowser

# Windows 控制台统一 UTF-8 输出，避免特殊字符/中文编码崩溃
if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

# 将 backend 目录加入 sys.path，便于各模块直接 import config
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from config import PORT, CAMERA_ID  # noqa: E402
from instance import reserve_port, existing_service  # noqa: E402


def open_browser(port):
    """Only open a browser once this project's HTTP endpoint is ready."""
    for _ in range(40):
        if existing_service(port):
            webbrowser.open("http://127.0.0.1:%d" % port)
            return
        time.sleep(0.1)


def parse_args():
    parser = argparse.ArgumentParser(description="手势切水果 - 后端服务")
    def port_number(value):
        number = int(value)
        if not 1 <= number <= 65535:
            raise argparse.ArgumentTypeError("端口必须在 1~65535 之间")
        return number
    parser.add_argument("--port", type=port_number, default=PORT, help="服务端口")
    parser.add_argument("--camera", type=int, default=None, choices=range(21), help="摄像头索引（默认使用已保存设置）")
    parser.add_argument("--no-camera", action="store_true", help="仅鼠标/演示，不初始化摄像头及模型")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        sock = reserve_port(args.port)
    except OSError:
        if existing_service(args.port):
            print("[启动] 本项目已在 http://127.0.0.1:%d 运行，复用现有服务；本次启动参数不覆盖现有设置。" % args.port)
            if not args.no_browser:
                webbrowser.open("http://127.0.0.1:%d" % args.port)
            return 0
        print("[启动失败] 端口 %d 被占用或无法绑定，请关闭占用程序或用 --port 指定其他端口。" % args.port)
        return 1

    try:
        return run_server(args, sock)
    finally:
        sock.close()


def run_server(args, sock):
    from gesture_server import GestureServer

    server = GestureServer(camera_id=args.camera, no_camera=args.no_camera)

    # 启动服务
    app = server.build_app()
    host = "127.0.0.1"

    if not args.no_browser:
        threading.Thread(target=open_browser, args=(args.port,), daemon=True).start()

    print("=" * 56)
    print("  疯狂切水果 - 手势识别服务")
    print("  访问地址: http://%s:%d" % (host, args.port))
    print("  摄像头:   %s    手势引擎: MediaPipe Hands" % ("已禁用" if args.no_camera else server.settings["camera_id"]))
    print("=" * 56)

    # 导入 web 后运行（延迟 import 避免循环）
    from aiohttp import web
    web.run_app(app, sock=sock, print=None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
