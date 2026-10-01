import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GOLD_FILE = ROOT / "data" / "gold" / "gold_v0.5.jsonl"

REPORT_FILE = (
    ROOT
    / "evaluations"
    / "reports"
    / "gold_v05_behavior_audit.txt"
)


SUBJECT_TERMS = [
    "matematik",
    "problem",
    "geometri",
    "türkçe",
    "paragraf",
    "fizik",
    "kimya",
    "biyoloji",
    "fen",
    "ayt",
    "tyt",
]


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def words(text: str) -> list[str]:
    return re.findall(
        r"[0-9a-zA-ZçğıöşüÇĞİÖŞÜ]+",
        normalize(text),
    )


def repeated_ngram_stats(text: str) -> dict:
    tokens = words(text)

    best = {
        "coverage": 0.0,
        "count": 0,
        "ngram": "",
    }

    for n in range(5, 9):
        if len(tokens) < n:
            continue

        grams = [
            tuple(tokens[i:i + n])
            for i in range(len(tokens) - n + 1)
        ]

        counts = Counter(grams)

        repeated = {
            gram: count
            for gram, count in counts.items()
            if count >= 2
        }

        if not repeated:
            continue

        covered = set()

        for i, gram in enumerate(grams):
            if gram in repeated:
                covered.update(
                    range(i, min(i + n, len(tokens)))
                )

        coverage = len(covered) / len(tokens)

        max_gram, max_count = max(
            repeated.items(),
            key=lambda item: item[1],
        )

        if coverage > best["coverage"]:
            best = {
                "coverage": coverage,
                "count": max_count,
                "ngram": " ".join(max_gram),
            }

    return best


def echo_ratio(user_text: str, assistant_text: str) -> float:
    user_words = words(user_text)
    assistant_words = words(assistant_text)

    if not user_words or not assistant_words:
        return 0.0

    user_counts = Counter(user_words)
    assistant_counts = Counter(assistant_words)

    common = sum(
        min(count, assistant_counts[word])
        for word, count in user_counts.items()
    )

    return common / len(assistant_words)


def extract_numbers(text: str) -> set[str]:
    return set(
        re.findall(
            r"\b\d+(?:[.,]\d+)?\b",
            normalize(text),
        )
    )


def introduced_subjects(
    user_context: str,
    assistant_text: str,
) -> list[str]:
    user_norm = normalize(user_context)
    assistant_norm = normalize(assistant_text)

    found = []

    for term in SUBJECT_TERMS:
        if (
            term in assistant_norm
            and term not in user_norm
        ):
            found.append(term)

    return found


def main():
    rows = [
        json.loads(line)
        for line in GOLD_FILE.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]

    report = []

    total_assistant = 0
    question_turns = 0
    echo_flags = 0
    loop_flags = 0
    number_flags = 0
    subject_flags = 0

    for example_index, row in enumerate(rows, start=1):
        messages = row["messages"]

        user_context_parts = []

        for message_index, message in enumerate(messages):
            role = message["role"]
            content = message["content"]

            if role == "user":
                user_context_parts.append(content)
                continue

            if role != "assistant":
                continue

            total_assistant += 1

            user_context = "\n".join(user_context_parts)

            questions = content.count("?")
            echo = echo_ratio(
                user_context,
                content,
            )

            loop = repeated_ngram_stats(content)

            user_numbers = extract_numbers(
                user_context
            )

            assistant_numbers = extract_numbers(
                content
            )

            new_numbers = sorted(
                assistant_numbers - user_numbers
            )

            new_subjects = introduced_subjects(
                user_context,
                content,
            )

            loop_flag = (
                loop["count"] >= 3
                or (
                    loop["count"] >= 2
                    and loop["coverage"] >= 0.20
                )
            )

            echo_flag = echo >= 0.80

            if questions > 0:
                question_turns += 1

            if echo_flag:
                echo_flags += 1

            if loop_flag:
                loop_flags += 1

            if new_numbers:
                number_flags += 1

            if new_subjects:
                subject_flags += 1

            if (
                questions > 0
                or echo_flag
                or loop_flag
                or new_numbers
                or new_subjects
            ):
                report.extend(
                    [
                        "=" * 100,
                        (
                            f"ORNEK {example_index} "
                            f"| MESAJ {message_index}"
                        ),
                        "",
                        "KULLANICI BAGLAMI:",
                        user_context,
                        "",
                        "ASSISTANT:",
                        content,
                        "",
                        f"Soru sayisi       : {questions}",
                        f"Echo orani        : {echo:.3f}",
                        (
                            "Loop              : "
                            f"coverage={loop['coverage']:.3f}, "
                            f"count={loop['count']}"
                        ),
                        (
                            "Loop ornegi       : "
                            f"{loop['ngram']}"
                        ),
                        (
                            "Yeni sayilar      : "
                            f"{new_numbers}"
                        ),
                        (
                            "Yeni ders/alan    : "
                            f"{new_subjects}"
                        ),
                        "",
                    ]
                )

    summary = [
        "=" * 100,
        "GOLD v0.5 DAVRANIS DENETIMI",
        "=" * 100,
        f"Gold ornek sayisi          : {len(rows)}",
        f"Assistant mesaj sayisi     : {total_assistant}",
        (
            "Soru iceren assistant     : "
            f"{question_turns}/{total_assistant}"
        ),
        (
            "Yuksek echo               : "
            f"{echo_flags}/{total_assistant}"
        ),
        (
            "Loop adayi                : "
            f"{loop_flags}/{total_assistant}"
        ),
        (
            "Yeni sayi kullanan        : "
            f"{number_flags}/{total_assistant}"
        ),
        (
            "Yeni ders/alan kullanan   : "
            f"{subject_flags}/{total_assistant}"
        ),
        "",
        "NOT:",
        (
            "Yeni sayi veya yeni ders/alan bayragi otomatik olarak hata "
            "anlamina gelmez. Bunlar manuel inceleme adayidir."
        ),
        "",
    ]

    final_text = "\n".join(
        summary + report
    )

    REPORT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_FILE.write_text(
        final_text,
        encoding="utf-8",
    )

    print("\n".join(summary))

    print(
        f"Rapor: {REPORT_FILE}"
    )


if __name__ == "__main__":
    main()