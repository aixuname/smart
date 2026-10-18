"""Reserve the listening port before loading camera libraries or opening hardware."""
import hashlib
import json
import os
from pathlib import Path
import socket
import tempfile
import urllib.request

SERVICE_ID = "fruit-flash-hand-tracking"
PROJECT_ID = hashlib.sha256(os.path.normcase(str(Path(__file__).resolve().parent.parent)).encode()).hexdigest()[:16]


def reserve_port(port, host="127.0.0.1"):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if os.name == "nt":
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        sock.bind((host, port))
        sock.listen(128)
        sock.setblocking(False)
        return sock
    except OSError:
        sock.close()
        raise


def existing_service(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=1) as response:
            status = json.loads(response.read(16384))
        return status.get("service_id") == SERVICE_ID and status.get("project_id") == PROJECT_ID
    except (OSError, ValueError, AttributeError):
        return False


class CameraLease:
    """An OS file lock prevents two project instances opening the same camera."""
    def __init__(self, camera_id, directory=None):
        self.path = Path(directory or tempfile.gettempdir()) / f"fruit-flash-camera-{camera_id}.lock"
        self.file = None

    def acquire(self):
        handle = self.path.open("a+b")
        try:
            handle.seek(0, 2)
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            return False
        self.file = handle
        return True

    def release(self):
        if self.file:
            self.file.close()  # Closing releases the OS lock, including after process exit.
            self.file = None
