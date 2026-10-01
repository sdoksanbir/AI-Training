import json
import re
from collections import Counter
from pathlib import Path
from difflib import SequenceMatcher


ROOT = Path(__file__).resolve().parent.parent
SOURCE_FILE = ROOT / "data" / "gold" / "gold_v0.4.jsonl"

EXPECTED_TOTAL = 120


def load_jsonl(path: Path):
    rows = []

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue

            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"JSON hatasi - satir {line_number}: {exc}"
                ) from exc

    return rows


def normalize(text: str):
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\wçğıöşü ]", "", text)
    return text.strip()


def assistant_text(example):
    return " ".join(
        message["content"]
        for message in example["messages"]
        if message.get("role") == "assistant"
    )


def user_text(example):
    return " ".join(
        message["content"]
        for message in example["messages"]
        if message.get("role") == "user"
    )


def conversation_type(example):
    user_count = sum(
        1
        for message in example["messages"]
        if message.get("role") == "user"
    )

    return "multi_turn" if user_count > 1 else "single_turn"


def main():
    examples = load_jsonl(SOURCE_FILE)

    print("EDUCOACH GOLD v0.4 KALITE KONTROLU")
    print("=" * 60)
    print()

    print(f"Toplam ornek: {len(examples)}")

    if len(examples) != EXPECTED_TOTAL:
        print(
            f"UYARI: Beklenen {EXPECTED_TOTAL}, "
            f"bulunan {len(examples)}"
        )

    single_turn = sum(
        1 for example in examples
        if conversation_type(example) == "single_turn"
    )

    multi_turn = len(examples) - single_turn

    print(f"Tek turlu : {single_turn}")
    print(f"Cok turlu : {multi_turn}")
    print()

    # --------------------------------------------------
    # 1. Tam tekrar kontrolü
    # --------------------------------------------------

    normalized_assistant = [
        normalize(assistant_text(example))
        for example in examples
    ]

    counts = Counter(normalized_assistant)

    exact_duplicates = [
        text
        for text, count in counts.items()
        if count > 1
    ]

    print("1. TAM TEKRAR KONTROLU")
    print("-" * 60)

    if exact_duplicates:
        print(
            f"UYARI: {len(exact_duplicates)} tam tekrar bulundu."
        )

        for duplicate in exact_duplicates:
            indexes = [
                index + 1
                for index, text in enumerate(normalized_assistant)
                if text == duplicate
            ]

            print(f"  Ornekler: {indexes}")
    else:
        print("OK - Tam tekrar bulunmadi.")

    print()

    # --------------------------------------------------
    # 2. Yuksek benzerlik kontrolü
    # --------------------------------------------------

    print("2. YUKSEK BENZERLIK KONTROLU")
    print("-" * 60)

    similar_pairs = []

    for i in range(len(examples)):
        for j in range(i + 1, len(examples)):
            a = normalized_assistant[i]
            b = normalized_assistant[j]

            ratio = SequenceMatcher(None, a, b).ratio()

            if ratio >= 0.82:
                similar_pairs.append(
                    (i + 1, j + 1, ratio)
                )

    if similar_pairs:
        print(
            f"UYARI: {len(similar_pairs)} yuksek benzerlik cifti bulundu."
        )

        for first, second, ratio in similar_pairs[:30]:
            print(
                f"  Ornek {first} <-> Ornek {second}: "
                f"{ratio:.3f}"
            )

        if len(similar_pairs) > 30:
            print(
                f"  ... ve {len(similar_pairs) - 30} cift daha."
            )
    else:
        print("OK - 0.82 uzeri benzer cevap cifti bulunmadi.")

    print()

    # --------------------------------------------------
    # 3. Riskli ifade taraması
    # --------------------------------------------------

    print("3. RISKLI IFADE TARAMASI")
    print("-" * 60)

    risky_patterns = {
        "garanti": r"\bgaranti\b",
        "kesin": r"\bkesin\b",
        "100 puan": r"\b100 puan\b",
        "net_esittir_puan": r"\bnet\s*=\s*puan\b",
        "siralamam_kesin": r"sıralama.{0,20}kesin|kesin.{0,20}sıralama",
    }

    for label, pattern in risky_patterns.items():
        found = []

        for index, example in enumerate(examples, start=1):
            text = assistant_text(example).lower()

            if re.search(pattern, text):
                found.append(index)

        print(
            f"{label}: "
            f"{found if found else 'yok'}"
        )

    print()

    # --------------------------------------------------
    # 4. Soru işareti yoğunluğu
    # --------------------------------------------------

    print("4. ASISTAN SORU YOGUNLUGU")
    print("-" * 60)

    question_heavy = []

    for index, example in enumerate(examples, start=1):
        text = assistant_text(example)
        question_count = text.count("?")

        if question_count >= 3:
            question_heavy.append(
                (index, question_count)
            )

    if question_heavy:
        for index, count in question_heavy:
            print(
                f"  Ornek {index}: {count} soru isareti"
            )
    else:
        print("OK - Asiri soru yogunlugu bulunmadi.")

    print()

    # --------------------------------------------------
    # 5. Cevap uzunlukları
    # --------------------------------------------------

    print("5. CEVAP UZUNLUKLARI")
    print("-" * 60)

    lengths = []

    for index, example in enumerate(examples, start=1):
        words = assistant_text(example).split()
        lengths.append((index, len(words)))

    shortest = sorted(lengths, key=lambda x: x[1])[:10]
    longest = sorted(lengths, key=lambda x: x[1], reverse=True)[:10]

    average = sum(length for _, length in lengths) / len(lengths)

    print(f"Ortalama kelime: {average:.1f}")

    print()
    print("En kisa 10:")
    for index, length in shortest:
        print(f"  Ornek {index}: {length}")

    print()
    print("En uzun 10:")
    for index, length in longest:
        print(f"  Ornek {index}: {length}")

    print()

    # --------------------------------------------------
    # 6. Kullanıcı giriş tekrarları
    # --------------------------------------------------

    print("6. KULLANICI GIRIS TEKRARLARI")
    print("-" * 60)

    normalized_users = [
        normalize(user_text(example))
        for example in examples
    ]

    user_counts = Counter(normalized_users)

    duplicate_users = [
        text
        for text, count in user_counts.items()
        if count > 1
    ]

    if duplicate_users:
        for duplicate in duplicate_users:
            indexes = [
                index + 1
                for index, text in enumerate(normalized_users)
                if text == duplicate
            ]

            print(f"  Tekrar: {indexes}")
    else:
        print("OK - Tam ayni kullanici girdisi yok.")

    print()
    print("=" * 60)
    print("KONTROL TAMAMLANDI")


if __name__ == "__main__":
    main()