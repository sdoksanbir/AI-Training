import json
import re
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

SHORT_FILE = (
    ROOT
    / "evaluations"
    / "post_training"
    / "educoach_v0.2_holdout_results.jsonl"
)

TRAINING_SYSTEM_FILE = (
    ROOT
    / "evaluations"
    / "post_training"
    / "educoach_v0.2_training_system_results.jsonl"
)


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
    questions = 0
    repeats = []

    for row in rows:
        answer = row["assistant"]

        words.append(
            word_count(answer)
        )

        questions += question_count(answer)

        score = repetition_score(answer)

        if score >= 0.80:
            repeats.append(
                (row["id"], round(score, 3))
            )

    return {
        "average_words": sum(words) / len(words),
        "questions": questions,
        "repeats": repeats,
    }


def main():
    short_rows = load_jsonl(SHORT_FILE)
    training_rows = load_jsonl(TRAINING_SYSTEM_FILE)

    if len(short_rows) != 30:
        raise ValueError(
            f"Kisa prompt sonucu 30 degil: {len(short_rows)}"
        )

    if len(training_rows) != 30:
        raise ValueError(
            f"Egitim prompt sonucu 30 degil: {len(training_rows)}"
        )

    short_ids = [row["id"] for row in short_rows]
    training_ids = [row["id"] for row in training_rows]

    if short_ids != training_ids:
        raise ValueError(
            "Iki sonuc dosyasinin ID sirasi ayni degil."
        )

    short = summarize(short_rows)
    training = summarize(training_rows)

    print("=" * 70)
    print("EDUCOACH v0.2 - SYSTEM PROMPT KARSILASTIRMASI")
    print("=" * 70)
    print()

    print("KISA SYSTEM PROMPT")
    print(
        f"Ortalama kelime : {short['average_words']:.1f}"
    )
    print(
        f"Toplam soru     : {short['questions']}"
    )
    print(
        f"Yuksek tekrar   : {len(short['repeats'])}/30"
    )
    print(
        f"Tekrar ID'leri  : {short['repeats']}"
    )

    print()
    print("EGITIM SYSTEM PROMPT")
    print(
        f"Ortalama kelime : {training['average_words']:.1f}"
    )
    print(
        f"Toplam soru     : {training['questions']}"
    )
    print(
        f"Yuksek tekrar   : {len(training['repeats'])}/30"
    )
    print(
        f"Tekrar ID'leri  : {training['repeats']}"
    )


if __name__ == "__main__":
    main()