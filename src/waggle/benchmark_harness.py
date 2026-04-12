from __future__ import annotations

import argparse
import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from waggle.embeddings import EmbeddingModel
from waggle.extractor import EXTRACT_MODEL, OLLAMA_TIMEOUT_SECONDS, OLLAMA_URL, extract_with_llm
from waggle.graph import MemoryGraph
from waggle.intelligence import extract_conversation_candidates
from waggle.models import NodeType

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURES_DIR = ROOT / "benchmarks" / "fixtures"
DEFAULT_DEDUP_THRESHOLDS = [0.82, 0.85, 0.88, 0.9, 0.92, 0.95, 0.97]


class BenchmarkRuntimeError(RuntimeError):
    """Raised when a requested benchmark cannot be executed honestly."""


@dataclass
class MetricSummary:
    metric: str
    backend: str
    passed: int
    total: int
    accuracy: float
    case_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkReport:
    fixtures: dict[str, Any]
    metrics: list[MetricSummary]
    errors: list[str] = field(default_factory=list)
    threshold_sweep: list[MetricSummary] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fixtures": self.fixtures,
            "metrics": [asdict(metric) for metric in self.metrics],
            "errors": list(self.errors),
            "threshold_sweep": [asdict(metric) for metric in self.threshold_sweep],
        }


def load_benchmark_fixtures(fixtures_dir: Path | str = DEFAULT_FIXTURES_DIR) -> dict[str, Any]:
    base = Path(fixtures_dir)
    extraction_cases = json.loads((base / "extraction_cases.json").read_text(encoding="utf-8"))
    retrieval_cases = json.loads((base / "retrieval_cases.json").read_text(encoding="utf-8"))
    dedup_cases = json.loads((base / "dedup_cases.json").read_text(encoding="utf-8"))
    return {
        "base_dir": str(base),
        "extraction_cases": extraction_cases,
        "retrieval_cases": retrieval_cases,
        "dedup_cases": dedup_cases,
    }


def _embedding_benchmark_error(exc: Exception, embedding_model: Any) -> BenchmarkRuntimeError:
    model_name = getattr(embedding_model, "model_name", "all-MiniLM-L6-v2")
    return BenchmarkRuntimeError(
        "Embedding-backed benchmarks require a locally available sentence-transformer model "
        f"('{model_name}'). Pre-cache the model before running retrieval/dedup benchmarks. "
        f"Original error: {exc}"
    )


def _graph(
    embedding_model: Any,
    *,
    dedup_similarity_threshold: float = 0.97,
    dedup_same_label_threshold: float = 0.9,
) -> MemoryGraph:
    tmpdir = tempfile.TemporaryDirectory()
    graph = MemoryGraph(
        Path(tmpdir.name) / "benchmark.db",
        embedding_model,
        dedup_similarity_threshold=dedup_similarity_threshold,
        dedup_same_label_threshold=dedup_same_label_threshold,
    )
    setattr(graph, "_benchmark_tmpdir", tmpdir)
    return graph


def _normalize_node_type(value: Any) -> str:
    if isinstance(value, NodeType):
        return value.value
    return str(value)


def _score_extraction_case(case: dict[str, Any], found_types: set[str]) -> bool:
    expected_types = set(case.get("expected_node_types", []))
    min_type_matches = int(case.get("min_type_matches", len(expected_types)))
    forbidden_types = set(case.get("forbidden_node_types", []))

    if expected_types:
        if len(found_types & expected_types) < min_type_matches:
            return False
    elif found_types:
        return False

    return not bool(found_types & forbidden_types)


def run_extraction_benchmark(
    cases: list[dict[str, Any]],
    *,
    backend: Literal["regex", "llm"],
    model: str = EXTRACT_MODEL,
    ollama_url: str = OLLAMA_URL,
    timeout_seconds: float = OLLAMA_TIMEOUT_SECONDS,
) -> MetricSummary:
    passed = 0
    for case in cases:
        if backend == "regex":
            candidates = extract_conversation_candidates(
                user_message=case["user_message"],
                assistant_response=case["assistant_response"],
            )
        else:
            candidates = extract_with_llm(
                case["user_message"],
                case["assistant_response"],
                model=model,
                ollama_url=ollama_url,
                timeout_seconds=timeout_seconds,
            )
            if candidates is None:
                raise BenchmarkRuntimeError(
                    f"LLM extraction backend unavailable at {ollama_url} using model '{model}' "
                    f"with timeout {timeout_seconds}s."
                )

        found_types = {_normalize_node_type(candidate["node_type"]) for candidate in candidates}
        if _score_extraction_case(case, found_types):
            passed += 1

    total = len(cases)
    return MetricSummary(
        metric="extraction",
        backend=backend,
        passed=passed,
        total=total,
        accuracy=passed / total if total else 0.0,
        case_count=total,
        metadata={
            "model": model if backend == "llm" else None,
            "ollama_url": ollama_url if backend == "llm" else None,
            "timeout_seconds": timeout_seconds if backend == "llm" else None,
        },
    )


