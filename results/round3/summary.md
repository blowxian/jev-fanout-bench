# Round 3: Laya-MLX on an Apple M4 Pro

## Laya 421M (English, 512 ctx)

`aac6fef/laya-mlx` @ `047678560251`, FP16, batch_size 64. Apple M4 Pro (20 GPU cores, 64 GB), macOS 27.0, MLX 0.32.2, laya-mlx 0.2.0 @ `0a8595186341`, on AC power: True. 3 independent processes.

Cold start (median of 3): import 0.2 s, load 0.17 s, first call 42.2 ms; process start to first answer 0.36 s. Peak MLX allocation: 943.6 MiB for one short question, 1736.1 MiB for 50 questions.

| Cell | Input tokens (Laya's count) | Questions | P50 ms | P95 ms | P99 ms | P50 range across processes | Questions/s |
|---|---:|---:|---:|---:|---:|---|---:|
| headline_one_short_question | 93 | 1 | 17.49 | 17.86 | 18.27 | 17.467–17.501 | 57.2 |
| state_length (40 words) | 77 | 1 | 17.3 | 17.46 | 17.55 | 17.219–17.312 | 57.8 |
| state_length (190 words) | 239 | 1 | 34.07 | 34.25 | 34.41 | 33.983–34.073 | 29.4 |
| state_length (360 words) | 423 | 1 | 57.14 | 57.48 | 58.24 | 57.135–57.344 | 17.5 |
| questions_per_call | 93 | 1 | 17.52 | 18.81 | 20.9 | 17.465–17.545 | 57.1 |
| questions_per_call | 347 | 4 | 47.79 | 48.07 | 48.2 | 47.782–47.843 | 83.7 |
| questions_per_call | 1363 | 16 | 174.53 | 179.97 | 183.89 | 172.392–177.866 | 91.7 |
| questions_per_call | 4237 | 50 | 519.27 | 538.45 | 546.28 | 515.895–526.465 | 96.3 |
| choice_options (2 options) | 67 | 1 | 17.23 | 17.44 | 17.57 | 17.157–17.247 | 58.0 |
| choice_options (8 options) | 85 | 1 | 17.45 | 17.62 | 17.72 | 17.421–17.455 | 57.3 |
| choice_options (32 options) | 157 | 1 | 25.27 | 25.48 | 25.59 | 25.229–25.3 | 39.6 |

Sustained 5.0 min, 3 questions per call, 500 tokens per call: median 14.23 calls/s (42.7 questions/s), slowest 30 s window 13.52 calls/s; P50 69.978 ms in the first window, 70.79 ms in the last; worst window P95 76.862 ms.

## Laya multilingual 322M (1,024 ctx)

`aac6fef/laya-multilingual-mlx` @ `ba40c87fcb35`, FP16, batch_size 64. Apple M4 Pro (20 GPU cores, 64 GB), macOS 27.0, MLX 0.32.2, laya-mlx 0.2.0 @ `0a8595186341`, on AC power: True. 3 independent processes.

Cold start (median of 3): import 0.18 s, load 0.4 s, first call 34.3 ms; process start to first answer 0.62 s. Peak MLX allocation: 687.6 MiB for one short question, 1704.9 MiB for 50 questions.

| Cell | Input tokens (Laya's count) | Questions | P50 ms | P95 ms | P99 ms | P50 range across processes | Questions/s |
|---|---:|---:|---:|---:|---:|---|---:|
| headline_one_short_question | 91 | 1 | 7.8 | 7.97 | 8.03 | 7.792–7.838 | 128.2 |
| state_length (40 words) | 77 | 1 | 7.67 | 7.81 | 7.88 | 7.645–7.738 | 130.4 |
| state_length (190 words) | 239 | 1 | 14.09 | 14.28 | 14.34 | 14.079–14.129 | 71.0 |
| state_length (360 words) | 423 | 1 | 23.02 | 23.18 | 23.25 | 22.956–23.024 | 43.4 |
| state_length (730 words) | 823 | 1 | 43.06 | 43.27 | 43.4 | 43.031–43.248 | 23.2 |
| questions_per_call | 91 | 1 | 7.79 | 7.95 | 8.05 | 7.772–7.814 | 128.4 |
| questions_per_call | 348 | 4 | 19.32 | 19.57 | 19.61 | 19.296–19.571 | 207.0 |
| questions_per_call | 1376 | 16 | 60.81 | 61.2 | 61.31 | 60.808–60.854 | 263.1 |
| questions_per_call | 4287 | 50 | 182.6 | 185.4 | 185.94 | 182.251–183.593 | 273.8 |
| choice_options (2 options) | 70 | 1 | 7.68 | 7.84 | 7.98 | 7.641–7.684 | 130.2 |
| choice_options (8 options) | 94 | 1 | 7.76 | 7.95 | 8.0 | 7.747–7.795 | 128.9 |
| choice_options (32 options) | 213 | 1 | 13.52 | 13.7 | 13.76 | 13.497–13.519 | 74.0 |

Sustained 5.0 min, 3 questions per call, 500 tokens per call: median 35.8 calls/s (107.4 questions/s), slowest 30 s window 34.56 calls/s; P50 27.247 ms in the first window, 27.68 ms in the last; worst window P95 32.31 ms.

## What this does and does not show

- Timing wraps `agent.predict` with `mx.synchronize()`: prompt building, tokenization, inference, calibration and formatting. Model loading is reported separately as cold start.
- One machine, one run of each process, sequential calls (no concurrency). Other Macs, other loads and thermal conditions will differ.
- Nothing here measures accuracy, and no Jev call was made. Every answer was discarded.
- `Input tokens` is Laya's own `usage.input_tokens`; nothing is billed when it runs locally. Laya encodes the state once per question, so tokens grow with the number of questions; Jev bills the state once per call.
