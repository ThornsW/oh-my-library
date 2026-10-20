import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from core.netutil import find_free_port, api_get, api_put


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send(200, {"method": "GET", "path": self.path,
                         "auth": self.headers.get("Authorization", "")})

    def do_PUT(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n).decode() if n else ""
        self._send(204, {"method": "PUT", "body": raw})


class TestNetutil(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = find_free_port()
        cls.srv = HTTPServer(("127.0.0.1", cls.port), _Handler)
        cls.t = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.t.start()
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_find_free_port_in_range(self):
        p = find_free_port()
        self.assertTrue(1024 < p < 65536)

    def test_api_get_returns_json_and_sends_auth(self):
        data = api_get(self.base + "/version", secret="abc")
        self.assertEqual(data["method"], "GET")
        self.assertEqual(data["auth"], "Bearer abc")

    def test_api_put_sends_body_and_returns_status(self):
        status = api_put(self.base + "/proxies/T", {"name": "node1"}, secret="abc")
        self.assertEqual(status, 204)


if __name__ == "__main__":
    unittest.main()
