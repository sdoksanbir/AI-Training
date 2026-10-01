import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SOURCE = ROOT / "data" / "gold" / "gold_v0.4.jsonl"

OUTPUT = (
    ROOT
    / "evaluations"
    / "reports"
    / "gold_v05_candidate_review.txt"
)

# 1-based gold örnek numaraları.
CANDIDATES = [
    1,
    39,
    41,
    42,
    44,
    73,
    92,
    93,
    96,
    97,
    98,
    100,
    110,
    113,
]


def main():
    rows = [
        json.loads(line)
        for line in SOURCE.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]

    if len(rows) != 120:
        raise ValueError(
            f"Beklenen 120 gold örneği, bulunan: {len(rows)}"
        )

    out = []

    for example_no in CANDIDATES:
        row = rows[example_no - 1]
        messages = row["messages"]

        out.extend(
            [
                "=" * 100,
                f"ORNEK {example_no}",
                "=" * 100,
                "",
            ]
        )

        for i, message in enumerate(messages):
            role = message["role"].upper()
            content = message["content"]

            out.extend(
                [
                    f"[{i}] {role}",
                    content,
                    "",
                ]
            )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        "\n".join(out),
        encoding="utf-8",
    )

    print(
        f"Aday sayisi : {len(CANDIDATES)}"
    )
    print(
        f"Kaynak      : {SOURCE}"
    )
    print(
        f"Cikti       : {OUTPUT}"
    )


if __name__ == "__main__":
    main()