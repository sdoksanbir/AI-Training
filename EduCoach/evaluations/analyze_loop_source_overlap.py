import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

GOLD_FILE = (
    ROOT
    / "data"
    / "gold"
    / "gold_v0.5.jsonl"
)

V06_FILE = (
    ROOT
    / "evaluations"
    / "post_training"
    / "educoach_v0.6_training_system_results.jsonl"
)

REPORT_FILE = (
    ROOT
    / "evaluations"
    / "reports"
    / "v06_loop_source_overlap.txt"
)


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
        sentence.strip()
        for sentence in re.split(r"[.!?]+", normalized)
        if sentence.strip()
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
        "gram": tuple(),
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
                    range(
                        i,
                        min(i + n, len(token_words)),
                    )
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
            "gram": max_gram,
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


def load_jsonl(path: Path) -> list[dict]:
    rows = []

    for line in path.read_text(
        encoding="utf-8"
    ).splitlines():
        if line.strip():
            rows.append(json.loads(line))

    return rows


def extract_gold_assistant_messages(
    gold_rows: list[dict],
) -> list[dict]:
    messages = []

    for example_no, row in enumerate(
        gold_rows,
        start=1,
    ):
        for message_index, message in enumerate(
            row["messages"]
        ):
            if message.get("role") != "assistant":
                continue

            messages.append(
                {
                    "example_no": example_no,
                    "message_index": message_index,
                    "text": message["content"],
                    "words": words(message["content"]),
                }
            )

    return messages


def contains_ngram(
    message_words: list[str],
    target: tuple[str, ...],
) -> bool:
    if not target:
        return False

    n = len(target)

    if len(message_words) < n:
        return False

    for i in range(
        len(message_words) - n + 1
    ):
        if tuple(
            message_words[i : i + n]
        ) == target:
            return True

    return False


def count_ngram_occurrences(
    message_words: list[str],
    target: tuple[str, ...],
) -> int:
    if not target:
        return 0

    n = len(target)

    if len(message_words) < n:
        return 0

    count = 0

    for i in range(
        len(message_words) - n + 1
    ):
        if tuple(
            message_words[i : i + n]
        ) == target:
            count += 1

    return count


def make_snippet(
    text: str,
    target_text: str,
    radius: int = 90,
) -> str:
    normalized = normalize_text(text)
    target_normalized = normalize_text(target_text)

    pos = normalized.find(target_normalized)

    if pos < 0:
        return normalized[:220]

    start = max(
        0,
        pos - radius,
    )

    end = min(
        len(normalized),
        pos + len(target_normalized) + radius,
    )

    snippet = normalized[start:end]

    if start > 0:
        snippet = "..." + snippet

    if end < len(normalized):
        snippet = snippet + "..."

    return snippet


