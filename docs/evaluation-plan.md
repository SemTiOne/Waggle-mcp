# Implementation Plan: Dedup → Context Assembly → Corpus Hardening

> **Execute in sequence.** Each phase changes the numbers the next phase measures.
> Do not run phases in parallel.

```
Phase 1: Dedup improvement       → fixes product-blocking bug; changes graph density
Phase 2: Context assembly depth  → changes what Waggle returns per query; depends on cleaner graph
Phase 3: Corpus hardening        → re-measures everything; must run against the improved system
```

**Estimated total:** 2–3 focused weeks.

---

## Phase 1 — Dedup Improvement

**Current state:** complete as of the latest saved benchmark. The dedup fixture is now 32 balanced cases (16 true-dup, 16 false-friend), and the threshold sweep reports 32/32 with `false_positives = 0`.

**Target:** ≥90% on a 30+ pair fixture without regressing false-friend rejection (maintain fp=0).

### Step 1A — Expand the fixture set

22 pairs is enough to develop against but marginal for validation.

- Add 8–10 more pairs targeting the specific remaining failure modes:
  - Pure-paraphrase true-dups with no entity anchor ("user prefers dark mode" / "user wants dark mode UI")
  - Cross-type pairs (decision vs fact about the same topic)
  - Temporal near-duplicates ("chose PostgreSQL in April" vs "still using PostgreSQL in May" — these should **not** merge)
- **Target: 30–35 pairs minimum before declaring victory**

### Step 1B — Paraphrase detection pre-filter

The 4 remaining false-negatives are pairs where:
- No named entity exists to anchor the merge
- Cosine similarity is below threshold despite semantic equivalence

Implement a lightweight paraphrase pre-score on top of the existing Jaccard path:

```python
# Proposed scoring path for entity-less pairs
paraphrase_score = 0.6 * cosine_similarity + 0.4 * jaccard_overlap
if paraphrase_score >= ENTITY_LESS_THRESHOLD:  # tune on fixture set, start at 0.72
    return existing_node, "paraphrase_merge", paraphrase_score
```

This is distinct from the existing Jaccard-boosted path (which requires jaccard ≥ 0.35 first). The combined score catches cases where neither metric alone is strong enough.

**Tune on fixture set. Commit threshold values with the fixture results that justify them.**

### Step 1C — Measure and ship

- Run full dedup benchmark: report old accuracy vs new accuracy on the same fixture set
- If ≥90%: update product default threshold, merge to main
- If <90%: document what's still failing, decide whether to pursue bi-encoder fine-tuning

**Exit criteria:**
- [x] Dedup accuracy ≥90% on ≥30 fixture pairs
- [x] fp=0 maintained (no false-friend regressions)
- [x] Product default threshold validated with fixture-backed justification
- [x] README dedup section updated with new numbers

---

## Phase 2 — Context Assembly Depth

**Current state:** 93% Hit@k, 70% exact support on graph-routed queries in the comparative corpus. Worst case remains `cross_scenario_synthesis` — hit rate is high, but exact support stays low because loosely linked scenarios are still hard to bundle cleanly.  
Waggle now finds the right topic much more reliably in graph mode; the remaining work is improving bundle precision without losing the relational context that makes graph retrieval useful.

**Latest attempt:** failure analysis is checked in at `docs/context_assembly_failure_analysis.json`. `expand_depth` is implemented and exposed on `query_graph`, but it remains disabled in the saved comparative policy because broad expansion only moved exact support from 77% to 78% while raising mean tokens above budget. A bounded multi-intent reranker is now enabled and recovers one additional exact-support case without increasing `max_nodes`; larger gains still require stronger query decomposition/reranking, not wider 1-hop expansion.

**Target:** Improve graph-mode exact support without collapsing graph-mode Hit@k, and keep blended comparative mean tokens well below naive RAG.

### Step 2A — Diagnose the failure pattern first

Before writing a line of code, manually inspect every case where Hit@k = true but exact support = false.

For each failing query, record:
- Which node was retrieved (the "hit")
- What supporting information was missing
- Where that missing info lives in the graph (adjacent node? two hops away? different session?)
- Whether the missing info is connected by a typed edge to the retrieved node

