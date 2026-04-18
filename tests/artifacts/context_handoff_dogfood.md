# Waggle Context Bundle

- Tenant: `local-default`
- Project: `MCP`
- Mode: `query`
- Query: `What changed in extraction, what still lags in evaluation, and what should the next AI work on?`
- Generated at: `2026-04-18T04:57:45.019764+00:00`

## How To Use

Use this as authoritative imported context. Prefer the summary, decisions, contradictions, timeline, and relationship map before consulting the appendix for raw node details.

## Memory Summary

Key context: The comparative benchmark still measures 88% Hit@k and 79% exact support for Waggle on 27 scenarios and 66 queries, despite the extraction improvements.; The deterministic extraction corpus was expanded from 18 to 25 cases and now covers favorite-language phrasing, multi-clause turns, hedged statements, conditio…. Decisions: Hedged or conditional turns such as "I think we should probably go with Redis" are stored as note nodes instead of hard… Supported by Avoid premature commitment; Negated statements such as "We are not using MongoDB anymore" are stored as decision nodes with negated tags so the gra… Supported by Preserve user polarity. Open items: Context handoff dogfood; Query bundle summary improvement.

## Key Facts By Node Type

### Decision
- "Hedged statements policy" (created 2026-04-18, updated 2026-04-18): Hedged or conditional turns such as "I think we should probably go with Redis" are stored as note nodes instead of hard decisions.
- "Negated tool choice policy" (created 2026-04-18, updated 2026-04-18): Negated statements such as "We are not using MongoDB anymore" are stored as decision nodes with negated tags so the graph preserves polarity.

### Fact
- "Current comparative gap" (created 2026-04-18, updated 2026-04-18): The comparative benchmark still measures 88% Hit@k and 79% exact support for Waggle on 27 scenarios and 66 queries, despite the extraction improvements.
- "Extraction corpus expansion" (created 2026-04-18, updated 2026-04-18): The deterministic extraction corpus was expanded from 18 to 25 cases and now covers favorite-language phrasing, multi-clause turns, hedged statements, conditional choices, and negated tool decisions.
- "Avoid premature commitment" (created 2026-04-18, updated 2026-04-18): Tentative language should not be promoted into durable decision memory until it becomes explicit.
- "Preserve user polarity" (created 2026-04-18, updated 2026-04-18): Missing negation would store the opposite of what the user said and silently corrupt the graph.

### Note
- "Context handoff dogfood" (created 2026-04-18, updated 2026-04-18): Context handoff was tested by exporting a bundle from the Waggle project and checking whether another model could continue work without replaying the whole thread.
- "Query bundle summary improvement" (created 2026-04-18, updated 2026-04-18): Query-mode export now synthesizes selected nodes into a useful summary instead of emitting a generic node-and-edge count.
- "LongMemEval methodology note" (created 2026-04-18, updated 2026-04-18): A methodology note explains graph_raw versus graph_hybrid, the cold-versus-warm prepared-session cache, and how the saved artifacts were produced.

## Decisions With Reasons

- "Hedged statements policy"
  - support: Avoid premature commitment (depends_on)
- "Negated tool choice policy"
  - support: Preserve user polarity (depends_on)

## Contradictions And Updates

- No contradiction or update edges in this bundle.

## Timeline Of Recent Changes

- [edge_relates_to] `2026-04-18T04:57:45.009523+00:00` LongMemEval methodology note -> Current comparative gap — relates_to
- [edge_depends_on] `2026-04-18T04:57:45.009093+00:00` Context handoff dogfood -> Query bundle summary improvement — depends_on
- [edge_relates_to] `2026-04-18T04:57:45.008573+00:00` Extraction corpus expansion -> Current comparative gap — relates_to
- [edge_depends_on] `2026-04-18T04:57:45.008095+00:00` Negated tool choice policy -> Preserve user polarity — depends_on
- [edge_depends_on] `2026-04-18T04:57:45.007437+00:00` Hedged statements policy -> Avoid premature commitment — depends_on
- [node_updated] `2026-04-18T04:57:45.001205+00:00` Query bundle summary improvement — Query-mode export now synthesizes selected nodes into a useful summary instead of emitting a generic node-and-edge count.
- [node_updated] `2026-04-18T04:57:44.994101+00:00` Context handoff dogfood — Context handoff was tested by exporting a bundle from the Waggle project and checking whether another model could continue work without replaying the whole thread.
- [node_updated] `2026-04-18T04:57:44.988089+00:00` LongMemEval methodology note — A methodology note explains graph_raw versus graph_hybrid, the cold-versus-warm prepared-session cache, and how the saved artifacts were produced.
- [node_updated] `2026-04-18T04:57:44.982163+00:00` Preserve user polarity — Missing negation would store the opposite of what the user said and silently corrupt the graph.
- [node_updated] `2026-04-18T04:57:44.973644+00:00` Negated tool choice policy — Negated statements such as "We are not using MongoDB anymore" are stored as decision nodes with negated tags so the graph preserves polarity.
- [node_updated] `2026-04-18T04:57:44.967185+00:00` Avoid premature commitment — Tentative language should not be promoted into durable decision memory until it becomes explicit.
- [node_updated] `2026-04-18T04:57:44.960594+00:00` Hedged statements policy — Hedged or conditional turns such as "I think we should probably go with Redis" are stored as note nodes instead of hard decisions.
- [node_updated] `2026-04-18T04:57:44.948048+00:00` Current comparative gap — The comparative benchmark still measures 88% Hit@k and 79% exact support for Waggle on 27 scenarios and 66 queries, despite the extraction improvements.
- [node_created] `2026-04-18T04:57:41.917355+00:00` Extraction corpus expansion — The deterministic extraction corpus was expanded from 18 to 25 cases and now covers favorite-language phrasing, multi-clause turns, hedged statements, conditional choices, and negated tool decisions.

