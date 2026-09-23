# Round 2 results

Runs 20260923T164332Z-r2, 20260923T164502Z-r2, 20260923T164851Z-r2 via openrouter (`typesafe/jev-1.13-20260917`): 487 requests (479 returned 200; the rest are deliberate over-limit probes), 851,428 input tokens, $0.0358 billed. Answers were used only to compute the distances below and are not published (TypeSafe MCA).

## E1 · What a request is billed

Base request (state `.`, one 1-word Noul): **270 tokens**.

| Factor | Tokens per unit | R² | Points (unit → billed) |
|---|---:|---:|---|
| Noul instruction word | 1.0 | 1.0 | 1→269, 10→278, 30→298, 80→348 |
| Choice option (bare key) | 8.56 | 0.9991 | 2→289, 3→296, 5→310, 10→345, 20→425, 50→665, 100→1065, 255→2460 |
| Choice option (6-word description) | 20.77 | 0.9998 | 2→319, 5→376, 10→471, 50→1311 |
| Score level | 8.0 | 1.0 | 2→292, 3→300, 5→316, 7→332, 10→356 |

Single conditions: {'noul_criteria': 292, 'choice_longkeys': 425, 'instr_plain': 287, 'instr_structured': 298}. Additivity (several questions in one call vs singles): three_nouls: residual 20 tokens; mixed: residual 20 tokens — i.e. ~10 tokens of framing per extra question.

| Language | Chars per token | R² | Texts |
|---|---:|---:|---:|
| en | 4.92 | 0.9986 | 9 |
| zh | 1.0 | 0.9952 | 9 |
| ja | 1.01 | 0.9983 | 9 |
| ko | 1.44 | 0.9941 | 9 |
| es | 4.44 | 0.9867 | 9 |
| hi | 1.72 | 0.9961 | 9 |
| ar | 1.49 | 0.9884 | 9 |
| ru | 1.78 | 0.9834 | 9 |

## E2 · Context limits (bisection, via OpenRouter)

**state + one short question:** 32000→200 (32,571 billed), 34000→400, 33000→400, 32500→400, 32250→200 (32,823 billed), 32375→200 (32,948 billed)

**20k state + N ~300-token questions:** 200→400, 180→400, 170→200 (63,856 billed), 175→200 (65,136 billed), 177→200 (65,648 billed), 178→400

State + one ~2.5k-token question: 29,000→200, 30,500→400, 31,500→400

Reading: content (state + longest question) up to 32,768 tokens passes; state + all questions up to 65,536 passes; the ~260-token overhead is not counted toward either.

## E3 · Unrelated questions in the same call

| Condition | Noul mean shift | Score mean shift | Choice TVD | Choice top changed |
|---|---:|---:|---:|---:|
| targets alone, repeated (noise) | 0.003 | 0.012 | 0.005 | 0.000 |
| long_m16 | 0.003 | 0.008 | 0.007 | 0.000 |
| short_m120 | 0.002 | 0.009 | 0.005 | 0.000 |
| short_m16 | 0.002 | 0.010 | 0.005 | 0.000 |
| short_m60 | 0.003 | 0.008 | 0.004 | 0.000 |

Median latency by questions in the call: 4: 426 ms, 20: 441 ms, 64: 434 ms, 124: 436 ms

Question-count probe: 255→200, 256→200, 257→200, 400→200, 1000→200

## E4 · Cross-language consistency (vs the English run; no labels)

English repeat noise: Noul 0.003, Score 0.009.

| Language | Noul shift: state translated / + questions | Score shift: state / + questions | Top choice changed | Billed tokens: EN q / translated q |
|---|---:|---:|---:|---:|
| zh | 0.017 / 0.018 | 0.029 / 0.056 | 0.062 / 0.062 | 624.0 / 695.0 |
| ja | 0.017 / 0.023 | 0.059 / 0.041 | 0.000 / 0.000 | 644.5 / 819.5 |
| ko | 0.015 / 0.042 | 0.042 / 0.069 | 0.000 / 0.000 | 632.0 / 728.0 |
| es | 0.013 / 0.026 | 0.040 / 0.059 | 0.000 / 0.000 | 616.5 / 674.5 |
| hi | 0.010 / 0.031 | 0.051 / 0.057 | 0.000 / 0.000 | 663.0 / 980.0 |
| ar | 0.016 / 0.035 | 0.033 / 0.051 | 0.000 / 0.000 | 646.0 / 905.0 |
| ru | 0.016 / 0.067 | 0.032 / 0.038 | 0.000 / 0.000 | 664.5 / 915.5 |

## E5 · Wording sensitivity (vs the unchanged question)

Repeat noise: Noul 0.003, Choice TVD 0.009.

| Change | Noul shift | Choice TVD | Top choice changed |
|---|---:|---:|---:|
| order | — | 0.020 | 0.000 |
| no_descriptions | — | 0.096 | 0.000 |
| structured | 0.028 | — | — |
| paraphrase | 0.024 | — | — |

Wording results describe stability, not accuracy: the tickets are unlabelled.
