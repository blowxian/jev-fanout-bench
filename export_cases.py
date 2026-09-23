#!/usr/bin/env python3
"""
Rebuild round 2's request bodies and pair each with its billed input tokens,
for validating token estimators. A body is kept only if its SHA-256 matches
the one logged when it was sent, so every case is a request that was billed.
Bodies contain only our inputs (tickets, questions); no answers.

    python3 export_cases.py   # -> results/round2/estimator-cases.jsonl
"""
import hashlib, json
from pathlib import Path
import bench2

LOG = Path("results/round2/requests.jsonl")


class Recorder:
    """Stands in for bench2.Runner and records what it would have sent."""
    def __init__(self, model):
        self.model, self.sent = model, []
    def ask(self, exp, cond, state, questions):
        body = json.dumps({"state": state, "model": self.model, "questions": questions}, ensure_ascii=False)
        self.sent.append((exp, body))
        return {"status": 200, "input_tokens": 0, "error_class": None, "answers": None}


def main():
    rows = [json.loads(l) for l in LOG.read_text().splitlines() if l.strip()]
    logged = {r["request_sha256"]: r for r in rows if r.get("kind") == "request" and r["status"] == 200}
    model = next(r["requested_model"] for r in rows if r.get("kind") == "run")
    rec = Recorder(model)
    for fn in (bench2.e1, bench2.e3, bench2.e4, bench2.e5):
        fn(rec)
    out, matched = [], 0
    for exp, body in rec.sent:
        sha = hashlib.sha256(body.encode()).hexdigest()
        r = logged.get(sha)
        if not r:
            continue
        matched += 1
        lang = r.get("lang") or "en"
        out.append({"exp": exp, "cond": r.get("cond"), "lang": lang, "billed_input_tokens": r["input_tokens"],
                    "request": json.loads(body)})
    Path("results/round2/estimator-cases.jsonl").write_text("\n".join(json.dumps(o, ensure_ascii=False) for o in out) + "\n")
    print(f"{matched} of {len(rec.sent)} rebuilt requests matched a billed request by SHA-256")


if __name__ == "__main__":
    main()
