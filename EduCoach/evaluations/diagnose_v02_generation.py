import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from transformers import AutoTokenizer


ROOT = Path(__file__).resolve().parent.parent
MODEL = "Qwen/Qwen3-4B"

FILES = {
    "BASE_KISA": (
        ROOT
        / "evaluations"
        / "holdout"
        / "qwen3_4b_hf_baseline_v0.2.jsonl"
    ),
    "BASE_EGITIM_PROMPT": (
        ROOT
        / "evaluations"
        / "holdout"
        / "qwen3_4b_hf_training_system_v0.2.jsonl"
    ),
    "V02_KISA": (
        ROOT
        / "evaluations"
        / "post_training"
        / "educoach_v0.2_holdout_results.jsonl"
    ),
    "V02_EGITIM_PROMPT": (
        ROOT
        / "evaluations"
        / "post_training"
        / "educoach_v0.2_training_system_results.jsonl"
    ),
}

GOLD_FILE = (
    ROOT
    / "data"
    / "gold"
    / "gold_v0.4.jsonl"
)


def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        return [
            json.loads(line)
            for line in f
            if line.strip()
        ]


def repetition_score(text):
    text = re.sub(
        r"\s+",
        " ",
        text.lower(),
    ).strip()

    sentences = [
        s.strip()
        for s in re.split(r"[.!?]+", text)
        if s.strip()
    ]

    if len(sentences) < 2:
        return 0.0

    highest = 0.0

    for i in range(len(sentences)):
        for j in range(i + 1, len(sentences)):
            score = SequenceMatcher(
                None,
                sentences[i],
                sentences[j],
            ).ratio()

            highest = max(
                highest,
                score,
            )

    return highest


def inspect_results(name, rows, tokenizer):
    token_counts = []
    near_limit = []
    high_repeat = []

    for row in rows:
        answer = row["assistant"]

        tokens = tokenizer.encode(
            answer,
            add_special_tokens=False,
        )

        token_count = len(tokens)
        token_counts.append(token_count)

        if token_count >= 290:
            near_limit.append(
                (row["id"], token_count)
            )

        score = repetition_score(answer)

        if score >= 0.80:
            high_repeat.append(
                (row["id"], round(score, 3))
            )

    print(name)
    print(
        f"  Ortalama token     : "
        f"{sum(token_counts) / len(token_counts):.1f}"
    )
    print(
        f"  En uzun cevap      : "
        f"{max(token_counts)} token"
    )
    print(
        f"  290+ token cevap   : "
        f"{len(near_limit)}/30"
    )
    print(
        f"  290+ token ID      : "
        f"{near_limit}"
    )
    print(
        f"  Yuksek tekrar      : "
        f"{len(high_repeat)}/30"
    )
    print()


def inspect_gold(tokenizer):
    rows = load_jsonl(GOLD_FILE)

    assistant_messages = []

    for example_index, row in enumerate(
        rows,
        start=1,
    ):
        for message_index, message in enumerate(
            row["messages"],
            start=1,
        ):
            if message.get("role") == "assistant":
                assistant_messages.append(
                    (
                        example_index,
                        message_index,
                        message.get("content", ""),
                    )
                )

    repeats = []
    token_counts = []

    for example_index, message_index, text in assistant_messages:
        score = repetition_score(text)

        tokens = tokenizer.encode(
            text,
            add_special_tokens=False,
        )

        token_counts.append(len(tokens))

        if score >= 0.80:
            repeats.append(
                (
                    example_index,
                    message_index,
                    round(score, 3),
                )
            )

    print("GOLD v0.4")
    print(
        f"  Assistant mesaj    : "
        f"{len(assistant_messages)}"
    )
    print(
        f"  Ortalama token     : "
        f"{sum(token_counts) / len(token_counts):.1f}"
    )
    print(
        f"  Yuksek tekrar      : "
        f"{len(repeats)}/{len(assistant_messages)}"
    )
    print(
        f"  Tekrar konumlari   : "
        f"{repeats}"
    )
    print()


def main():
    print("Tokenizer yukleniyor...")

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL,
        trust_remote_code=True,
    )

    print()
    print("=" * 80)
    print("GENERATION TESHis RAPORU")
    print("=" * 80)
    print()

    for name, path in FILES.items():
        rows = load_jsonl(path)

        if len(rows) != 30:
            raise ValueError(
                f"{name}: 30 sonuc bekleniyordu, "
                f"{len(rows)} bulundu."
            )

        inspect_results(
            name,
            rows,
            tokenizer,
        )

    inspect_gold(tokenizer)


if __name__ == "__main__":
    main()