"""Vercel @vercel/python entry — class `handler` routes /api/* to admin_core.Handler."""
from __future__ import annotations

import os
import sys
from io import BytesIO
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from admin_core.server import Handler, setup  # noqa: E402
from admin_core.merchant_community import handle as merchant_handle  # noqa: E402

_INITIALIZED = False


class _HeaderMap:
    def __init__(self, items):
        self._m = {k.lower(): v for k, v in items}

    def get(self, name, default=None):
        return self._m.get(name.lower(), default)


class _DummyServer:
    dbpath = os.environ.get("GARAK_ADMIN_DB", str(ROOT / "runtime" / "garak_beta.sqlite3"))


def _ensure_setup():
    global _INITIALIZED
    if not _INITIALIZED:
        setup()
        _INITIALIZED = True


def _parse_http(raw: bytes):
    if not raw:
        return 500, {"Content-Type": "application/json"}, b'{"error":"empty response"}'
    head, _, body = raw.partition(b"\r\n\r\n")
    lines = head.decode("iso-8859-1", errors="replace").split("\r\n")
    status = 500
    if lines:
        parts = lines[0].split(" ", 2)
        if len(parts) >= 2 and parts[1].isdigit():
            status = int(parts[1])
    headers = {}
    for line in lines[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip()] = v.strip()
    return status, headers, body


def _invoke(method: str, path: str, headers: dict, body: bytes):
    if path.split('?', 1)[0].rstrip('/') in {'/api/merchant-applications', '/api/community/posts', '/api/community/comments', '/api/community/moderation'}:
        return merchant_handle(method, path, headers, body)
    out = BytesIO()

    class OneShot(Handler):
        def __init__(self):
            self.rfile = BytesIO(body)
            self.wfile = out
            self.raw_requestline = f"{method} {path} HTTP/1.1".encode()
            self.requestline = self.raw_requestline.decode()
            self.command = method
            self.request_version = "HTTP/1.1"
            self.path = path
            self.headers = _HeaderMap(headers.items())
            self.client_address = ("127.0.0.1", 0)
            self.server = _DummyServer()
            self.directory = str(ROOT / "storefront")

    h = OneShot()
    if method == "GET":
        h.do_GET()
    elif method == "POST":
        h.do_POST()
    elif method == "OPTIONS":
        h.send_response(204)
        h.send_header("Access-Control-Allow-Origin", os.environ.get("GARAK_PUBLIC_BASE_URL", "*"))
        h.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        h.send_header("Access-Control-Allow-Headers", "Content-Type, X-Garak-CSRF")
        h.end_headers()
    else:
        h.send_error(405)
    return _parse_http(out.getvalue())


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        _ensure_setup()
        status, headers, body = _invoke("GET", self.path, dict(self.headers), b"")
        self._emit(status, headers, body)

    def do_POST(self):
        _ensure_setup()
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length > 0 else b""
        status, headers, body = _invoke("POST", self.path, dict(self.headers), raw)
        self._emit(status, headers, body)

    def do_OPTIONS(self):
        _ensure_setup()
        status, headers, body = _invoke("OPTIONS", self.path, dict(self.headers), b"")
        self._emit(status, headers, body)

    def log_message(self, *_args, **_kwargs):
        return

    def _emit(self, status, headers, body):
        self.send_response(status)
        for key, value in headers.items():
            if key.lower() not in ("content-length", "connection", "transfer-encoding"):
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def vercel_handler(request):
    _ensure_setup()
    method = getattr(request, "method", "GET") or "GET"
    path = getattr(request, "path", "/") or "/"
    query = getattr(request, "query", None) or {}
    if query and "?" not in path:
        path = path + "?" + urlencode(query, doseq=True)
    body_raw = getattr(request, "body", b"") or b""
    if isinstance(body_raw, str):
        body_raw = body_raw.encode("utf-8")
    hdrs = {k: v for k, v in (getattr(request, "headers", {}) or {}).items()}
    status, headers, body = _invoke(method, path, hdrs, body_raw)
    return {"statusCode": status, "headers": headers, "body": body.decode("utf-8", errors="replace")}


app = vercel_handler
application = vercel_handler