def main():
    if not GOLD_FILE.exists():
        raise FileNotFoundError(
            f"Gold bulunamadi: {GOLD_FILE}"
        )

    if not V06_FILE.exists():
        raise FileNotFoundError(
            f"V06 sonucu bulunamadi: {V06_FILE}"
        )

    gold_rows = load_jsonl(GOLD_FILE)
    v06_rows = load_jsonl(V06_FILE)

    gold_messages = extract_gold_assistant_messages(
        gold_rows
    )

    report = []

    report.extend(
        [
            "=" * 100,
            "V06 LOOP KAYNAK ORTUSME ANALIZI",
            "=" * 100,
            "",
            f"Gold ornek sayisi      : {len(gold_rows)}",
            f"Gold assistant mesaji  : {len(gold_messages)}",
            f"V06 benchmark sonucu   : {len(v06_rows)}",
            "",
        ]
    )

    loop_count = 0
    repeated_ngram_loop_count = 0
    exact_gold_match_count = 0
    no_gold_match_count = 0
    sentence_only_loop_count = 0

    for row in v06_rows:
        assistant = row["assistant"]

        sentence_sim = sentence_similarity(
            assistant
        )

        ngram = repeated_ngram_stats(
            assistant
        )

        loop_candidate = (
            sentence_sim >= 0.80
            or ngram["max_count"] >= 3
            or (
                ngram["max_count"] >= 2
                and ngram["coverage"] >= 0.20
            )
        )

        if not loop_candidate:
            continue

        loop_count += 1

        report.extend(
            [
                "=" * 100,
                f"{row['id']}",
                "=" * 100,
                f"Kategori             : {row.get('category', '')}",
                f"Sentence similarity  : {sentence_sim:.4f}",
                f"Ngram boyutu         : {ngram['ngram_size']}",
                f"Ngram coverage       : {ngram['coverage']:.4f}",
                f"Ngram tekrar sayisi  : {ngram['max_count']}",
                f"Tekrar tipi sayisi   : {ngram['repeated_types']}",
                f"Tekrar ornegi        : {ngram['example']}",
                "",
            ]
        )

        if not ngram["gram"]:
            sentence_only_loop_count += 1

            report.extend(
                [
                    "SONUC:",
                    (
                        "Bu loop n-gram tekrariyla degil, "
                        "cumle benzerligiyle yakalandi."
                    ),
                    (
                        "Bu vaka icin birebir tekrar ifadesi "
                        "gold'da aranamaz."
                    ),
                    "",
                ]
            )

            continue

        repeated_ngram_loop_count += 1

        matching_messages = []

        total_gold_occurrences = 0

        for gold_message in gold_messages:
            occurrence_count = (
                count_ngram_occurrences(
                    gold_message["words"],
                    ngram["gram"],
                )
            )

            if occurrence_count <= 0:
                continue

            total_gold_occurrences += (
                occurrence_count
            )

            matching_messages.append(
                {
                    **gold_message,
                    "occurrences": occurrence_count,
                }
            )

        if matching_messages:
            exact_gold_match_count += 1

            report.extend(
                [
                    "GOLD ESLESMESI: EVET",
                    (
                        "Eslesen gold assistant mesaji: "
                        f"{len(matching_messages)}"
                    ),
                    (
                        "Gold toplam occurrence       : "
                        f"{total_gold_occurrences}"
                    ),
                    "",
                    "ESLESEN GOLD MESAJLARI:",
                ]
            )

            for match in matching_messages:
                report.extend(
                    [
                        (
                            f"- Ornek {match['example_no']} "
                            f"| mesaj index "
                            f"{match['message_index']} "
                            f"| occurrence "
                            f"{match['occurrences']}"
                        ),
                        (
                            "  "
                            + make_snippet(
                                match["text"],
                                ngram["example"],
                            )
                        ),
                    ]
                )

            report.append("")

        else:
            no_gold_match_count += 1

            report.extend(
                [
                    "GOLD ESLESMESI: HAYIR",
                    (
                        "V06'nin tekrar ettigi bu 5-8 kelimelik "
                        "ifade gold_v0.5 assistant mesajlarinda "
                        "birebir bulunmadi."
                    ),
                    "",
                ]
            )

    report.extend(
        [
            "=" * 100,
            "OZET",
            "=" * 100,
            f"Toplam V06 loop adayi              : {loop_count}",
            (
                "Ngram tekrari bulunan loop         : "
                f"{repeated_ngram_loop_count}"
            ),
            (
                "Yalniz cumle benzerligi loopu       : "
                f"{sentence_only_loop_count}"
            ),
            (
                "Tekrar ifadesi gold'da bulunan      : "
                f"{exact_gold_match_count}"
            ),
            (
                "Tekrar ifadesi gold'da bulunmayan   : "
                f"{no_gold_match_count}"
            ),
            "",
            "YORUM KILAVUZU:",
            (
                "- Gold eslesmesi EVET: modelin tekrar ettigi "
                "ifadenin en az bir 5-8 kelimelik kalibi "
                "egitim verisinde birebir var."
            ),
            (
                "- Gold eslesmesi HAYIR: loop ifadesi "
                "gold assistant cevaplarindan birebir "
                "kopyalanmis gorunmuyor."
            ),
            (
                "- Bu test tek basina nedensellik kanitlamaz; "
                "yalnizca tekrar kalibinin gold'daki birebir "
                "varligini test eder."
            ),
            "",
        ]
    )

    REPORT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_FILE.write_text(
        "\n".join(report),
        encoding="utf-8",
    )

    print("=" * 70)
    print("V06 LOOP KAYNAK ORTUSME ANALIZI TAMAMLANDI")
    print("=" * 70)
    print(
        f"Toplam loop               : {loop_count}"
    )
    print(
        "Ngram loop                : "
        f"{repeated_ngram_loop_count}"
    )
    print(
        "Cumle-benzerligi loop     : "
        f"{sentence_only_loop_count}"
    )
    print(
        "Gold'da birebir bulunan   : "
        f"{exact_gold_match_count}"
    )
    print(
        "Gold'da bulunmayan        : "
        f"{no_gold_match_count}"
    )
    print()
    print(f"Rapor: {REPORT_FILE}")


if __name__ == "__main__":
    main()