<p align="center">
  <img src="https://raw.githubusercontent.com/Abhigyan-Shekhar/graph-memory-mcp/main/assets/banner.png" alt="waggle-mcp" width="720"/>
</p>

<p align="center">
  <strong>Persistent, structured memory for AI agents — backed by a real knowledge graph.</strong><br/>
  Your LLM remembers facts, decisions, and context <em>across every conversation</em>.
</p>

<p align="center">
  <a href="https://pypi.org/project/waggle-mcp"><img src="https://img.shields.io/pypi/v/waggle-mcp?color=39d5cf&label=pypi" alt="PyPI"/></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+"/>
  <img src="https://img.shields.io/badge/MCP-compatible-brightgreen" alt="MCP"/>
  <img src="https://img.shields.io/badge/embeddings-local%2C%20no%20API%20key-orange" alt="Local embeddings"/>
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="MIT"/>
</p>

---

## Why waggle-mcp?

Most LLMs forget everything when the conversation ends.  
`waggle-mcp` fixes that by giving your AI a **persistent knowledge graph** it can read and write through any MCP-compatible client.

| Without waggle-mcp | With waggle-mcp |
|--------------------------|----------------------|
| "What did we decide about the DB schema?" → ❌ no idea | ✅ Recalls the decision node, when it was made, and what it contradicts |
| Context stuffed into a 200k-token prompt | Compact subgraph — only relevant nodes retrieved |
| Flat bullet-list memory | Typed edges: `relates_to`, `contradicts`, `depends_on`, `updates`… |
| One session, one agent | Multi-tenant, multi-session, multi-agent |

---

## Demo

<p align="center">
  <img src="https://raw.githubusercontent.com/Abhigyan-Shekhar/graph-memory-mcp/main/assets/demo.svg" alt="waggle-mcp init demo" width="720"/>
</p>

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

## How it works

Memory doesn't just get stored — it flows through a lifecycle:

```
You talk to your AI
        │
        ▼
  observe_conversation()          ← AI drops the turn in; facts are extracted via structured LLM (regex fallback)
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

## See it in action

Here's a concrete before/after for a developer using the AI daily:

**Session 1** — April 10
```
User:  Let's use PostgreSQL. MySQL replication has been painful.
Agent: [calls observe_conversation()]
       → stores decision node: "Chose PostgreSQL over MySQL"
       → stores reason node: "MySQL replication painful"
       → links them with depends_on edge
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

---

## Fact Extraction Schema

When the agent observes a conversation, the backend runs a Pydantic-validated LLM extraction pass (or falls back to a regex engine) to pull structured facts out of messy dialogue.

**Example Input:**
> "Let's use PostgreSQL for the generic event storage because MySQL replication is too painful to manage."

**Validated Output:**
```json
{
  "facts": [
    {
      "label": "PostgreSQL for generic events",
      "content": "Chose PostgreSQL over MySQL because MySQL replication is too painful.",
      "node_type": "decision",
      "confidence": 0.95,
      "tags": ["llm-extracted", "confidence:0.95"]
    }
  ]
}
```

*Any extraction with `confidence < 0.5` or an invalid schema is silently dropped to prevent hallucination noise.*

---

## Performance & Benchmarking

All benchmark claims in this repository should be reproducible from checked-in fixtures plus the local harness at [scripts/benchmark_extraction.py](./scripts/benchmark_extraction.py).

Current fixture inventory:

- **Extraction:** 12 checked-in dialogue cases covering simple recall, interruptions, reversals, vague statements, conflicting statements, and mixed user/assistant signal.
- **Retrieval:** an 8-node benchmark corpus with 6 queries covering paraphrase and temporal phrasing.
- **Deduplication:** 6 checked-in node pairs with both true-duplicate and false-friend cases.

Run the harness locally:

