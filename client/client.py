"""Inventory client.

Talks to the Inventory Service only through its Kubernetes Service DNS
name (default http://inventory-service:5001) — never to individual Pod
addresses — and prints which Pod served each response.

Modes:
    python client.py            loop forever, one request every
                                REQUEST_INTERVAL seconds (default 2)
    python client.py burst N    send N requests back to back, print each
                                response and a per-Pod summary, then exit
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

BASE_URL = os.environ.get("INVENTORY_URL", "http://inventory-service:5001")
INTERVAL = float(os.environ.get("REQUEST_INTERVAL", "2"))


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_inventory():
    """One GET /inventory through the Service. Returns the parsed body."""
    with urllib.request.urlopen(f"{BASE_URL}/inventory", timeout=5) as resp:
        return json.loads(resp.read().decode())


def one_request():
    data = fetch_inventory()
    print(f"{now()} response from pod={data['pod']} "
          f"pod_ip={data.get('pod_ip', '')} items={data['count']}", flush=True)
    return data["pod"]


def loop_forever():
    print(f"{now()} client starting, inventory url = {BASE_URL}", flush=True)
    while True:
        try:
            one_request()
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            print(f"{now()} request via service failed: {exc}", flush=True)
        time.sleep(INTERVAL)


def burst(count):
    print(f"sending {count} requests to {BASE_URL}/inventory", flush=True)
    tally = {}
    for i in range(1, count + 1):
        try:
            pod = one_request()
            tally[pod] = tally.get(pod, 0) + 1
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            print(f"{now()} request {i} failed: {exc}", flush=True)
    print("summary of responses per pod:", flush=True)
    for pod in sorted(tally):
        print(f"  {pod}: {tally[pod]} responses", flush=True)
    return 0 if tally else 1


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "burst":
        sys.exit(burst(int(sys.argv[2]) if len(sys.argv) >= 3 else 10))
    loop_forever()