def run_retrieval_benchmark(
    retrieval_fixtures: dict[str, Any],
    *,
    embedding_model: Any,
) -> MetricSummary:
    try:
        graph = _graph(embedding_model)
        for node in retrieval_fixtures["nodes"]:
            graph.add_node(
                label=node["label"],
                content=node["content"],
                node_type=NodeType(node["node_type"]),
                tags=["benchmark"],
            )

        passed = 0
        queries = retrieval_fixtures["queries"]
        for case in queries:
            result = graph.query(query=case["query"], max_nodes=5, max_depth=0)
            labels = [node.label for node in result.nodes]
            if any(case["expected_label_contains"].lower() in label.lower() for label in labels):
                passed += 1
    except Exception as exc:
        raise _embedding_benchmark_error(exc, embedding_model) from exc

    total = len(queries)
    return MetricSummary(
        metric="retrieval",
        backend="semantic-query",
        passed=passed,
        total=total,
        accuracy=passed / total if total else 0.0,
        case_count=total,
        metadata={"corpus_nodes": len(retrieval_fixtures["nodes"]), "top_k": 5},
    )


def run_dedup_benchmark(
    cases: list[dict[str, Any]],
    *,
    embedding_model: Any,
    dedup_threshold: float,
) -> MetricSummary:
    try:
        passed = 0
        true_positives = 0
        true_negatives = 0
        false_positives = 0
        false_negatives = 0

        for case in cases:
            graph = _graph(
                embedding_model,
                dedup_similarity_threshold=dedup_threshold,
                dedup_same_label_threshold=dedup_threshold,
            )
            first = case["first"]
            second = case["second"]
            node_type = NodeType(case["node_type"])
            graph.add_node(label=first["label"], content=first["content"], node_type=node_type)
            second_result = graph.add_node(label=second["label"], content=second["content"], node_type=node_type)
            did_dedup = not second_result.created
            expected = bool(case["should_dedup"])

            if did_dedup == expected:
                passed += 1
                if expected:
                    true_positives += 1
                else:
                    true_negatives += 1
            elif expected:
                false_negatives += 1
            else:
                false_positives += 1
    except Exception as exc:
        raise _embedding_benchmark_error(exc, embedding_model) from exc

    total = len(cases)
    return MetricSummary(
        metric="deduplication",
        backend="semantic-dedup",
        passed=passed,
        total=total,
        accuracy=passed / total if total else 0.0,
        case_count=total,
        metadata={
            "threshold": dedup_threshold,
            "positive_cases": sum(1 for case in cases if case["should_dedup"]),
            "negative_cases": sum(1 for case in cases if not case["should_dedup"]),
            "true_positives": true_positives,
            "true_negatives": true_negatives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
        },
    )


def choose_best_dedup_threshold(
    cases: list[dict[str, Any]],
    *,
    embedding_model: Any,
    thresholds: list[float] | None = None,
) -> tuple[MetricSummary, list[MetricSummary]]:
    candidates = thresholds or DEFAULT_DEDUP_THRESHOLDS
    sweep = [
        run_dedup_benchmark(cases, embedding_model=embedding_model, dedup_threshold=threshold)
        for threshold in candidates
    ]
    best = max(
        sweep,
        key=lambda summary: (
            summary.accuracy,
            summary.metadata["true_negatives"],
            summary.metadata["true_positives"],
            summary.metadata["threshold"],
        ),
    )
    return best, sweep