## Relationship Map

- "Hedged statements policy" --[depends_on, weight=1.00]--> "Avoid premature commitment"
- "Negated tool choice policy" --[depends_on, weight=1.00]--> "Preserve user polarity"
- "Extraction corpus expansion" --[relates_to, weight=1.00]--> "Current comparative gap"
- "Context handoff dogfood" --[depends_on, weight=1.00]--> "Query bundle summary improvement"
- "LongMemEval methodology note" --[relates_to, weight=1.00]--> "Current comparative gap"

## Replay Evidence

- No replay evidence included in this bundle.

## Full Node Appendix

- id: `bc529adc-301f-4fdf-92f7-906fe1297d2e`
  - type: `fact`
  - project: MCP
  - label: Current comparative gap
  - content: The comparative benchmark still measures 88% Hit@k and 79% exact support for Waggle on 27 scenarios and 66 queries, despite the extraction improvements.
  - tags: evaluation, comparative
  - created_at: 2026-04-18T04:57:44.948046+00:00
  - updated_at: 2026-04-18T04:57:44.948048+00:00
- id: `ad0eeb71-97c0-48dc-9a87-7de6b652dcae`
  - type: `decision`
  - project: MCP
  - label: Hedged statements policy
  - content: Hedged or conditional turns such as "I think we should probably go with Redis" are stored as note nodes instead of hard decisions.
  - tags: extraction, policy
  - created_at: 2026-04-18T04:57:44.960592+00:00
  - updated_at: 2026-04-18T04:57:44.960594+00:00
- id: `e11ea6af-2178-4695-83b7-88cd11037e78`
  - type: `fact`
  - project: MCP
  - label: Extraction corpus expansion
  - content: The deterministic extraction corpus was expanded from 18 to 25 cases and now covers favorite-language phrasing, multi-clause turns, hedged statements, conditional choices, and negated tool decisions.
  - tags: evaluation, extraction
  - created_at: 2026-04-18T04:57:41.917355+00:00
  - updated_at: 2026-04-18T04:57:41.917355+00:00
- id: `63771b2a-3a13-47e5-ae35-f639829a0b08`
  - type: `note`
  - project: MCP
  - label: Context handoff dogfood
  - content: Context handoff was tested by exporting a bundle from the Waggle project and checking whether another model could continue work without replaying the whole thread.
  - tags: handoff, next-step
  - created_at: 2026-04-18T04:57:44.994100+00:00
  - updated_at: 2026-04-18T04:57:44.994101+00:00
- id: `c9c5174c-62e2-47fe-88e7-5f194b0c9112`
  - type: `fact`
  - project: MCP
  - label: Avoid premature commitment
  - content: Tentative language should not be promoted into durable decision memory until it becomes explicit.
  - tags: extraction, rationale
  - created_at: 2026-04-18T04:57:44.967184+00:00
  - updated_at: 2026-04-18T04:57:44.967185+00:00
- id: `37d6caaa-d1b4-4db3-8169-d2c212d5a0c3`
  - type: `decision`
  - project: MCP
  - label: Negated tool choice policy
  - content: Negated statements such as "We are not using MongoDB anymore" are stored as decision nodes with negated tags so the graph preserves polarity.
  - tags: extraction, policy
  - created_at: 2026-04-18T04:57:44.973643+00:00
  - updated_at: 2026-04-18T04:57:44.973644+00:00
- id: `aa93be78-5bef-4018-ac4c-42f49a34e444`
  - type: `note`
  - project: MCP
  - label: Query bundle summary improvement
  - content: Query-mode export now synthesizes selected nodes into a useful summary instead of emitting a generic node-and-edge count.
  - tags: handoff, ux
  - created_at: 2026-04-18T04:57:45.001204+00:00
  - updated_at: 2026-04-18T04:57:45.001205+00:00
- id: `b3f06311-a33e-45ac-ae94-f7eaf8ac756a`
  - type: `fact`
  - project: MCP
  - label: Preserve user polarity
  - content: Missing negation would store the opposite of what the user said and silently corrupt the graph.
  - tags: extraction, rationale
  - created_at: 2026-04-18T04:57:44.982161+00:00
  - updated_at: 2026-04-18T04:57:44.982163+00:00
- id: `62747327-1ab1-4f01-8e36-523e20417466`
  - type: `note`
  - project: MCP
  - label: LongMemEval methodology note
  - content: A methodology note explains graph_raw versus graph_hybrid, the cold-versus-warm prepared-session cache, and how the saved artifacts were produced.
  - tags: docs, longmemeval, next-step
  - created_at: 2026-04-18T04:57:44.988088+00:00
  - updated_at: 2026-04-18T04:57:44.988089+00:00
