# Results

Run `20260923T133522Z-3536c9` via `https://openrouter.ai/api/v1/systemone`, model `typesafe/jev-1.13-20260917` (requested `typesafe/jev-1.13`), 2,976 requests, 3,717,630 input tokens, $0.1561 at $0.042/1M. Python 3.14.5, commit `fed758e1c1`.

## Tokens billed: one call with N questions vs N calls

Medians across tickets, question subsets and repeats; saving with its 95% CI.

| State | N | Batched | Separate | Saving | Saved per 1k items | Latency, serial ÷ batched (median / p95) |
|---|---:|---:|---:|---:|---:|---:|
| tiny | 2 | 344 | 604 | 43.4% ± 0.5 | $0.0110 | 2.02x / 2.43x |
| tiny | 4 | 422 | 1,206 | 65.0% ± 0.4 | $0.0329 | 3.93x / 4.82x |
| tiny | 8 | 584 | 2,411 | 75.8% ± 0.0 | $0.0767 | 7.68x / 9.93x |
| small | 2 | 370 | 656 | 43.9% ± 0.4 | $0.0120 | 2.02x / 2.53x |
| small | 4 | 448 | 1,310 | 65.7% ± 0.4 | $0.0360 | 4.09x / 4.94x |
| small | 8 | 608 | 2,607 | 76.7% ± 0.0 | $0.0839 | 7.72x / 9.10x |
| medium | 2 | 1,020 | 1,958 | 47.9% ± 0.2 | $0.0394 | 2.06x / 2.61x |
| medium | 4 | 1,100 | 3,914 | 71.9% ± 0.1 | $0.1182 | 4.14x / 5.07x |
| medium | 8 | 1,261 | 7,827 | 83.9% ± 0.0 | $0.2758 | 7.87x / 9.05x |
| large | 2 | 3,344 | 6,604 | 49.4% ± 0.0 | $0.1370 | 2.02x / 2.59x |
| large | 4 | 3,422 | 13,206 | 74.1% ± 0.0 | $0.4109 | 4.16x / 5.35x |
| large | 8 | 3,584 | 26,415 | 86.4% ± 0.0 | $0.9589 | 8.63x / 9.17x |

## Does the bill match the rate?

2,976 responses reported what they were charged (`usage.cost`): $0.156140 in total. Against input tokens × $0.042/1M, the largest per-request difference is $0.000000000. Those requests also returned 122,844 output tokens, which the charge does not include.

## Is billing linear?

Under a linear model, `separate − batched = (N − 1) × F`, where F is what one request bills apart from its questions: the state plus a fixed per-request overhead. F is derived independently at every N and question subset; for the same state it varies by at most **0.0 tokens**.

The `tiny` control (a one-word state) puts the fixed overhead at about **261 tokens** per request.

| State | Implied F, median | min | max |
|---|---:|---:|---:|
| tiny | 261.0 | 261.0 | 261.0 |
| small | 285.5 | 283.0 | 291.0 |
| medium | 938.0 | 933.0 | 943.0 |
| large | 3,261.5 | 3,257.0 | 3,265.0 |

## Do the answers change?

Batched-vs-single differences, next to the difference between two identical requests (the noise floor). Noul and Score are on a 0–1 scale (Score divided by its number of steps); Choice reports how often the top option differs and the total-variation distance between the two probability distributions. This measures stability, not accuracy: there are no labels.

| Answer · metric | Batched vs single (mean / p95) | Same request twice (mean / p95) |
|---|---:|---:|
| choice.differs | 0.000 / 0.000 | 0.000 / 0.000 |
| choice.tvd | 0.008 / 0.030 | 0.007 / 0.030 |
| noul.abs | 0.005 / 0.020 | 0.005 / 0.020 |
| score.abs | 0.010 / 0.030 | 0.010 / 0.033 |

Limitations: one region and one client; separate calls are timed serially (an application that fans out concurrently would see a smaller latency gap); synthetic English tickets.
