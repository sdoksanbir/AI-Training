import json
import re
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

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


def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        return [
            json.loads(line)
            for line in f
            if line.strip()
        ]


def word_count(text):
    return len(text.split())


def question_count(text):
    return text.count("?")


def repetition_score(text):
    text = text.lower()
    text = re.sub(r"\s+", " ", text)

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

            highest = max(highest, score)

    return highest


def summarize(rows):
    words = []
    total_questions = 0
    high_repeats = []

    for row in rows:
        answer = row["assistant"]

        words.append(word_count(answer))
        total_questions += question_count(answer)

        score = repetition_score(answer)

        if score >= 0.80:
            high_repeats.append(
                (row["id"], round(score, 3))
            )

    return {
        "count": len(rows),
        "average_words": sum(words) / len(words),
        "questions": total_questions,
        "repeats": high_repeats,
    }


def main():
    summaries = {}

    for name, path in FILES.items():
        if not path.exists():
            raise FileNotFoundError(
                f"{name} dosyasi bulunamadi: {path}"
            )

        rows = load_jsonl(path)

        if len(rows) != 30:
            raise ValueError(
                f"{name}: 30 sonuc bekleniyordu, bulunan {len(rows)}"
            )

        summaries[name] = summarize(rows)

    print("=" * 90)
    print("EDUCOACH - DORT KOSUL KARSILASTIRMASI")
    print("=" * 90)
    print()

    for name, result in summaries.items():
        print(name)
        print(
            f"  Sonuc sayisi   : {result['count']}"
        )
        print(
            f"  Ortalama kelime: {result['average_words']:.1f}"
        )
        print(
            f"  Toplam soru    : {result['questions']}"
        )
        print(
            f"  Yuksek tekrar  : {len(result['repeats'])}/30"
        )
        print(
            f"  Tekrar ID'leri : {result['repeats']}"
        )
        print()


if __name__ == "__main__":
    main()