**Deliverable:** `docs/context_assembly_failure_analysis.json` — feed this into Step 2B.

### Step 2B — 1-hop subgraph expansion

Based on the expected diagnosis (missing adjacent context), add selective expansion:

```
query_graph("database decision")
  → finds node: "Chose PostgreSQL over MySQL"
  → current:  returns just that node
  → proposed: also returns nodes connected by [depends_on, updates, contradicts, derived_from] (1 hop)
  → skip:     relates_to, similar_to (too broad — would blow up token count)
```

**Implementation:**
- Add `expand_depth` parameter to `query_graph` (default: `0` for backward compatibility)
- When `expand_depth=1`: for each retrieved node, fetch edges of types `[depends_on, updates, contradicts, derived_from]` and include connected nodes
- Deduplicate expanded results
- Cap total returned nodes at `top_k * 2`
- Current implementation exposes `expand_depth`, but benchmark policy keeps it at `0` until precision improves enough to justify the token cost.

**Hard constraint:** If expansion pushes mean tokens materially upward, the efficiency claim must be reframed honestly. The current blended benchmark is already closer to ~2.7× than ~4×, so further context expansion has to justify its token cost.

### Step 2C — Selective expansion based on query type

Not every query needs expansion. Auto-trigger expansion only when the query contains relational or temporal signals:

```python
EXPANSION_TRIGGERS = [
    "how did * affect",
    "what changed",
    "relationship between",
    "connected to",
    "depends on",
    "because of",
    "before and after",
    "why did we",
]
```

Start simple: literal substring matching. Refine later if needed.

### Step 2D — Measure and validate

- Re-run comparative benchmark with expansion enabled
- Report exact support improvement per task family
- Verify token cost stays within the "~4×" claim range
- If token cost increases significantly: report the new ratio honestly and update all tables

**Latest measurement:** on the hardened 120-query corpus, saved benchmark is `91% Hit@k`, `88% exact support`, `63.0` mean tokens. Broad expansion measured similar exact support with materially higher mean tokens on the earlier corpus, so it was not adopted as the default policy.

**Exit criteria:**
- [x] Exact support ≥85% on current hardened corpus
- [ ] Mean tokens ≤55 (preserving ≥2.5× advantage)
- [x] `cross_scenario_synthesis` exact support materially improves
- [ ] No regression on Hit@k
- [ ] Token efficiency table in README updated

---

## Phase 3 — Corpus Hardening

**Current state:** initial hardening is complete. The comparative corpus now has 32 scenarios and 120 queries across 9 task families, including `negation` and `implicit_reference`. `rag_naive` dropped to 94% Hit@k and 91% exact support, so the old "RAG gets everything" ceiling is broken. Waggle is at 91% Hit@k / 88% exact after topic-gated temporal ranking, negation-aware ranking, clause-aware multi-intent seeding, alias-expanded topic scoring, and clause-coverage selection; remaining gaps are concentrated in the last few temporal-latest and flat factual misses.

**Target:** At least 2 task families where naive RAG Hit@k drops below 90%, creating real separation between systems.

### Step 3A — New query types that break chunk boundaries

The structural weakness of chunked RAG: if the answer requires combining information from two different sessions (stored in different chunks), a single-chunk retrieval can't surface both pieces. Design queries that exploit this:

| Query type | Example | Why RAG struggles |
|---|---|---|
| **Cross-session synthesis** | "What's the relationship between the auth timeout fix and the deployment delay?" | Auth info in session 3 chunk, deploy info in session 7 — need both simultaneously |
| **Contradiction resolution** | "What's our current position on MySQL?" | Two chunks say opposite things; RAG returns both without resolving |
| **Temporal sequence** | "List the database decisions in chronological order" | Facts spread across many chunks; RAG returns them unordered |
| **Negation queries** | "What did we decide NOT to do?" | Negations semantically similar to assertions; cosine can't distinguish |
| **Implicit reference** | "That thing from the security review" | Vague query; graph edges provide disambiguation that raw chunks can't |

### Step 3B — Expand scenario count and depth

