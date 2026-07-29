import hashlib
import json
import socket
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from searchpars.model_installer import (
    install_model,
    parse_model_reference,
)


class _RegistryHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    manifest = b""
    blobs = {}
    interrupted_digest = ""
    interrupted_once = False
    requested_offsets = {}

    def log_message(self, _format, *_args):
        return

    def do_GET(self):
        if "/manifests/" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(self.manifest)))
            self.end_headers()
            self.wfile.write(self.manifest)
            return

        marker = "/blobs/"
        if marker not in self.path:
            self.send_error(404)
            return
        digest = self.path.split(marker, 1)[1]
        data = self.blobs.get(digest)
        if data is None:
            self.send_error(404)
            return

        range_header = self.headers.get("Range", "")
        start = 0
        if range_header.startswith("bytes="):
            start = int(range_header[6:].split("-", 1)[0] or "0")
        self.requested_offsets.setdefault(digest, []).append(start)

        if digest == self.interrupted_digest and not self.interrupted_once:
            type(self).interrupted_once = True
            cut = min(len(data) // 3, 64 * 1024)
            self.send_response(200)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data[:cut])
            self.wfile.flush()
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            return

        payload = data[start:]
        self.send_response(206 if start else 200)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(len(payload)))
        if start:
            self.send_header(
                "Content-Range", f"bytes {start}-{len(data) - 1}/{len(data)}"
            )
        self.end_headers()
        self.wfile.write(payload)


class ModelInstallerTests(unittest.TestCase):
    def setUp(self):
        _RegistryHandler.interrupted_once = False
        _RegistryHandler.requested_offsets = {}
        self.config_data = b'{"model_format":"gguf"}'
        self.model_data = bytes(range(256)) * 2048
        self.config_digest = "sha256:" + hashlib.sha256(
            self.config_data
        ).hexdigest()
        self.model_digest = "sha256:" + hashlib.sha256(
            self.model_data
        ).hexdigest()
        manifest = {
            "schemaVersion": 2,
            "config": {
                "mediaType": "application/vnd.docker.container.image.v1+json",
                "digest": self.config_digest,
                "size": len(self.config_data),
            },
            "layers": [
                {
                    "mediaType": "application/vnd.ollama.image.model",
                    "digest": self.model_digest,
                    "size": len(self.model_data),
                }
            ],
        }
        _RegistryHandler.manifest = json.dumps(manifest).encode()
        _RegistryHandler.blobs = {
            self.config_digest: self.config_data,
            self.model_digest: self.model_data,
        }
        _RegistryHandler.interrupted_digest = self.model_digest
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _RegistryHandler)
        self.thread = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_model_reference(self):
        reference = parse_model_reference("qwen3.5:4b")
        self.assertEqual(reference.namespace, "library")
        self.assertEqual(reference.repository, "qwen3.5")
        self.assertEqual(reference.tag, "4b")

    def test_setup_does_not_use_ollama_pull_for_model_download(self):
        project_dir = Path(__file__).resolve().parents[1]
        setup_script = (project_dir / "setup-local-ai.sh").read_text()
        self.assertIn("searchpars/model_installer.py", setup_script)
        self.assertNotIn('"${OLLAMA_BIN}" pull', setup_script)

    def test_interrupted_blob_resumes_and_is_verified(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = Path(temp_dir) / "models"
            registry = f"http://127.0.0.1:{self.server.server_port}"
            install_model(
                model="test-model:v1",
                models_dir=models_dir,
                registry=registry,
                attempts=5,
                retry_wait=0,
            )

            final_blob = models_dir / "blobs" / self.model_digest.replace(
                ":", "-", 1
            )
            self.assertEqual(final_blob.read_bytes(), self.model_data)
            self.assertFalse(
                Path(f"{final_blob}.searchpars-part").exists()
            )

            offsets = _RegistryHandler.requested_offsets[self.model_digest]
            self.assertEqual(offsets[0], 0)
            self.assertGreater(offsets[1], 0)
            self.assertLess(offsets[1], len(self.model_data))

            manifest_path = (
                models_dir
                / "manifests"
                / f"127.0.0.1:{self.server.server_port}"
                / "library"
                / "test-model"
                / "v1"
            )
            self.assertEqual(
                json.loads(manifest_path.read_bytes())["schemaVersion"], 2
            )


if __name__ == "__main__":
    unittest.main()
