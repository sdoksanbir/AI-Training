import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

from transformers import AutoTokenizer


ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "BASE": ROOT
    / "evaluations"
    / "holdout"
    / "qwen3_4b_hf_training_system_v0.2.jsonl",

    "V02": ROOT
    / "evaluations"
    / "post_training"
    / "educoach_v0.2_training_system_results.jsonl",

    "V02_REP105": ROOT
    / "evaluations"
    / "post_training"
    / "educoach_v0.2_reppen105_results.jsonl",
}

REPORT_JSON = (
    ROOT
    / "evaluations"
    / "reports"
    / "behavior_metrics_v01.json"
)

REPORT_TXT = (
    ROOT
    / "evaluations"
    / "reports"
    / "behavior_metrics_v01.txt"
)

MODEL_NAME = "Qwen/Qwen3-4B"


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def words(text: str) -> list[str]:
    return re.findall(
        r"[0-9a-zA-ZçğıöşüÇĞİÖŞÜ]+",
        normalize_text(text),
    )


def sentence_similarity(text: str) -> float:
    normalized = normalize_text(text)

    sentences = [
        s.strip()
        for s in re.split(r"[.!?]+", normalized)
        if s.strip()
    ]

    if len(sentences) < 2:
        return 0.0

    maximum = 0.0

    for i, first in enumerate(sentences):
        for second in sentences[i + 1 :]:
            ratio = SequenceMatcher(
                None,
                first,
                second,
            ).ratio()

            maximum = max(maximum, ratio)

    return maximum


def repeated_ngram_stats(text: str) -> dict:
    token_words = words(text)

    best = {
        "ngram_size": 0,
        "coverage": 0.0,
        "max_count": 0,
        "repeated_types": 0,
        "example": "",
    }

    if len(token_words) < 5:
        return best

    for n in range(5, 9):
        if len(token_words) < n:
            continue

        grams = [
            tuple(token_words[i : i + n])
            for i in range(len(token_words) - n + 1)
        ]

        counts = Counter(grams)

        repeated = {
            gram: count
            for gram, count in counts.items()
            if count >= 2
        }

        if not repeated:
            continue

        covered_positions = set()

        for i, gram in enumerate(grams):
            if gram in repeated:
                covered_positions.update(
                    range(i, min(i + n, len(token_words)))
                )

        coverage = (
            len(covered_positions) / len(token_words)
            if token_words
            else 0.0
        )

        max_gram, max_count = max(
            repeated.items(),
            key=lambda item: item[1],
        )

        candidate = {
            "ngram_size": n,
            "coverage": coverage,
            "max_count": max_count,
            "repeated_types": len(repeated),
            "example": " ".join(max_gram),
        }

        if (
            candidate["coverage"] > best["coverage"]
            or (
                candidate["coverage"] == best["coverage"]
                and candidate["max_count"] > best["max_count"]
            )
        ):
            best = candidate

    return best


def user_echo_similarity(user: str, assistant: str) -> float:
    user_words = words(user)
    assistant_words = words(assistant)

    if not user_words or not assistant_words:
        return 0.0

    user_counts = Counter(user_words)
    assistant_counts = Counter(assistant_words)

    common = sum(
        min(count, assistant_counts[word])
        for word, count in user_counts.items()
    )

    return common / len(assistant_words)


def load_rows(path: Path) -> list[dict]:
    rows = []

    for line in path.read_text(
        encoding="utf-8"
    ).splitlines():
        if line.strip():
            rows.append(json.loads(line))

    return rows


def analyze_row(row: dict, tokenizer) -> dict:
    assistant = row["assistant"]
    user = row["user"]

    sentence_sim = sentence_similarity(assistant)
    ngram = repeated_ngram_stats(assistant)
    echo_sim = user_echo_similarity(user, assistant)

    token_count = len(
        tokenizer.encode(
            assistant,
            add_special_tokens=False,
        )
    )

    question_count = assistant.count("?")
    word_count = len(words(assistant))

    loop_candidate = (
        sentence_sim >= 0.80
        or ngram["max_count"] >= 3
        or (
            ngram["max_count"] >= 2
            and ngram["coverage"] >= 0.20
        )
    )

    user_echo_candidate = echo_sim >= 0.80

    near_token_cap = token_count >= 290

    return {
        "id": row["id"],
        "category": row["category"],
        "word_count": word_count,
        "token_count": token_count,
        "question_count": question_count,

        "sentence_similarity": round(
            sentence_sim,
            4,
        ),

        "ngram_size": ngram["ngram_size"],

        "ngram_coverage": round(
            ngram["coverage"],
            4,
        ),

        "ngram_max_count": ngram["max_count"],
        "ngram_repeated_types": ngram["repeated_types"],
        "ngram_example": ngram["example"],

        "user_echo_similarity": round(
            echo_sim,
            4,
        ),

        "loop_candidate": loop_candidate,
        "user_echo_candidate": user_echo_candidate,
        "near_token_cap": near_token_cap,
    }


