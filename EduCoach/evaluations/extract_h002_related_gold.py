import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

GOLD_FILE = (
    ROOT
    / "data"
    / "gold"
    / "gold_v0.5.jsonl"
)

REPORT_FILE = (
    ROOT
    / "evaluations"
    / "reports"
    / "h002_related_gold_examples.txt"
)


# H002'nin gerçek girdisinden gelen kavramlar.
TARGET_TERMS = {
    "mezun": 4,
    "eşit ağırlık": 6,
    "eşit ağırlığım": 6,
    "tyt": 3,
    "ayt": 3,
    "matematik": 5,
    "edebiyat": 5,
    "net": 3,
    "saat": 2,
    "çalış": 2,
    "zorlan": 4,
    "iyi": 1,
    "nereden başla": 4,
    "başla": 2,
}


# Özellikle şüphelendiğimiz davranış kalıpları.
SUSPICIOUS_PATTERNS = [
    r"\b\d+\s*[-–]\s*\d+\b",
    r"\b\d+\s*(?:net|puan)\b",
    r"\bhedef\b",
    r"\bartış\b",
    r"\byüksel",
    r"\bmatematik\b",
    r"\btyt\b",
    r"\bayt\b",
    r"\bedebiyat\b",
]


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


def normalize(text: str) -> str:
    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def flatten_messages(
    messages: list[dict],
) -> str:
    return "\n".join(
        str(message.get("content", ""))
        for message in messages
    )


def score_example(
    messages: list[dict],
) -> tuple[int, list[str]]:
    text = normalize(
        flatten_messages(messages)
    )

    score = 0
    matched = []

    for term, weight in (
        TARGET_TERMS.items()
    ):
        if term in text:
            score += weight
            matched.append(term)

    # Kullanıcının birden fazla temel özelliği aynı
    # örnekte birlikte geçiyorsa bonus veriyoruz.
    combo_terms = [
        "tyt",
        "ayt",
        "matematik",
        "saat",
    ]

    combo_count = sum(
        1
        for term in combo_terms
        if term in text
    )

    if combo_count >= 3:
        score += 5

    if (
        "eşit ağırlık" in text
        and "matematik" in text
    ):
        score += 4

    if (
        "edebiyat" in text
        and "matematik" in text
    ):
        score += 4

    return score, matched


def find_suspicious_lines(
    messages: list[dict],
) -> list[str]:
    found = []

    for turn_index, message in enumerate(
        messages
    ):
        if message.get("role") != "assistant":
            continue

        content = str(
            message.get(
                "content",
                "",
            )
        )

        normalized = normalize(
            content
        )

        matched_patterns = []

        for pattern in SUSPICIOUS_PATTERNS:
            if re.search(
                pattern,
                normalized,
            ):
                matched_patterns.append(
                    pattern
                )

        if matched_patterns:
            found.append(
                (
                    f"assistant turn "
                    f"{turn_index}: "
                    f"{content}"
                )
            )

    return found


def main():
    if not GOLD_FILE.exists():
        raise FileNotFoundError(
            f"Gold bulunamadi: "
            f"{GOLD_FILE}"
        )

    rows = load_jsonl(
        GOLD_FILE
    )

    ranked = []

    for example_no, row in enumerate(
        rows,
        start=1,
    ):
        messages = row.get(
            "messages",
            [],
        )

        score, matched = (
            score_example(
                messages
            )
        )

        if score <= 0:
            continue

        suspicious = (
            find_suspicious_lines(
                messages
            )
        )

        ranked.append(
            {
                "example_no": (
                    example_no
                ),
                "score": score,
                "matched": matched,
                "messages": messages,
                "suspicious": (
                    suspicious
                ),
            }
        )

    ranked.sort(
        key=lambda item: (
            item["score"],
            len(
                item["matched"]
            ),
        ),
        reverse=True,
    )

    # İlk etapta en ilgili 25 örnek yeterli.
    top = ranked[:25]

    lines = [
        "=" * 100,
        "H002 ILE ILGILI GOLD v0.5 ORNEKLERI",
        "=" * 100,
        "",
        "H002:",
        (
            "Mezunum, eşit ağırlığım. TYT 78, "
            "AYT 44 yapıyorum. Edebiyatım iyi, "
            "matematikte zorlanıyorum. "
            "Günde 5 saat çalışabiliyorum. "
            "Nereden başlamalıyım?"
        ),
        "",
        f"Gold toplam: {len(rows)}",
        f"Aday toplam: {len(ranked)}",
        f"Rapora alinan: {len(top)}",
        "",
    ]

    for rank, item in enumerate(
        top,
        start=1,
    ):
        lines.extend(
            [
                "=" * 100,
                (
                    f"SIRA {rank} | "
                    f"GOLD ORNEK "
                    f"{item['example_no']} | "
                    f"SKOR {item['score']}"
                ),
                "=" * 100,
                (
                    "Eslesen kavramlar: "
                    + ", ".join(
                        item["matched"]
                    )
                ),
                "",
                "MESAJLAR",
                "-" * 100,
            ]
        )

        for turn_index, message in enumerate(
            item["messages"]
        ):
            role = (
                message.get(
                    "role",
                    "?"
                )
            )

            content = (
                message.get(
                    "content",
                    ""
                )
            )

            lines.extend(
                [
                    (
                        f"[{turn_index}] "
                        f"{role.upper()}"
                    ),
                    str(content),
                    "",
                ]
            )

        lines.extend(
            [
                "SAYISAL / DAVRANISSAL ADAYLAR",
                "-" * 100,
            ]
        )

        if item["suspicious"]:
            lines.extend(
                item["suspicious"]
            )
        else:
            lines.append(
                "YOK"
            )

        lines.append("")

    REPORT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_FILE.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print("=" * 90)
    print(
        "H002 GOLD BENZERLIK TARAMASI"
    )
    print("=" * 90)

    print(
        f"Gold toplam : "
        f"{len(rows)}"
    )

    print(
        f"Aday toplam : "
        f"{len(ranked)}"
    )

    print(
        f"Rapora alindi: "
        f"{len(top)}"
    )

    print()
    print("EN ILGILI 15 ORNEK")
    print("-" * 90)

    for rank, item in enumerate(
        top[:15],
        start=1,
    ):
        print(
            f"{rank:02d}. "
            f"Ornek {item['example_no']:03d} | "
            f"skor={item['score']:02d} | "
            f"{', '.join(item['matched'])}"
        )

    print()
    print(
        f"Rapor: "
        f"{REPORT_FILE}"
    )

    print()
    print("=" * 90)
    print(
        "TARAMA TAMAMLANDI"
    )
    print("=" * 90)


if __name__ == "__main__":
    main()