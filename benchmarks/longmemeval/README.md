# LongMemEval Baseline

This directory contains the downloaded `longmemeval_s_cleaned.json` split and Waggle's exploratory benchmark outputs.

## Dataset

- Source: `xiaowu0162/longmemeval-cleaned`
- File: `longmemeval_s_cleaned.json`
- Cases: `500`

## Reproduction

Run the latest raw retrieval-only baseline:

```bash
.venv/bin/python scripts/benchmark_longmemeval.py \
  benchmarks/longmemeval/longmemeval_s_cleaned.json \
  --mode graph_raw \
  --embedding-model all-MiniLM-L6-v2 \
  --output benchmarks/longmemeval/results_graph_raw_0.1.10_full.json
```

Run the heuristic hybrid baseline:

```bash
.venv/bin/python scripts/benchmark_longmemeval.py \
  benchmarks/longmemeval/longmemeval_s_cleaned.json \
  --mode graph_hybrid \
  --output benchmarks/longmemeval/results_graph_hybrid.json
```

To control where prepared-entry cache files are written:

```bash
.venv/bin/python scripts/benchmark_longmemeval.py \
  benchmarks/longmemeval/longmemeval_s_cleaned.json \
  --mode graph_hybrid \
  --cache-dir /tmp/longmemeval-cache
```

Each run prints whether the prepared-session cache was `cold` or `warm`, and the saved JSON artifact records the cache status, cache key, cache path, and prepared-entry counts.

## Current measured result

Measured locally on the full `500`-question `s` split:

| Mode | R@5 | Exact@5 |
|------|-----|---------|
| `graph_raw` | `97.4%` | `88.4%` |
| `graph_hybrid` | `96.4%` | `85.6%` |

Raw output artifact:

- [`results_graph_raw_0.1.10_full.json`](./results_graph_raw_0.1.10_full.json)
- [`results_graph_hybrid.json`](./results_graph_hybrid.json)
- Methodology note: [docs/longmemeval-methodology.md](../../docs/longmemeval-methodology.md)

## Notes

- This adapter now prepares each LongMemEval entry in memory, batches unique session embeddings, and caches them per run instead of rebuilding a fresh graph per case.
- By default cache files are written to `benchmarks/longmemeval/.cache/`; warm reruns reuse the prepared-session cache and skip re-embedding the same split.
- `graph_raw` is the fairest current comparison to raw retrieval systems because it does not add reranking.
- The latest `graph_raw` proof artifact used `all-MiniLM-L6-v2`, evaluated all `500` cases, prepared `23,796` sessions, and reported `13/500` misses plus `58/500` non-exact top-5 support sets.
- `graph_hybrid` now uses the same prepared-session cache and the full 500-case artifact is saved, but it should still be treated as exploratory rather than a fast CI benchmark.
- The current saved artifacts were generated from cold-cache runs and now include `cache_status`, `cache_path`, `cache_key`, and prepared-entry counts.
