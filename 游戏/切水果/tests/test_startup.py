import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from instance import CameraLease, reserve_port, existing_service, SERVICE_ID, PROJECT_ID


class StartupTests(unittest.TestCase):
    def test_port_reserved_before_camera_import(self):
        sock = reserve_port(0)
        try:
            port = sock.getsockname()[1]
            with self.assertRaises(OSError):
                reserve_port(port)
            result = subprocess.run([sys.executable, "backend/main.py", "--port", str(port), "--no-browser"],
                                    cwd=Path(__file__).resolve().parents[1], capture_output=True, timeout=6)
            self.assertEqual(result.returncode, 1)
            self.assertNotIn(b"TensorFlow", result.stderr)
        finally:
            sock.close()

    def test_camera_lease_excludes_second_owner_and_releases(self):
        with tempfile.TemporaryDirectory() as temp:
            first, second = CameraLease(0, temp), CameraLease(0, temp)
            try:
                self.assertTrue(first.acquire())
                self.assertFalse(second.acquire())
                first.release()
                self.assertTrue(second.acquire())
            finally:
                first.release()
                second.release()

    def test_service_identity_does_not_accept_other_project(self):
        import io
        for status, expected in [({"service_id": SERVICE_ID, "project_id": PROJECT_ID}, True),
                                 ({"service_id": SERVICE_ID, "project_id": "other"}, False), ({}, False)]:
            with patch("instance.urllib.request.urlopen", return_value=io.BytesIO(json.dumps(status).encode())):
                self.assertEqual(existing_service(8000), expected)