def build_summary(name: str, results: list[dict]) -> dict:
    count = len(results)

    return {
        "name": name,
        "count": count,

        "avg_words": round(
            sum(r["word_count"] for r in results) / count,
            1,
        ),

        "avg_tokens": round(
            sum(r["token_count"] for r in results) / count,
            1,
        ),

        "total_questions": sum(
            r["question_count"]
            for r in results
        ),

        "loop_candidates": sum(
            1
            for r in results
            if r["loop_candidate"]
        ),

        "user_echo_candidates": sum(
            1
            for r in results
            if r["user_echo_candidate"]
        ),

        "near_token_cap": sum(
            1
            for r in results
            if r["near_token_cap"]
        ),

        "loop_ids": [
            r["id"]
            for r in results
            if r["loop_candidate"]
        ],

        "echo_ids": [
            r["id"]
            for r in results
            if r["user_echo_candidate"]
        ],

        "near_cap_ids": [
            r["id"]
            for r in results
            if r["near_token_cap"]
        ],
    }


def main():
    print("=" * 70)
    print("EduCoach Davranis Metrikleri v0.1")
    print("=" * 70)

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        local_files_only=True,
    )

    all_results = {}
    summaries = {}

    for name, path in FILES.items():
        if not path.exists():
            raise FileNotFoundError(
                f"Dosya bulunamadi: {path}"
            )

        rows = load_rows(path)

        results = [
            analyze_row(row, tokenizer)
            for row in rows
        ]

        all_results[name] = results
        summaries[name] = build_summary(
            name,
            results,
        )

    REPORT_JSON.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_JSON.write_text(
        json.dumps(
            {
                "summaries": summaries,
                "results": all_results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    text_lines = []

    for name in FILES:
        summary = summaries[name]

        text_lines.extend(
            [
                "=" * 70,
                name,
                "=" * 70,
                f"Sonuc             : {summary['count']}",
                f"Ortalama kelime   : {summary['avg_words']}",
                f"Ortalama token    : {summary['avg_tokens']}",
                f"Toplam soru       : {summary['total_questions']}",
                (
                    "Loop adayi         : "
                    f"{summary['loop_candidates']}/"
                    f"{summary['count']}"
                ),
                (
                    "Kullanici echo     : "
                    f"{summary['user_echo_candidates']}/"
                    f"{summary['count']}"
                ),
                (
                    "290+ token         : "
                    f"{summary['near_token_cap']}/"
                    f"{summary['count']}"
                ),
                f"Loop IDleri        : {summary['loop_ids']}",
                f"Echo IDleri        : {summary['echo_ids']}",
                f"290+ token IDleri  : {summary['near_cap_ids']}",
                "",
            ]
        )

        loop_results = [
            r
            for r in all_results[name]
            if r["loop_candidate"]
        ]

        if loop_results:
            text_lines.append(
                "LOOP DETAYLARI"
            )

            for result in loop_results:
                text_lines.extend(
                    [
                        (
                            f"{result['id']} | "
                            f"sentence={result['sentence_similarity']} | "
                            f"ngram={result['ngram_size']} | "
                            f"coverage={result['ngram_coverage']} | "
                            f"count={result['ngram_max_count']}"
                        ),
                        (
                            "  tekrar ornegi: "
                            f"{result['ngram_example']}"
                        ),
                    ]
                )

            text_lines.append("")

    REPORT_TXT.write_text(
        "\n".join(text_lines),
        encoding="utf-8",
    )

    print()
    print("\n".join(text_lines))

    print("=" * 70)
    print("Raporlar olusturuldu:")
    print(REPORT_TXT)
    print(REPORT_JSON)
    print("=" * 70)


if __name__ == "__main__":
    main()