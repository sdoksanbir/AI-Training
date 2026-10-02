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

REPORT_FILE = (
    ROOT
    / "evaluations"
    / "reports"
    / "training_mask_audit_all_gold.txt"
)

# v0.6 egitimindeki mevcut sequence limiti.
# TRL varsayilan truncation_mode = keep_start.
MAX_LENGTH = 2048


def load_jsonl(path: Path) -> list[dict]:
    rows = []

    for line in path.read_text(
        encoding="utf-8"
    ).splitlines():
        if line.strip():
            rows.append(json.loads(line))

    return rows


def main():
    print("=" * 90)
    print("EDUCOACH TUM GOLD MASK / TRUNCATION DENETIMI")
    print("=" * 90)

    if not GOLD_FILE.exists():
        raise FileNotFoundError(
            f"Gold bulunamadi: {GOLD_FILE}"
        )

    rows = load_jsonl(GOLD_FILE)

    print(f"Gold dosyasi : {GOLD_FILE}")
    print(f"Ornek sayisi : {len(rows)}")
    print(f"Max length   : {MAX_LENGTH}")
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

    patched_has_generation_markers = (
        has_generation_markers(
            training_chat_template
        )
    )

    stop_token_trained = (
        is_chat_template_stop_token_trained(
            tokenizer,
            chat_template=training_chat_template,
        )
    )

    print(
        "Ham template generation marker : "
        f"{raw_has_generation_markers}"
    )
    print(
        "Egitim template                : "
        f"{template_source}"
    )
    print(
        "Egitim generation marker       : "
        f"{patched_has_generation_markers}"
    )
    print(
        "TRL stop-token kontrolu        : "
        f"{stop_token_trained}"
    )
    print()

    im_end_token = "<|im_end|>"

    im_end_id = tokenizer.convert_tokens_to_ids(
        im_end_token
    )

    if im_end_id is None:
        raise RuntimeError(
            "<|im_end|> token ID bulunamadi."
        )

    over_limit_examples = []
    length_mismatch_examples = []
    no_assistant_mask_examples = []
    no_assistant_after_truncation = []
    im_end_count_mismatch_examples = []

    assistant_im_end_mask_errors = []
    nonassistant_im_end_mask_errors = []

    truncation_lost_assistant_end = []
    truncation_ends_inside_assistant = []

    token_lengths = []
    assistant_token_counts = []
    truncated_assistant_token_counts = []

    report_details = []

    for example_no, row in enumerate(
        rows,
        start=1,
    ):
        messages = row["messages"]

        processed = _tokenize(
            tokenizer,
            messages,
            return_assistant_tokens_mask=True,
            chat_template=training_chat_template,
        )

        input_ids = list(
            processed["input_ids"]
        )

        if "assistant_masks" not in processed:
            no_assistant_mask_examples.append(
                example_no
            )
            continue

        assistant_masks = list(
            processed["assistant_masks"]
        )

        if len(input_ids) != len(
            assistant_masks
        ):
            length_mismatch_examples.append(
                example_no
            )
            continue

        full_length = len(input_ids)

        assistant_token_count = sum(
            assistant_masks
        )

        token_lengths.append(
            (example_no, full_length)
        )

        assistant_token_counts.append(
            (
                example_no,
                assistant_token_count,
            )
        )

        if assistant_token_count == 0:
            no_assistant_mask_examples.append(
                example_no
            )

        im_end_positions = [
            index
            for index, token_id in enumerate(
                input_ids
            )
            if token_id == im_end_id
        ]

        if len(im_end_positions) != len(
            messages
        ):
            im_end_count_mismatch_examples.append(
                (
                    example_no,
                    len(messages),
                    len(im_end_positions),
                )
            )

        mapped_turns = min(
            len(messages),
            len(im_end_positions),
        )

        lost_assistant_end_positions = []

        for turn_index in range(
            mapped_turns
        ):
            message = messages[turn_index]
            position = im_end_positions[
                turn_index
            ]

            mask_bit = assistant_masks[
                position
            ]

            role = message["role"]

            if role == "assistant":
                if mask_bit != 1:
                    assistant_im_end_mask_errors.append(
                        (
                            example_no,
                            turn_index,
                            position,
                        )
                    )

                if position >= MAX_LENGTH:
                    lost_assistant_end_positions.append(
                        (
                            turn_index,
                            position,
                        )
                    )

            else:
                if mask_bit != 0:
                    nonassistant_im_end_mask_errors.append(
                        (
                            example_no,
                            turn_index,
                            role,
                            position,
                        )
                    )

        if full_length > MAX_LENGTH:
            over_limit_examples.append(
                (
                    example_no,
                    full_length,
                )
            )

        truncated_ids = input_ids[
            :MAX_LENGTH
        ]

        truncated_masks = assistant_masks[
            :MAX_LENGTH
        ]

        truncated_assistant_tokens = sum(
            truncated_masks
        )

        truncated_assistant_token_counts.append(
            (
                example_no,
                truncated_assistant_tokens,
            )
        )

        if truncated_assistant_tokens == 0:
            no_assistant_after_truncation.append(
                example_no
            )

        if lost_assistant_end_positions:
            truncation_lost_assistant_end.append(
                (
                    example_no,
                    full_length,
                    lost_assistant_end_positions,
                )
            )

        ends_inside_assistant = False

        if full_length > MAX_LENGTH:
            if truncated_masks:
                last_mask_bit = (
                    truncated_masks[-1]
                )

                last_token_id = (
                    truncated_ids[-1]
                )

                if (
                    last_mask_bit == 1
                    and last_token_id != im_end_id
                ):
                    ends_inside_assistant = True

        if ends_inside_assistant:
            truncation_ends_inside_assistant.append(
                (
                    example_no,
                    full_length,
                )
            )

        anomalies = []

        if full_length > MAX_LENGTH:
            anomalies.append(
                f"OVER_LIMIT={full_length}"
            )

        if lost_assistant_end_positions:
            anomalies.append(
                "ASSISTANT_END_CUT"
            )

        if ends_inside_assistant:
            anomalies.append(
                "CUT_INSIDE_ASSISTANT"
            )

        if truncated_assistant_tokens == 0:
            anomalies.append(
                "NO_ASSISTANT_AFTER_TRUNC"
            )

        if anomalies:
            report_details.append(
                {
                    "example_no": example_no,
                    "tokens": full_length,
                    "assistant_tokens": (
                        assistant_token_count
                    ),
                    "assistant_tokens_after_trunc": (
                        truncated_assistant_tokens
                    ),
                    "issues": anomalies,
                }
            )

    if token_lengths:
        longest_example = max(
            token_lengths,
            key=lambda item: item[1],
        )

        shortest_example = min(
            token_lengths,
            key=lambda item: item[1],
        )
    else:
        longest_example = (None, 0)
        shortest_example = (None, 0)

    total_examples = len(rows)

    print()
    print("=" * 90)
    print("OZET")
    print("=" * 90)

    print(
        f"Toplam gold ornegi                    : "
        f"{total_examples}"
    )

    print(
        f"2048 tokeni asan                      : "
        f"{len(over_limit_examples)}"
    )

    print(
        f"input_ids / mask uzunluk hatasi        : "
        f"{len(length_mismatch_examples)}"
    )

    print(
        f"Assistant mask olmayan / bos           : "
        f"{len(no_assistant_mask_examples)}"
    )

    print(
        f"Truncation sonrasi assistant tokeni 0  : "
        f"{len(no_assistant_after_truncation)}"
    )

    print(
        f"Mesaj / im_end sayisi uyusmayan        : "
        f"{len(im_end_count_mismatch_examples)}"
    )

    print(
        f"Assistant im_end LOSS disi             : "
        f"{len(assistant_im_end_mask_errors)}"
    )

    print(
        f"System/user im_end LOSS icinde          : "
        f"{len(nonassistant_im_end_mask_errors)}"
    )

    print(
        f"Truncation assistant im_end kesiyor     : "
        f"{len(truncation_lost_assistant_end)}"
    )

    print(
        f"Truncation assistant cevabinin icinde   : "
        f"{len(truncation_ends_inside_assistant)}"
    )

    print(
        f"En uzun ornek                          : "
        f"{longest_example[0]} "
        f"({longest_example[1]} token)"
    )

    print(
        f"En kisa ornek                          : "
        f"{shortest_example[0]} "
        f"({shortest_example[1]} token)"
    )

    print()
    print("2048 USTU ORNEKLER")
    print("-" * 90)

    if over_limit_examples:
        for example_no, length in (
            over_limit_examples
        ):
            print(
                f"Ornek {example_no}: "
                f"{length} token"
            )
    else:
        print("YOK")

    print()
    print("ASSISTANT END KESILEN ORNEKLER")
    print("-" * 90)

    if truncation_lost_assistant_end:
        for (
            example_no,
            length,
            positions,
        ) in truncation_lost_assistant_end:
            print(
                f"Ornek {example_no}: "
                f"{length} token | "
                f"{positions}"
            )
    else:
        print("YOK")

    print()
    print("ASSISTANT ICINDE KESILEN ORNEKLER")
    print("-" * 90)

    if truncation_ends_inside_assistant:
        for (
            example_no,
            length,
        ) in truncation_ends_inside_assistant:
            print(
                f"Ornek {example_no}: "
                f"{length} token"
            )
    else:
        print("YOK")

    report_lines = [
        "=" * 90,
        "EDUCOACH TUM GOLD MASK / TRUNCATION DENETIMI",
        "=" * 90,
        "",
        f"Gold              : {GOLD_FILE}",
        f"Ornek             : {total_examples}",
        f"Max length        : {MAX_LENGTH}",
        f"Template          : {template_source}",
        (
            "Generation marker : "
            f"{patched_has_generation_markers}"
        ),
        (
            "Stop-token trained: "
            f"{stop_token_trained}"
        ),
        "",
        "OZET",
        "-" * 90,
        (
            "2048 tokeni asan                     : "
            f"{len(over_limit_examples)}"
        ),
        (
            "input_ids / mask uzunluk hatasi       : "
            f"{len(length_mismatch_examples)}"
        ),
        (
            "Assistant mask olmayan / bos          : "
            f"{len(no_assistant_mask_examples)}"
        ),
        (
            "Truncation sonrasi assistant tokeni 0 : "
            f"{len(no_assistant_after_truncation)}"
        ),
        (
            "Mesaj / im_end sayisi uyusmayan       : "
            f"{len(im_end_count_mismatch_examples)}"
        ),
        (
            "Assistant im_end LOSS disi            : "
            f"{len(assistant_im_end_mask_errors)}"
        ),
        (
            "System/user im_end LOSS icinde         : "
            f"{len(nonassistant_im_end_mask_errors)}"
        ),
        (
            "Truncation assistant im_end kesiyor    : "
            f"{len(truncation_lost_assistant_end)}"
        ),
        (
            "Truncation assistant cevabinin icinde  : "
            f"{len(truncation_ends_inside_assistant)}"
        ),
        (
            "En uzun ornek                         : "
            f"{longest_example[0]} "
            f"({longest_example[1]} token)"
        ),
        (
            "En kisa ornek                         : "
            f"{shortest_example[0]} "
            f"({shortest_example[1]} token)"
        ),
        "",
        "DETAYLAR",
        "-" * 90,
    ]

    if report_details:
        for item in report_details:
            report_lines.append(
                (
                    f"Ornek {item['example_no']} | "
                    f"tokens={item['tokens']} | "
                    f"assistant={item['assistant_tokens']} | "
                    f"assistant_after_trunc="
                    f"{item['assistant_tokens_after_trunc']} | "
                    f"issues={','.join(item['issues'])}"
                )
            )
    else:
        report_lines.append(
            "Anomali bulunmadi."
        )

    report_lines.extend(
        [
            "",
            "MASK HATALARI",
            "-" * 90,
            (
                "Length mismatch: "
                f"{length_mismatch_examples}"
            ),
            (
                "No assistant mask: "
                f"{no_assistant_mask_examples}"
            ),
            (
                "No assistant after truncation: "
                f"{no_assistant_after_truncation}"
            ),
            (
                "im_end count mismatch: "
                f"{im_end_count_mismatch_examples}"
            ),
            (
                "Assistant im_end errors: "
                f"{assistant_im_end_mask_errors}"
            ),
            (
                "Non-assistant im_end errors: "
                f"{nonassistant_im_end_mask_errors}"
            ),
            (
                "Assistant end cut: "
                f"{truncation_lost_assistant_end}"
            ),
            (
                "Cut inside assistant: "
                f"{truncation_ends_inside_assistant}"
            ),
            "",
        ]
    )

    REPORT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_FILE.write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    print()
    print(f"Rapor: {REPORT_FILE}")
    print()
    print("=" * 90)
    print("DENETIM TAMAMLANDI")
    print("=" * 90)


if __name__ == "__main__":
    main()