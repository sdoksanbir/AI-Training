"""Run the deterministic RAG v0.1 retrieval evaluation."""

import json
from pathlib import Path

from educoach.rag import InMemoryRetriever, KnowledgeChunk


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVALUATION_PATH = PROJECT_ROOT / "evaluations" / "rag" / "retrieval_v0.1.jsonl"


def _filters(raw_filters: dict[str, str | list[str]]) -> dict[str, str | set[str]]:
    return {
        key: set(value) if isinstance(value, list) else value
        for key, value in raw_filters.items()
    }


def run() -> tuple[float, float, int, list[str]]:
    cases = [
        json.loads(line)
        for line in EVALUATION_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    expected_total = 0
    recalled_total = 0
    single_answer_total = 0
    top_one_total = 0
    forbidden_violations = 0
    failures: list[str] = []

    for case in cases:
        retriever = InMemoryRetriever([
            KnowledgeChunk(**item) for item in case["chunks"]
        ])
        results = retriever.search(
            case["query"],
            limit=3,
            filters=_filters(case.get("filters", {})),
        )
        result_ids = [item.chunk_id for item in results]
        expected_ids = case["expected_chunk_ids"]
        forbidden_ids = set(case.get("forbidden_chunk_ids", []))

        expected_total += len(expected_ids)
        recalled_total += len(set(expected_ids) & set(result_ids))
        if len(expected_ids) == 1:
            single_answer_total += 1
            if result_ids and result_ids[0] == expected_ids[0]:
                top_one_total += 1
            else:
                failures.append(
                    f"{case['case_id']}: expected top-1 {expected_ids[0]}, got {result_ids}"
                )

        missing = set(expected_ids) - set(result_ids)
        if missing:
            failures.append(
                f"{case['case_id']}: missing expected chunks {sorted(missing)}"
            )
        violations = forbidden_ids & set(result_ids)
        forbidden_violations += len(violations)
        if violations:
            failures.append(
                f"{case['case_id']}: returned forbidden chunks {sorted(violations)}"
            )

    recall_at_three = recalled_total / expected_total if expected_total else 0.0
    top_one_accuracy = (
        top_one_total / single_answer_total if single_answer_total else 0.0
    )
    return recall_at_three, top_one_accuracy, forbidden_violations, failures


if __name__ == "__main__":
    recall_at_three, top_one_accuracy, forbidden_violations, failures = run()
    print(f"Recall@3: {recall_at_three:.0%}")
    print(f"Top-1 accuracy: {top_one_accuracy:.0%}")
    print(f"Forbidden violations: {forbidden_violations}")
    for failure in failures:
        print(f"FAIL {failure}")
    passed = (
        recall_at_three == 1.0
        and top_one_accuracy == 1.0
        and forbidden_violations == 0
        and not failures
    )
    raise SystemExit(0 if passed else 1)