```bash
PYTHONPATH=src .venv/bin/python scripts/benchmark_extraction.py
PYTHONPATH=src .venv/bin/python scripts/benchmark_extraction.py --extraction-backend regex
PYTHONPATH=src .venv/bin/python scripts/benchmark_extraction.py --extraction-backend llm --ollama-model qwen2.5:7b --ollama-timeout-seconds 30
```

Saved verification artifacts live under [`tests/artifacts`](./tests/artifacts/).

Measured results from the saved runs on this branch:

| Run | Result |
|-----|--------|
| **MCP smoke test** | Server initialized, `store_node` succeeded, `query_graph` returned the stored node, graph stats reported `1` node / `0` edges |
| **Regex extraction** | `4/12 = 33%` |
| **LLM extraction** | `9/12 = 75%` using local Ollama `qwen2.5:7b` with `30s` request timeout |
| **Retrieval** | `5/6 = 83%` |
| **Deduplication** | `3/6 = 50%` |

Deduplication threshold sweep on the checked-in fixture set:

- `0.82` -> `3/6 = 50%`
- `0.85` -> `2/6 = 33%`
- `0.88` -> `2/6 = 33%`
- `0.90` -> `2/6 = 33%`
- `0.92` -> `2/6 = 33%`
- `0.95` -> `3/6 = 50%`
- `0.97` -> `3/6 = 50%`

What these saved runs demonstrate:

- regex extraction as a standalone baseline
- Ollama-backed extraction through the same local LLM codepath used by Waggle at runtime
- semantic retrieval over the checked-in corpus
- deduplication accuracy over the checked-in duplicate and non-duplicate pairs
- an end-to-end MCP store/query demo against the live server

The LLM benchmark does **not** silently fall back to regex. In the first saved attempt, two cases timed out at the extractor's original `15s` Ollama request limit and the run recorded an explicit backend-unavailable error instead of publishing substituted numbers. The stable saved run on this branch uses a configurable `30s` timeout.

Deduplication benchmarking uses a checked-in threshold sweep and reports the best fixture-backed threshold in the benchmark output. Product defaults remain conservative (`dedup_similarity_threshold=0.97`) until broader validation justifies changing runtime behavior.

### When Extraction Fails

*What happens when the user is too vague?*

> **User:** "Yeah, let's just do that thing we talked about."

*(Waggle LLM extraction pass runs...)*

Because the statement is entirely ambiguous, the LLM assigns a low confidence (`confidence < 0.5`). Waggle **silently drops** the extraction to protect the graph integrity. It is architecturally safer to aggressively omit noisy extraction than to pollute the memory graph with hallucinatory, unanchored nodes.

### Scaling to 10k+ Nodes

Graph datasets grow iteratively. How does Waggle survive long-term memory accumulation across months of multi-agent sessions?

1. **Local Embeddings Stay On-Device:** Waggle uses `all-MiniLM-L6-v2` locally, so semantic search does not require network calls or per-query API spend.
2. **Neo4j Remains the Scale-Up Path:** SQLite is the default local backend, but the graph model can be backed by Neo4j when deployments outgrow single-file storage.
3. **`access_count` Helps Context Ranking:** Nodes that are frequently reused rise in `prime_context`, while stale nodes naturally sink over time.

---

## Advanced Demo: Multi-Session Debugging

Memory isn't just about simple recall; it's about context evolution and reasoning across time.

**Session 1 (Monday)**
*Agent investigates an auth timeout.*
> **Agent:** Looks like the JWT tokens expire after 15 minutes, but the refresh logic has a race condition.
> *(Waggle automatically extracts: `[Node: JWT 15m expiry]`, `[Node: Refresh logic race condition]`)*

**Session 2 (Wednesday)**
*User opens a fresh window with no chat history.*
> **User:** We're seeing intermittent auth failures again.
> **Agent:** *(Retrieves prime context)* This matches the race condition we discovered on Monday in the refresh logic. Let's look at that specific code path.
> 
> *Without Waggle, the agent wastes 10 minutes re-diagnosing the entire auth stack from scratch.*

