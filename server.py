#!/usr/bin/env python3
"""Serve dist/ on :4271 with /healthz and /api/tracker."""
import http.server, os, json, functools
ROOT = os.path.dirname(os.path.abspath(__file__))
class H(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthz":
            b = b'{"ok":true,"app":"chelsea-tracker"}'; ct = "application/json"
        elif self.path == "/api/tracker":
            b = open(os.path.join(ROOT, "data/tracker.json"), "rb").read(); ct = "application/json"
        else:
            return super().do_GET()
        self.send_response(200); self.send_header("Content-Type", ct); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass
http.server.ThreadingHTTPServer(("0.0.0.0", 4271), functools.partial(H, directory=os.path.join(ROOT, "dist"))).serve_forever()
