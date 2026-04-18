<p align="center">
  <img src="https://raw.githubusercontent.com/Abhigyan-Shekhar/graph-memory-mcp/main/assets/banner.png" alt="waggle-mcp" width="720"/>
</p>

<p align="center">
  <strong>Persistent, structured memory for AI agents — up to 4× fewer tokens than chunk-based retrieval.</strong><br/>
  Your LLM remembers facts, decisions, and context <em>across every conversation</em>, backed by a real knowledge graph.
</p>

<p align="center">
  <a href="https://pypi.org/project/waggle-mcp"><img src="https://img.shields.io/pypi/v/waggle-mcp?color=39d5cf&label=pypi" alt="PyPI"/></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+"/>
  <img src="https://img.shields.io/badge/MCP-compatible-brightgreen" alt="MCP compatible"/>
  <img src="https://img.shields.io/badge/embeddings-local%2C%20no%20API%20key-orange" alt="Local embeddings"/>
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="MIT"/>
</p>

<p align="center">
  <a href="https://glama.ai/mcp/servers/Abhigyan-Shekhar/Waggle-mcp"><img src="https://glama.ai/mcp/servers/Abhigyan-Shekhar/Waggle-mcp/badges/card.svg" alt="Waggle-mcp MCP server"/></a>
  <a href="https://glama.ai/mcp/servers/Abhigyan-Shekhar/Waggle-mcp"><img src="https://glama.ai/mcp/servers/Abhigyan-Shekhar/Waggle-mcp/badges/score.svg" alt="Waggle-mcp MCP server score"/></a>
</p>

---

## Why waggle-mcp?

`waggle-mcp` is a local-first memory layer for MCP-compatible AI clients, built on a persistent knowledge graph. It gives your AI a persistent knowledge graph it can read and write through any MCP-compatible client (Claude Desktop, Cursor, Codex, Antigravity, etc.).

| Stuffed context | Structured retrieval |
|-----------------|----------------------|
| Huge prompts every session | Compact subgraph retrieved at query time |
| Session-local memory | Persistent multi-session memory |
| Flat notes and chunks | Typed nodes and edges: decisions, reasons, contradictions |
| "What changed?" requires replaying logs | Temporal queries and diffs are first-class |

Waggle yields **up to ~4× fewer tokens** than naive chunked retrieval on factual queries. Graph-traversal queries spend more tokens to include necessary reasoning context such as updates, contradictions, and dependencies.

---

## Quick start

```bash
pip install waggle-mcp
waggle-mcp init
# Restart your MCP client. Done.
```

`init` detects your MCP client, writes its config, and creates the local database directory. Default mode is local SQLite with on-device embeddings. Antigravity and manual configuration details are in [docs/reference.md](./docs/reference.md).

---

## Using It In MCP Clients

Once Waggle is installed in an MCP client, people normally do not run `waggle-mcp` commands by hand during everyday use. They talk to the agent normally, and the agent uses Waggle's MCP tools to store and retrieve memory.

### Codex

Typical pattern:
- You work in a normal Codex thread.
- Codex calls `observe_conversation`, `store_node`, `store_edge`, `query_graph`, or `prime_context` when memory is useful.
- On a later task, Codex can pull back the connected subgraph instead of relying on the current chat window alone.

Example:
- You say: `Remember that we chose PostgreSQL because MySQL replication was painful.`
- Codex stores that as structured memory.
- Days later you ask: `What did we decide about the database?`
- Codex can call `query_graph` and recover the earlier decision plus its reason.

### Claude Code

Typical pattern:
- You configure Waggle as an MCP server in Claude Code.
- Claude Code uses Waggle tools to persist decisions, preferences, architecture notes, and project state across sessions.
- `prime_context` and `export_context_bundle` are useful when starting a fresh task or handing context to another model.

### Cursor

Typical pattern:
- Cursor uses Waggle over MCP while you work in the editor.
- Facts and decisions can be saved as graph memory instead of getting lost in past chats.
- Later questions like `why did we change this?` or `what superseded this decision?` can be answered from connected nodes and edges.

### Antigravity

Typical pattern:
- Antigravity can use Waggle as its persistent memory backend through MCP.
- Conversation turns can be extracted with `observe_conversation`.
- Linked context can be exported with `export_context_bundle` or edited through the Markdown vault workflow.

