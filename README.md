# jev-fanout-bench

A reproducible measurement of one claim about [Jev](https://docs.typesafe.ai/),
TypeSafe AI's System One decision model:

> Jev ingests the `state` once and evaluates every question against it in
> parallel. — [TypeSafe, *Models*](https://docs.typesafe.ai/models)

If that holds on the bill, asking N questions in **one** request should cost
the state once, and asking them in **N** requests should cost it N times.
TypeSafe's own [parallel-questions cookbook](https://docs.typesafe.ai/cookbooks/parallel_questions)
measured this once, on one document, as 12.2x cheaper. This repository
measures it across state sizes and question counts, and checks three things
the cookbook does not:

1. **Is billing exactly linear?** Under a linear model,
   `separate − batched = (N − 1) × F`, where F is everything one request bills
   apart from its questions: the state plus a fixed per-request overhead. The
   report derives F independently at every N and question subset and shows
   how far the estimates for one state disagree. A one-word `tiny` state is
   included as a control, so the fixed overhead can be read off on its own.
2. **How big is the saving, by state size?** Roughly 30, 440 and 1,800-token
   states (a bare ticket; a ticket with account history; a ticket with long
   history and order records), at N = 2, 4 and 8 questions, in percent and in
   dollars per thousand items.
3. **Do the answers change?** Every question is asked both inside the batch
   and alone, and every request is repeated, so the batched-vs-single
   difference is reported next to the difference between two identical
   requests. A shift smaller than that noise floor is not an effect of
   batching.

**Status: the harness is complete; results are not yet published.** Nothing
under `results/` is a measurement until a real run has produced it.

## Run it

Python 3.10+, standard library only.

```bash
export TYPESAFE_API_KEY=...        # from https://console.typesafe.ai/
python bench.py run                # ~2,980 requests, ~15 minutes
python bench.py report             # -> results/summary.md, summary.json, fanout.svg
```

A full run sends 2,976 requests and about 2 million input tokens: roughly
**$0.09** at the published $0.042 per million input tokens (output is not
billed). It pins `jev-1.13.0` rather than `jev-latest`, which can move to a
new model mid-study; `--model` overrides it. 429 and 529 responses and
network errors are retried with backoff, as the API docs ask.

To exercise the whole pipeline without a key or network access:

```bash
python bench.py run --dry-run --out /tmp/dry/raw.jsonl
python bench.py report --input /tmp/dry/raw.jsonl
```

Dry-run numbers are a characters-divided-by-four estimate, are labelled
`DRY RUN` everywhere they appear, and are never a result.

## What is measured, exactly

- **Inputs** (`bench_data.py`): 8 synthetic support tickets, written for this
  repository, at 3 state sizes plus the `tiny` control. Eight questions — four
  Noul, two Choice, two Score — split for each N into 8/N disjoint subsets, so
  every question is asked equally often at every N and N is not confounded
  with which questions were asked.
- **Blocks**: one block is a (ticket, size, N, subset, repeat). Its batched
  call and its N single calls run back to back, batched-first or
  singles-first at random, so both arms see the same moment of API load.
  Blocks run in a seeded random order; every block is repeated 3 times.
- **Tokens**: `usage.input_tokens` as returned by the API. Nothing is
  estimated in a real run.
- **Latency**: per request over one persistent, pre-warmed HTTPS connection,
  excluding retries (which are logged and dropped from the latency figures).
  The N single calls of a block are summed as a serial sequence — how an
  application asking one question at a time experiences them.
- **Answers**: Noul and Score on a 0–1 scale; for Choice, how often the top
  option differs and the total-variation distance between the probability
  distributions. This is stability, not accuracy: the tickets are unlabelled.
- **Raw data**: every request body (and its SHA-256), status, timings and full
  response, plus a run header with the Python version, platform, git commit
  and the price used, are appended to `results/raw.jsonl` before anything is
  summarised. `report` refuses runs with failed or duplicated requests or
  mixed model versions unless told otherwise.

## Limitations

One client, one network location, one region. Serial timing of the separate
calls overstates the latency gap an application that fans out concurrently
would see. The tickets are synthetic and in English, the language TypeSafe
says Jev is most accurate in.

## Related

- [jevpricing.com](https://jevpricing.com/fan-out/) — an independent
  calculator that applies the fan-out arithmetic to your own workload. Same
  author.
- [TypeSafe: speculative fan-out](https://docs.typesafe.ai/patterns/fan-out)
  and [parallel questions](https://docs.typesafe.ai/cookbooks/parallel_questions).

Independent and unofficial. Not affiliated with or endorsed by TypeSafe AI.

## License

Code: MIT. The inputs in `bench_data.py` and anything under `results/`: CC0.
