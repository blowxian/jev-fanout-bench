#!/usr/bin/env python3
"""
Round 2: what a Jev request costs, where its limits are, and what changes the
answers. Five experiments, one log.

    python bench2.py run --provider openrouter      # all experiments
    python bench2.py run --provider openrouter --only e1,e3
    python bench2.py report                          # results/round2/summary.{json,md}

  E1  token grid: billed tokens per question type, option count, level count,
      instruction form, and per language (chars/token by regression)
  E2  context limits: the 32k state+longest-question rule and the 64k total,
      found by bisection on real requests
  E3  fan-out at the extreme: do 4 target answers move when 16–120 unrelated
      questions share the call; question-count ceiling; latency vs N
  E4  cross-language consistency: English vs translated state, and vs
      translated state *and* questions, against the repeat-noise floor
  E5  wording sensitivity: Choice option order, option descriptions removed,
      plain vs structured instructions, paraphrases

Publication rule (TypeSafe's MCA forbids using outputs for distillation or to
build a competing model): answers are written only to results/round2/private/
(git-ignored) and used to compute distances. The public log holds conditions,
billed tokens, latency, status and error class — never an answer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from bench import PROVIDERS, USD_PER_M_INPUT, Client, distance, norm_answer, read_key
from bench_data import QUESTIONS, SIZES, TICKETS, build_state
from bench_i18n import LANGS, PARAGRAPH, QUESTIONS_I18N, TICKETS_I18N

ROOT = Path(__file__).parent
OUT = ROOT / "results" / "round2"
PUBLIC = OUT / "requests.jsonl"
PRIVATE = OUT / "private" / "answers.jsonl"
QMAP = dict(QUESTIONS)
TMAP = {t["id"]: t["text"] for t in TICKETS}
TARGETS = ["is_billing", "department", "urgency", "wants_refund"]

# --------------------------------------------------------------------------
# Plumbing
# --------------------------------------------------------------------------


class Runner:
    def __init__(self, provider: str, model: str | None, sleep: float):
        prov = PROVIDERS[provider]
        self.model = model or prov["model"]
        self.client = Client(read_key(provider), prov["host"], prov["path"], prov.get("wire", "systemone"))
        self.sleep = sleep
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-r2"
        OUT.mkdir(parents=True, exist_ok=True)
        PRIVATE.parent.mkdir(parents=True, exist_ok=True)
        self.pub = PUBLIC.open("a")
        self.priv = PRIVATE.open("a")
        self.n = 0
        self.fatal = 0
        self.pub.write(json.dumps({"kind": "run", "run_id": self.run_id, "provider": provider,
                                   "requested_model": self.model, "usd_per_m_input": USD_PER_M_INPUT,
                                   "started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                   "python": sys.version.split()[0]}) + "\n")

    def ask(self, exp: str, cond: dict, state, questions: dict) -> dict:
        body = json.dumps({"state": state, "model": self.model, "questions": questions},
                          ensure_ascii=False).encode()
        res = self.client.call(body)
        self.n += 1
        rid = f"{self.run_id}:{self.n}"
        ok = res["status"] == 200
        usage = res["response"]["usage"] if ok else {}
        rec = {"kind": "request", "run_id": self.run_id, "id": rid, "exp": exp, **cond,
               "status": res["status"], "attempts": res.get("attempts"),
               "latency_ms": res.get("latency_ms"), "total_ms": res.get("total_ms"),
               "input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
               "cost": usage.get("cost"), "model": res["response"].get("model") if ok else None,
               "request_chars": len(body.decode()), "state_chars": len(state) if isinstance(state, str) else None,
               "n_questions": len(questions),
               "request_sha256": hashlib.sha256(body).hexdigest(),
               "error_class": None if ok else error_class(res.get("status"), res.get("error"))}
        self.pub.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self.pub.flush()
        if ok:
            self.priv.write(json.dumps({"id": rid, "answers": res["response"]["answers"]}) + "\n")
            self.priv.flush()
            self.fatal = 0
        else:
            self.fatal = self.fatal + 1 if res["status"] in (401, 402, 403) else 0
            if self.fatal >= 3:
                raise SystemExit(f"Stopping: repeated HTTP {res['status']} — the key or balance no longer works.")
        if self.sleep:
            time.sleep(self.sleep)
        rec["answers"] = res["response"]["answers"] if ok else None
        return rec


def error_class(status, body) -> str:
    """A coarse, publishable label for a failure: never the raw body."""
    b = (body or "").lower()
    for key, label in [("context", "context_length"), ("token", "token_limit"), ("too many questions", "question_count"),
                       ("question", "question_validation"), ("rate", "rate_limit"), ("credit", "billing"),
                       ("balance", "billing"), ("timeout", "timeout")]:
        if key in b:
            return f"{status}:{label}"
    return f"{status}:other"


def noul(text: str) -> dict:
    return {"type": "noul", "instructions": text}


WORDS = ("does the customer explicitly say that the problem must be resolved quickly because "
         "their business depends on it and they cannot wait for a normal support response time "
         "without losing revenue or customers during the coming days of the busy season").split()


def words(n: int) -> str:
    return " ".join((WORDS * 4)[:n]).capitalize() + "?"


# --------------------------------------------------------------------------
# E1  token grid
# --------------------------------------------------------------------------

def e1(r: Runner) -> dict:
    base_q = {"q": noul("Urgent?")}
    r.ask("e1", {"cond": "base"}, ".", base_q)
    for n in (1, 10, 30, 80):
        r.ask("e1", {"cond": "noul_words", "x": n}, ".", {"q": noul(words(n))})
    r.ask("e1", {"cond": "noul_criteria"}, ".", {"q": {"type": "noul", "instructions": "Urgent?",
                                                        "criteria": {"true": "Must be handled today",
                                                                     "false": "Can wait"}}})
    for k in (2, 3, 5, 10, 20, 50, 100, 255):
        r.ask("e1", {"cond": "choice_bare", "x": k}, ".",
              {"q": {"type": "choice", "instructions": "Which category fits?", "criteria": {f"opt{i}": None for i in range(k)}}})
    for k in (2, 5, 10, 50):
        r.ask("e1", {"cond": "choice_described", "x": k}, ".",
              {"q": {"type": "choice", "instructions": "Which category fits?",
                     "criteria": {f"opt{i}": f"Short description of option number {i}" for i in range(k)}}})
    r.ask("e1", {"cond": "choice_longkeys", "x": 10}, ".",
          {"q": {"type": "choice", "instructions": "Which category fits?",
                 "criteria": {f"a_much_longer_option_key_name_{i}": None for i in range(10)}}})
    for lv in (2, 3, 5, 7, 10):
        r.ask("e1", {"cond": "score_levels", "x": lv}, ".",
              {"q": {"type": "score", "instructions": "How urgent?", "criteria": [f"Level {i}" for i in range(lv)]}})
    plain = "Is the ticket about billing? The customer tier is gold and the account is 3 years old."
    structured = {"question": "Is the ticket about billing?", "customer_tier": "gold", "account_age_years": 3}
    r.ask("e1", {"cond": "instr_plain"}, ".", {"q": noul(plain)})
    r.ask("e1", {"cond": "instr_structured"}, ".", {"q": {"type": "noul", "instructions": structured}})
    # Additivity: several questions in one call vs the same questions alone.
    combos = {
        "mixed": {"a": noul("Urgent?"), "b": {"type": "choice", "instructions": "Which category fits?",
                                              "criteria": {f"opt{i}": None for i in range(10)}},
                  "c": {"type": "score", "instructions": "How urgent?", "criteria": [f"Level {i}" for i in range(5)]}},
        "three_nouls": {"a": noul("Urgent?"), "b": noul(words(10)), "c": noul(words(30))},
    }
    for name, qs in combos.items():
        r.ask("e1", {"cond": "combo", "combo": name, "part": "all"}, ".", qs)
        for k, q in qs.items():
            r.ask("e1", {"cond": "combo", "combo": name, "part": k}, ".", {"q": q})
    # Languages: nine texts per language (8 tickets + one email), one Noul each.
    for lang in LANGS:
        texts = [(t["id"], t["text"] if lang == "en" else TICKETS_I18N[t["id"]][lang]) for t in TICKETS]
        texts.append(("paragraph", PARAGRAPH[lang]))
        for tid, text in texts:
            r.ask("e1", {"cond": "lang", "lang": lang, "text": tid, "chars": len(text)}, text, base_q)
    return {}


# --------------------------------------------------------------------------
# E2  context limits (adaptive)
# --------------------------------------------------------------------------

FILLER_EN = (PARAGRAPH["en"] + " ") * 400


def state_of(tokens: int, chars_per_token: float) -> str:
    return FILLER_EN[: max(1, int(tokens * chars_per_token))]


def bisect(r: Runner, label: str, lo: int, hi: int, make, steps: int = 7, tol: int | None = None) -> dict:
    """Largest value in [lo, hi] that succeeds, by bisection on make(v)."""
    last_ok, first_fail, trail = None, None, []
    for _ in range(steps):
        mid = (lo + hi) // 2
        rec = make(mid)
        trail.append({"v": mid, "status": rec["status"], "billed": rec["input_tokens"], "error": rec["error_class"]})
        if rec["status"] == 200:
            last_ok, lo = rec, mid
        else:
            first_fail, hi = rec, mid
        if hi - lo <= (tol if tol is not None else max(64, lo // 200)):
            break
    return {"label": label, "trail": trail}


def e2(r: Runner, cpt: float) -> dict:
    out = {"chars_per_token_en": cpt}
    one_q = {"q": noul("Urgent?")}
    long_q = lambda i: noul(f"[{i}] " + words(60) + " " + words(60) + " " + words(60) + " " + words(60))
    # (a) one short question: where does the state stop fitting?
    if getattr(r, "only_total", False):
        out["total_budget"] = bisect(r, "20k state + N ~300-token questions", 160, 240,
                                     lambda n: r.ask("e2", {"cond": "total", "n_q": n}, state_of(20_000, cpt),
                                                     {f"q{i}": long_q(i) for i in range(n)}), steps=8, tol=1)
        return out
    out["single_question"] = bisect(r, "state + one short question", 28_000, 36_000,
                                    lambda t: r.ask("e2", {"cond": "single_q", "target": t}, state_of(t, cpt), one_q))
    # (b) state under 32k, total pushed toward 64k with many ~300-token questions.
    def total_case(n_q: int):
        qs = {f"q{i}": long_q(i) for i in range(n_q)}
        return r.ask("e2", {"cond": "total", "n_q": n_q}, state_of(20_000, cpt), qs)
    out["total_budget"] = bisect(r, "20k state + N ~300-token questions", 160, 240, total_case, steps=8, tol=1)
    # (c) state + one long question just over 32k while the total is far under 64k.
    for t in (29_000, 30_500, 31_500):
        q2k = {"q": noul((" " + words(80)) * 25)}  # ~2k tokens
        r.ask("e2", {"cond": "state_plus_long_q", "target": t}, state_of(t, cpt), q2k)
    return out


# --------------------------------------------------------------------------
# E3  fan-out at the extreme
# --------------------------------------------------------------------------

TOPICS = ["the weather in Paris", "a recipe for lasagne", "the rules of cricket", "a famous painting", "the moon landing",
          "a volcano", "classical music", "a football transfer", "the price of gold", "a chess opening", "mountain hiking",
          "a wedding", "a new smartphone", "gardening tips", "a traffic jam", "a birthday party", "space tourism",
          "a public holiday", "a museum visit", "ocean currents", "a marathon", "a film premiere", "coffee beans",
          "a lighthouse", "the stock market", "a school exam", "a train timetable", "desert wildlife", "a jazz concert",
          "a cooking show"]
VERBS = ["mention", "discuss", "ask about", "refer to"]


def fillers(m: int, seed: int, long: bool = False) -> dict:
    rng = random.Random(seed)
    pool = [f"Does the ticket {v} {t}?" for t in TOPICS for v in VERBS]
    rng.shuffle(pool)
    out = {}
    for i in range(m):
        text = pool[i % len(pool)]
        if long:
            text = text + " " + " ".join(words(60) for _ in range(4))
        out[f"filler_{i}"] = noul(text)
    return out


def e3(r: Runner) -> dict:
    targets = {q: QMAP[q] for q in TARGETS}
    for t in TICKETS:
        state = build_state(t, "medium")
        for rep in range(3):  # M = 0: the targets alone in one call, repeated for the noise floor
            r.ask("e3", {"cond": "targets", "ticket": t["id"], "m": 0, "seed": None, "rep": rep}, state, targets)
        for m in (16, 60, 120):
            for seed in (1, 2):
                qs = dict(fillers(m, seed * 100 + m))
                items = list(qs.items()) + list(targets.items())
                random.Random(seed * 7 + m).shuffle(items)  # targets at random positions
                r.ask("e3", {"cond": "targets", "ticket": t["id"], "m": m, "seed": seed, "rep": 0}, state, dict(items))
        for seed in (1, 2):  # token-matched: 16 long fillers ~ 120 short ones in tokens
            qs = dict(fillers(16, seed * 100 + 16, long=True))
            items = list(qs.items()) + list(targets.items())
            random.Random(seed * 11).shuffle(items)
            r.ask("e3", {"cond": "targets_long_fillers", "ticket": t["id"], "m": 16, "seed": seed, "rep": 0}, state, dict(items))
    # Question-count ceiling.
    cap = []
    for n in (255, 256, 257, 400, 1000):
        rec = r.ask("e3", {"cond": "count_cap", "n": n}, ".", {f"q{i}": noul("Yes?") for i in range(n)})
        cap.append({"n": n, "status": rec["status"], "error": rec["error_class"], "billed": rec["input_tokens"]})
        if rec["status"] != 200:
            break
    return {"count_cap": cap}


# --------------------------------------------------------------------------
# E4  cross-language consistency
# --------------------------------------------------------------------------

def localized(lang: str) -> dict:
    out = {}
    for q, spec in QUESTIONS:
        s = json.loads(json.dumps(spec))
        tr = QUESTIONS_I18N[lang][q]
        s["instructions"] = tr["instructions"]
        if "criteria" in tr:
            s["criteria"] = tr["criteria"]
        out[q] = s
    return out


def e4(r: Runner) -> dict:
    en_qs = dict(QUESTIONS)
    for t in TICKETS:
        for rep in range(2):
            r.ask("e4", {"cond": "en_en", "ticket": t["id"], "lang": "en", "rep": rep}, t["text"], en_qs)
        for lang in LANGS[1:]:
            text = TICKETS_I18N[t["id"]][lang]
            r.ask("e4", {"cond": "xx_state_en_q", "ticket": t["id"], "lang": lang, "rep": 0}, text, en_qs)
            for rep in range(2):
                r.ask("e4", {"cond": "xx_state_xx_q", "ticket": t["id"], "lang": lang, "rep": rep}, text, localized(lang))
    return {}


# --------------------------------------------------------------------------
# E5  wording sensitivity
# --------------------------------------------------------------------------

PARAPHRASES = {
    "is_billing": ["Is this ticket about money: a bill, a charge or a refund?", "Does the new ticket concern billing, a charge or getting money back?"],
    "wants_refund": ["Is the customer asking to be refunded?", "Does the ticket request that money be returned to the customer?"],
    "mentions_competitor": ["Does the customer bring up a rival product or switching to one?", "Is a competitor mentioned as an alternative?"],
    "production_impact": ["Is something the customer runs in production, or their income, being hit right now?", "Are the customer's live systems or sales currently affected?"],
}
STRUCTURED = {
    "is_billing": {"question": "Is the ticket about this topic?", "topic": "billing, charges or refunds"},
    "wants_refund": {"question": "Does the customer ask for this?", "request": "money back"},
    "mentions_competitor": {"question": "Does the customer mention this?", "subject": "moving to or comparing with a competitor"},
    "production_impact": {"question": "Is this affected right now?", "what": "the customer's own production system or revenue"},
}


def reorder(spec: dict, how: str) -> dict:
    s = json.loads(json.dumps(spec))
    keys = list(s["criteria"].keys())
    if how == "reversed":
        keys = keys[::-1]
    elif how.startswith("shuffle"):
        random.Random(how).shuffle(keys)
    s["criteria"] = {k: s["criteria"][k] for k in keys}
    return s


def e5(r: Runner) -> dict:
    base = dict(QUESTIONS)
    for t in TICKETS:
        st = t["text"]
        for rep in range(2):
            r.ask("e5", {"cond": "baseline", "ticket": t["id"], "rep": rep}, st, base)
        for how in ("reversed", "shuffle1", "shuffle2"):
            qs = dict(base)
            qs["department"], qs["sentiment"] = reorder(base["department"], how), reorder(base["sentiment"], how)
            r.ask("e5", {"cond": "order", "variant": how, "ticket": t["id"], "rep": 0}, st, qs)
        qs = dict(base)
        qs["department"] = {**base["department"], "criteria": {k: None for k in base["department"]["criteria"]}}
        for rep in range(2):
            r.ask("e5", {"cond": "no_descriptions", "ticket": t["id"], "rep": rep}, st, qs)
        qs = dict(base)
        for q, v in STRUCTURED.items():
            qs[q] = {"type": "noul", "instructions": v}
        for rep in range(2):
            r.ask("e5", {"cond": "structured", "ticket": t["id"], "rep": rep}, st, qs)
        for p in (0, 1):
            qs = dict(base)
            for q, alts in PARAPHRASES.items():
                qs[q] = noul(alts[p])
            r.ask("e5", {"cond": "paraphrase", "variant": f"p{p}", "ticket": t["id"], "rep": 0}, st, qs)
    return {}


# --------------------------------------------------------------------------
# Run
# --------------------------------------------------------------------------

def fit_cpt(r: Runner, lang: str = "en") -> float:
    """Chars per billed token for `lang`, from this run's E1 records."""
    rows = [json.loads(l) for l in PUBLIC.read_text().splitlines()]
    rows = [x for x in rows if x.get("run_id") == r.run_id and x.get("exp") == "e1"]
    base = next(x["input_tokens"] for x in rows if x.get("cond") == "base" and x["status"] == 200)
    pts = [(x["chars"], x["input_tokens"] - base) for x in rows if x.get("cond") == "lang" and x.get("lang") == lang and x["status"] == 200]
    return sum(c for c, _ in pts) / max(1, sum(t for _, t in pts))