**Session 3 (Friday)**
> **User:** We fixed the refresh race condition, but it feels like users are still getting kicked out too fast.
> **Agent:** *(Queries graph)* Since we fixed the refresh issue, the problem might be the 15-minute aggressive expiry we noted on Monday. Should we extend that to 1 hour?

The agent tracks the evolving state of the system across sessions, identifies contradictions, and leverages them to skip dead-end debugging branches.

---

## Temporal queries — a solved problem most memory systems skip

Most memory systems answer "what do you know about X?" — but can't answer
*when* you learned it or how knowledge changed over time.

`waggle-mcp` understands temporal natural language natively:

| Query | What happens |
|-------|-------------|
| `query_graph("what did we decide recently")` | Filters nodes updated in the last 24–48h |
| `query_graph("what was the original plan")` | Retrieves the earliest version of relevant nodes |
| `query_graph("what changed last week")` | Returns a diff of nodes created/updated in that window |
| `graph_diff(since="48h")` | Explicit changelog: added nodes, updated nodes, new conflicts |

This is built on timestamped nodes + temporal phrase parsing — no vector-clock
complexity, but enough to reconstruct a meaningful timeline of decisions.

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

`relates_to` · `contradicts` · `depends_on` · `part_of` · `updates` · `derived_from` · `similar_to`

---

## MCP tools

> Your AI calls these directly — you don't need to use them manually.

| Tool | What it does |
|------|-------------|
| `observe_conversation` | **Drop a conversation turn in — facts extracted via structured LLM (regex fallback), stored, and linked** |
| `query_graph` | Semantic + temporal search across the graph |
| `store_node` | Manually save a fact, preference, decision, or note |
| `store_edge` | Link two nodes with a typed relationship |
| `get_related` | Traverse edges from a specific node |
| `update_node` | Update content or tags on an existing node |
| `delete_node` | Remove a node and all its edges |
| `decompose_and_store` | Break long content into atomic nodes automatically |
| `graph_diff` | See what changed in the last N hours |
| `prime_context` | Generate a compact brief for a new conversation |
| `get_topics` | Detect topic clusters via community detection |
| `get_stats` | Node/edge counts and most-connected nodes |
| `export_graph_html` | Interactive browser visualization |
| `export_graph_backup` | Portable JSON backup |
| `import_graph_backup` | Restore from a JSON backup |

---

## Installation

### Local / development (SQLite, no extra services)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
waggle-mcp init        # ← writes your client config automatically
```

Three key variables for local mode:

| Variable | What it does |
|----------|-------------|
| `WAGGLE_BACKEND=sqlite` | Local file DB, zero setup |
| `WAGGLE_TRANSPORT=stdio` | Connects to desktop MCP clients |
| `WAGGLE_DB_PATH` | Where the graph is stored (default: `memory.db`) |

### Production (Neo4j backend)

```bash
pip install -e ".[dev,neo4j]"
```

Then run the server:

```bash
WAGGLE_TRANSPORT=http \
WAGGLE_BACKEND=neo4j \
WAGGLE_DEFAULT_TENANT_ID=workspace-default \
WAGGLE_NEO4J_URI=bolt://localhost:7687 \
WAGGLE_NEO4J_USERNAME=neo4j \
WAGGLE_NEO4J_PASSWORD=change-me \
waggle-mcp
```

### Docker

```bash
docker build -t waggle-mcp:latest .

docker run --rm -p 8080:8080 \
  -e WAGGLE_TRANSPORT=http \
  -e WAGGLE_BACKEND=neo4j \
  -e WAGGLE_DEFAULT_TENANT_ID=workspace-default \
  -e WAGGLE_NEO4J_URI=bolt://host.docker.internal:7687 \
  -e WAGGLE_NEO4J_USERNAME=neo4j \
  -e WAGGLE_NEO4J_PASSWORD=change-me \
  waggle-mcp:latest