### What The Agent Actually Uses

Common memory tools:
- `observe_conversation`: extract memory from a completed turn
- `store_node`: save one fact, note, preference, or decision directly
- `store_edge`: connect two nodes explicitly
- `query_graph`: retrieve relevant graph context
- `prime_context`: build a short briefing for a fresh session
- `list_conflicts` / `resolve_conflict`: inspect and resolve contradictions
- `export_context_bundle`: hand memory to another model as Markdown or JSON

Important:
- `store_node` alone does not create edges.
- Connected context comes from `store_edge`, `observe_conversation`, `decompose_and_store`, and automatic contradiction/update detection.
- The graph-aware retrieval tools are what bring that connected context back to the model.

For a built-in CLI explanation of the feature surface, run:

```bash
waggle-mcp features
```

---

## See it in action

**Session 1** — April 10
```text
User:  Let's use PostgreSQL. MySQL replication has been painful.
Agent: [calls observe_conversation()]
       → stores decision node: "Chose PostgreSQL over MySQL"
       → stores reason node:   "MySQL replication painful"
       → links them with a depends_on edge
```

**Session 2** — April 12 (fresh context window, no history)
```text
User:  What did we decide about the database?
Agent: [calls query_graph("database decision")]
       → retrieves the decision node + linked reason from April 10

       "You decided on PostgreSQL on April 10. The reason recorded was
        that MySQL replication had been painful."
```

**Session 3** — April 14
```text
User:  Actually, let's reconsider — the team is more familiar with MySQL.
Agent: [calls store_node() + store_edge(new_node → old_node, "contradicts")]
       → both positions are preserved, and the contradiction is explicit
```

---

## Key Features

- **Automatic Extraction**: `observe_conversation` ingests facts into the graph without manual schema work.
- **Portable Context**: `export_context_bundle` generates Markdown/JSON context packs for another AI.
- **Vault Round-trip**: `export_markdown_vault` / `import_markdown_vault` for Obsidian-style node editing.
- **Conflict Resolution**: `list_conflicts` / `resolve_conflict` to manage contradictions without losing history.
- **Deterministic Fallback**: Stable SHA-256 hashing for reliable, reproducible offline operation when transformer models are unavailable.

---

## Benchmarks & Verification

Waggle performance is verified against checked-in fixtures and automated regression tests.

### Project Fixtures
| Area | Corpus | Result |
|------|--------|--------|
| Extraction | 25-case deterministic fixture | `100.0%` |
| Retrieval | 18-query retrieval fixture | `83.3% Hit@k` |
| Query stress | 40 adversarial retrieval-only cases | `97.5% Hit@k`, `97.5% exact support` |
| Deduplication | 22 cases (semi-semantic) | `77.3% (17/22)`, zero false merges |
| Automated tests | Infrastructure & logic | `91 passed` |

### External Benchmarks
| Benchmark | Coverage | Metric | Status |
|-----------|----------|--------|--------|
| **LongMemEval** | 500 questions | `97.4% R@5` | Verified (Held-out split: 81.6% deterministic) |

- **Deduplication**: Zero false-positive merges across the threshold sweep. Accuracy limited by conservative similarity bounds.
- **Comparative benchmark note**: The comparative Waggle-vs-RAG corpus is still evolving. For current per-family/token numbers, use the checked-in artifact index in [tests/artifacts/README.md](./tests/artifacts/README.md) rather than this top-level summary.

Detailed benchmark artifacts and the new **[Benchmark Methodology](./docs/benchmark-methodology.md)** guide provide full traceability.

---

## Reference & Docs

Detailed reference material lives in external documentation:

- **[docs/reference.md](./docs/reference.md)**: Environment variables, admin commands, Docker setup, and full tool surface.
- **[deploy/kubernetes/README.md](./deploy/kubernetes/README.md)**: Production deployment.
- **[docs/runbooks/](./docs/runbooks/)**: Operations and troubleshooting.
- **[tests/artifacts/README.md](./tests/artifacts/README.md)**: Benchmark artifacts and traceability.

---

## License

MIT — see [LICENSE](./LICENSE).
