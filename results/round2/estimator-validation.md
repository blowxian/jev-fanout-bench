# Estimator validation

jevpricing.com's `estimateRequest()` (lib/calc.ts) against distinct round-2 requests, each rebuilt and SHA-256-matched to a billed request. Error = (estimate − billed) / billed.

| Group | Requests | Median |error| | P90 |error| | Max |error| | Mean (signed) |
|---|---:|---:|---:|---:|---:|
| **All** | 353 | 1.4% | 4.6% | 11.8% | -1.1% |
| e1 choice_bare | 7 | 1.1% | 2.9% | 3.2% | +1.1% |
| e1 choice_described | 4 | 1.1% | 2.1% | 2.2% | -1.3% |
| e1 choice_longkeys | 1 | 1.9% | 1.9% | 1.9% | +1.9% |
| e1 combo | 7 | 0.3% | 1.6% | 2.0% | +0.2% |
| e1 instr_plain | 1 | 0.3% | 0.3% | 0.3% | -0.3% |
| e1 instr_structured | 1 | 1.3% | 1.3% | 1.3% | -1.3% |
| e1 lang | 72 | 0.9% | 3.5% | 8.4% | -0.0% |
| e1 noul_criteria | 1 | 3.4% | 3.4% | 3.4% | +3.4% |
| e1 noul_words | 2 | 0.3% | 0.3% | 0.4% | +0.3% |
| e1 score_levels | 4 | 1.5% | 1.7% | 1.7% | -1.6% |
| e3 count_cap | 5 | 0.0% | 0.0% | 0.0% | +0.0% |
| e3 targets | 56 | 0.2% | 0.5% | 0.9% | +0.0% |
| e3 targets_long_fillers | 16 | 1.2% | 1.2% | 1.2% | -1.1% |
| e4 baseline | 8 | 2.1% | 2.3% | 2.6% | -2.2% |
| e4 xx_state_en_q | 56 | 1.9% | 3.2% | 6.3% | -1.8% |
| e4 xx_state_xx_q | 56 | 6.0% | 10.4% | 11.8% | -2.7% |
| e5 no_descriptions | 8 | 1.1% | 1.5% | 1.6% | +1.2% |
| e5 order | 24 | 2.1% | 2.3% | 2.6% | -2.2% |
| e5 paraphrase | 16 | 2.3% | 2.8% | 3.0% | -2.4% |
| e5 structured | 8 | 3.8% | 3.9% | 4.2% | -3.8% |
The largest errors are requests whose *question instructions* were translated
(`e4 xx_state_xx_q`, worst 11.8%): non-Latin question text is counted at the
per-character rate measured for prose in that script, which is approximate.

## Coefficients and where they come from

- Per-request overhead 260: round 1, tiny control (F = 261 including the word "Ticket.").
- Per question: 8 tokens of framing + ~1 per Latin-script instruction word (E1 `noul_words`, `count_cap`: 1,000 one-word questions bill 9.0 each).
- Choice option: ~6.8 + 0.3 × key characters (E1: 8/option for `opt0`-style keys, 16/option for 31-character keys) + ~2 per description word (E1 `choice_described`).
- Score level: 8, including a two-word label (E1 `score_levels`, R² 1.00).
- Structured instructions: +4 per object key (E1 `instr_structured`).
- Prose state: characters ÷ per-language rate (E1 `lang`, nine texts per language).
- JSON state: characters of compact JSON ÷ 2.4. Round 1's structured states bill 2.46 (medium) and 2.27 (large) compact-JSON characters per token; 2.4 sits between them and is within 1% on round 2's 56 medium-state requests.

Reproduce: `python3 export_cases.py` here, then in the jevpricing repo
`node scripts/validate-estimator.mts <path>/estimator-cases.jsonl`.