def cmd_run(args) -> int:
    only = set((args.only or "e1,e2,e3,e4,e5").split(","))
    r = Runner(args.provider, args.model, args.sleep)
    notes = {}
    if "e1" in only:
        e1(r)
    r.only_total = args.e2_total_only
    if "e2" in only:
        cpt = fit_cpt(r) if "e1" in only else args.cpt
        notes["e2"] = e2(r, cpt)
    if "e3" in only:
        notes["e3"] = e3(r)
    if "e4" in only:
        e4(r)
    if "e5" in only:
        e5(r)
    r.pub.write(json.dumps({"kind": "notes", "run_id": r.run_id, **notes}) + "\n")
    print(f"Run {r.run_id}: {r.n} requests.")
    return 0


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------

def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def linfit(pts):
    n = len(pts)
    mx = sum(x for x, _ in pts) / n
    my = sum(y for _, y in pts) / n
    sxx = sum((x - mx) ** 2 for x, _ in pts)
    slope = sum((x - mx) * (y - my) for x, y in pts) / sxx if sxx else 0.0
    inter = my - slope * mx
    ss_tot = sum((y - my) ** 2 for _, y in pts)
    ss_res = sum((y - (inter + slope * x)) ** 2 for x, y in pts)
    return slope, inter, (1 - ss_res / ss_tot) if ss_tot else 1.0


