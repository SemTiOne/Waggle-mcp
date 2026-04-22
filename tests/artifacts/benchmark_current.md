# Waggle Comparative Evaluation

- Scenarios: 32
- Queries: 120
- Task families: adversarial_paraphrase, cross_scenario_synthesis, decision_delta, factual_recall, implicit_reference, multi_session_change, negation, temporal_latest, temporal_original

| System | Hit@k | Exact support | Mean tokens | Median tokens | p95 tokens |
|--------|-------|---------------|-------------|---------------|------------|
| waggle | 91% | 88% | 63.0 | 49.0 | 121.0 |
| rag_naive | 94% | 91% | 161.8 | 159.0 | 184.1 |
| rag_tuned | 95% | 93% | 259.6 | 259.0 | 289.2 |

## Waggle Query Policy

- `flat`: max_depth=0; expand_depth=0; families=factual_recall, temporal_latest, temporal_original
- `graph`: max_depth=1,2; expand_depth=0; families=adversarial_paraphrase, cross_scenario_synthesis, decision_delta, multi_session_change

## Waggle Mode Breakdown

| Mode | Cases | Max depth | Hit@k | Exact support |
|------|-------|-----------|-------|---------------|
| flat | 78 | 0 | 87% | 87% |
| graph | 42 | 1, 2 | 98% | 88% |

## Failure Protocol

- If Waggle token reduction is under 15 percent, inspect whether graph serialization or context assembly is offsetting compression gains.
- If the tuned baseline matches Waggle on retrieval quality, frame the result as efficiency and structure first rather than retrieval superiority.
- If temporal queries do not separate systems, audit whether the corpus actually requires temporal reasoning before expanding claims.
- If multi-session change queries are inconclusive, expand that slice before broadening the whole pilot corpus.

## Query Stress Eval

- Cases: 40
- Families: adversarial_paraphrase, temporal_latest

| System | Hit@k | Exact support | Mean tokens |
|--------|-------|---------------|-------------|
| graph_raw | 98% | 98% | 39.7 |
| graph_hybrid | 100% | 100% | 74.3 |