Current: 24 scenarios, ~2–3 turns each.  
**Target: 35–40 scenarios** with:
- ≥10 scenarios with 5+ turns (deeper conversation history)
- ≥8 scenarios that reference facts from other scenarios (cross-scenario dependencies)
- ≥5 scenarios with explicit contradictions or reversals
- Facts that are only inferrable by combining nodes from 2+ sessions

### Step 3C — Expand query count per family

| Task family | Current n | Target n | Priority |
|---|---|---|---|
| `factual_recall` | 18 | 18 | Sufficient — both systems ace it |
| `temporal_original` | 19 | 19 | Sufficient |
| `multi_session_change` | 11 | 15 | Add reversals and updates |
| `cross_scenario_synthesis` | 8 | 15 | **Priority** — where Waggle should win |
| `decision_delta` | 4 | 10 | Too small; raise to be statistically meaningful |
| `adversarial_paraphrase` | 4 | 10 | Too small |
| `temporal_latest` | 2 | 8 | Far too small |
| **`negation`** (new) | 0 | 6 | "What did we reject?" queries |
| **`implicit_reference`** (new) | 0 | 6 | Vague, context-dependent queries |
| **Total** | **66** | **~107** | |

### Step 3D — Validate that RAG actually drops (do this first)

After building the new corpus, **run naive RAG baseline first**, before running Waggle.

If RAG still hits ≥95% overall, the corpus isn't hard enough yet. Iterate on scenarios until RAG drops before investing time in a full comparison. This is the validation gate.

### Step 3E — Full comparison run and reporting

- Run Waggle + rag_naive on the hardened corpus
- Produce new `tests/artifacts/benchmark_current.json`
- Update all README tables; preserve old corpus as `benchmarks/fixtures/v1/` for historical comparison
- If Waggle beats RAG on Hit@k in any family: report it clearly, label it as the hardened-corpus result
- If Waggle still trails: report honestly and identify next architectural gap

**Exit criteria:**
- [x] Corpus has ≥100 queries across ≥8 task families
- [x] Naive RAG Hit@k drops below 95% overall
- [ ] At least 2 task families show meaningful Waggle advantage on Hit@k
- [x] `benchmark_current.json` regenerated
- [x] README/artifact tables updated

---

## Dependency chain

```
Phase 1 (Dedup)
  └─ cleaner graph
       └─ Phase 2 (Context Assembly)
            └─ better exact support numbers
                 └─ Phase 3 (Corpus Hardening)
                      └─ stress test on both improvements
                           └─ README update with final revised benchmarks
```

## What not to do during these phases

- **No MCP tool surface changes.** No new tools, no API changes.
- **No extraction accuracy work.** 75% LLM extraction is not the bottleneck.
- **No new features.** No new node types, no new edge types.
- **No new README claims until Phase 3 numbers are in.** The README is honest as-is.

---

## Checklist

### Phase 1 — Dedup
- [x] 1A: Expand fixture set to ≥30 pairs (add paraphrase + temporal near-dup + cross-type pairs)
- [x] 1B: Implement paraphrase pre-score for entity-less pairs; tune threshold on fixture
- [x] 1C: Run dedup benchmark; achieve ≥90%; validate product default; update README

### Phase 2 — Context Assembly
- [x] 2A: Failure analysis — inspect all Hit@k=true / exact=false cases; write analysis JSON
- [x] 2B: Implement `expand_depth=1` in `query_graph`; keep disabled by default until token tradeoff is justified
- [x] 2C: Add query-type trigger plumbing for selective expansion
- [ ] 2D: Re-run benchmark; verify exact support ≥85% and mean tokens ≤55; update README

### Phase 3 — Corpus Hardening
- [ ] 3A: Add 5 new query types (cross-session synthesis, contradiction, temporal sequence, negation, implicit reference)
- [ ] 3B: Expand to 35–40 scenarios with deeper histories and cross-scenario dependencies
- [ ] 3C: Expand per-family counts to targets in table above (total ≥107 queries)
- [ ] 3D: Run RAG baseline first; confirm it drops below 95% before running Waggle
- [ ] 3E: Full comparison run; update all tables; preserve v1 corpus
