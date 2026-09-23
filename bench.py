#!/usr/bin/env python3
"""
jev-fanout-bench: does asking Jev N questions in one call really bill the state
once, and do the answers change?

    python bench.py run              # real run against TypeSafe (TYPESAFE_API_KEY)
    python bench.py run --provider openrouter   # same API via OpenRouter
    python bench.py run --dry-run    # no key, no network: synthetic usage
    python bench.py report           # latest run in results/raw.jsonl -> summary

Standard library only. Every request body and its full response is appended to
results/raw.jsonl before anything is summarised, so the report can always be
regenerated, and audited, from the raw file.

Design (see README):
  - blocks of (ticket, size, N, question subset, repeat); inside a block the
    batched call and the N single calls run back to back, in a random order
    (batched-first or singles-first), so both arms share the same moment;
  - every block is repeated, so run-to-run variation of the same request gives
    a noise floor to compare batched-vs-single differences against;
  - question subsets are disjoint and balanced (bench_data.subsets), so every
    question is asked equally often at every N.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import platform
import random
import ssl
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from bench_data import QUESTION_COUNTS, QUESTIONS, SIZES, TICKETS, build_state, subsets

# Published rate, https://docs.typesafe.ai/models, checked 2026-09-22.
# OpenRouter lists the same rate: https://openrouter.ai/typesafe/jev-1.13
USD_PER_M_INPUT = 0.042

# Two routes to the same System One API. OpenRouter's /systemone endpoint is
# documented as TypeSafe-SDK compatible (same body, same answers) and adds
# usage.cost, the amount actually billed — which lets the report check the
# bill in dollars, not just tokens. TypeSafe paused new signups on
# 2026-09-22, so for new users OpenRouter is the only way in.
PROVIDERS = {
    "typesafe": {"host": "api.typesafe.ai", "path": "/v1/systemone",
                 "env": "TYPESAFE_API_KEY", "model": "jev-1.13.0"},
    "openrouter": {"host": "openrouter.ai", "path": "/api/v1/systemone",
                   "env": "OPENROUTER_API_KEY", "model": "typesafe/jev-1.13"},
    # Workers AI serves Jev as a third-party model at the same $0.042/1M
    # (Cloudflare dashboard, checked 2026-09-23). Its REST API wraps the same
    # body as {"model", "input"} and the answer as {"result"}; Client
    # translates both ways, so the log and the analysis see TypeSafe's shape.
    # It does not take a version pin: it forwards to jev-latest, and the
    # report refuses a run whose responses name more than one model.
    "cloudflare": {"host": "api.cloudflare.com", "path": "/client/v4/accounts/{account}/ai/run",
                   "env": "CLOUDFLARE_API_TOKEN", "model": "typesafe/jev", "wire": "cloudflare"},
}
ROOT = Path(__file__).parent
RAW = ROOT / "results" / "raw.jsonl"
QMAP = dict(QUESTIONS)


# --------------------------------------------------------------------------
# Requests
# --------------------------------------------------------------------------

class Client:
    """One persistent HTTPS connection, so every request pays the same
    (already warm) connection cost and latency compares like with like."""

    def __init__(self, key: str, host: str, path: str, wire: str = "systemone"):
        self.key, self.host, self.path, self.wire = key, host, path, wire
        self.conn: http.client.HTTPSConnection | None = None

    def encode(self, body: bytes) -> bytes:
        if self.wire != "cloudflare":
            return body
        req = json.loads(body)
        return json.dumps({"model": req["model"],
                           "input": {"state": req["state"], "questions": req["questions"]}}).encode()

    def decode(self, raw: bytes, requested_model: str) -> tuple[dict | None, str | None]:
        """(response in TypeSafe's shape, error)."""
        j = json.loads(raw)
        if self.wire != "cloudflare":
            return j, None
        if not j.get("success", True) or "result" not in j:
            return None, json.dumps(j.get("errors") or j)[:2000]
        res = j["result"]
        res.setdefault("model", requested_model)
        return res, None

    def _conn(self) -> http.client.HTTPSConnection:
        if self.conn is None:
            self.conn = http.client.HTTPSConnection(self.host, timeout=60, context=ssl.create_default_context())
        return self.conn

    def _retry_after(self, value: str | None, fallback: float) -> float:
        if not value:
            return fallback
        try:
            return max(0.0, float(value))
        except ValueError:
            try:  # HTTP-date form
                return max(0.0, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError):
                return fallback

    def call(self, body: bytes, max_tries: int = 6) -> dict:
        requested_model = json.loads(body)["model"]
        body = self.encode(body)
        """POST with backoff on 429/529 and on network errors. `latency_ms` is
        the successful attempt; `total_ms` includes every retry and wait."""
        t_start = time.perf_counter()
        delay, last_err = 1.0, None
        for attempt in range(1, max_tries + 1):
            t0 = time.perf_counter()
            try:
                c = self._conn()
                c.request("POST", self.path, body=body, headers={
                    "Authorization": f"Bearer {self.key}",
                    "Content-Type": "application/json",
                    "User-Agent": "jev-fanout-bench/2.0",
                })
                r = c.getresponse()
                raw = r.read()
                latency = (time.perf_counter() - t0) * 1000
                if r.status in (429, 529) and attempt < max_tries:
                    time.sleep(self._retry_after(r.getheader("retry-after"), delay))
                    delay = min(delay * 2, 30)
                    continue
                base = {"status": r.status, "attempts": attempt, "latency_ms": round(latency, 1),
                        "total_ms": round((time.perf_counter() - t_start) * 1000, 1)}
                if r.status != 200:
                    return {**base, "error": raw.decode(errors="replace")[:2000]}
                resp, err = self.decode(raw, requested_model)
                if err:
                    return {**base, "status": 502, "error": err}
                return {**base, "response": resp}
            except (OSError, http.client.HTTPException, json.JSONDecodeError) as e:
                last_err = f"{type(e).__name__}: {e}"
                self.conn = None  # reconnect on the next attempt
                if attempt < max_tries:
                    time.sleep(delay)
                    delay = min(delay * 2, 30)
        return {"status": 0, "attempts": max_tries, "error": last_err,
                "total_ms": round((time.perf_counter() - t_start) * 1000, 1)}


def fake_call(body: bytes) -> dict:
    """Dry run: plausible usage from a chars/4 estimate. Never a real number."""
    req = json.loads(body)
    tokens = 40 + len(json.dumps(req["state"])) // 4 + sum(len(json.dumps(v)) // 4 + 8 for v in req["questions"].values())
    answers = {}
    for k, v in req["questions"].items():
        rng = random.Random(k)
        if v["type"] == "noul":
            answers[k] = {"type": "noul", "noul": round(rng.random(), 3)}
        elif v["type"] == "choice":
            opts = list(v["criteria"])
            p = [rng.random() for _ in opts]
            p = [x / sum(p) for x in p]
            answers[k] = {"type": "choice", "choice": opts[p.index(max(p))], "probabilities": dict(zip(opts, p)), "confidence": 0.8}
        else:
            answers[k] = {"type": "score", "score": round(rng.uniform(0, len(v["criteria"]) - 1), 2), "confidence": 0.8}
    ms = round(random.uniform(200, 400), 1)
    return {"status": 200, "attempts": 1, "latency_ms": ms, "total_ms": ms,
            "response": {"model": "dry-run", "answers": answers,
                         "usage": {"input_tokens": tokens, "output_tokens": 0,
                                   "cost": tokens / 1e6 * USD_PER_M_INPUT}}}


def blocks(repeats: int, seed: int = 2026) -> list[dict]:
    rng = random.Random(seed)
    out = []
    for t in TICKETS:
        for size in SIZES:
            for n in QUESTION_COUNTS:
                for si, qids in enumerate(subsets(n)):
                    for rep in range(repeats):
                        out.append({"ticket": t["id"], "size": size, "n": n, "subset": si, "repeat": rep,
                                    "qids": qids, "batched_first": rng.random() < 0.5})
    rng.shuffle(out)
    return out


def body_for(ticket_id: str, size: str, qids: list[str], model: str) -> bytes:
    ticket = next(t for t in TICKETS if t["id"] == ticket_id)
    return json.dumps({"state": build_state(ticket, size), "model": model,
                       "questions": {q: QMAP[q] for q in qids}}, sort_keys=True).encode()


def git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def read_config(provider: str, name: str, env: str) -> str:
    """The environment variable, else ~/.config/<provider>/<name>."""
    if os.environ.get(env):
        return os.environ[env].strip()
    f = Path.home() / ".config" / provider / name
    return f.read_text().strip() if f.exists() else ""


def read_key(provider: str) -> str:
    """The API key or token. It is only ever sent in the Authorization
    header; it is never logged."""
    name = "api_token" if provider == "cloudflare" else "api_key"
    return read_config(provider, name, PROVIDERS[provider]["env"])


def cmd_run(args) -> int:
    prov = PROVIDERS[args.provider]
    args.model = args.model or prov["model"]
    key = "" if args.dry_run else read_key(args.provider)
    if not args.dry_run and not key:
        name = "api_token" if args.provider == "cloudflare" else "api_key"
        print(f"No key: set {prov['env']} or write it to ~/.config/{args.provider}/{name}. "
              "Use --dry-run to exercise the pipeline without one.", file=sys.stderr)
        return 2
    bl = blocks(args.repeats)
    if args.max_blocks:
        bl = bl[: args.max_blocks]
    total = sum(1 + b["n"] for b in bl)
    print(f"{len(bl)} blocks, {total} requests ({len(TICKETS)} tickets x {len(SIZES)} sizes x N in "
          f"{QUESTION_COUNTS} x balanced subsets x {args.repeats} repeats), plus {args.warmup} warm-up.")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Timestamp plus a random suffix: two runs started in the same second must
    # not share an id, or the report would pair one run's requests with another's.
    run_id = (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + os.urandom(3).hex()
              + ("-dry" if args.dry_run else ""))
    path = prov["path"]
    if "{account}" in path:
        account = read_config(args.provider, "account_id", "CLOUDFLARE_ACCOUNT_ID")
        if not account and not args.dry_run:
            print("No Cloudflare account id: set CLOUDFLARE_ACCOUNT_ID or ~/.config/cloudflare/account_id.", file=sys.stderr)
            return 2
        path = path.format(account=account or "DRY")
    client = None if args.dry_run else Client(key, prov["host"], path, prov.get("wire", "systemone"))
    send = (lambda body: fake_call(body)) if args.dry_run else client.call
    meta = {"kind": "run", "run_id": run_id, "dry_run": args.dry_run, "provider": args.provider,
            "endpoint": f"https://{prov['host']}{prov['path']}", "requested_model": args.model,
            "started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "python": sys.version.split()[0], "platform": platform.platform(),
            "git_commit": git_commit(), "usd_per_m_input": USD_PER_M_INPUT,
            "repeats": args.repeats, "requests_planned": total}
    failures = done = streak = 0
    # 401/402/403/404/422 will not fix themselves: an auth, balance or schema
    # problem would otherwise send thousands of requests that are all refused.
    fatal = {401, 402, 403, 404, 422}
    with out.open("a") as f:
        f.write(json.dumps(meta) + "\n")
        for _ in range(args.warmup):  # excluded from analysis: kind=warmup
            r = send(body_for(TICKETS[0]["id"], "small", subsets(2)[0], args.model))
            f.write(json.dumps({"kind": "warmup", "run_id": run_id, **r}) + "\n")
        for bi, b in enumerate(bl):
            arms = [("batched", b["qids"])] + [("single", [q]) for q in b["qids"]]
            if not b["batched_first"]:
                arms = arms[1:] + arms[:1]
            block_t0 = time.perf_counter()
            for mode, qids in arms:
                body = body_for(b["ticket"], b["size"], qids, args.model)
                res = send(body)
                rec = {"kind": "request", "run_id": run_id, "block": bi, "mode": mode,
                       **{k: b[k] for k in ("ticket", "size", "n", "subset", "repeat", "batched_first")},
                       "qids": qids, "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       "request_sha256": hashlib.sha256(body).hexdigest(),
                       "request": json.loads(body), **res}
                f.write(json.dumps(rec) + "\n")
                done += 1
                if res["status"] != 200:
                    failures += 1
                    print(f"[{done}/{total}] HTTP {res['status']}: {str(res.get('error'))[:200]}", file=sys.stderr)
                streak = streak + 1 if res["status"] in fatal else 0
                if streak >= 3:
                    f.flush()
                    print(f"Stopping: {streak} consecutive HTTP {res['status']} responses will not succeed on retry.",
                          file=sys.stderr)
                    return 1
                if not args.dry_run and args.sleep:
                    time.sleep(args.sleep)
            f.write(json.dumps({"kind": "block", "run_id": run_id, "block": bi,
                                "wall_ms": round((time.perf_counter() - block_t0) * 1000, 1)}) + "\n")
            f.flush()
            if (bi + 1) % 50 == 0 or bi + 1 == len(bl):
                print(f"[{done}/{total}] requests sent")
    print(f"Run {run_id} done. {failures} failed request(s). Raw log: {out}")
    return 1 if failures else 0


# --------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------

def load_run(path: Path, run_id: str | None) -> tuple[dict, list[dict]]:
    lines = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    runs = [l for l in lines if l.get("kind") == "run"]
    if not runs:
        raise SystemExit("No run header in the log.")
    meta = next((r for r in runs if r["run_id"] == run_id), None) if run_id else runs[-1]
    if meta is None:
        raise SystemExit(f"Run {run_id} not found. Runs: {[r['run_id'] for r in runs]}")
    return meta, [l for l in lines if l.get("run_id") == meta["run_id"] and l.get("kind") == "request"]


def norm_answer(a: dict, q: dict) -> dict:
    """Put every answer on a comparable 0..1 scale."""
    if a["type"] == "noul":
        return {"value": a["noul"]}
    if a["type"] == "score":
        return {"value": a["score"] / (len(q["criteria"]) - 1)}
    return {"choice": a["choice"], "p": a.get("probabilities") or {}}


def distance(a: dict, b: dict) -> dict:
    if "value" in a:
        return {"abs": abs(a["value"] - b["value"])}
    keys = set(a["p"]) | set(b["p"])
    tvd = 0.5 * sum(abs(a["p"].get(k, 0) - b["p"].get(k, 0)) for k in keys) if keys else None
    return {"differs": float(a["choice"] != b["choice"]), "tvd": tvd}


def pct(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))]


