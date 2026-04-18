# Context Handoff Dogfood

This note records a real handoff test using Waggle's current project state rather than a toy one-node example.

## Goal

Test whether `export_context_bundle` produces enough structure for a receiving model to continue work on Waggle without replaying the full thread.

The handoff query was:

`What changed in extraction, what still lags in evaluation, and what should the next AI work on?`

Generated artifacts:
- [tests/artifacts/context_handoff_dogfood.md](../tests/artifacts/context_handoff_dogfood.md)
- [tests/artifacts/context_handoff_dogfood.json](../tests/artifacts/context_handoff_dogfood.json)

## Setup

The exported bundle was built from current Waggle project facts, including:
- extraction corpus expansion from `18` to `25` cases
- current comparative benchmark gap at `88% Hit@k / 79% exact`
- the new policy for hedged or conditional turns
- the new policy for negated tool choices
- open work on the LongMemEval methodology note and handoff verification

The bundle was exported in `query` mode for an `llm` audience with edges and timestamps enabled.

## Current Result

After the query-summary and conflict-heuristic fixes, the receiving model can recover the main project state without reading the appendix:
- what changed in extraction
- what evaluation number still lags
- which policy decisions were made
- which open tasks were still pending

The strongest sections were:
- `Key Facts By Node Type`
- `Decisions With Reasons`
- `Relationship Map`
- `Timeline Of Recent Changes`
- the top-level `Memory Summary`

Those sections now carry enough continuation context for a second model to resume work without replaying the original thread.

## Fixes Confirmed

Two user-facing problems from the first dogfood run are now fixed.

`1.` Query-mode summary is now synthesized from the selected nodes and edges.
It no longer falls back to a generic sentence of the form:
`Query context for '...' with N nodes and M edges.`

`2.` Conflict heuristics no longer create a false contradiction edge for meta-policy nodes that mention example technologies.
The current exported bundle shows:
- `No contradiction or update edges in this bundle.`

## Practical Takeaway

`export_context_bundle` is now a credible handoff mechanism for this kind of project snapshot.

In practice:
- the bundle is good enough for continuation
- the summary is now contentful enough to orient a receiving model
- conflict detection is less likely to erode trust on policy/meta text

## Recommended Follow-Up

- Tighten summary formatting so synthesized summaries are shorter and less repetitive.
- Add a handoff evaluation fixture that checks whether the exported bundle answers 3 to 5 continuation questions correctly.
- Keep an adversarial conflict fixture for policy/meta nodes that mention concrete technologies but should not contradict each other.
