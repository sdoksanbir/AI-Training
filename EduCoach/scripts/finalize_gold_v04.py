import json
from pathlib import Path

from create_gold_v04 import NEW_EXAMPLES


ROOT = Path(__file__).resolve().parent.parent

SOURCE_FILE = ROOT / "data" / "gold" / "gold_v0.3.jsonl"
OUTPUT_FILE = ROOT / "data" / "gold" / "gold_v0.4.jsonl"

EXPECTED_OLD = 38
EXPECTED_NEW = 82
EXPECTED_TOTAL = 120

EXPECTED_SINGLE_TURN = 70
EXPECTED_MULTI_TURN = 50


def load_jsonl(path: Path):
    rows = []

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue

            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"JSON hatasi: {path.name}, satir {line_number}: {exc}"
                ) from exc

            rows.append(row)

    return rows


def validate_example(example, index):
    if not isinstance(example, dict):
        raise ValueError(f"Ornek {index}: dict degil.")

    messages = example.get("messages")

    if not isinstance(messages, list) or not messages:
        raise ValueError(f"Ornek {index}: messages eksik veya bos.")

    for message_index, message in enumerate(messages, start=1):
        if not isinstance(message, dict):
            raise ValueError(
                f"Ornek {index}, mesaj {message_index}: dict degil."
            )

        role = message.get("role")
        content = message.get("content")

        if role not in {"system", "user", "assistant"}:
            raise ValueError(
                f"Ornek {index}, mesaj {message_index}: "
                f"gecersiz role = {role!r}"
            )

        if not isinstance(content, str) or not content.strip():
            raise ValueError(
                f"Ornek {index}, mesaj {message_index}: content bos."
            )

    user_count = sum(
        1 for message in messages if message.get("role") == "user"
    )

    assistant_count = sum(
        1 for message in messages if message.get("role") == "assistant"
    )

    if user_count == 0:
        raise ValueError(f"Ornek {index}: user mesaji yok.")

    if assistant_count == 0:
        raise ValueError(f"Ornek {index}: assistant mesaji yok.")


def conversation_type(example):
    messages = example["messages"]

    user_count = sum(
        1 for message in messages if message.get("role") == "user"
    )

    return "multi_turn" if user_count > 1 else "single_turn"


def main():
    old_examples = load_jsonl(SOURCE_FILE)

    print("Gold Dataset v0.4 finalizasyonu")
    print()

    print(f"Eski ornek sayisi : {len(old_examples)}")
    print(f"Yeni ornek sayisi : {len(NEW_EXAMPLES)}")

    if len(old_examples) != EXPECTED_OLD:
        raise ValueError(
            f"Eski ornek sayisi beklenenden farkli: "
            f"{len(old_examples)} != {EXPECTED_OLD}"
        )

    if len(NEW_EXAMPLES) != EXPECTED_NEW:
        raise ValueError(
            f"Yeni ornek sayisi beklenenden farkli: "
            f"{len(NEW_EXAMPLES)} != {EXPECTED_NEW}"
        )

    all_examples = old_examples + NEW_EXAMPLES

    if len(all_examples) != EXPECTED_TOTAL:
        raise ValueError(
            f"Toplam ornek sayisi hatali: "
            f"{len(all_examples)} != {EXPECTED_TOTAL}"
        )

    for index, example in enumerate(all_examples, start=1):
        validate_example(example, index)

    single_turn = sum(
        1 for example in all_examples
        if conversation_type(example) == "single_turn"
    )

    multi_turn = sum(
        1 for example in all_examples
        if conversation_type(example) == "multi_turn"
    )

    print()
    print(f"Tek turlu : {single_turn}")
    print(f"Cok turlu : {multi_turn}")

    if single_turn != EXPECTED_SINGLE_TURN:
        raise ValueError(
            f"Tek turlu sayisi hatali: "
            f"{single_turn} != {EXPECTED_SINGLE_TURN}"
        )

    if multi_turn != EXPECTED_MULTI_TURN:
        raise ValueError(
            f"Cok turlu sayisi hatali: "
            f"{multi_turn} != {EXPECTED_MULTI_TURN}"
        )

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        for example in all_examples:
            json.dump(
                example,
                f,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            f.write("\n")

    # Yazilan dosyayi tekrar okuyarak son kontrol.
    written_examples = load_jsonl(OUTPUT_FILE)

    if len(written_examples) != EXPECTED_TOTAL:
        raise ValueError(
            f"Yazilan dosya tekrar okundugunda "
            f"{len(written_examples)} ornek bulundu."
        )

    print()
    print("JSON yapisi       : OK")
    print("Ornek yapilari    : OK")
    print("Konusma dagilimi  : OK")
    print("Dosya tekrar okuma: OK")
    print()
    print(f"v0.4 olusturuldu:")
    print(OUTPUT_FILE)
    print()
    print(f"TOPLAM: {len(written_examples)}")


if __name__ == "__main__":
    main()