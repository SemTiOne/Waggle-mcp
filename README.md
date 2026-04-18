<p align="center">
  <img src="https://raw.githubusercontent.com/Abhigyan-Shekhar/graph-memory-mcp/main/assets/banner.png" alt="waggle-mcp" width="720"/>
</p>

<p align="center">
  <strong>Persistent, structured memory for AI agents — 4× fewer tokens than chunk-based retrieval.</strong><br/>
  Your LLM remembers facts, decisions, and context <em>across every conversation</em>, backed by a real knowledge graph.
</p>

<p align="center">
  <a href="https://pypi.org/project/waggle-mcp"><img src="https://img.shields.io/pypi/v/waggle-mcp?color=39d5cf&label=pypi" alt="PyPI"/></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+"/>
  <img src="https://img.shields.io/badge/MCP-compatible-brightgreen" alt="MCP compatible"/>
  <img src="https://img.shields.io/badge/embeddings-local%2C%20no%20API%20key-orange" alt="Local embeddings"/>
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="MIT"/>
</p>

---

## Why waggle-mcp?

Most LLMs forget everything when the conversation ends.  
`waggle-mcp` fixes that by giving your AI a **persistent knowledge graph** it can read and write through any MCP-compatible client.

Waggle's key advantage is **token efficiency with structured context**:

| Without waggle-mcp | With waggle-mcp |
|--------------------------|----------------------|
| Context stuffed into a 200k-token prompt | **~4× fewer tokens** — compact subgraph, only relevant nodes retrieved |
| "What did we decide about the DB schema?" → ❌ Lost when the session ended | ✅ Recalls the decision node, when it was made, and what it contradicts |
| Flat bullet-list memory | Typed edges: `relates_to`, `contradicts`, `depends_on`, `updates`… |
| One session, one agent | Multi-tenant, multi-session, multi-agent |

### How Waggle compares to chunk-replay memory systems

Most AI memory tools store raw conversation chunks and replay them into context. Waggle takes a different approach: it stores structured knowledge as a typed graph — decisions, reasons, contradictions, dependencies — and assembles compact context at query time.

The tradeoff is deliberate: Waggle uses ~4× fewer tokens per retrieval and surfaces full reasoning chains (decision + why + what changed), at some cost to raw verbatim recall on retrieval benchmarks. If your use case values structured reasoning and token efficiency over exhaustive session replay, Waggle is built for that.