def summarise(xs: list[float]) -> dict:
    if not xs:
        return {}
    return {"n": len(xs), "mean": statistics.mean(xs), "median": statistics.median(xs),
            "p95": pct(xs, 0.95), "max": max(xs),
            # Normal-approx 95% CI on the mean; fine at these n, stated as such.
            "ci95": 1.96 * statistics.stdev(xs) / len(xs) ** 0.5 if len(xs) > 1 else None}


def cmd_report(args) -> int:
    meta, reqs = load_run(Path(args.input), args.run_id)
    bad = [r for r in reqs if r["status"] != 200]
    if bad and not args.allow_failures:
        raise SystemExit(f"{len(bad)} failed request(s) in run {meta['run_id']}; rerun, or pass --allow-failures.")
    ok = [r for r in reqs if r["status"] == 200]
    models = sorted({r["response"]["model"] for r in ok})
    if len(models) > 1:
        raise SystemExit(f"Run mixes models {models}; a comparison across versions is not this benchmark.")

    blocks_ = defaultdict(lambda: {"batched": None, "single": {}})
    for r in ok:
        g = blocks_[r["block"]]
        if r["mode"] == "batched":
            if g["batched"] is not None:
                raise SystemExit(f"Duplicate batched request in block {r['block']}.")
            g["batched"] = r
        else:
            q = r["qids"][0]
            if q in g["single"]:
                raise SystemExit(f"Duplicate single request for {q} in block {r['block']}.")
            g["single"][q] = r

    cells, incomplete = [], 0
    for bi, g in blocks_.items():
        b = g["batched"]
        if b is None or len(g["single"]) != b["n"]:
            incomplete += 1
            continue
        B = b["response"]["usage"]["input_tokens"]
        U = sum(s["response"]["usage"]["input_tokens"] for s in g["single"].values())
        n = b["n"]
        cells.append({
            "block": bi, "ticket": b["ticket"], "size": b["size"], "n": n, "subset": b["subset"], "repeat": b["repeat"],
            "batched_tokens": B, "separate_tokens": U, "saved_tokens": U - B,
            "saved_usd_per_1k_items": (U - B) / 1e6 * USD_PER_M_INPUT * 1000,
            "ratio": U / B, "saving_pct": 100 * (1 - B / U),
            # Linear model: U - B = (N-1) * F, F = everything a request bills
            # apart from its questions (state + fixed request overhead).
            "implied_fixed_tokens": (U - B) / (n - 1),
            "latency_batched_ms": b["latency_ms"],
            "latency_separate_serial_ms": sum(s["latency_ms"] for s in g["single"].values()),
            "retried": any(x["attempts"] > 1 for x in [b, *g["single"].values()]),
        })
    if incomplete and not args.allow_failures:
        raise SystemExit(f"{incomplete} incomplete block(s); rerun, or pass --allow-failures.")

    # Linearity: F for one (ticket, size) must not depend on N or the subset.
    by_state = defaultdict(list)
    for c in cells:
        by_state[(c["ticket"], c["size"])].append(c["implied_fixed_tokens"])
    spread = {f"{t}/{s}": max(v) - min(v) for (t, s), v in sorted(by_state.items())}
    fixed_by_size = {s: summarise([c["implied_fixed_tokens"] for c in cells if c["size"] == s]) for s in SIZES}
    overhead = fixed_by_size.get("tiny", {}).get("median")

    agg = []
    for size in SIZES:
        for n in QUESTION_COUNTS:
            cs = [c for c in cells if c["size"] == size and c["n"] == n]
            if cs:
                agg.append({"size": size, "n": n,
                            "batched_tokens": summarise([c["batched_tokens"] for c in cs]),
                            "separate_tokens": summarise([c["separate_tokens"] for c in cs]),
                            "saving_pct": summarise([c["saving_pct"] for c in cs]),
                            "saved_usd_per_1k_items": summarise([c["saved_usd_per_1k_items"] for c in cs]),
                            "latency_ratio": summarise([c["latency_separate_serial_ms"] / c["latency_batched_ms"]
                                                        for c in cs if not c["retried"]])})

    # Answers: batched-vs-single, against the noise floor of asking the very
    # same request twice (same arm, same block key, different repeat).
    def key(r):
        return (r["ticket"], r["size"], r["n"], r["subset"])
    arms = defaultdict(lambda: defaultdict(list))  # (key, qid) -> mode -> [norm answer by repeat]
    for r in ok:
        for q, a in r["response"]["answers"].items():
            arms[(key(r), q)][r["mode"]].append(norm_answer(a, QMAP[q]))
    between = defaultdict(list)  # (qtype, metric) -> distances
    noise = defaultdict(list)
    for (k, q), modes in arms.items():
        qt = QMAP[q]["type"]
        for a in modes["batched"]:
            for s in modes["single"]:
                for m, v in distance(a, s).items():
                    if v is not None:
                        between[(qt, m)].append(v)
        for mode in ("batched", "single"):
            xs = modes[mode]
            for i in range(len(xs)):
                for j in range(i + 1, len(xs)):
                    for m, v in distance(xs[i], xs[j]).items():
                        if v is not None:
                            noise[(qt, m)].append(v)
    answers = {f"{qt}.{m}": {"batched_vs_single": summarise(v), "same_request_repeated": summarise(noise.get((qt, m), []))}
               for (qt, m), v in sorted(between.items())}

    total = sum(r["response"]["usage"]["input_tokens"] for r in ok)
    # Where the route reports what it charged (OpenRouter's usage.cost), check
    # the bill against tokens x published rate, request by request.
    billed = [r for r in ok if isinstance(r["response"]["usage"].get("cost"), (int, float))]
    billing = None
    if billed:
        dev = [abs(r["response"]["usage"]["cost"] - r["response"]["usage"]["input_tokens"] / 1e6 * USD_PER_M_INPUT)
               for r in billed]
        billing = {"requests_with_cost": len(billed),
                   "billed_usd_total": sum(r["response"]["usage"]["cost"] for r in billed),
                   "max_abs_deviation_usd": max(dev),
                   "output_tokens_total": sum(r["response"]["usage"].get("output_tokens", 0) for r in billed)}
    summary = {
        "run": meta, "model": models[0] if models else None, "requests_ok": len(ok),
        "requests_failed": len(bad), "blocks_incomplete": incomplete,
        "total_input_tokens": total, "total_cost_usd": total / 1e6 * USD_PER_M_INPUT,
        "billing_check": billing,
        "fixed_overhead_tokens_median": overhead,
        "implied_fixed_tokens_by_size": fixed_by_size,
        "linearity_max_spread_tokens": max(spread.values(), default=0),
        "linearity_spread_by_state": spread,
        "by_size_and_n": agg, "answers": answers, "cells": cells,
    }
    outdir = Path(args.input).parent
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2))
    (outdir / "summary.md").write_text(render_md(summary))
    (outdir / "fanout.svg").write_text(render_svg(agg, meta["dry_run"]))
    print((outdir / "summary.md").read_text())
    return 0


