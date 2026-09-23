#!/usr/bin/env python3
"""
E7 (no new requests): does Jev's own `confidence` tell you which answers are
fragile? Pairs every E4/E5 answer (translated ticket or questions; reordered,
reworded, restructured questions) with the same question's baseline answer,
then relates the *baseline* confidence to how far the answer moved.

Reads the private answer log; writes only aggregates to
results/round2/confidence.{json,md}.
"""
import json, statistics
from pathlib import Path
from bench import norm_answer, distance
from bench_data import QUESTIONS

QMAP = dict(QUESTIONS)
R2 = Path("results/round2")


def spearman(xs, ys):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):  # average ranks for ties
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2
            i = j + 1
        return r
    rx, ry = ranks(xs), ranks(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    return cov / ((sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5)


def main():
    req = {r["id"]: r for r in map(json.loads, (R2 / "requests.jsonl").read_text().splitlines())
           if r.get("kind") == "request" and r["status"] == 200}
    ans = {d["id"]: d["answers"] for d in map(json.loads, (R2 / "private" / "answers.jsonl").read_text().splitlines())}
    base = {}
    for rid, r in req.items():
        if r["exp"] == "e5" and r["cond"] == "baseline" and r["rep"] == 0:
            base[("e5", r["ticket"])] = rid
        if r["exp"] == "e4" and r["cond"] == "en_en" and r["rep"] == 0:
            base[("e4", r["ticket"])] = rid
    pairs = []
    for rid, r in req.items():
        if r["exp"] == "e5" and r["cond"] in ("order", "no_descriptions", "structured", "paraphrase"):
            b = base.get(("e5", r["ticket"]))
        elif r["exp"] == "e4" and r["cond"] in ("xx_state_en_q", "xx_state_xx_q"):
            b = base.get(("e4", r["ticket"]))
        else:
            continue
        if not b or rid not in ans or b not in ans:
            continue
        for q, a in ans[rid].items():
            ba = ans[b].get(q)
            if q not in QMAP or not ba or a.get("type") not in ("choice", "score") or ba.get("confidence") is None:
                continue
            d = distance(norm_answer(a, QMAP[q]), norm_answer(ba, QMAP[q]))
            pairs.append({"type": a["type"], "conf": ba["confidence"], "shift": d.get("abs", d.get("tvd")),
                          "top_changed": d.get("differs")})
    out = {"pairs": len(pairs), "by_type": {}}
    md = ["# E7 · Does confidence flag fragile answers?", "",
          f"{len(pairs)} pairs: an answer after rewording, reordering, restructuring or translating, against the same "
          "question's baseline answer. Grouped by the *baseline* answer's confidence. No new requests; aggregates only.", "",
          "| Type | Confidence tercile | Range | Mean shift | Top option changed | Pairs |", "|---|---|---|---:|---:|---:|"]
    for t in ("choice", "score"):
        xs = sorted((p for p in pairs if p["type"] == t), key=lambda p: p["conf"])
        k = len(xs) // 3
        terc = {"low": xs[:k], "mid": xs[k:2 * k], "high": xs[2 * k:]}
        rho = spearman([p["conf"] for p in xs], [p["shift"] for p in xs])
        out["by_type"][t] = {"spearman_conf_vs_shift": round(rho, 3), "terciles": {}}
        for name, g in terc.items():
            flips = [p["top_changed"] for p in g if p["top_changed"] is not None]
            row = {"conf_min": round(min(p["conf"] for p in g), 2), "conf_max": round(max(p["conf"] for p in g), 2),
                   "mean_shift": round(statistics.mean(p["shift"] for p in g), 4),
                   "top_changed": sum(flips) if flips else None, "n": len(g)}
            out["by_type"][t]["terciles"][name] = row
            md.append(f"| {t} | {name} | {row['conf_min']}–{row['conf_max']} | {row['mean_shift']:.3f} | "
                      f"{row['top_changed'] if row['top_changed'] is not None else '—'} | {row['n']} |")
        md.append(f"| {t} | Spearman ρ (confidence vs shift) | | {rho:.2f} | | |")
    md += ["", "Shift: Noul/Score absolute change (0–1 scale), Choice total-variation distance. "
           "This is stability under rewording, not accuracy: the tickets are unlabelled.", ""]
    (R2 / "confidence.json").write_text(json.dumps(out, indent=2))
    (R2 / "confidence.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
