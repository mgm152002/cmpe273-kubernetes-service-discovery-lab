"""Inventory Service.

A small HTTP service that reports the stock levels of a fixed set of items.
Every response includes the name of the Pod that served it, so callers can
see which replica they reached through the Kubernetes Service.

Endpoints:
    GET /               service info
    GET /inventory      full inventory, served by this Pod
    GET /inventory/<id> a single item, or 404
    GET /health         readiness: 200 normally, 503 while the file named by
                        READINESS_FILE (default /tmp/unready) exists

Run locally:
    python app.py            # listens on PORT (default 5001)
"""

import json
import os
import socket
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "5001"))
POD_NAME = os.environ.get("POD_NAME", socket.gethostname())
POD_IP = os.environ.get("POD_IP", "")
READINESS_FILE = os.environ.get("READINESS_FILE", "/tmp/unready")

ITEMS = [
    {"id": 1, "name": "laptop", "stock": 14},
    {"id": 2, "name": "wireless mouse", "stock": 57},
    {"id": 3, "name": "mechanical keyboard", "stock": 32},
    {"id": 4, "name": "27-inch monitor", "stock": 9},
    {"id": 5, "name": "usb-c hub", "stock": 41},
]


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class InventoryHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # keep stdout to our own format
        pass

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        print(f"{now()} pod={POD_NAME} {self.command} {self.path} -> {status}",
              flush=True)

    def do_GET(self):
        if self.path == "/health":
            if os.path.exists(READINESS_FILE):
                self._send_json(503, {"status": "unready", "pod": POD_NAME})
            else:
                self._send_json(200, {"status": "ok", "pod": POD_NAME})
        elif self.path == "/":
            self._send_json(200, {
                "service": "inventory",
                "pod": POD_NAME,
                "pod_ip": POD_IP,
                "endpoints": ["/inventory", "/inventory/<id>", "/health"],
            })
        elif self.path == "/inventory":
            self._send_json(200, {
                "pod": POD_NAME,
                "pod_ip": POD_IP,
                "count": len(ITEMS),
                "items": ITEMS,
            })
        elif self.path.startswith("/inventory/"):
            try:
                item_id = int(self.path.rsplit("/", 1)[1])
            except ValueError:
                item_id = None
            item = next((i for i in ITEMS if i["id"] == item_id), None)
            if item is None:
                self._send_json(404, {"error": "item not found", "pod": POD_NAME})
            else:
                self._send_json(200, {"pod": POD_NAME, "item": item})
        else:
            self._send_json(404, {"error": "not found", "pod": POD_NAME})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), InventoryHandler)
    print(f"{now()} pod={POD_NAME} inventory service listening on :{PORT}",
          flush=True)
    server.serve_forever()
