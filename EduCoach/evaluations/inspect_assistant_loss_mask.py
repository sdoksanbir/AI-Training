import json
from pathlib import Path

from transformers import AutoTokenizer

from trl.chat_template_utils import (
    get_training_chat_template,
    has_generation_markers,
    is_chat_template_stop_token_trained,
)
from trl.data_utils import _tokenize


ROOT = Path(__file__).resolve().parents[1]

MODEL_NAME = "Qwen/Qwen3-4B"

GOLD_FILE = (
    ROOT
    / "data"
    / "gold"
    / "gold_v0.5.jsonl"
)


def load_example(example_no: int) -> dict:
    rows = []

    for line in GOLD_FILE.read_text(
        encoding="utf-8"
    ).splitlines():
        if line.strip():
            rows.append(json.loads(line))

    if example_no < 1 or example_no > len(rows):
        raise ValueError(
            f"Gecersiz example_no: {example_no}"
        )

    return rows[example_no - 1]


def short_text(text: str, limit: int = 220) -> str:
    text = text.replace("\n", "\\n")

    if len(text) <= limit:
        return text

    return text[:limit] + "..."


def main():
    print("=" * 100)
    print("EDUCOACH ASSISTANT-ONLY LOSS MASK DENETIMI")
    print("=" * 100)

    if not GOLD_FILE.exists():
        raise FileNotFoundError(
            f"Gold bulunamadi: {GOLD_FILE}"
        )

    # Example 1 multi-turn oldugu icin birden fazla
    # assistant cevabinin maskesini ayni anda gorebiliriz.
    example_no = 1
    example = load_example(example_no)

    messages = example["messages"]

    print(f"Gold dosyasi : {GOLD_FILE}")
    print(f"Ornek        : {example_no}")
    print(f"Mesaj sayisi : {len(messages)}")
    print()

    print("MESAJ ROLLERI")
    print("-" * 100)

    for index, message in enumerate(messages):
        print(
            f"{index:02d} | "
            f"{message['role']:<9} | "
            f"{short_text(message['content'], 120)}"
        )

    print()
    print("Tokenizer yukleniyor...")

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True,
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    tokenizer.padding_side = "right"

    raw_has_generation_markers = (
        has_generation_markers(
            tokenizer.chat_template
        )
    )

    if raw_has_generation_markers:
        training_chat_template = (
            tokenizer.chat_template
        )
        template_source = "MODEL_TEMPLATE"
    else:
        training_chat_template = (
            get_training_chat_template(
                tokenizer
            )
        )
        template_source = "TRL_PATCHED_TEMPLATE"

    print()
    print("CHAT TEMPLATE")
    print("-" * 100)
    print(
        "Ham template generation marker : "
        f"{raw_has_generation_markers}"
    )
    print(
        "Egitimde kullanilan template    : "
        f"{template_source}"
    )

    patched_has_generation_markers = (
        has_generation_markers(
            training_chat_template
        )
    )

    print(
        "Egitim template generation mark.: "
        f"{patched_has_generation_markers}"
    )

    stop_token_trained = (
        is_chat_template_stop_token_trained(
            tokenizer,
            chat_template=training_chat_template,
        )
    )

    print(
        "TRL stop-token trained kontrolu : "
        f"{stop_token_trained}"
    )

    print()
    print("TRL ile tokenize ediliyor...")

    processed = _tokenize(
        tokenizer,
        messages,
        return_assistant_tokens_mask=True,
        chat_template=training_chat_template,
    )

    input_ids = processed["input_ids"]

    if "assistant_masks" not in processed:
        raise RuntimeError(
            "assistant_masks uretilmedi."
        )

    assistant_masks = processed[
        "assistant_masks"
    ]

    if len(input_ids) != len(assistant_masks):
        raise RuntimeError(
            "input_ids ile assistant_masks "
            "uzunlugu esit degil."
        )

    labels = [
        token_id if mask_bit else -100
        for token_id, mask_bit in zip(
            input_ids,
            assistant_masks,
            strict=False,
        )
    ]

    total_tokens = len(input_ids)

    loss_tokens = sum(
        1
        for label in labels
        if label != -100
    )

    non_loss_tokens = (
        total_tokens - loss_tokens
    )

    print()
    print("MASK OZETI")
    print("-" * 100)
    print(
        f"Toplam token          : {total_tokens}"
    )
    print(
        f"LOSS alan token       : {loss_tokens}"
    )
    print(
        f"LOSS disi token       : {non_loss_tokens}"
    )
    print(
        "Assistant mask 1      : "
        f"{sum(assistant_masks)}"
    )
    print(
        "Assistant mask 0      : "
        f"{len(assistant_masks) - sum(assistant_masks)}"
    )

    print()
    print("MASK BLOKLARI")
    print("-" * 100)

    if not assistant_masks:
        raise RuntimeError(
            "Assistant mask bos."
        )

    block_start = 0
    current_bit = assistant_masks[0]
    block_no = 1

    for index in range(
        1,
        len(assistant_masks) + 1,
    ):
        at_end = index == len(
            assistant_masks
        )

        changed = (
            not at_end
            and assistant_masks[index]
            != current_bit
        )

        if not at_end and not changed:
            continue

        block_ids = input_ids[
            block_start:index
        ]

        decoded = tokenizer.decode(
            block_ids,
            skip_special_tokens=False,
        )

        label = (
            "LOSS VAR (assistant)"
            if current_bit == 1
            else "LOSS YOK"
        )

        print()
        print(
            f"[BLOK {block_no}] "
            f"{label}"
        )
        print(
            f"Token araligi: "
            f"{block_start}-{index - 1}"
        )
        print(
            f"Token sayisi : {len(block_ids)}"
        )
        print(
            short_text(
                decoded,
                limit=700,
            )
        )

        block_no += 1

        if not at_end:
            block_start = index
            current_bit = (
                assistant_masks[index]
            )

    print()
    print("<|im_end|> TOKEN DENETIMI")
    print("-" * 100)

    im_end_token = "<|im_end|>"

    im_end_id = tokenizer.convert_tokens_to_ids(
        im_end_token
    )

    print(
        f"<|im_end|> token id: {im_end_id}"
    )

    im_end_positions = [
        index
        for index, token_id in enumerate(
            input_ids
        )
        if token_id == im_end_id
    ]

    print(
        f"<|im_end|> occurrence: "
        f"{len(im_end_positions)}"
    )

    print()

    for occurrence_no, position in enumerate(
        im_end_positions,
        start=1,
    ):
        start = max(
            0,
            position - 30,
        )

        end = min(
            len(input_ids),
            position + 2,
        )

        context = tokenizer.decode(
            input_ids[start:end],
            skip_special_tokens=False,
        )

        role = (
            messages[occurrence_no - 1]["role"]
            if occurrence_no <= len(messages)
            else "BILINMIYOR"
        )

        mask_bit = assistant_masks[
            position
        ]

        label_value = labels[
            position
        ]

        print(
            f"{occurrence_no:02d} | "
            f"role={role:<9} | "
            f"position={position:<4} | "
            f"mask={mask_bit} | "
            f"label={label_value}"
        )

        print(
            "     context: "
            + short_text(
                context,
                limit=300,
            )
        )

    print()
    print("ROL BAZLI <|im_end|> SONUCU")
    print("-" * 100)

    if len(im_end_positions) == len(messages):
        all_ok = True

        for message, position in zip(
            messages,
            im_end_positions,
            strict=False,
        ):
            role = message["role"]
            mask_bit = assistant_masks[
                position
            ]

            expected = (
                1
                if role == "assistant"
                else 0
            )

            ok = mask_bit == expected

            if not ok:
                all_ok = False

            print(
                f"{role:<9} "
                f"im_end mask={mask_bit} "
                f"beklenen={expected} "
                f"=> {'OK' if ok else 'HATALI'}"
            )

        print()

        if all_ok:
            print(
                "SONUC: System/user turn sonlari "
                "loss disinda; assistant turn sonlari "
                "loss icinde."
            )
        else:
            print(
                "SONUC: En az bir rol icin "
                "<|im_end|> maskesi beklenenden farkli."
            )

    else:
        print(
            "Mesaj sayisi ile <|im_end|> sayisi "
            "eslesmedi. Yukaridaki token baglamlari "
            "manuel incelenmeli."
        )

    print()
    print("=" * 100)
    print("DENETIM TAMAMLANDI")
    print("=" * 100)


if __name__ == "__main__":
    main()