def run_benchmarks(
    *,
    extraction_backend: Literal["regex", "llm", "both"] = "both",
    model: str = EXTRACT_MODEL,
    ollama_url: str = OLLAMA_URL,
    ollama_timeout_seconds: float = OLLAMA_TIMEOUT_SECONDS,
    fixtures_dir: Path | str = DEFAULT_FIXTURES_DIR,
    embedding_model: Any | None = None,
    dedup_threshold: float | None = None,
) -> BenchmarkReport:
    fixtures = load_benchmark_fixtures(fixtures_dir)
    model_instance = embedding_model or EmbeddingModel()
    report = BenchmarkReport(
        fixtures={
            "directory": fixtures["base_dir"],
            "extraction_cases": len(fixtures["extraction_cases"]),
            "retrieval_nodes": len(fixtures["retrieval_cases"]["nodes"]),
            "retrieval_queries": len(fixtures["retrieval_cases"]["queries"]),
            "dedup_cases": len(fixtures["dedup_cases"]),
        },
        metrics=[],
    )

    if extraction_backend in ("regex", "both"):
        report.metrics.append(
            run_extraction_benchmark(fixtures["extraction_cases"], backend="regex")
        )

    if extraction_backend in ("llm", "both"):
        try:
            report.metrics.append(
                run_extraction_benchmark(
                    fixtures["extraction_cases"],
                    backend="llm",
                    model=model,
                    ollama_url=ollama_url,
                    timeout_seconds=ollama_timeout_seconds,
                )
            )
        except BenchmarkRuntimeError as exc:
            report.errors.append(str(exc))

    embedding_ready = True

    try:
        report.metrics.append(
            run_retrieval_benchmark(fixtures["retrieval_cases"], embedding_model=model_instance)
        )
    except BenchmarkRuntimeError as exc:
        report.errors.append(str(exc))
        embedding_ready = False

    if embedding_ready:
        try:
            if dedup_threshold is None:
                dedup_result, sweep = choose_best_dedup_threshold(
                    fixtures["dedup_cases"],
                    embedding_model=model_instance,
                )
                report.threshold_sweep.extend(sweep)
            else:
                dedup_result = run_dedup_benchmark(
                    fixtures["dedup_cases"],
                    embedding_model=model_instance,
                    dedup_threshold=dedup_threshold,
                )
            report.metrics.append(dedup_result)
        except BenchmarkRuntimeError as exc:
            report.errors.append(str(exc))
    return report


def _format_metric(metric: MetricSummary) -> str:
    extras = []
    if metric.metric == "extraction":
        extras.append(f"backend={metric.backend}")
        if metric.metadata.get("model"):
            extras.append(f"model={metric.metadata['model']}")
        if metric.metadata.get("timeout_seconds") is not None:
            extras.append(f"timeout={metric.metadata['timeout_seconds']}s")
    elif metric.metric == "retrieval":
        extras.append(f"backend={metric.backend}")
        extras.append(f"corpus_nodes={metric.metadata['corpus_nodes']}")
    elif metric.metric == "deduplication":
        extras.append(f"backend={metric.backend}")
        extras.append(f"threshold={metric.metadata['threshold']:.2f}")
        extras.append(
            f"positives={metric.metadata['positive_cases']}, negatives={metric.metadata['negative_cases']}"
        )
    extras.append(f"cases={metric.case_count}")
    return (
        f"{metric.metric:<14} {metric.passed}/{metric.total} = {metric.accuracy:.0%} "
        f"({' | '.join(extras)})"
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reproducible local benchmark harness for waggle-mcp.")
    parser.add_argument(
        "--extraction-backend",
        choices=["regex", "llm", "both"],
        default=os.getenv("WAGGLE_BENCHMARK_EXTRACTION_BACKEND", "both"),
        help="Which extraction benchmark(s) to run.",
    )
    parser.add_argument(
        "--ollama-model",
        default=os.getenv("WAGGLE_EXTRACT_MODEL", EXTRACT_MODEL),
        help="Ollama model used for the LLM extraction benchmark.",
    )
    parser.add_argument(
        "--ollama-url",
        default=os.getenv("WAGGLE_OLLAMA_URL", OLLAMA_URL),
        help="Base URL for the local Ollama instance used in the LLM extraction benchmark.",
    )
    parser.add_argument(
        "--ollama-timeout-seconds",
        type=float,
        default=float(os.getenv("WAGGLE_OLLAMA_TIMEOUT_SECONDS", str(OLLAMA_TIMEOUT_SECONDS))),
        help="Timeout for each Ollama extraction request.",
    )
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=DEFAULT_FIXTURES_DIR,
        help="Directory containing checked-in benchmark fixture JSON files.",
    )
    parser.add_argument(
        "--dedup-threshold",
        type=float,
        default=None,
        help="Optional fixed dedup threshold. If omitted, the harness sweeps checked-in thresholds and picks the best score.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON output path. No file is written unless this flag is provided.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    report = run_benchmarks(
        extraction_backend=args.extraction_backend,
        model=args.ollama_model,
        ollama_url=args.ollama_url,
        ollama_timeout_seconds=args.ollama_timeout_seconds,
        fixtures_dir=args.fixtures_dir,
        dedup_threshold=args.dedup_threshold,
    )

    print("=" * 72)
    print("waggle-mcp benchmark harness")
    print("=" * 72)
    print(
        f"fixtures: extraction={report.fixtures['extraction_cases']} "
        f"retrieval_nodes={report.fixtures['retrieval_nodes']} "
        f"retrieval_queries={report.fixtures['retrieval_queries']} "
        f"dedup_cases={report.fixtures['dedup_cases']}"
    )
    for metric in report.metrics:
        print(_format_metric(metric))

    if report.threshold_sweep:
        print("dedup threshold sweep:")
        for metric in report.threshold_sweep:
            print(f"  {_format_metric(metric)}")

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        print(f"wrote JSON report to {args.output}")

    if report.errors:
        for error in report.errors:
            print(f"ERROR: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
