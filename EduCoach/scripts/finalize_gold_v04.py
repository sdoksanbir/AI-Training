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
        raise ValueError(
            f"Ornek {index}: messages eksik veya bos."
        )

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

    if messages[0].get("role") != "system":
        raise ValueError(
            f"Ornek {index}: ilk mesaj system degil."
        )

    user_count = sum(
        1 for message in messages
        if message.get("role") == "user"
    )

    assistant_count = sum(
        1 for message in messages
        if message.get("role") == "assistant"
    )

    if user_count == 0:
        raise ValueError(
            f"Ornek {index}: user mesaji yok."
        )

    if assistant_count == 0:
        raise ValueError(
            f"Ornek {index}: assistant mesaji yok."
        )


def conversation_type(example):
    user_count = sum(
        1
        for message in example["messages"]
        if message.get("role") == "user"
    )

    return (
        "multi_turn"
        if user_count > 1
        else "single_turn"
    )


def get_system_prompt(example):
    for message in example["messages"]:
        if message.get("role") == "system":
            return message.get("content")

    return None


def validate_old_system_prompts(old_examples):
    if not old_examples:
        raise ValueError(
            "Eski dataset bos."
        )

    first_system = get_system_prompt(
        old_examples[0]
    )

    if not first_system:
        raise ValueError(
            "Ilk eski ornekte system mesaji bulunamadi."
        )

    for index, example in enumerate(
        old_examples,
        start=1,
    ):
        current_system = get_system_prompt(
            example
        )

        if current_system != first_system:
            raise ValueError(
                f"Eski ornek {index}: system prompt farkli."
            )

    print("Eski system promptlari: OK")

    return first_system


def add_system_prompt(example, system_prompt):
    messages = example["messages"]

    if (
        messages
        and messages[0].get("role") == "system"
    ):
        return example

    return {
        **example,
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            *messages,
        ],
    }


def main():
    old_examples = load_jsonl(
        SOURCE_FILE
    )

    system_prompt = validate_old_system_prompts(
        old_examples
    )

    normalized_new_examples = [
        add_system_prompt(
            example,
            system_prompt,
        )
        for example in NEW_EXAMPLES
    ]

    print()
    print("Gold Dataset v0.4 finalizasyonu")
    print()

    print(
        f"Eski ornek sayisi : "
        f"{len(old_examples)}"
    )

    print(
        f"Yeni ornek sayisi : "
        f"{len(normalized_new_examples)}"
    )

    if len(old_examples) != EXPECTED_OLD:
        raise ValueError(
            f"Eski ornek sayisi beklenenden farkli: "
            f"{len(old_examples)} != {EXPECTED_OLD}"
        )

    if (
        len(normalized_new_examples)
        != EXPECTED_NEW
    ):
        raise ValueError(
            f"Yeni ornek sayisi beklenenden farkli: "
            f"{len(normalized_new_examples)} "
            f"!= {EXPECTED_NEW}"
        )

    all_examples = (
        old_examples
        + normalized_new_examples
    )

    if len(all_examples) != EXPECTED_TOTAL:
        raise ValueError(
            f"Toplam ornek sayisi hatali: "
            f"{len(all_examples)} "
            f"!= {EXPECTED_TOTAL}"
        )

    for index, example in enumerate(
        all_examples,
        start=1,
    ):
        validate_example(
            example,
            index,
        )

    all_system_prompts = [
        get_system_prompt(example)
        for example in all_examples
    ]

    system_count = sum(
        prompt is not None
        for prompt in all_system_prompts
    )

    unique_system_count = len(
        set(all_system_prompts)
    )

    print()
    print(
        f"System bulunan        : "
        f"{system_count}"
    )

    print(
        f"Benzersiz system      : "
        f"{unique_system_count}"
    )

    if system_count != EXPECTED_TOTAL:
        raise ValueError(
            f"System mesaj sayisi hatali: "
            f"{system_count} "
            f"!= {EXPECTED_TOTAL}"
        )

    if unique_system_count != 1:
        raise ValueError(
            f"Benzersiz system prompt sayisi "
            f"1 olmali, bulunan: "
            f"{unique_system_count}"
        )

    single_turn = sum(
        1
        for example in all_examples
        if conversation_type(example)
        == "single_turn"
    )

    multi_turn = sum(
        1
        for example in all_examples
        if conversation_type(example)
        == "multi_turn"
    )

    print()
    print(
        f"Tek turlu : {single_turn}"
    )

    print(
        f"Cok turlu : {multi_turn}"
    )

    if (
        single_turn
        != EXPECTED_SINGLE_TURN
    ):
        raise ValueError(
            f"Tek turlu sayisi hatali: "
            f"{single_turn} "
            f"!= {EXPECTED_SINGLE_TURN}"
        )

    if (
        multi_turn
        != EXPECTED_MULTI_TURN
    ):
        raise ValueError(
            f"Cok turlu sayisi hatali: "
            f"{multi_turn} "
            f"!= {EXPECTED_MULTI_TURN}"
        )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as f:
        for example in all_examples:
            json.dump(
                example,
                f,
                ensure_ascii=False,
                separators=(",", ":"),
            )

            f.write("\n")

    written_examples = load_jsonl(
        OUTPUT_FILE
    )

    if (
        len(written_examples)
        != EXPECTED_TOTAL
    ):
        raise ValueError(
            f"Yazilan dosya tekrar okundugunda "
            f"{len(written_examples)} "
            f"ornek bulundu."
        )

    for index, example in enumerate(
        written_examples,
        start=1,
    ):
        validate_example(
            example,
            index,
        )

    written_systems = [
        get_system_prompt(example)
        for example in written_examples
    ]

    if any(
        system != system_prompt
        for system in written_systems
    ):
        raise ValueError(
            "Yazilan dosyada system prompt "
            "tutarsizligi bulundu."
        )

    print()
    print("JSON yapisi       : OK")
    print("Ornek yapilari    : OK")
    print("System promptlari : OK")
    print("Konusma dagilimi  : OK")
    print("Dosya tekrar okuma: OK")
    print()

    print("v0.4 olusturuldu:")
    print(OUTPUT_FILE)
    print()

    print(
        f"TOPLAM: "
        f"{len(written_examples)}"
    )


if __name__ == "__main__":
    main()