```

---

## Manual client configuration

If you prefer to edit config files directly, or `init` doesn't cover your client:

### Claude Desktop — `claude_desktop_config.json`

```json
{
  "mcpServers": {
    "waggle": {
      "command": "/path/to/.venv/bin/python",
      "args": ["-m", "waggle.server"],
      "env": {
        "PYTHONPATH": "/path/to/waggle-mcp/src",
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

### Codex — `codex_config.toml`

```toml
[mcp_servers.waggle]
command = "/path/to/.venv/bin/python"
args    = ["-m", "waggle.server"]
cwd     = "/path/to/waggle-mcp"
env     = {
  PYTHONPATH                     = "/path/to/waggle-mcp/src",
  WAGGLE_TRANSPORT         = "stdio",
  WAGGLE_BACKEND           = "sqlite",
  WAGGLE_DB_PATH           = "~/.waggle/memory.db",
  WAGGLE_DEFAULT_TENANT_ID = "local-default",
  WAGGLE_MODEL             = "all-MiniLM-L6-v2"
}
```

A pre-filled example is in [`codex_config.example.toml`](./codex_config.example.toml).

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

</details>

---

## Admin commands

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

---

## Kubernetes & observability

Full production deployment assets are in [`deploy/`](./deploy/):

| Path | What's inside |
|------|--------------|
| `deploy/kubernetes/` | Deployment, Service, Ingress (TLS), NetworkPolicy, HPA, PDB, cert-manager, ExternalSecrets — see [`deploy/kubernetes/README.md`](./deploy/kubernetes/README.md) |
| `deploy/observability/` | Prometheus scrape config, Grafana dashboard, one-command Docker Compose observability stack |

---

## Runbooks

Operational runbooks are in [`docs/runbooks/`](./docs/runbooks/):

- [API key rotation](./docs/runbooks/api-key-rotation.md) — zero-downtime create-then-revoke
- [Incident response](./docs/runbooks/incident-response.md) — Neo4j down, OOM, rate storm, auth failures
- [Backup & restore](./docs/runbooks/backup-restore.md) — manual and automated drill
- [Tenant onboarding](./docs/runbooks/onboarding.md) — new tenant checklist
- [Secret management](./docs/runbooks/secret-management.md) — External Secrets + cert-manager

---

## Testing

```bash
.venv/bin/pytest -q
```

Coverage: graph CRUD, deduplication, conflict detection, tenant isolation,
backup/import, stdio MCP, HTTP auth/health/metrics, payload limits.

```bash
# End-to-end backup/restore drill
WAGGLE_HOST=http://localhost:8080 WAGGLE_API_KEY=<key> \
  ./scripts/backup_restore_drill.sh

# Load test (p50/p95/p99 latency report)
WAGGLE_API_KEY=<key> ./scripts/load_test.sh --medium
```

---

## Architecture

```
waggle-mcp
├── Core domain    graph CRUD · dedup · local embeddings · conflict detection · export/import
├── Transport      stdio MCP (Codex/Desktop) · streamable HTTP MCP (Kubernetes)
└── Platform       config · auth · tenant isolation · rate limiting · logging · metrics
```

**Backend:**
- Local/dev → SQLite (zero config, instant start)
- Production → Neo4j (`WAGGLE_TRANSPORT=http` requires `WAGGLE_BACKEND=neo4j`)

---

## Project layout

```
waggle-mcp/
├── assets/                   ← banner + demo SVG
├── deploy/
│   ├── kubernetes/           ← full K8s manifests + guide
│   └── observability/        ← Prometheus + Grafana stack
├── docs/runbooks/            ← operational runbooks
├── scripts/
│   ├── load_test.py / .sh
│   └── backup_restore_drill.py / .sh
├── src/waggle/         ← server, graph, neo4j_graph, auth, config …
├── tests/
├── Dockerfile
├── pyproject.toml
└── README.md
```

---

## License

MIT — see [LICENSE](./LICENSE).