def render_md(s: dict) -> str:
    m = s["run"]
    f = lambda d, k="median", fmt="{:,.0f}": fmt.format(d[k]) if d and d.get(k) is not None else "—"
    lines = ["# Results", ""]
    if m["dry_run"]:
        lines += ["> **DRY RUN — synthetic token counts, not measurements.**", ""]
    lines += [
        f"Run `{m['run_id']}` via `{m.get('endpoint', 'api.typesafe.ai')}`, model `{s['model']}` "
        f"(requested `{m['requested_model']}`), "
        f"{s['requests_ok']:,} requests, {s['total_input_tokens']:,} input tokens, "
        f"${s['total_cost_usd']:.4f} at ${m['usd_per_m_input']}/1M. Python {m['python']}, "
        f"commit `{m['git_commit'][:10] if m['git_commit'] else 'uncommitted'}`.", "",
        "## Tokens billed: one call with N questions vs N calls", "",
        "Medians across tickets, question subsets and repeats; saving with its 95% CI.", "",
        "| State | N | Batched | Separate | Saving | Saved per 1k items | Latency, serial ÷ batched (median / p95) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for a in s["by_size_and_n"]:
        sv = a["saving_pct"]
        ci = f" ± {sv['ci95']:.1f}" if sv.get("ci95") is not None else ""
        lines.append(
            f"| {a['size']} | {a['n']} | {f(a['batched_tokens'])} | {f(a['separate_tokens'])} | "
            f"{sv['mean']:.1f}%{ci} | ${f(a['saved_usd_per_1k_items'], 'median', '{:.4f}')} | "
            f"{f(a['latency_ratio'], 'median', '{:.2f}x')} / {f(a['latency_ratio'], 'p95', '{:.2f}x')} |")
    lines += [
    ]
    b = s.get("billing_check")
    if b:
        lines += ["", "## Does the bill match the rate?", "",
                  f"{b['requests_with_cost']:,} responses reported what they were charged (`usage.cost`): "
                  f"${b['billed_usd_total']:.6f} in total. Against input tokens × ${m['usd_per_m_input']}/1M, "
                  f"the largest per-request difference is ${b['max_abs_deviation_usd']:.9f}. Those requests also "
                  f"returned {b['output_tokens_total']:,} output tokens, which the charge does not include."]
    lines += [
        "", "## Is billing linear?", "",
        "Under a linear model, `separate − batched = (N − 1) × F`, where F is what one request bills apart "
        "from its questions: the state plus a fixed per-request overhead. F is derived independently at every "
        f"N and question subset; for the same state it varies by at most **{s['linearity_max_spread_tokens']:.1f} tokens**.",
        "",
        f"The `tiny` control (a one-word state) puts the fixed overhead at about **{f({'m': s['fixed_overhead_tokens_median']}, 'm')} tokens** per request.",
        "", "| State | Implied F, median | min | max |", "|---|---:|---:|---:|",
    ]
    for size, d in s["implied_fixed_tokens_by_size"].items():
        if d:
            lines.append(f"| {size} | {d['median']:,.1f} | {min(c['implied_fixed_tokens'] for c in s['cells'] if c['size']==size):,.1f} | {d['max']:,.1f} |")
    lines += [
        "", "## Do the answers change?", "",
        "Batched-vs-single differences, next to the difference between two identical requests "
        "(the noise floor). Noul and Score are on a 0–1 scale (Score divided by its number of steps); "
        "Choice reports how often the top option differs and the total-variation distance between "
        "the two probability distributions. This measures stability, not accuracy: there are no labels.", "",
        "| Answer · metric | Batched vs single (mean / p95) | Same request twice (mean / p95) |", "|---|---:|---:|",
    ]
    for k, v in s["answers"].items():
        a, n = v["batched_vs_single"], v["same_request_repeated"]
        lines.append(f"| {k} | {f(a, 'mean', '{:.3f}')} / {f(a, 'p95', '{:.3f}')} | {f(n, 'mean', '{:.3f}')} / {f(n, 'p95', '{:.3f}')} |")
    lines += ["", "Limitations: one region and one client; separate calls are timed serially (an application "
              "that fans out concurrently would see a smaller latency gap); synthetic English tickets.", ""]
    return "\n".join(lines)


def render_svg(agg: list[dict], dry: bool) -> str:
    """Saving % against N, one line per state size. Dependency-free SVG."""
    W, H, P = 640, 360, 56
    colors = {"tiny": "#cbd5e1", "small": "#94a3b8", "medium": "#10b981", "large": "#0f766e"}
    ns = QUESTION_COUNTS
    x = lambda n: P + ns.index(n) * (W - 2 * P) / (len(ns) - 1)
    y = lambda v: H - P - v / 100 * (H - 2 * P)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="system-ui,sans-serif" font-size="12">',
        f'<rect width="{W}" height="{H}" fill="#fff"/>',
        f'<text x="{P}" y="24" font-size="14" font-weight="600">Input tokens saved by asking N questions in one Jev call'
        + (" (DRY RUN)" if dry else "") + "</text>",
    ]
    for v in range(0, 101, 25):
        parts.append(f'<line x1="{P}" x2="{W-P}" y1="{y(v)}" y2="{y(v)}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{P-8}" y="{y(v)+4}" text-anchor="end" fill="#6b7280">{v}%</text>')
    for n in ns:
        parts.append(f'<text x="{x(n)}" y="{H-P+18}" text-anchor="middle" fill="#6b7280">N={n}</text>')
    for size in SIZES:
        pts = [(x(a["n"]), y(a["saving_pct"]["mean"])) for a in agg if a["size"] == size]
        if not pts:
            continue
        parts.append(f'<polyline fill="none" stroke="{colors[size]}" stroke-width="2.5" points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in pts)}"/>')
        for a, b in pts:
            parts.append(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="3.5" fill="{colors[size]}"/>')
        parts.append(f'<text x="{W-P+6}" y="{pts[-1][1]+4}" fill="{colors[size]}">{size}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="send the requests")
    r.add_argument("--dry-run", action="store_true", help="no key, no network, synthetic usage")
    r.add_argument("--provider", choices=sorted(PROVIDERS), default="typesafe")
    r.add_argument("--model", default=None, help="default: the provider's pinned Jev 1.13 id")
    r.add_argument("--repeats", type=int, default=3)
    r.add_argument("--warmup", type=int, default=3)
    r.add_argument("--out", default=str(RAW))
    r.add_argument("--sleep", type=float, default=0.05, help="seconds between requests")
    r.add_argument("--max-blocks", type=int, default=0, help="smoke test: stop after this many blocks")
    r.set_defaults(fn=cmd_run)
    s = sub.add_parser("report", help="summarise one run from the raw log")
    s.add_argument("--input", default=str(RAW))
    s.add_argument("--run-id", help="default: the most recent run in the file")
    s.add_argument("--allow-failures", action="store_true")
    s.set_defaults(fn=cmd_report)
    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
