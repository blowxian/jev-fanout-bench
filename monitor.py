#!/usr/bin/env python3
"""
E6: end-to-end latency of one fixed Jev request, every 5 minutes.

    nohup python3 monitor.py --provider openrouter --hours 72 >/dev/null 2>&1 &

One location, one client, a fresh HTTPS connection per sample (so latency
includes the TLS handshake): an observation of what one caller saw, not a
service-level measurement. Samples before 2026-09-23T17:05Z reused a stale
keep-alive connection and show attempts=2. Each sample appends a line to
results/round2/latency.jsonl (timestamp, status, latency, billed tokens, cost,
model — no answers). It stops on its own after --hours, or after three
consecutive 401/402/403 responses, i.e. when the key or the free window ends.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bench import PROVIDERS, Client, read_key
from bench_data import QUESTIONS, TICKETS

OUT = Path(__file__).parent / "results" / "round2" / "latency.jsonl"
QMAP = dict(QUESTIONS)
BODY_QS = {q: QMAP[q] for q in ("is_billing", "department", "urgency", "wants_refund")}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--provider", default="openrouter", choices=sorted(PROVIDERS))
    p.add_argument("--hours", type=float, default=72)
    p.add_argument("--every", type=float, default=300, help="seconds between samples")
    a = p.parse_args()
    prov = PROVIDERS[a.provider]
    client = Client(read_key(a.provider), prov["host"], prov["path"], prov.get("wire", "systemone"))
    body = json.dumps({"state": TICKETS[0]["text"], "model": prov["model"], "questions": BODY_QS}).encode()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    end = datetime.now(timezone.utc) + timedelta(hours=a.hours)
    fatal = 0
    while datetime.now(timezone.utc) < end:
        t0 = time.time()
        # A fresh connection every sample: a keep-alive socket idle for five
        # minutes is closed by the server, which made every first attempt fail
        # and retry. Each sample is now a cold request, handshake included.
        client.conn = None
        res = client.call(body)
        ok = res["status"] == 200
        u = res["response"]["usage"] if ok else {}
        with OUT.open("a") as f:
            f.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                "status": res["status"], "attempts": res.get("attempts"),
                                "latency_ms": res.get("latency_ms"), "total_ms": res.get("total_ms"),
                                "input_tokens": u.get("input_tokens"), "cost": u.get("cost"),
                                "model": res["response"].get("model") if ok else None}) + "\n")
        fatal = fatal + 1 if res["status"] in (401, 402, 403) else 0
        if fatal >= 3:
            return 1
        time.sleep(max(1.0, a.every - (time.time() - t0)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
