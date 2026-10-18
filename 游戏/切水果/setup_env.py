"""Create an isolated runtime, using this interpreter only to bootstrap venv."""
from pathlib import Path
import subprocess
import sys
import venv


def main():
    if sys.version_info < (3, 10):
        print("Python 3.10+ is required; Python 3.12 is recommended.")
        return 1
    root = Path(__file__).resolve().parent
    environment = root / ".venv"
    python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not python.exists():
        print("Creating project environment...", flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)
    lock = root / "requirements-lock.txt"
    # An existing environment may use a different Python than the bootstrapper.
    target_version = subprocess.check_output(
        [str(python), "-c", "import sys; print('%s.%s' % sys.version_info[:2])"], text=True
    ).strip()
    requirements = lock if lock.exists() and sys.platform == "win32" and target_version == "3.12" else root / "requirements.txt"
    result = subprocess.run([str(python), "-X", "utf8", "-m", "pip", "install", "-r", str(requirements)], cwd=root)
    if result.returncode:
        print("Installation failed. Retry: python setup_env.py")
    else:
        print("Environment ready. Double-click start.bat to play.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