> **Note on retrieval:** Waggle prioritizes compact, structured context over raw recall volume — delivering ~4× fewer tokens per retrieval with full reasoning chains. See the [benchmark section](#performance--benchmarking) for honest numbers.

---

## Quick start — 30 seconds

```bash
pip install waggle-mcp
waggle-mcp init
```

The `init` wizard detects your MCP client, writes its config file, and creates
the database directory — no JSON editing required. Supports **Claude Desktop**,
**Cursor**, **Codex**, and a generic JSON fallback.

After init, restart your MCP client and your AI has persistent memory.  
No cloud service. No API key. Semantic search runs fully locally.

---

## The Query Pipeline

Here's how Waggle assembles compact, relational context:

```
User Query
   ↓
Semantic Seed Selection (most-connected, recent, project-relevant)
   ↓
Weighted Graph Traversal (relation-aware priority heap)
   ↓
Support Bundling (decision+reason, old+new, contradiction-pairs)
   ↓
Noise Pruning (weak paths eliminated by min_priority threshold)
   ↓
Compact Context → LLM (4× fewer tokens than naive RAG)
```

**Result:** Full reasoning context without token bloat.

---

## See it in action

Here's a concrete before/after for a developer using the AI daily:

**Session 1** — April 10
```
User:  Let's use PostgreSQL. MySQL replication has been painful.
Agent: [calls observe_conversation()]
       → stores decision node: "Chose PostgreSQL over MySQL"
       → stores reason node:   "MySQL replication painful"
       → links them with a depends_on edge
```

**Session 2** — April 12 (fresh context window, no history)
```
User:  What did we decide about the database?
Agent: [calls query_graph("database decision")]
       → retrieves the decision node + linked reason from April 10

       "You decided on PostgreSQL on April 10. The reason recorded was
        that MySQL replication had been painful."
```

**Session 3** — April 14
```
User:  Actually, let's reconsider — the team is more familiar with MySQL.
Agent: [calls store_node() + store_edge(new_node → old_node, "contradicts")]
       → conflict is flagged automatically; both positions are preserved in the graph
```

> The agent never needed explicit instructions to remember or retrieve — it called
> the right tools based on the conversation, and the graph gave it the right context.

---

## Portable context handoff

Hit a rate limit? Switching models mid-project? Handing context to a colleague's AI?

`export_context_bundle` generates a Markdown or JSON context pack that any AI can consume directly — no Waggle installation required on the receiving end.

```python
export_context_bundle({
  "mode": "query",
  "query": "database architecture decisions",
  "format": "both"
})
```

The Markdown bundle is structured for LLM ingestion:

```markdown
# Waggle Context Bundle
> Exported 2025-06-20T14:32:00Z · query mode · 8 nodes

## Summary
This context covers database architecture decisions across 3 sessions.

## Key Decisions
- **Use PostgreSQL over MySQL** (April 10)
  Reason: MySQL replication was painful
  Status: Under reconsideration — team familiarity with MySQL raised April 14

## Active Contradictions
- PostgreSQL vs MySQL: original decision (April 10) contradicted April 14

## Timeline
- April 10: Decided PostgreSQL, stored reason
- April 12: Retrieved decision + reason successfully
- April 14: New position recorded, contradiction flagged
```

The JSON bundle carries the same information in a structured schema with token estimates, node IDs, edge types, and render hints for programmatic consumption.

Three modes:
- `prime` — curated brief from the existing `prime_context` pipeline
- `query` — retrieval results plus supporting edges for a specific question
- `graph` — full tenant graph, chunked and summarized for large exports

For `mode="query"`, you can also choose a retrieval lane:
- `retrieval_mode="graph"` — graph-native retrieval only
- `retrieval_mode="replay"` — raw transcript/session replay only
- `retrieval_mode="fusion"` — reciprocal-rank fusion of graph context and replay evidence

### Markdown vault round-trip

`export_markdown_vault` writes one Markdown file per node with YAML frontmatter, Obsidian-friendly wikilinks, and stable full-ID filenames. `import_markdown_vault` round-trips those edits back into Waggle non-destructively: new wikilinks create edges, explicit strikethrough wikilinks delete edges, and missing links do not prune history.

---

## Context Assembly: Before & After

The query system now uses **graph-native context assembly** (not chunk retrieval) to avoid the "decision without reasoning" problem.

### Before (FIFO traversal, no support coverage)
```
Query: "What database did we decide on?"

Result: 1 node
├─ ✓ "Use PostgreSQL" (decision)
└─ ✗ NO REASON why PostgreSQL was chosen
   (Agent has to guess or ask follow-up)
```

### After (weighted traversal + support bundling)
```
Query: "What database did we decide on?"

Result: 2+ nodes
├─ ✓ "Use PostgreSQL" (decision)
├─ ✓ "ACID compliance required" (reason, via depends_on edge)
└─ ✓ "SQLite can't handle concurrent writes" (underlying fact)
   (Agent has full context and can explain the choice)
```

**What changed:**
- **Relation weights**: `contradicts=1.0` → `depends_on=0.95` → `similar_to=0.30` (prioritize strong reasoning)
- **Support bundling**: auto-includes contradictions, updates, dependencies
- **Priority heap traversal**: relation priority × edge weight × depth decay (weak paths prune)
- **Expansion metadata**: tracks *how* each node was reached

---

## How it works

Memory doesn't just get stored — it flows through a lifecycle:

```
You talk to your AI
        │
        ▼
  observe_conversation()          ← AI drops the turn in; facts extracted via deterministic conversation parsing
        │
        ▼
  Graph nodes are created         ← "Chose PostgreSQL" becomes a decision node
  Edges are inferred              ← linked to the "database" entity node
        │
        ▼
  Future conversation starts
        │
        ▼
  query_graph("DB schema")        ← semantic search finds the node from 3 sessions ago
        │
        ▼
  AI answers with full context    ← "You decided on PostgreSQL on Apr 10, here's why…"
```

Every node carries semantic embeddings computed **locally** using
[`all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) —
a fast, lightweight model that runs entirely on-device with no API key or network
call required. This means semantic search works offline, costs nothing per query,
and keeps your data private.

---

## The magic tool: `observe_conversation`

> **This is the tool you'll use most.** You don't have to manually store facts — just
> tell the agent to observe each conversation turn and it handles the rest.

```
observe_conversation(user_message, assistant_response)
```

Under the hood, it:
1. Extracts atomic facts from both sides of the conversation
2. Deduplicates against existing nodes using semantic similarity
3. Creates typed edges between related concepts
4. Flags contradictions with existing stored beliefs

No instructions needed. No schema to define. Just observe.

Under the hood, every call runs a deterministic extraction pass that turns messy dialogue into typed graph nodes without requiring a second local model runtime.

**Example:** `"Let's use PostgreSQL because MySQL replication is too painful."`

```json
{
  "facts": [
    {
      "label": "PostgreSQL for generic events",
      "content": "Chose PostgreSQL over MySQL because MySQL replication is too painful.",
      "node_type": "decision",
      "tags": ["observed", "speaker:user"]
    }
  ]
}
```

---

## Memory model

**Node types** — what gets stored:

| Type | Example |
|------|---------| 
| `fact` | "The API uses JWT tokens" |
| `preference` | "User prefers dark mode" |
| `decision` | "Chose PostgreSQL over MySQL" |
| `entity` | "Project: waggle-mcp" |
| `concept` | "Rate limiting" |
| `question` | "Should we add GraphQL?" |
| `note` | "TODO: add integration tests" |

**Edge types** — how nodes connect:

Built-in defaults: `relates_to` · `contradicts` · `depends_on` · `part_of` · `updates` · `derived_from` · `similar_to`

Vault imports and other advanced workflows can also create additional normalized relationship strings when a user-authored edge type does not map cleanly onto the built-in set.

---

## MCP tools

> Your AI calls these directly — you don't need to use them manually.

| Tool | What it does |
|------|-------------|
| `observe_conversation` | **Drop a conversation turn in — facts extracted, stored, and linked** |
| `query_graph` | Semantic + temporal search across the graph, transcript replay, or fusion mode |
| `store_node` | Manually save a fact, preference, decision, or note |
| `store_edge` | Link two nodes with a typed relationship |
| `get_related` | Traverse edges from a specific node |
| `get_node_history` | Inspect one node's evidence, validity window, and related context |
| `list_context_scopes` | Enumerate stored `agent_id`, `project`, and `session_id` scopes |
| `timeline` | Build a chronological memory view for a node, query, or tenant |
| `list_conflicts` | List unresolved contradiction and update edges |
| `resolve_conflict` | Mark a contradiction or update edge as resolved without deleting history |
| `update_node` | Update content or tags on an existing node |
| `delete_node` | Remove a node and all its edges |
| `decompose_and_store` | Break long content into atomic nodes automatically |
| `graph_diff` | See what changed in the last N hours |
| `prime_context` | Generate a compact brief for a new conversation |
| `get_topics` | Detect topic clusters via community detection |
| `get_stats` | Node/edge counts and most-connected nodes |
| `export_graph_html` | Interactive browser visualization |
| `export_graph_backup` | Portable JSON backup |
| `export_context_bundle` | Export Markdown/JSON context packs for handing memory to another AI |
| `export_markdown_vault` | Export one-file-per-node Markdown vaults for Obsidian-compatible editing |
| `import_graph_backup` | Restore from a JSON backup |
| `import_markdown_vault` | Round-trip Markdown vault edits back into the graph |

Most ingestion and retrieval tools also accept optional `agent_id`, `project`, and `session_id` fields so you can keep one tenant’s memory sliced by workspace, agent, or session without spinning up separate databases.

See [Portable context handoff](#portable-context-handoff) for details on `export_context_bundle`.

---

## Performance & Benchmarking

All numbers below are reproducible from the checked-in fixtures in `benchmarks/fixtures/` using the harness at [`scripts/benchmark_extraction.py`](./scripts/benchmark_extraction.py). Saved output artifacts live in [`tests/artifacts/`](./tests/artifacts/README.md).

**One command produces all the tables below** (deterministic extraction, retrieval, dedup, and the comparative token-efficiency pilot):

```bash
.venv/bin/python scripts/benchmark_extraction.py --output tests/artifacts/benchmark_current.json
```


### Extraction accuracy

Corpus: 12 dialogue pairs covering simple recall, interruptions, reversals, vague statements, and conflicting signals (`benchmarks/fixtures/extraction_cases.json`).

| Backend | Cases | Accuracy |
|---------|-------|----------|
| Deterministic conversation parser | 12 | 100% |

### Retrieval accuracy

Corpus: 18 nodes, 18 queries — 6 easy (direct paraphrase) and 12 hard (adversarial: semantic generalization, temporal disambiguation, indirect domain translation, privacy framing). Source: `benchmarks/fixtures/retrieval_cases.json`.

| Difficulty | Queries | Hit@k |
|------------|---------|-------|
| Easy | 6 | 6/6 = 100% |
| Hard (adversarial) | 12 | 9/12 = 75% |
| **Overall** | **18** | **15/18 = 83%** |

### Token efficiency vs. naive chunked-vector RAG

*The retrieval accuracy table above measures Waggle's standalone search quality. The comparison below uses a separate multi-session corpus designed to test token efficiency against a chunked-vector baseline.*

Corpus: 27 multi-session scenarios, 66 retrieval queries across 7 task families (`benchmarks/fixtures/comparative_eval.json`).

| Task family | Queries | Waggle Hit@k | RAG Hit@k |
|-------------|---------|-------------|----------|
| `factual_recall` | 18 | 18/18 = 100% | 100% |
| `temporal_original` | 19 | 17/19 = 89% | 100% |
| `multi_session_change` | 11 | 10/11 = 91% | 100% |
| `cross_scenario_synthesis` | 8 | 7/8 = 88% | 100% |
| `decision_delta` | 4 *(small n)* | 4/4 = 100% | 100% |
| `adversarial_paraphrase` | 4 *(small n)* | 1/4 = 25% | 100% |
| `temporal_latest` | 2 *(small n)* | 1/2 = 50% | 100% |
| **Overall** | **66** | **58/66 = 88%** | **100%** |

| System | Mean tokens | Median tokens | p95 tokens | Hit@k | Exact support |
|--------|-------------|---------------|------------|-------|---------------|
| **Waggle** | **37.7** | **38.0** | **45.0** | 88% | 73% |
| Naive chunked-vector RAG | 150.2 | 149.0 | 161.0 | 100% | 98% |

**Waggle uses ~4× fewer tokens per retrieval** than the naive chunked baseline on this corpus.

The graph-native context assembly work below targets the remaining gap between Waggle's Hit@k (88%) and exact support (73%). The system now automatically:
- Co-surfaces decision + reason nodes (dependency coverage)
- Includes both old and new decisions when contradictions are found (conflict symmetry)
- Traverses multi-hop reasoning chains while pruning weak paths (noise resistance)
- Ranks nodes by relationship type, not just similarity (semantic priority)

The dedicated context-assembly suite below passes, but the larger comparative corpus still exposes misses on adversarial paraphrase and some cross-scenario synthesis queries. That tradeoff is reflected in the saved artifact rather than hidden.

### Context Assembly Validation (NEW)

These improvements are validated in the dedicated benchmark suite (`run_context_assembly_benchmark.py`):

| Benchmark | Measurement | Result |
|-----------|-------------|--------|
| Decision + reason co-appear | Support coverage | 100% |
| Old + new + updates edge | Contradiction symmetry | 100% |
| Multi-hop dependency chain | Chain preservation | 100% |
| 10 noise nodes vs. core | Noise resistance | 100% |

The tradeoff is honest: the chunked baseline achieves 100% Hit@k on this corpus because at `top_k=5` every fact is retrievable from its own session chunk. The token efficiency advantage is real and reproducible; the retrieval superiority claim requires a corpus where chunk coverage can't compensate for missing relational context. Corpus hardening is ongoing.

### Query Stress Eval (NEW)

The system was also tested on a pure query stress evaluation corpus containing 40 adversarial cases across `adversarial_paraphrase` and `temporal_latest` task families:

> **Methodology note:** The comparative corpus above is an end-to-end evaluation: raw conversation → extraction → graph construction → retrieval. The Query Stress Eval below pre-loads a known graph and tests retrieval in isolation against 40 adversarial queries, with extraction removed as a variable. The gap between these two evaluations shows that retrieval quality is strong (98%) in isolation, while the broader end-to-end corpus still exposes harder paraphrase and temporal edge cases. The current 12-case extraction fixture now scores 100%, but the comparative corpus remains the more important test of real-world robustness.

| System | Hit@k | Exact support | Mean tokens |
|--------|-------|---------------|-------------|
| graph_raw | 98% | 98% | 37.0 |
| graph_hybrid | 98% | 98% | 63.9 |

This demonstrates that against more complex retrieval targets specifically crafted to break generic keyword/vector chunk systems, the raw semantic graph traversal retains an incredibly high 98% Hit@k profile with very minimal token burn.


### When extraction is ambiguous

> **User:** "Yeah, let's just do that thing we talked about."

The deterministic extractor ignores vague turns like this rather than storing a guess. Waggle only persists content that resolves to a concrete fact, decision, preference, entity, concept, question, or note.

<details>
<summary>Deduplication results (22-pair fixture — click to expand)</summary>

Corpus: 22 node pairs — 11 true duplicates (synonym, paraphrase, domain equivalence) and 11 false friends (same technology category, different technology). Source: `benchmarks/fixtures/dedup_cases.json`.

The pipeline runs five layers:
1. **Layer 0 — Entity-key hard block** — if both nodes name *different* technologies in the *same* category (e.g. `postgresql` vs `mysql`), merge is blocked unconditionally.
2. **Layer 0b — Numeric-conflict guard** — same entity but *different critical numbers* (e.g. `jwt` 15 min vs 1 hr) → block. Guards against merging distinct facts that share a technology but differ on a key value.
3. **Layer 1 — Exact string match** — normalized content or label equality.
4. **Layer 2 — Substring containment** — one sentence is a strict subset of the other.
5. **Layer 3 — Semantic similarity** — cosine via `all-MiniLM-L6-v2`:
   - Same-entity aggressive path: if both reference the **same** entity token, merge at cosine ≥ 0.60 (catches paraphrase true-dups like "fastapi was chosen" / "we chose fastapi because async")
   - Type-aware threshold: `decision`/`preference` → 0.82; `fact` → 0.92; `entity` → 0.97
   - Jaccard-boosted path: word overlap ≥ 0.35 AND cosine ≥ (type threshold − 0.05)
   - Conservative global fallback

Best measured: **17/22 = 77%** at threshold 0.82. **fp=0 across all thresholds** — no false-friend merges at any tested threshold.

The remaining 4 false-negatives are pure-paraphrase pairs with no recognisable entity anchor ("user prefers dark mode" / "user wants dark mode UI", "async non-negotiable" / "concurrent without blocking"). These require either semantic similarity fine-tuning or a learned paraphrase classifier to close.

Full threshold sweep and detailed methodology: [`tests/artifacts/README.md`](./tests/artifacts/README.md).

</details>

### External benchmark evaluation

A LongMemEval exploratory adapter has been built and supports two currently implemented evaluation modes plus one planned reranked mode:

- `graph_raw` — graph retrieval only, no LLM
- `graph_hybrid` — graph retrieval plus deterministic query expansion and temporal boosts
- `graph_reranked` — planned lightweight LLM reranking mode for external comparison

Exploratory external baseline on the full `500`-question `s` split:

| Mode | R@5 | Exact@5 | Status |
|------|-----|---------|--------|
| `graph_raw` | `97.0%` | `76.4%` | Full exploratory run completed |
| `graph_hybrid` | `95.8%` | `82.0%` | Full exploratory run completed |

No threshold claims are made until the methodology note is finalized and the reranked comparison path is measured.

The benchmark runner now keys its prepared-session cache by dataset content hash plus embedding model/version. CLI runs report whether the result came from a cold or warm cache, and warm reruns reuse the saved prepared entries instead of rebuilding the split from scratch.

> LongMemEval artifacts and reproduction notes: [`benchmarks/longmemeval/README.md`](./benchmarks/longmemeval/README.md)  
> Full internal artifacts, methodology, and rag_tuned comparison: [`tests/artifacts/README.md`](./tests/artifacts/README.md)  
> Improvement roadmap (dedup → context assembly → corpus hardening): [`docs/evaluation-plan.md`](./docs/evaluation-plan.md)



---

## Temporal queries — built-in, not bolted on

Most memory systems answer "what do you know about X?" — but can't answer
*when* you learned it or how knowledge changed over time.

`waggle-mcp` timestamps every node and understands temporal natural language:

| Query | What happens |
|-------|-------------|
| `query_graph("what did we decide recently")` | Filters nodes updated in the last 24–48h |
| `query_graph("what was the original plan")` | Retrieves the earliest version of relevant nodes |
| `query_graph("what changed last week")` | Returns a diff of nodes created/updated in that window |
| `graph_diff(since="48h")` | Explicit changelog: added nodes, updated nodes, new conflicts |

---

## Testing

Beyond empirical benchmarks, `waggle-mcp` ships with a comprehensive pytest suite covering both memory logic and server protocols. This guarantees core behaviours — multi-tenant isolation, conflict detection, semantic deduplication, scoped retrieval, context bundle export, and MCP protocol handling — remain stable across updates.

<details>
<summary>View a recent pytest run on the latest branch (click to expand)</summary>

```text
============================= test session starts ==============================
collected 81 items

tests/test_benchmark_harness.py .....
tests/test_embeddings.py ....
tests/test_graph.py .............................
tests/test_packaging_metadata.py ..
tests/test_platform.py ......
tests/test_server.py .........................
tests/test_stdio_integration.py .
tests/test_longmemeval_benchmark.py .

============================== 81 passed in 6.75s ==============================
```
</details>

---

## Installation

<details>
<summary>Local / development (SQLite, no extra services)</summary>

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
waggle-mcp init        # ← writes your client config automatically
```

If `.venv` already exists from a different Python version, remove it first and recreate it. Reusing a stale environment can leave the wrapper scripts pointing at the wrong interpreter.

Key variables for local mode:

| Variable | What it does |
|----------|-------------|
| `WAGGLE_BACKEND=sqlite` | Local file DB, zero setup |
| `WAGGLE_TRANSPORT=stdio` | Connects to desktop MCP clients |
| `WAGGLE_DB_PATH` | Where the graph is stored (default: `memory.db`) |

</details>

<details>
<summary>Production (Neo4j backend)</summary>

```bash
pip install -e ".[dev,neo4j]"

WAGGLE_TRANSPORT=http \
WAGGLE_BACKEND=neo4j \
WAGGLE_DEFAULT_TENANT_ID=workspace-default \
WAGGLE_NEO4J_URI=bolt://localhost:7687 \
WAGGLE_NEO4J_USERNAME=neo4j \
WAGGLE_NEO4J_PASSWORD=change-me \
waggle-mcp
```

</details>

<details>
<summary>Docker</summary>

```bash
docker build -t waggle-mcp:latest .

# CLI arguments pass through to the module entrypoint
docker run --rm waggle-mcp:latest --help

docker run --rm -p 8080:8080 \
  -e WAGGLE_TRANSPORT=http \
  -e WAGGLE_BACKEND=neo4j \
  -e WAGGLE_DEFAULT_TENANT_ID=workspace-default \
  -e WAGGLE_NEO4J_URI=bolt://host.docker.internal:7687 \
  -e WAGGLE_NEO4J_USERNAME=neo4j \
  -e WAGGLE_NEO4J_PASSWORD=change-me \
  waggle-mcp:latest
```

</details>

<details>
<summary>Manual client configuration</summary>

**Claude Desktop — `claude_desktop_config.json`**

```json
{
  "mcpServers": {
    "waggle": {
      "command": "/path/to/.venv/bin/python",
      "args": ["-m", "waggle.server"],
      "env": {
        "WAGGLE_TRANSPORT": "stdio",
        "WAGGLE_BACKEND": "sqlite",
        "WAGGLE_DB_PATH": "~/.waggle/memory.db",
        "WAGGLE_DEFAULT_TENANT_ID": "local-default",
        "WAGGLE_MODEL": "all-MiniLM-L6-v2"
      }
    }
  }
}
```

**Codex — `codex_config.toml`**

```toml
[mcp_servers.waggle]
command = "/path/to/.venv/bin/python"
args    = ["-m", "waggle.server"]
env     = {
  WAGGLE_TRANSPORT         = "stdio",
  WAGGLE_BACKEND           = "sqlite",
  WAGGLE_DB_PATH           = "~/.waggle/memory.db",
  WAGGLE_DEFAULT_TENANT_ID = "local-default",
  WAGGLE_MODEL             = "all-MiniLM-L6-v2"
}
```

A pre-filled example is in [`codex_config.example.toml`](./codex_config.example.toml).

</details>

---

## Environment variables

<details>
<summary>Click to expand full reference</summary>

### Core

| Variable | Default | Description |
|----------|---------|-------------|
| `WAGGLE_BACKEND` | `sqlite` | `sqlite` or `neo4j` |
| `WAGGLE_TRANSPORT` | `stdio` | `stdio` or `http` |
| `WAGGLE_MODEL` | `all-MiniLM-L6-v2` | sentence-transformers model (local inference) |
| `WAGGLE_DEFAULT_TENANT_ID` | `local-default` | default tenant |
| `WAGGLE_EXPORT_DIR` | — | optional export directory |

### SQLite

| Variable | Default | Description |
|----------|---------|-------------|
| `WAGGLE_DB_PATH` | `memory.db` | path to the SQLite file |

### HTTP service

| Variable | Default | Description |
|----------|---------|-------------|
| `WAGGLE_HTTP_HOST` | `0.0.0.0` | bind host |
| `WAGGLE_HTTP_PORT` | `8080` | bind port |
| `WAGGLE_LOG_LEVEL` | `INFO` | log level |
| `WAGGLE_RATE_LIMIT_RPM` | `120` | global rate limit (req/min) |
| `WAGGLE_WRITE_RATE_LIMIT_RPM` | `60` | write-tool rate limit |
| `WAGGLE_MAX_CONCURRENT_REQUESTS` | `8` | concurrency cap |
| `WAGGLE_MAX_PAYLOAD_BYTES` | `1048576` | max request size |
| `WAGGLE_REQUEST_TIMEOUT_SECONDS` | `30` | per-request timeout |

### Neo4j

| Variable | Description |
|----------|-------------|
| `WAGGLE_NEO4J_URI` | Bolt URI, e.g. `bolt://localhost:7687` |
| `WAGGLE_NEO4J_USERNAME` | Neo4j username |
| `WAGGLE_NEO4J_PASSWORD` | Neo4j password |
| `WAGGLE_NEO4J_DATABASE` | Neo4j database name |

### Conversation Extraction

No extra extraction runtime is required. `observe_conversation` uses the built-in deterministic parser and stores only structured facts that map cleanly onto Waggle node types.

</details>

---

<details>
<summary>Admin commands</summary>

```bash
# Create a tenant
waggle-mcp create-tenant --tenant-id workspace-a --name "Workspace A"

# Issue an API key (raw key returned once — store it securely)
waggle-mcp create-api-key --tenant-id workspace-a --name "ci-agent"

# List keys for a tenant
waggle-mcp list-api-keys --tenant-id workspace-a

# Revoke a key
waggle-mcp revoke-api-key --api-key-id <id>

# Migrate SQLite data → Neo4j
WAGGLE_BACKEND=neo4j WAGGLE_NEO4J_URI=bolt://localhost:7687 \
WAGGLE_NEO4J_USERNAME=neo4j WAGGLE_NEO4J_PASSWORD=change-me \
  waggle-mcp migrate-sqlite --db-path ./memory.db --tenant-id workspace-a
```

</details>

<details>
<summary>Kubernetes & observability</summary>

Full production deployment assets are in [`deploy/`](./deploy/):

| Path | What's inside |
|------|--------------|
| `deploy/kubernetes/` | Deployment, Service, Ingress (TLS), NetworkPolicy, HPA, PDB, cert-manager, ExternalSecrets — see [`deploy/kubernetes/README.md`](./deploy/kubernetes/README.md) |
| `deploy/observability/` | Prometheus scrape config, Grafana dashboard, one-command Docker Compose observability stack |

Operational runbooks are in [`docs/runbooks/`](./docs/runbooks/):

- [API key rotation](./docs/runbooks/api-key-rotation.md) — zero-downtime create-then-revoke
- [Incident response](./docs/runbooks/incident-response.md) — Neo4j down, OOM, rate storm, auth failures
- [Backup & restore](./docs/runbooks/backup-restore.md) — manual and automated drill
- [Tenant onboarding](./docs/runbooks/onboarding.md) — new tenant checklist
- [Secret management](./docs/runbooks/secret-management.md) — External Secrets + cert-manager

</details>

<details>
<summary>Architecture & project layout</summary>

```
waggle-mcp
├── Core domain    graph CRUD · dedup · local embeddings · conflict detection · export/import
├── Transport      stdio MCP (Codex/Desktop) · streamable HTTP MCP (Kubernetes)
└── Platform       config · auth · tenant isolation · rate limiting · logging · metrics
```

**Backend:**
- Local/dev → SQLite (zero config, instant start)
- Production → Neo4j (`WAGGLE_TRANSPORT=http` requires `WAGGLE_BACKEND=neo4j`)

```
waggle-mcp/
├── assets/                   ← banner + demo SVG
├── benchmarks/fixtures/      ← checked-in eval datasets
├── deploy/
│   ├── kubernetes/           ← full K8s manifests + guide
│   └── observability/        ← Prometheus + Grafana stack
├── docs/runbooks/            ← operational runbooks
├── scripts/
│   ├── benchmark_extraction.py
│   ├── load_test.py / .sh
│   └── backup_restore_drill.py / .sh
├── src/waggle/         ← server, graph, neo4j_graph, auth, config …
├── tests/artifacts/    ← saved benchmark runs
├── Dockerfile
├── pyproject.toml
└── README.md
```

</details>

---

## Next Steps

**Retrieval & assembly** ✅ — Completed. Relation-aware context assembly now automatically bundles supporting context (decisions + reasons, old + new decisions with updates, full dependency chains), with all benchmarks passing.

**Extraction hardening** 🎯 — The deterministic parser now scores 100% on the current 12-case extraction corpus after adding better reversal, final-choice, and numeric rate-limit handling. The next step is broadening the fixture set and relation inference so these gains hold on larger paraphrase- and temporality-heavy corpora, not just the current small benchmark.

Planned improvements:
- Expand the extraction fixture beyond the current 12 cases so adversarial phrasing and temporal updates are measured directly
- Improve the deterministic parser's coverage of hedged statements, multi-fact sentences, and cross-turn context
- Add `ConversationContext` to relation inference (sentence proximity, coreference)
- Introduce structured `RichEdge` with proof snippets and confidence scores
- Add richer relation inference so user-authored vault relations and conversation-derived relations stay high-quality without manual cleanup

**External benchmarks** 🔜 — The exploratory LongMemEval baselines are now published at `97.0% R@5 / 76.4% Exact@5` for `graph_raw` and `95.8% R@5 / 82.0% Exact@5` for `graph_hybrid` on the full 500-case `s` split. The next deliverable is a short methodology note, a saved cold/warm cache comparison in the docs, and the planned reranked comparison path.

**Product hardening** 🧭 — Transcript replay/fusion retrieval and markdown-vault round-trip are now in the product on both SQLite and Neo4j. The remaining work is polish rather than surface area: more aggressive replay ranking for recall-heavy corpora, cleaner Neo4j query warnings, and a stronger import report for large edited vaults.

---

## Running tests

```bash
.venv/bin/pytest -q
```

Coverage: graph CRUD, deduplication, conflict detection, tenant isolation,
backup/import, stdio MCP, HTTP auth/health/metrics, payload limits.

---

## License

MIT — see [LICENSE](./LICENSE).
