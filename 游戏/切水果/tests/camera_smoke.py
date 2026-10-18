"""Short real camera check. No camera frames are stored on disk."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from gesture_server import GestureServer
from aiohttp import web, ClientSession


async def main():
    with tempfile.TemporaryDirectory() as temp:
        server = GestureServer(settings_path=Path(temp) / "settings.json")
        runner = web.AppRunner(server.build_app())
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        try:
            async with ClientSession() as client:
                async with client.ws_connect(f"http://127.0.0.1:{port}/ws") as ws:
                    frames = visible = 0
                    deadline = asyncio.get_running_loop().time() + 12
                    while asyncio.get_running_loop().time() < deadline:
                        msg = await ws.receive_json(timeout=3)
                        if msg["type"] == "gesture":
                            frames += 1
                            visible += int(msg["visible"])
                    status = server.status_msg()
                    async with client.get(f"http://127.0.0.1:{port}/api/preview.jpg") as response:
                        await response.read()
                    await asyncio.sleep(0.3)
                    async with client.get(f"http://127.0.0.1:{port}/api/preview.jpg") as response:
                        status["preview_status"] = response.status
                        status["preview_bytes"] = len(await response.read())
                    print(json.dumps({"status": status, "gesture_frames": frames, "visible_hand_frames": visible}, ensure_ascii=True))
        finally:
            await runner.cleanup()


asyncio.run(main())
