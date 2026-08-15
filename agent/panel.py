"""Local monitoring panel — python -m agent panel. Serves a single HTML
page and JSON/SSE endpoints over the agent's JSONL event stream. Binds
only to 127.0.0.1: this process can start pipeline runs, and a wider
bind would expose that to the network."""

from __future__ import annotations

import socketserver
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HOST = "127.0.0.1"
PORT = 5679

AGENT_DIR = Path(__file__).parent
RUNS_DIR = AGENT_DIR / "runs"
PAGE_PATH = AGENT_DIR / "panel_page.html"


class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True


class PanelHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/":
            self._serve_page()
        else:
            self.send_error(404)

    def _serve_page(self) -> None:
        body = PAGE_PATH.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_panel() -> None:
    server = ThreadingHTTPServer((HOST, PORT), PanelHandler)
    print(f"Panel running at http://{HOST}:{PORT}/ (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
