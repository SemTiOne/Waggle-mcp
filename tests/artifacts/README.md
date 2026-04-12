# Verification Artifacts

Saved on branch `codex-save-verification-artifacts`.

## Files

- `smoke_test_output.txt`: full output from `./.venv/bin/python scripts/smoke_test_mcp.py`
- `benchmark_regex_output.txt`: full console output from the regex benchmark run
- `benchmark_regex.json`: JSON report from the regex benchmark run
- `benchmark_llm_output.txt`: full console output from the LLM benchmark run
- `benchmark_llm.json`: JSON report from the LLM benchmark run

## Captured Results

### Smoke test

- MCP server initialized successfully as `waggle`
- `store_node` succeeded for `Smoke Test Preference`
- `query_graph` returned the stored preference node
- graph stats reported `1` node and `0` edges

### Regex benchmark

- Extraction: `4/12 = 33%`
- Retrieval: `5/6 = 83%`
- Deduplication: `3/6 = 50%`
- Threshold sweep:
  - `0.82` -> `3/6 = 50%`
  - `0.85` -> `2/6 = 33%`
  - `0.88` -> `2/6 = 33%`
  - `0.90` -> `2/6 = 33%`
  - `0.92` -> `2/6 = 33%`
  - `0.95` -> `3/6 = 50%`
  - `0.97` -> `3/6 = 50%`

### LLM benchmark

- Intended command: `PYTHONPATH=src ./.venv/bin/python scripts/benchmark_extraction.py --extraction-backend llm --ollama-model qwen2.5:7b`
- Saved artifact outcome after increasing the Ollama request timeout to `30s`:
  - Extraction: `9/12 = 75%`
  - Retrieval: `5/6 = 83%`
  - Deduplication: `3/6 = 50%`
  - Errors: none
- The original failed saved run was caused by the extractor's hardcoded `15s` Ollama timeout. A timed probe showed cases 10 and 12 hitting exactly `15.00s` and returning `None`; the persisted successful run now proves the benchmark is stable with a longer timeout.
