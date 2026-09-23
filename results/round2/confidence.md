# E7 · Does confidence flag fragile answers?

960 pairs: an answer after rewording, reordering, restructuring or translating, against the same question's baseline answer. Grouped by the *baseline* answer's confidence. No new requests; aggregates only.

| Type | Confidence tercile | Range | Mean shift | Top option changed | Pairs |
|---|---|---|---:|---:|---:|
| choice | low | 0.54–0.92 | 0.078 | 5.0 | 160 |
| choice | mid | 0.92–1 | 0.016 | 0.0 | 160 |
| choice | high | 1–1 | 0.005 | 0.0 | 160 |
| choice | Spearman ρ (confidence vs shift) | | -0.79 | | |
| score | low | 0–0.56 | 0.060 | — | 160 |
| score | mid | 0.56–0.79 | 0.045 | — | 160 |
| score | high | 0.79–1 | 0.008 | — | 160 |
| score | Spearman ρ (confidence vs shift) | | -0.51 | | |

Shift: Noul/Score absolute change (0–1 scale), Choice total-variation distance. This is stability under rewording, not accuracy: the tickets are unlabelled.