def dist_summary(pairs):
    """pairs: list of (answer_a, answer_b, qid). Returns per-type metrics."""
    by = defaultdict(list)
    for a, b, q in pairs:
        for m, v in distance(norm_answer(a, QMAP.get(q, a)), norm_answer(b, QMAP.get(q, b))).items():
            if v is not None:
                by[f"{a['type']}.{m}"].append(v)
    return {k: {"n": len(v), "mean": round(statistics.mean(v), 4), "p95": round(sorted(v)[int(0.95 * (len(v) - 1))], 4)}
            for k, v in sorted(by.items())}


def cmd_report(args) -> int:
    lines = [json.loads(l) for l in PUBLIC.read_text().splitlines() if l.strip()]
    # Round 2 ran in batches (E1 first, since E2 sizes its states from E1's
    # chars/token; then E2–E5; then a re-run of the 64k bisection). Report all
    # "-r2" runs together; for notes, a later batch overrides an earlier one.
    runs = [l for l in lines if l.get("kind") == "run" and l["run_id"].endswith("-r2")]
    if args.run_id:
        runs = [r for r in runs if r["run_id"] in args.run_id.split(",")]
    ids = {r["run_id"] for r in runs}
    run = {"run_ids": sorted(ids), **{k: runs[-1][k] for k in ("provider", "requested_model", "usd_per_m_input", "python")}}
    reqs = [l for l in lines if l.get("kind") == "request" and l["run_id"] in ids]
    notes = {}
    for l in lines:
        if l.get("kind") == "notes" and l["run_id"] in ids:
            for k, v in l.items():
                if k in ("kind", "run_id"):
                    continue
                if isinstance(v, dict) and isinstance(notes.get(k), dict):
                    notes[k] = {**notes[k], **v}
                else:
                    notes[k] = v
    ans = {}
    if PRIVATE.exists():
        for l in PRIVATE.read_text().splitlines():
            d = json.loads(l)
            ans[d["id"]] = d["answers"]
    ok = [x for x in reqs if x["status"] == 200]
    S = {"run": run, "requests": len(reqs), "ok": len(ok),
         "billed_usd": round(sum(x["cost"] or 0 for x in ok), 6),
         "input_tokens": sum(x["input_tokens"] or 0 for x in ok),
         "models": sorted({x["model"] for x in ok})}

    # E1
    e1r = [x for x in ok if x["exp"] == "e1"]
    base = next((x["input_tokens"] for x in e1r if x.get("cond") == "base"), None)
    grid = {}
    for cond in ("noul_words", "choice_bare", "choice_described", "score_levels"):
        pts = sorted((x["x"], x["input_tokens"]) for x in e1r if x.get("cond") == cond)
        if len(pts) >= 2:
            slope, inter, r2 = linfit(pts)
            grid[cond] = {"points": pts, "tokens_per_unit": round(slope, 2), "intercept": round(inter, 1), "r2": round(r2, 4)}
    single = {x.get("cond"): x["input_tokens"] for x in e1r if x.get("cond") in ("noul_criteria", "choice_longkeys", "instr_plain", "instr_structured")}
    combos = {}
    for name in {x.get("combo") for x in e1r if x.get("cond") == "combo"}:
        parts = {x["part"]: x["input_tokens"] for x in e1r if x.get("combo") == name}
        k = [p for p in parts if p != "all"]
        predicted = sum(parts[p] for p in k) - (len(k) - 1) * base
        combos[name] = {"all": parts.get("all"), "predicted_from_singles": predicted, "residual": parts.get("all", 0) - predicted}
    langs = {}
    for lang in LANGS:
        pts = [(x["chars"], x["input_tokens"] - base) for x in e1r if x.get("cond") == "lang" and x.get("lang") == lang]
        if len(pts) >= 3:
            slope, inter, r2 = linfit(pts)
            langs[lang] = {"n": len(pts), "tokens_per_char": round(slope, 4),
                           "chars_per_token": round(1 / slope, 2) if slope else None, "intercept": round(inter, 1), "r2": round(r2, 4)}
    S["e1"] = {"base_tokens": base, "grid": grid, "single": single, "additivity": combos, "languages": langs}

    # E2
    S["e2"] = notes.get("e2", {})
    S["e2"]["state_plus_long_q"] = [{"target": x.get("target"), "status": x["status"], "billed": x["input_tokens"], "error": x["error_class"]}
                                    for x in reqs if x["exp"] == "e2" and x.get("cond") == "state_plus_long_q"]

    # E3
    e3r = [x for x in ok if x["exp"] == "e3" and x.get("cond") in ("targets", "targets_long_fillers")]
    groups = defaultdict(list)
    for x in e3r:
        groups[(x["ticket"], x["cond"], x["m"])].append(x)
    noise_pairs, by_m = [], defaultdict(list)
    for (tid, cond, m), xs in groups.items():
        if cond == "targets" and m == 0:
            for i in range(len(xs)):
                for j in range(i + 1, len(xs)):
                    noise_pairs += [(ans[xs[i]["id"]][q], ans[xs[j]["id"]][q], q) for q in TARGETS if xs[i]["id"] in ans and xs[j]["id"] in ans]
    for (tid, cond, m), xs in groups.items():
        if m == 0 and cond == "targets":
            continue
        ref = groups.get((tid, "targets", 0), [])
        key = f"{'long' if cond == 'targets_long_fillers' else 'short'}_m{m}"
        for x in xs:
            for r0 in ref:
                if x["id"] in ans and r0["id"] in ans:
                    by_m[key] += [(ans[x["id"]][q], ans[r0["id"]][q], q) for q in TARGETS]
    lat = defaultdict(list)
    for x in e3r:
        lat[x["n_questions"]].append(x["latency_ms"])
    S["e3"] = {"noise_floor": dist_summary(noise_pairs),
               "vs_batch_of_targets": {k: dist_summary(v) for k, v in sorted(by_m.items())},
               "latency_by_questions": {n: {"median_ms": med(v), "n": len(v)} for n, v in sorted(lat.items())},
               "tokens_by_config": {f"{c}_m{m}": med([x["input_tokens"] for x in xs])
                                    for (t, c, m), xs in groups.items() if t == "t01"},
               **notes.get("e3", {})}

    # E4
    e4r = [x for x in ok if x["exp"] == "e4"]
    idx = defaultdict(list)
    for x in e4r:
        idx[(x["ticket"], x["cond"], x["lang"])].append(x)
    allq = [q for q, _ in QUESTIONS]
    def pairs_between(a_list, b_list):
        return [(ans[a["id"]][q], ans[b["id"]][q], q) for a in a_list for b in b_list if a["id"] in ans and b["id"] in ans for q in allq]
    en_noise = []
    for t in TICKETS:
        xs = idx[(t["id"], "en_en", "en")]
        en_noise += pairs_between(xs[:1], xs[1:2])
    e4 = {"en_repeat_noise": dist_summary(en_noise), "by_language": {}}
    for lang in LANGS[1:]:
        st_en, st_xx, xx_noise, tok = [], [], [], {}
        for t in TICKETS:
            en = idx[(t["id"], "en_en", "en")][:1]
            st_en += pairs_between(idx[(t["id"], "xx_state_en_q", lang)], en)
            xs = idx[(t["id"], "xx_state_xx_q", lang)]
            st_xx += pairs_between(xs[:1], en)
            xx_noise += pairs_between(xs[:1], xs[1:2])
        e4["by_language"][lang] = {"state_translated": dist_summary(st_en), "state_and_questions_translated": dist_summary(st_xx),
                                   "translated_repeat_noise": dist_summary(xx_noise),
                                   "median_billed_tokens": {c: med([x["input_tokens"] for x in e4r if x["lang"] == lang and x["cond"] == c])
                                                            for c in ("xx_state_en_q", "xx_state_xx_q")}}
    e4["en_median_billed_tokens"] = med([x["input_tokens"] for x in e4r if x["cond"] == "en_en"])
    S["e4"] = e4

    # E5
    e5r = [x for x in ok if x["exp"] == "e5"]
    idx5 = defaultdict(list)
    for x in e5r:
        idx5[(x["ticket"], x["cond"])].append(x)
    base_noise, res5 = [], defaultdict(list)
    for t in TICKETS:
        b = idx5[(t["id"], "baseline")]
        base_noise += [(ans[b[0]["id"]][q], ans[b[1]["id"]][q], q) for q in allq if len(b) > 1 and b[0]["id"] in ans and b[1]["id"] in ans]
        for cond, qs in (("order", ["department", "sentiment"]), ("no_descriptions", ["department"]),
                         ("structured", list(STRUCTURED)), ("paraphrase", list(PARAPHRASES))):
            for x in idx5[(t["id"], cond)]:
                if x["id"] in ans and b and b[0]["id"] in ans:
                    res5[cond] += [(ans[x["id"]][q], ans[b[0]["id"]][q], q) for q in qs]
    S["e5"] = {"baseline_repeat_noise": dist_summary(base_noise), **{k: dist_summary(v) for k, v in res5.items()}}

    (OUT / "summary.json").write_text(json.dumps(S, indent=2, ensure_ascii=False, default=str))
    (OUT / "summary.md").write_text(render_md2(S))
    print(json.dumps({k: S[k] for k in ("requests", "ok", "billed_usd", "input_tokens", "models")}, indent=1))
    return 0


