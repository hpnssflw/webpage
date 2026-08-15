"""Local monitoring panel — python -m agent panel. Serves a single HTML
page and JSON/SSE endpoints over the agent's JSONL event stream. Binds
only to 127.0.0.1: this process can start pipeline runs, and a wider
bind would expose that to the network."""

from __future__ import annotations

import json
import re
import socketserver
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from agent.events import read_events
from agent.funnel import compute_funnel

HOST = "127.0.0.1"
PORT = 5679

AGENT_DIR = Path(__file__).parent
RUNS_DIR = AGENT_DIR / "runs"
PAGE_PATH = AGENT_DIR / "panel_page.html"

RUN_ID_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{4}Z$")


class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True


class PanelHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/":
            self._serve_page()
        elif self.path == "/runs":
            self._serve_runs_list()
        elif self.path.startswith("/runs/"):
            self._serve_run_detail(self.path[len("/runs/"):])
        else:
            self.send_error(404)

    def _serve_page(self) -> None:
        body = PAGE_PATH.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_runs_list(self) -> None:
        runs = []
        for path in sorted(RUNS_DIR.glob("*.jsonl"), reverse=True):
            run_events = read_events(path)
            runs.append(
                {
                    "run_id": path.stem,
                    "event_count": len(run_events),
                    "funnel": compute_funnel(run_events),
                }
            )
        self._send_json(runs)

    def _serve_run_detail(self, run_id: str) -> None:
        if not RUN_ID_RE.match(run_id):
            self.send_error(400, "invalid run id")
            return
        path = RUNS_DIR / f"{run_id}.jsonl"
        if not path.exists():
            self.send_error(404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
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
