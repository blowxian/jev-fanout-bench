#!/usr/bin/env python3
"""
Aggregate round 3 (bench_laya.py) into results/round3/summary.{json,md}.

Each cell's figure is the median across the three independent processes of
that process's own P50/P95/P99; the range across processes is kept so a
reader can see how stable it was.

    python3 laya/report_laya.py
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R3 = ROOT / "results" / "round3"
NAMES = {"en": "Laya 421M (English, 512 ctx)", "multi": "Laya multilingual 322M (1,024 ctx)"}


def med(xs):
    return round(statistics.median(xs), 2)


def key(c):
    return (c["cell"], c.get("words"), c.get("options"), c["questions"])


def main() -> int:
    out = {"models": {}}
    md = ["# Round 3: Laya-MLX on an Apple M4 Pro", ""]
    for m in ("en", "multi"):
        runs = [json.loads(p.read_text()) for p in sorted(R3.glob(f"laya-{m}-p*.json"))]
        if not runs:
            continue
        env = runs[0]["environment"]
        cells = {}
        for r in runs:
            for c in r["cells"]:
                cells.setdefault(key(c), []).append(c)
        agg = []
        for k, cs in cells.items():
            agg.append({
                "cell": k[0], "words": k[1], "options": k[2], "questions": k[3],
                "input_tokens": cs[0]["input_tokens"], "processes": len(cs),
                "samples_per_process": cs[0]["n"],
                "p50_ms": med([c["p50_ms"] for c in cs]),
                "p95_ms": med([c["p95_ms"] for c in cs]),
                "p99_ms": med([c["p99_ms"] for c in cs]),
                "p50_range_ms": [min(c["p50_ms"] for c in cs), max(c["p50_ms"] for c in cs)],
                "questions_per_s": round(k[3] / (med([c["p50_ms"] for c in cs]) / 1000), 1),
                "tokens_per_s": round(cs[0]["input_tokens"] / (med([c["p50_ms"] for c in cs]) / 1000)),
            })
        cold = {k: med([r["cold_start"][k] for r in runs]) for k in runs[0]["cold_start"]}
        sus_path = R3 / f"laya-{m}-sustained.json"
        sustained = json.loads(sus_path.read_text())["sustained"] if sus_path.exists() else None
        if sustained and sustained["windows_30s"]:
            w = sustained["windows_30s"]
            sustained["summary"] = {
                "calls_per_s_median": med([x["calls_per_s"] for x in w]),
                "calls_per_s_min": min(x["calls_per_s"] for x in w),
                "questions_per_s_median": round(med([x["calls_per_s"] for x in w]) * sustained["questions_per_call"], 1),
                "tokens_per_s_median": round(med([x["calls_per_s"] for x in w]) * sustained["input_tokens"]),
                "p50_ms_first_window": w[0]["p50_ms"], "p50_ms_last_window": w[-1]["p50_ms"],
                "p95_ms_worst_window": max(x["p95_ms"] for x in w),
            }
        out["models"][m] = {
            "name": NAMES[m], "repo": runs[0]["repo"], "revision": runs[0]["revision"],
            "context_limit": runs[0]["context_limit"], "environment": env, "cold_start": cold,
            "peak_mb_one_question": med([r["peak_mb_one_question"] for r in runs]),
            "peak_mb_fifty_questions": med([r["peak_mb_fifty_questions"] for r in runs]),
            "cells": agg, "sustained": sustained,
        }

        md += [f"## {NAMES[m]}", "",
               f"`{runs[0]['repo']}` @ `{runs[0]['revision'][:12]}`, FP16, batch_size 64. "
               f"{env['chip']} ({env['gpu_cores']} GPU cores, {env['memory_gb']} GB), macOS {env['macos']}, "
               f"MLX {env['mlx']}, laya-mlx {env['laya_mlx']} @ `{(env['laya_mlx_commit'] or '')[:12]}`, "
               f"on AC power: {env['on_ac_power']}. {len(runs)} independent processes.", "",
               f"Cold start (median of {len(runs)}): import {cold['import_s']} s, load {cold['load_s']} s, "
               f"first call {cold['first_call_ms']} ms; process start to first answer {cold['process_start_to_first_answer_s']} s. "
               f"Peak MLX allocation: {out['models'][m]['peak_mb_one_question']} MiB for one short question, "
               f"{out['models'][m]['peak_mb_fifty_questions']} MiB for 50 questions.", "",
               "| Cell | Input tokens (Laya's count) | Questions | P50 ms | P95 ms | P99 ms | P50 range across processes | Questions/s |",
               "|---|---:|---:|---:|---:|---:|---|---:|"]
        for a in agg:
            label = a["cell"] + (f" ({a['words']} words)" if a["words"] else "") + (f" ({a['options']} options)" if a["options"] else "")
            md.append(f"| {label} | {a['input_tokens']} | {a['questions']} | {a['p50_ms']} | {a['p95_ms']} | {a['p99_ms']} | "
                      f"{a['p50_range_ms'][0]}–{a['p50_range_ms'][1]} | {a['questions_per_s']} |")
        if sustained and "summary" in sustained:
            s = sustained["summary"]
            md += ["", f"Sustained {sustained['minutes']} min, 3 questions per call, {sustained['input_tokens']} tokens per call: "
                       f"median {s['calls_per_s_median']} calls/s ({s['questions_per_s_median']} questions/s), slowest 30 s window "
                       f"{s['calls_per_s_min']} calls/s; P50 {s['p50_ms_first_window']} ms in the first window, "
                       f"{s['p50_ms_last_window']} ms in the last; worst window P95 {s['p95_ms_worst_window']} ms."]
        md.append("")

    md += ["## What this does and does not show", "",
           "- Timing wraps `agent.predict` with `mx.synchronize()`: prompt building, tokenization, inference, calibration "
           "and formatting. Model loading is reported separately as cold start.",
           "- One machine, one run of each process, sequential calls (no concurrency). Other Macs, other loads and "
           "thermal conditions will differ.",
           "- Nothing here measures accuracy, and no Jev call was made. Every answer was discarded.",
           "- `Input tokens` is Laya's own `usage.input_tokens`; nothing is billed when it runs locally. Laya encodes the state once per question, so tokens "
           "grow with the number of questions; Jev bills the state once per call.", ""]
    (R3 / "summary.json").write_text(json.dumps(out, indent=1) + "\n")
    (R3 / "summary.md").write_text("\n".join(md))
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