def render_md2(S: dict) -> str:
    f = lambda d, k="mean": f"{d[k]:.3f}" if d and d.get(k) is not None else "—"
    L = ["# Round 2 results", "",
         f"Runs {', '.join(S['run']['run_ids'])} via {S['run']['provider']} (`{', '.join(S['models'])}`): "
         f"{S['requests']} requests ({S['ok']} returned 200; the rest are deliberate over-limit probes), "
         f"{S['input_tokens']:,} input tokens, ${S['billed_usd']:.4f} billed. Answers were used only to "
         "compute the distances below and are not published (TypeSafe MCA).", "",
         "## E1 · What a request is billed", "",
         f"Base request (state `.`, one 1-word Noul): **{S['e1']['base_tokens']} tokens**.", "",
         "| Factor | Tokens per unit | R² | Points (unit → billed) |", "|---|---:|---:|---|"]
    names = {"noul_words": "Noul instruction word", "choice_bare": "Choice option (bare key)",
             "choice_described": "Choice option (6-word description)", "score_levels": "Score level"}
    for k, v in S["e1"]["grid"].items():
        L.append(f"| {names.get(k, k)} | {v['tokens_per_unit']} | {v['r2']} | {', '.join(f'{a}→{b}' for a, b in v['points'])} |")
    L += ["", f"Single conditions: {S['e1']['single']}. Additivity (several questions in one call vs singles): "
          + "; ".join(f"{k}: residual {v['residual']} tokens" for k, v in S["e1"]["additivity"].items())
          + " — i.e. ~10 tokens of framing per extra question.", "",
          "| Language | Chars per token | R² | Texts |", "|---|---:|---:|---:|"]
    for lang, v in S["e1"]["languages"].items():
        L.append(f"| {lang} | {v['chars_per_token']} | {v['r2']} | {v['n']} |")
    e2 = S["e2"]
    L += ["", "## E2 · Context limits (bisection, via OpenRouter)", ""]
    for key in ("single_question", "total_budget"):
        if key in e2:
            L.append(f"**{e2[key]['label']}:** " + ", ".join(
                f"{t['v']}→{t['status']}" + (f" ({t['billed']:,} billed)" if t['billed'] else "") for t in e2[key]["trail"]))
            L.append("")
    L += ["State + one ~2.5k-token question: " + ", ".join(f"{x['target']:,}→{x['status']}" for x in e2.get("state_plus_long_q", [])), "",
          "Reading: content (state + longest question) up to 32,768 tokens passes; state + all questions up to 65,536 passes; "
          "the ~260-token overhead is not counted toward either.", "",
          "## E3 · Unrelated questions in the same call", "",
          "| Condition | Noul mean shift | Score mean shift | Choice TVD | Choice top changed |", "|---|---:|---:|---:|---:|"]
    e3 = S["e3"]
    rows = [("targets alone, repeated (noise)", e3["noise_floor"])] + list(e3["vs_batch_of_targets"].items())
    for name, d in rows:
        L.append(f"| {name} | {f(d.get('noul.abs'))} | {f(d.get('score.abs'))} | {f(d.get('choice.tvd'))} | {f(d.get('choice.differs'))} |")
    L += ["", "Median latency by questions in the call: " + ", ".join(f"{n}: {v['median_ms']:.0f} ms" for n, v in e3["latency_by_questions"].items()),
          "", "Question-count probe: " + ", ".join(f"{c['n']}→{c['status']}" for c in e3.get("count_cap", [])), "",
          "## E4 · Cross-language consistency (vs the English run; no labels)", "",
          f"English repeat noise: Noul {f(S['e4']['en_repeat_noise'].get('noul.abs'))}, Score {f(S['e4']['en_repeat_noise'].get('score.abs'))}.", "",
          "| Language | Noul shift: state translated / + questions | Score shift: state / + questions | Top choice changed | Billed tokens: EN q / translated q |",
          "|---|---:|---:|---:|---:|"]
    for lang, v in S["e4"]["by_language"].items():
        a, b = v["state_translated"], v["state_and_questions_translated"]
        L.append(f"| {lang} | {f(a.get('noul.abs'))} / {f(b.get('noul.abs'))} | {f(a.get('score.abs'))} / {f(b.get('score.abs'))} | "
                 f"{f(a.get('choice.differs'))} / {f(b.get('choice.differs'))} | {v['median_billed_tokens']['xx_state_en_q']} / {v['median_billed_tokens']['xx_state_xx_q']} |")
    e5 = S["e5"]
    L += ["", "## E5 · Wording sensitivity (vs the unchanged question)", "",
          f"Repeat noise: Noul {f(e5['baseline_repeat_noise'].get('noul.abs'))}, Choice TVD {f(e5['baseline_repeat_noise'].get('choice.tvd'))}.", "",
          "| Change | Noul shift | Choice TVD | Top choice changed |", "|---|---:|---:|---:|"]
    for k in ("order", "no_descriptions", "structured", "paraphrase"):
        d = e5.get(k, {})
        L.append(f"| {k} | {f(d.get('noul.abs'))} | {f(d.get('choice.tvd'))} | {f(d.get('choice.differs'))} |")
    L += ["", "Wording results describe stability, not accuracy: the tickets are unlabelled.", ""]
    return "\n".join(L)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--provider", choices=sorted(PROVIDERS), default="openrouter")
    r.add_argument("--model", default=None)
    r.add_argument("--only", default=None, help="comma list of e1..e5")
    r.add_argument("--cpt", type=float, default=5.4, help="English chars/token for E2 when E1 is skipped")
    r.add_argument("--sleep", type=float, default=0.05)
    r.add_argument("--e2-total-only", action="store_true", help="re-run only the 64k total-budget bisection")
    r.set_defaults(fn=cmd_run)
    s = sub.add_parser("report")
    s.add_argument("--run-id", default=None)
    s.set_defaults(fn=cmd_report)
    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
