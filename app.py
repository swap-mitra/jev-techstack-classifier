"""Web UI for stack.py. Run: python app.py, then open http://localhost:8000.

Each request uses the visitor's key from the X-TypeSafe-Key header, falling back to
TYPESAFE_API_KEY on the server. On a public deployment leave TYPESAFE_API_KEY unset,
or every visitor spends your key. HOST and PORT env vars set the bind address.
"""

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from stack import recommend

HTML_PATH = Path(__file__).with_name("index.html")
MAX_CHARS = 5000
MAX_KEY_CHARS = 512


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/":
            return self.send_error(404)
        try:
            content = HTML_PATH.read_bytes()
            self._send(200, content, "text/html; charset=utf-8")
        except Exception as e:
            self.send_error(500, str(e))

    def do_POST(self):
        if self.path != "/api/recommend":
            return self.send_error(404)
        try:
            length = int(self.headers.get("Content-Length", 0))
            text = json.loads(self.rfile.read(min(length, MAX_CHARS * 4)))["requirements"].strip()
        except (ValueError, KeyError, TypeError, AttributeError):
            return self._json(400, {"error": "body must be JSON {\"requirements\": \"...\"}"})
        if not text or len(text) > MAX_CHARS:
            return self._json(400, {"error": f"requirements must be 1-{MAX_CHARS} characters"})
        api_key = self.headers.get("X-TypeSafe-Key", "").strip() or None
        if api_key and len(api_key) > MAX_KEY_CHARS:
            return self._json(400, {"error": "API key is too long"})
        if not api_key and not os.environ.get("TYPESAFE_API_KEY"):
            return self._json(401, {"error": "Enter your TypeSafe API key to run the classifier"})
        start = time.perf_counter()
        try:
            result = recommend(text, api_key)
        except Exception as e:  # surface service/auth failures to the UI instead of a dropped socket
            self.log_error("recommend failed: %r", e)
            return self._json(502, {"error": str(e)})
        result["ms"] = round((time.perf_counter() - start) * 1000)
        self._json(200, result)

    def _json(self, status, obj):
        self._send(status, json.dumps(obj).encode(), "application/json")

    def _send(self, status, body, ctype):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    host, port = os.environ.get("HOST", "127.0.0.1"), int(os.environ.get("PORT", "8000"))
    print(f"http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
