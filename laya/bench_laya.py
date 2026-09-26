#!/usr/bin/env python3
"""
Round 3: Laya-MLX on one Apple M4 Pro, measured end to end.

Laya is an open-weight "typed decision" model that people compare with Jev;
Laya-MLX is its port to Apple's MLX. Its README reports M3 Max numbers. This
re-measures them on another machine, and adds what a cost comparison needs:
how latency grows with state length, questions per call and options, what a
cold start costs, what one Mac sustains for minutes, and peak memory.

It never calls Jev and says nothing about accuracy. Only latency, throughput
and memory are measured; every answer is discarded.

Run inside the laya-mlx environment (https://github.com/mizorewww/laya-mlx):

    cd laya-mlx && uv sync
    HF_HUB_OFFLINE=1 uv run python ../jev-fanout-bench/laya/bench_laya.py \
        --model en --process 1 --out ../jev-fanout-bench/results/round3

One model per process, three processes per model (--process 1..3), then
--sustained once per model. `report_laya.py` aggregates.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

T0 = time.perf_counter()

import mlx.core as mx  # noqa: E402

import laya_mlx as laya  # noqa: E402

# Pinned to the revisions the port's author published and checksummed
# (benchmarks/results/hub-publication.json in laya-mlx).
MODELS = {
    "en": ("aac6fef/laya-mlx", "047678560251f28113ee8f5df4be82102c7bf336", 512),
    "multi": ("aac6fef/laya-multilingual-mlx", "ba40c87fcb357f1643d04d71323af9cdc3b9e591", 1024),
}

# The upstream README's "one short question": its example email and its first
# question. Same input, so the headline compares machine to machine.
EXAMPLE_STATE = {
    "from": "user@example.com",
    "subject": "Duplicate charge on invoice #4411",
    "body": "We were billed twice for March. Please refund the duplicate today or we will cancel our plan.",
}
DEPARTMENT = {
    "type": "choice",
    "instructions": "Which department should handle this email?",
    "criteria": {
        "billing": "invoices, payments, refunds",
        "technical": "bugs, outages, system errors",
        "sales": "pricing, new contracts",
        "other": "everything else",
    },
}
URGENCY = {
    "type": "score",
    "instructions": "How urgent is this request?",
    "criteria": ["not urgent", "soon", "critical deadline or blocking issue"],
}
REFUND = {"type": "noul", "instructions": "Does the customer ask for money back?"}

FILLER = (
    "The customer writes that the invoice for March shows the same subscription twice, "
    "that the card was charged on the first and again on the third, and that the bank "
    "statement is attached. They ask whether the second charge can be reversed before "
    "the end of the week, because the card is close to its limit and a supplier payment "
    "is due. They also mention an earlier ticket that was closed without a reply. "
)


def state_of(words: int) -> str:
    text = (FILLER * (words // len(FILLER.split()) + 2)).split()
    return " ".join(text[:words])


def questions(n: int) -> dict:
    base = [DEPARTMENT, URGENCY, REFUND]
    return {f"q{i}": base[i % 3] for i in range(n)}


def choice_with(k: int) -> dict:
    return {"type": "choice", "instructions": "Which queue should this go to?",
            "criteria": [f"queue {i + 1}" for i in range(k)]}


def pct(xs: list[float], p: float) -> float:
    s = sorted(xs)
    i = (len(s) - 1) * p
    lo, hi = int(i), min(int(i) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (i - lo)


def timed(agent, state, qs, n: int, warmup: int) -> dict:
    for _ in range(warmup):
        agent.predict(state, qs)
    mx.synchronize()
    samples, tokens = [], None
    for _ in range(n):
        t = time.perf_counter_ns()
        r = agent.predict(state, qs)
        mx.synchronize()
        samples.append((time.perf_counter_ns() - t) / 1e6)
        tokens = r["usage"]["input_tokens"]
    return {"n": n, "input_tokens": tokens, "questions": len(qs),
            "p50_ms": round(pct(samples, 0.5), 3), "p95_ms": round(pct(samples, 0.95), 3),
            "p99_ms": round(pct(samples, 0.99), 3), "mean_ms": round(statistics.fmean(samples), 3),
            "min_ms": round(min(samples), 3), "max_ms": round(max(samples), 3),
            "samples_ms": [round(x, 3) for x in samples]}


def environment() -> dict:
    def sh(*c):
        try:
            return subprocess.run(c, capture_output=True, text=True, timeout=10).stdout.strip()
        except Exception:
            return None
    power = sh("pmset", "-g", "batt") or ""
    return {
        "chip": sh("sysctl", "-n", "machdep.cpu.brand_string"),
        "memory_gb": int(sh("sysctl", "-n", "hw.memsize") or 0) // 2**30,
        "gpu_cores": (sh("system_profiler", "SPDisplaysDataType") or "").split("Total Number of Cores:")[-1].split()[0]
        if "Total Number of Cores" in (sh("system_profiler", "SPDisplaysDataType") or "") else None,
        "macos": platform.mac_ver()[0],
        "python": platform.python_version(),
        "mlx": mx.__version__,
        "laya_mlx": getattr(laya, "__version__", None),
        "laya_mlx_commit": sh("git", "-C", str(Path(laya.__file__).parent.parent), "rev-parse", "HEAD"),
        "on_ac_power": "AC Power" in power,
        "low_power_mode": "1" in (sh("pmset", "-g") or "").split("lowpowermode")[-1][:4] if "lowpowermode" in (sh("pmset", "-g") or "") else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=MODELS, required=True)
    ap.add_argument("--process", type=int, default=1)
    ap.add_argument("--sustained", type=float, default=0, help="minutes of sustained load instead of the matrix")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    repo, rev, ctx = MODELS[a.model]

    # Cold start: import + load + the first call, in a fresh process.
    t_load = time.perf_counter()
    agent = laya.load(repo, revision=rev, dtype="float16", batch_size=64)
    load_s = time.perf_counter() - t_load
    t_first = time.perf_counter()
    agent.predict(EXAMPLE_STATE, {"q0": DEPARTMENT})
    mx.synchronize()
    first_ms = (time.perf_counter() - t_first) * 1000
    cold = {"import_s": round(t_load - T0, 3), "load_s": round(load_s, 3),
            "first_call_ms": round(first_ms, 1),
            "process_start_to_first_answer_s": round(time.perf_counter() - T0, 3)}

    rec = {"created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "model": a.model, "repo": repo, "revision": rev, "context_limit": ctx,
           "dtype": "float16", "batch_size": 64, "process": a.process,
           "timing": "perf_counter around agent.predict with mx.synchronize; includes prompt building, "
                     "tokenization, inference, calibration and result formatting; excludes loading",
           "environment": environment(), "cold_start": cold, "cells": []}

    if a.sustained:
        state, qs = state_of(120), questions(3)
        for _ in range(20):
            agent.predict(state, qs)
        end = time.perf_counter() + a.sustained * 60
        windows, cur, t_win = [], [], time.perf_counter()
        while time.perf_counter() < end:
            t = time.perf_counter_ns()
            r = agent.predict(state, qs)
            mx.synchronize()
            cur.append((time.perf_counter_ns() - t) / 1e6)
            if time.perf_counter() - t_win >= 30:
                el = time.perf_counter() - t_win
                windows.append({"calls": len(cur), "calls_per_s": round(len(cur) / el, 2),
                                "p50_ms": round(pct(cur, .5), 3), "p95_ms": round(pct(cur, .95), 3)})
                cur, t_win = [], time.perf_counter()
        rec["sustained"] = {"minutes": a.sustained, "input_tokens": r["usage"]["input_tokens"],
                            "questions_per_call": 3, "windows_30s": windows}
        name = f"laya-{a.model}-sustained.json"
    else:
        mx.reset_peak_memory()
        rec["cells"].append({"cell": "headline_one_short_question",
                             **timed(agent, EXAMPLE_STATE, {"q0": DEPARTMENT}, a.n, 20)})
        rec["peak_mb_one_question"] = round(mx.get_peak_memory() / 2**20, 1)
        # State length, one yes/no question. Word counts chosen to land near
        # 64 / 256 / 480 tokens (and 960 on the 1,024-token multilingual model).
        for words in ([40, 190, 360] + ([730] if ctx >= 1024 else [])):
            rec["cells"].append({"cell": "state_length", "words": words,
                                 **timed(agent, state_of(words), {"q0": REFUND}, a.n, 10)})
        # Questions per call on the example email.
        for n in (1, 4, 16, 50):
            rec["cells"].append({"cell": "questions_per_call",
                                 **timed(agent, EXAMPLE_STATE, questions(n), a.n if n < 50 else 100, 5)})
        mx.reset_peak_memory()
        agent.predict(EXAMPLE_STATE, questions(50))
        mx.synchronize()
        rec["peak_mb_fifty_questions"] = round(mx.get_peak_memory() / 2**20, 1)
        # Options in one Choice question.
        for k in (2, 8, 32):
            rec["cells"].append({"cell": "choice_options", "options": k,
                                 **timed(agent, EXAMPLE_STATE, {"q0": choice_with(k)}, a.n, 10)})
        name = f"laya-{a.model}-p{a.process}.json"

    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / name).write_text(json.dumps(rec, indent=1) + "\n")
    print(f"wrote {a.out / name}  cold={cold}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
