import json
import re
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

GOLD_FILE = (
    ROOT
    / "data"
    / "gold"
    / "gold_v0.5.jsonl"
)

HOLDOUT_FILE = (
    ROOT
    / "evaluations"
    / "holdout"
    / "benchmark_v0.2.jsonl"
)

REPORT_TXT = (
    ROOT
    / "evaluations"
    / "reports"
    / "holdout_gold_overlap_audit.txt"
)

REPORT_JSON = (
    ROOT
    / "evaluations"
    / "reports"
    / "holdout_gold_overlap_audit.json"
)

TOP_K = 5


def load_jsonl(path: Path) -> list[dict]:
    rows = []

    for line in path.read_text(
        encoding="utf-8"
    ).splitlines():
        if line.strip():
            rows.append(
                json.loads(line)
            )

    return rows


def normalize(
    text: str,
    mask_numbers: bool,
) -> str:
    text = text.lower()

    text = (
        text
        .replace("’", "'")
        .replace("“", '"')
        .replace("”", '"')
    )

    if mask_numbers:
        text = re.sub(
            r"\d+(?:[.,]\d+)?",
            "<num>",
            text,
        )

    text = re.sub(
        r"[^\wçğıöşü<>]+",
        " ",
        text,
        flags=re.UNICODE,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def tokenize(
    text: str,
) -> list[str]:
    return [
        token
        for token in text.split()
        if token
    ]


def sequence_similarity(
    left: str,
    right: str,
) -> float:
    return SequenceMatcher(
        None,
        left,
        right,
    ).ratio()


def jaccard_similarity(
    left_tokens: list[str],
    right_tokens: list[str],
) -> float:
    left_set = set(
        left_tokens
    )

    right_set = set(
        right_tokens
    )

    if not left_set and not right_set:
        return 1.0

    union = (
        left_set
        | right_set
    )

    if not union:
        return 0.0

    intersection = (
        left_set
        & right_set
    )

    return (
        len(intersection)
        / len(union)
    )


def token_bigrams(
    tokens: list[str],
) -> set[tuple[str, str]]:
    if len(tokens) < 2:
        return set()

    return {
        (
            tokens[index],
            tokens[index + 1],
        )
        for index in range(
            len(tokens) - 1
        )
    }


def bigram_dice(
    left_tokens: list[str],
    right_tokens: list[str],
) -> float:
    left = token_bigrams(
        left_tokens
    )

    right = token_bigrams(
        right_tokens
    )

    if not left and not right:
        return 1.0

    denominator = (
        len(left)
        + len(right)
    )

    if denominator == 0:
        return 0.0

    return (
        2
        * len(left & right)
        / denominator
    )


def similarity_bundle(
    left: str,
    right: str,
    mask_numbers: bool,
) -> dict:
    left_normalized = normalize(
        left,
        mask_numbers=mask_numbers,
    )

    right_normalized = normalize(
        right,
        mask_numbers=mask_numbers,
    )

    left_tokens = tokenize(
        left_normalized
    )

    right_tokens = tokenize(
        right_normalized
    )

    seq = sequence_similarity(
        left_normalized,
        right_normalized,
    )

    jaccard = jaccard_similarity(
        left_tokens,
        right_tokens,
    )

    bigram = bigram_dice(
        left_tokens,
        right_tokens,
    )

    # Farkli acilardan gelen 3 sinyali birlikte
    # kullaniyoruz. Bu bir "gercek semantik model"
    # degildir; leakage adayi bulmak icin tanisal
    # bir skor.
    combined = (
        0.50 * seq
        + 0.30 * jaccard
        + 0.20 * bigram
    )

    return {
        "sequence": seq,
        "jaccard": jaccard,
        "bigram_dice": bigram,
        "combined": combined,
    }


def classify_candidate(
    masked_score: float,
    raw_score: float,
) -> str:
    # Bunlar kesin contamination karari degil;
    # manuel inceleme onceligi.
    if (
        masked_score >= 0.78
        or raw_score >= 0.78
    ):
        return "VERY_HIGH"

    if (
        masked_score >= 0.65
        or raw_score >= 0.65
    ):
        return "HIGH"

    if (
        masked_score >= 0.52
        or raw_score >= 0.52
    ):
        return "MEDIUM"

    return "LOW"


def extract_gold_user_turns(
    gold_rows: list[dict],
) -> list[dict]:
    turns = []

    for example_no, row in enumerate(
        gold_rows,
        start=1,
    ):
        messages = row.get(
            "messages",
            [],
        )

        user_messages = []

        for turn_index, message in enumerate(
            messages
        ):
            if (
                message.get("role")
                != "user"
            ):
                continue

            content = str(
                message.get(
                    "content",
                    "",
                )
            ).strip()

            if not content:
                continue

            user_messages.append(
                content
            )

            turns.append(
                {
                    "gold_example": (
                        example_no
                    ),
                    "turn_index": (
                        turn_index
                    ),
                    "kind": (
                        "single_user_turn"
                    ),
                    "text": content,
                }
            )

        # Multi-turn gold orneklerinde bazen holdout,
        # tek bir gold user turnunden degil butun user
        # bilgilerinin birlesiminden turemis olabilir.
        if len(user_messages) > 1:
            combined = " ".join(
                user_messages
            )

            turns.append(
                {
                    "gold_example": (
                        example_no
                    ),
                    "turn_index": None,
                    "kind": (
                        "combined_user_turns"
                    ),
                    "text": combined,
                }
            )

    return turns


def main():
    if not GOLD_FILE.exists():
        raise FileNotFoundError(
            f"Gold bulunamadi: "
            f"{GOLD_FILE}"
        )

    if not HOLDOUT_FILE.exists():
        raise FileNotFoundError(
            f"Holdout bulunamadi: "
            f"{HOLDOUT_FILE}"
        )

    gold_rows = load_jsonl(
        GOLD_FILE
    )

    holdout_rows = load_jsonl(
        HOLDOUT_FILE
    )

    gold_user_turns = (
        extract_gold_user_turns(
            gold_rows
        )
    )

    print("=" * 100)
    print(
        "EDUCOACH HOLDOUT / GOLD OVERLAP DENETIMI"
    )
    print("=" * 100)

    print(
        f"Gold ornek       : "
        f"{len(gold_rows)}"
    )

    print(
        f"Gold user aday   : "
        f"{len(gold_user_turns)}"
    )

    print(
        f"Holdout ornek    : "
        f"{len(holdout_rows)}"
    )

    print()

    all_results = []

    label_counts = {
        "VERY_HIGH": 0,
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
    }

    report_lines = [
        "=" * 100,
        "EDUCOACH HOLDOUT / GOLD OVERLAP DENETIMI",
        "=" * 100,
        "",
        (
            f"Gold: "
            f"{GOLD_FILE}"
        ),
        (
            f"Holdout: "
            f"{HOLDOUT_FILE}"
        ),
        (
            f"Gold ornek: "
            f"{len(gold_rows)}"
        ),
        (
            f"Gold user aday: "
            f"{len(gold_user_turns)}"
        ),
        (
            f"Holdout: "
            f"{len(holdout_rows)}"
        ),
        "",
        (
            "NOT: VERY_HIGH/HIGH/MEDIUM etiketleri "
            "otomatik contamination karari degildir. "
            "Manuel inceleme onceligidir."
        ),
        "",
    ]

    for holdout in holdout_rows:
        holdout_id = str(
            holdout.get(
                "id",
                "?"
            )
        )

        holdout_category = str(
            holdout.get(
                "category",
                ""
            )
        )

        holdout_user = str(
            holdout.get(
                "user",
                ""
            )
        ).strip()

        candidates = []

        for gold_turn in gold_user_turns:
            raw = similarity_bundle(
                holdout_user,
                gold_turn["text"],
                mask_numbers=False,
            )

            masked = similarity_bundle(
                holdout_user,
                gold_turn["text"],
                mask_numbers=True,
            )

            best_score = max(
                raw["combined"],
                masked["combined"],
            )

            label = classify_candidate(
                masked_score=(
                    masked["combined"]
                ),
                raw_score=(
                    raw["combined"]
                ),
            )

            candidates.append(
                {
                    "gold_example": (
                        gold_turn[
                            "gold_example"
                        ]
                    ),
                    "turn_index": (
                        gold_turn[
                            "turn_index"
                        ]
                    ),
                    "kind": (
                        gold_turn[
                            "kind"
                        ]
                    ),
                    "gold_user": (
                        gold_turn["text"]
                    ),
                    "raw": raw,
                    "masked": masked,
                    "best_score": (
                        best_score
                    ),
                    "label": label,
                }
            )

        candidates.sort(
            key=lambda item: (
                item["best_score"],
                item["masked"][
                    "combined"
                ],
            ),
            reverse=True,
        )

        top_matches = (
            candidates[:TOP_K]
        )

        top_label = (
            top_matches[0]["label"]
            if top_matches
            else "LOW"
        )

        label_counts[
            top_label
        ] += 1

        all_results.append(
            {
                "id": holdout_id,
                "category": (
                    holdout_category
                ),
                "user": holdout_user,
                "top_label": (
                    top_label
                ),
                "matches": (
                    top_matches
                ),
            }
        )

        top = top_matches[0]

        print(
            f"{holdout_id:<5} | "
            f"{top_label:<9} | "
            f"Gold {top['gold_example']:03d} | "
            f"raw={top['raw']['combined']:.3f} | "
            f"masked={top['masked']['combined']:.3f}"
        )

        report_lines.extend(
            [
                "=" * 100,
                (
                    f"{holdout_id} | "
                    f"{holdout_category} | "
                    f"TOP LABEL: {top_label}"
                ),
                "=" * 100,
                "",
                "HOLDOUT USER:",
                holdout_user,
                "",
                "TOP MATCHES",
                "-" * 100,
            ]
        )

        for rank, match in enumerate(
            top_matches,
            start=1,
        ):
            report_lines.extend(
                [
                    (
                        f"{rank}. GOLD "
                        f"{match['gold_example']} | "
                        f"{match['kind']} | "
                        f"turn="
                        f"{match['turn_index']}"
                    ),
                    (
                        f"   label="
                        f"{match['label']}"
                    ),
                    (
                        f"   raw combined="
                        f"{match['raw']['combined']:.4f} | "
                        f"seq="
                        f"{match['raw']['sequence']:.4f} | "
                        f"jaccard="
                        f"{match['raw']['jaccard']:.4f} | "
                        f"bigram="
                        f"{match['raw']['bigram_dice']:.4f}"
                    ),
                    (
                        f"   masked combined="
                        f"{match['masked']['combined']:.4f} | "
                        f"seq="
                        f"{match['masked']['sequence']:.4f} | "
                        f"jaccard="
                        f"{match['masked']['jaccard']:.4f} | "
                        f"bigram="
                        f"{match['masked']['bigram_dice']:.4f}"
                    ),
                    "   GOLD USER:",
                    (
                        f"   "
                        f"{match['gold_user']}"
                    ),
                    "",
                ]
            )

        report_lines.append("")

    very_high_ids = [
        row["id"]
        for row in all_results
        if row["top_label"]
        == "VERY_HIGH"
    ]

    high_ids = [
        row["id"]
        for row in all_results
        if row["top_label"]
        == "HIGH"
    ]

    medium_ids = [
        row["id"]
        for row in all_results
        if row["top_label"]
        == "MEDIUM"
    ]

    report_lines.extend(
        [
            "=" * 100,
            "GENEL OZET",
            "=" * 100,
            "",
            (
                "VERY_HIGH: "
                f"{label_counts['VERY_HIGH']} "
                f"{very_high_ids}"
            ),
            (
                "HIGH     : "
                f"{label_counts['HIGH']} "
                f"{high_ids}"
            ),
            (
                "MEDIUM   : "
                f"{label_counts['MEDIUM']} "
                f"{medium_ids}"
            ),
            (
                "LOW      : "
                f"{label_counts['LOW']}"
            ),
            "",
        ]
    )

    REPORT_TXT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_TXT.write_text(
        "\n".join(
            report_lines
        ),
        encoding="utf-8",
    )

    REPORT_JSON.write_text(
        json.dumps(
            {
                "gold_file": (
                    str(GOLD_FILE)
                ),
                "holdout_file": (
                    str(HOLDOUT_FILE)
                ),
                "gold_examples": (
                    len(gold_rows)
                ),
                "gold_user_candidates": (
                    len(
                        gold_user_turns
                    )
                ),
                "holdout_examples": (
                    len(
                        holdout_rows
                    )
                ),
                "label_counts": (
                    label_counts
                ),
                "results": (
                    all_results
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 100)
    print("OZET")
    print("=" * 100)

    print(
        f"VERY_HIGH : "
        f"{label_counts['VERY_HIGH']} "
        f"{very_high_ids}"
    )

    print(
        f"HIGH      : "
        f"{label_counts['HIGH']} "
        f"{high_ids}"
    )

    print(
        f"MEDIUM    : "
        f"{label_counts['MEDIUM']} "
        f"{medium_ids}"
    )

    print(
        f"LOW       : "
        f"{label_counts['LOW']}"
    )

    print()
    print(
        f"TXT  : "
        f"{REPORT_TXT}"
    )

    print(
        f"JSON : "
        f"{REPORT_JSON}"
    )

    print()
    print("=" * 100)
    print(
        "DENETIM TAMAMLANDI"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()