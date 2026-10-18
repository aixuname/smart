"""Fail-fast local checks; no camera or browser is opened by this command."""
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
node = shutil.which("node")
if not node:
    raise SystemExit("Node is needed for JavaScript checks; the game itself does not require it.")

commands = [
    [sys.executable, "-X", "utf8", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"],
    [node, "--test", *[str(p.relative_to(root)) for p in sorted((root / "tests").glob("*.test.js"))]],
    [sys.executable, "-m", "compileall", "-q", "backend", "setup_env.py"],
]
for command in commands:
    subprocess.run(command, cwd=root, check=True)
for path in (root / "frontend/js").rglob("*.js"):
    subprocess.run([node, "--check", str(path)], cwd=root, check=True, capture_output=True)
batch = (root / "start.bat").read_bytes()
assert batch.isascii() and b"\n" not in batch.replace(b"\r\n", b""), "start.bat must use ASCII / CRLF"
print("All core, syntax, and Windows launcher encoding checks passed.")
