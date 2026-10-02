import json
import re
from collections import Counter
from pathlib import Path

import torch
from peft import PeftModel
from peft.tuners.lora.layer import LoraLayer
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
)


ROOT = Path(__file__).resolve().parents[1]

BASE_MODEL = "Qwen/Qwen3-4B"

ADAPTER_PATH = (
    ROOT
    / "training"
    / "outputs"
    / "qwen3_4b_qlora_v06"
)

BENCHMARK_FILE = (
    ROOT
    / "evaluations"
    / "holdout"
    / "benchmark_v0.2.jsonl"
)

TRAINING_DATA_FILE = (
    ROOT
    / "data"
    / "gold"
    / "gold_v0.5.jsonl"
)

REFERENCE_FILE = (
    ROOT
    / "evaluations"
    / "reports"
    / "h002_token_probability_diagnostic.json"
)

REPORT_TXT = (
    ROOT
    / "evaluations"
    / "reports"
    / "h002_lora_scale_diagnostic_clean.txt"
)

REPORT_JSON = (
    ROOT
    / "evaluations"
    / "reports"
    / "h002_lora_scale_diagnostic_clean.json"
)

TARGET_ID = "H002"
MAX_NEW_TOKENS = 300

# Ilk ve son %100 kontrol.
TEST_SEQUENCE = [
    ("LORA_100_FIRST", 1.00),
    ("LORA_75", 0.75),
    ("LORA_50", 0.50),
    ("LORA_25", 0.25),
    ("LORA_100_FINAL", 1.00),
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


def load_system_prompt() -> str:
    rows = load_jsonl(
        TRAINING_DATA_FILE
    )

    for message in rows[0]["messages"]:
        if message["role"] == "system":
            return message["content"]

    raise RuntimeError(
        "System prompt bulunamadi."
    )


def load_target() -> dict:
    rows = load_jsonl(
        BENCHMARK_FILE
    )

    for row in rows:
        if row["id"] == TARGET_ID:
            return row

    raise RuntimeError(
        f"{TARGET_ID} bulunamadi."
    )


def normalize_text(
    text: str,
) -> str:
    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def extract_words(
    text: str,
) -> list[str]:
    return re.findall(
        r"[0-9a-zA-ZçğıöşüÇĞİÖŞÜ]+",
        normalize_text(text),
    )


def repeated_ngram_stats(
    text: str,
) -> dict:
    token_words = extract_words(
        text
    )

    best = {
        "ngram_size": 0,
        "coverage": 0.0,
        "max_count": 0,
        "example": "",
    }

    if len(token_words) < 5:
        return best

    for n in range(5, 9):
        if len(token_words) < n:
            continue

        grams = [
            tuple(
                token_words[i:i + n]
            )
            for i in range(
                len(token_words) - n + 1
            )
        ]

        counts = Counter(
            grams
        )

        repeated = {
            gram: count
            for gram, count
            in counts.items()
            if count >= 2
        }

        if not repeated:
            continue

        covered_positions = set()

        for i, gram in enumerate(
            grams
        ):
            if gram not in repeated:
                continue

            covered_positions.update(
                range(
                    i,
                    min(
                        i + n,
                        len(token_words),
                    ),
                )
            )

        coverage = (
            len(covered_positions)
            / len(token_words)
        )

        max_gram, max_count = max(
            repeated.items(),
            key=lambda item: item[1],
        )

        candidate = {
            "ngram_size": n,
            "coverage": coverage,
            "max_count": max_count,
            "example": " ".join(
                max_gram
            ),
        }

        if (
            candidate["coverage"]
            > best["coverage"]
            or (
                candidate["coverage"]
                == best["coverage"]
                and candidate[
                    "max_count"
                ]
                > best["max_count"]
            )
        ):
            best = candidate

    return best


def is_loop_candidate(
    text: str,
) -> tuple[bool, dict]:
    stats = repeated_ngram_stats(
        text
    )

    loop = (
        stats["max_count"] >= 3
        or (
            stats["max_count"] >= 2
            and stats["coverage"] >= 0.20
        )
    )

    return loop, stats


def get_lora_layers(
    model,
) -> list[LoraLayer]:
    return [
        module
        for module in model.modules()
        if isinstance(
            module,
            LoraLayer,
        )
    ]


def reset_lora(
    layers: list[LoraLayer],
):
    for layer in layers:
        layer.unscale_layer()


def set_lora_factor(
    layers: list[LoraLayer],
    factor: float,
):
    # Her deney once orijinal
    # alpha/r scaling'ine doner.
    reset_lora(
        layers
    )

    # %100 icin ek carpma yok.
    if factor == 1.0:
        return

    for layer in layers:
        layer.scale_layer(
            factor
        )


def get_scaling_snapshot(
    layers: list[LoraLayer],
) -> list[float]:
    values = []

    for layer in layers:
        for adapter_name in (
            layer.active_adapters
        ):
            if (
                adapter_name
                not in layer.scaling
            ):
                continue

            values.append(
                float(
                    layer.scaling[
                        adapter_name
                    ]
                )
            )

    return sorted(
        set(values)
    )


def first_difference(
    left: list[int],
    right: list[int],
):
    limit = min(
        len(left),
        len(right),
    )

    for index in range(limit):
        if left[index] != right[index]:
            return index

    if len(left) != len(right):
        return limit

    return None


def generate_once(
    model,
    tokenizer,
    inputs,
) -> dict:
    model_inputs = {
        key: value.to(
            model.device
        )
        for key, value
        in inputs.items()
    }

    with torch.no_grad():
        output = model.generate(
            **model_inputs,
            max_new_tokens=(
                MAX_NEW_TOKENS
            ),
            do_sample=False,
            temperature=None,
            top_p=None,
        )

    prompt_length = (
        model_inputs[
            "input_ids"
        ].shape[1]
    )

    generated_ids = (
        output[
            0,
            prompt_length:,
        ]
        .tolist()
    )

    answer = tokenizer.decode(
        generated_ids,
        skip_special_tokens=True,
    ).strip()

    im_end_id = (
        tokenizer
        .convert_tokens_to_ids(
            "<|im_end|>"
        )
    )

    im_end_positions = [
        i
        for i, token_id
        in enumerate(generated_ids)
        if token_id == im_end_id
    ]

    loop, loop_stats = (
        is_loop_candidate(
            answer
        )
    )

    return {
        "generated_ids": (
            generated_ids
        ),
        "assistant": answer,
        "generated_tokens": (
            len(generated_ids)
        ),
        "hit_max_new_tokens": (
            len(generated_ids)
            >= MAX_NEW_TOKENS
        ),
        "im_end_positions": (
            im_end_positions
        ),
        "im_end_count": (
            len(im_end_positions)
        ),
        "loop": loop,
        "ngram_size": (
            loop_stats[
                "ngram_size"
            ]
        ),
        "coverage": round(
            loop_stats[
                "coverage"
            ],
            4,
        ),
        "max_count": (
            loop_stats[
                "max_count"
            ]
        ),
        "repeat_example": (
            loop_stats[
                "example"
            ]
        ),
    }


def main():
    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA bulunamadi."
        )

    if not ADAPTER_PATH.exists():
        raise FileNotFoundError(
            f"Adapter bulunamadi: "
            f"{ADAPTER_PATH}"
        )

    if not REFERENCE_FILE.exists():
        raise FileNotFoundError(
            f"Referans bulunamadi: "
            f"{REFERENCE_FILE}"
        )

    print("=" * 90)
    print(
        "H002 CLEAN LORA SCALE DIAGNOSTIC"
    )
    print("=" * 90)

    print(
        f"GPU: "
        f"{torch.cuda.get_device_name(0)}"
    )

    tokenizer = (
        AutoTokenizer.from_pretrained(
            BASE_MODEL,
            trust_remote_code=True,
        )
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = (
            tokenizer.eos_token
        )

    target = load_target()

    system_prompt = (
        load_system_prompt()
    )

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": (
                target["user"]
            ),
        },
    ]

    prompt_text = (
        tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
    )

    inputs = tokenizer(
        prompt_text,
        return_tensors="pt",
    )

    reference_data = json.loads(
        REFERENCE_FILE.read_text(
            encoding="utf-8"
        )
    )

    reference_ids = (
        reference_data[
            "models"
        ][
            "V06_FINAL"
        ][
            "generated_ids"
        ]
    )

    print()
    print(
        f"Referans token sayisi: "
        f"{len(reference_ids)}"
    )

    print()
    print(
        "V06 temel model yukleniyor..."
    )

    base_model = (
        AutoModelForCausalLM
        .from_pretrained(
            BASE_MODEL,
            dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
        )
    )

    print(
        f"Adapter yukleniyor: "
        f"{ADAPTER_PATH}"
    )

    model = (
        PeftModel.from_pretrained(
            base_model,
            str(ADAPTER_PATH),
        )
    )

    model.eval()

    lora_layers = (
        get_lora_layers(
            model
        )
    )

    if not lora_layers:
        raise RuntimeError(
            "LoRA layer bulunamadi."
        )

    print(
        f"LoRA layer sayisi: "
        f"{len(lora_layers)}"
    )

    reset_lora(
        lora_layers
    )

    original_scaling = (
        get_scaling_snapshot(
            lora_layers
        )
    )

    print(
        f"Orijinal scaling: "
        f"{original_scaling}"
    )

    results = {}

    first_100_ids = None

    for name, factor in TEST_SEQUENCE:
        print()
        print("=" * 90)
        print(
            f"{name} | factor={factor}"
        )
        print("=" * 90)

        set_lora_factor(
            lora_layers,
            factor,
        )

        scaling = (
            get_scaling_snapshot(
                lora_layers
            )
        )

        print(
            f"Aktif scaling     : "
            f"{scaling}"
        )

        result = generate_once(
            model,
            tokenizer,
            inputs,
        )

        result[
            "factor"
        ] = factor

        result[
            "scaling"
        ] = scaling

        result[
            "matches_reference"
        ] = (
            result[
                "generated_ids"
            ]
            == reference_ids
        )

        result[
            "reference_first_diff"
        ] = first_difference(
            result[
                "generated_ids"
            ],
            reference_ids,
        )

        if name == "LORA_100_FIRST":
            first_100_ids = list(
                result[
                    "generated_ids"
                ]
            )

            result[
                "matches_first_100"
            ] = True

            result[
                "first_100_diff"
            ] = None

        else:
            result[
                "matches_first_100"
            ] = (
                result[
                    "generated_ids"
                ]
                == first_100_ids
            )

            result[
                "first_100_diff"
            ] = first_difference(
                result[
                    "generated_ids"
                ],
                first_100_ids,
            )

        results[name] = result

        print(
            f"Generated token   : "
            f"{result['generated_tokens']}"
        )

        print(
            f"300 limite vurdu : "
            f"{result['hit_max_new_tokens']}"
        )

        print(
            f"im_end positions : "
            f"{result['im_end_positions']}"
        )

        print(
            f"Loop             : "
            f"{result['loop']}"
        )

        print(
            f"Ngram            : "
            f"{result['ngram_size']}"
        )

        print(
            f"Coverage         : "
            f"{result['coverage']}"
        )

        print(
            f"Repeat count     : "
            f"{result['max_count']}"
        )

        print(
            f"Referansla ayni  : "
            f"{result['matches_reference']}"
        )

        print(
            f"Referans ilk fark: "
            f"{result['reference_first_diff']}"
        )

        if name != "LORA_100_FIRST":
            print(
                f"Ilk %100 ile ayni: "
                f"{result['matches_first_100']}"
            )

            print(
                f"Ilk %100 ilk fark: "
                f"{result['first_100_diff']}"
            )

    reset_lora(
        lora_layers
    )

    final_reset_scaling = (
        get_scaling_snapshot(
            lora_layers
        )
    )

    print()
    print("=" * 90)
    print("KONTROL OZETI")
    print("=" * 90)

    first_ok = (
        results[
            "LORA_100_FIRST"
        ][
            "matches_reference"
        ]
    )

    final_ok = (
        results[
            "LORA_100_FINAL"
        ][
            "matches_first_100"
        ]
    )

    final_ref_ok = (
        results[
            "LORA_100_FINAL"
        ][
            "matches_reference"
        ]
    )

    print(
        f"Ilk %100 == referans : "
        f"{first_ok}"
    )

    print(
        f"Son %100 == ilk %100 : "
        f"{final_ok}"
    )

    print(
        f"Son %100 == referans : "
        f"{final_ref_ok}"
    )

    print(
        f"Test sonrasi scaling : "
        f"{final_reset_scaling}"
    )

    scale_test_valid = (
        first_ok
        and final_ok
        and final_ref_ok
    )

    print(
        f"SCALE TEST GECERLI    : "
        f"{scale_test_valid}"
    )

    report_lines = [
        "=" * 100,
        "H002 CLEAN LORA SCALE DIAGNOSTIC",
        "=" * 100,
        "",
        f"GPU: "
        f"{torch.cuda.get_device_name(0)}",
        f"Reference tokens: "
        f"{len(reference_ids)}",
        f"Original scaling: "
        f"{original_scaling}",
        "",
        "KONTROL",
        "-" * 100,
        f"Ilk %100 == referans : "
        f"{first_ok}",
        f"Son %100 == ilk %100 : "
        f"{final_ok}",
        f"Son %100 == referans : "
        f"{final_ref_ok}",
        f"Scale test gecerli   : "
        f"{scale_test_valid}",
        "",
    ]

    for name, _ in TEST_SEQUENCE:
        result = results[name]

        report_lines.extend(
            [
                "=" * 100,
                name,
                "=" * 100,
                (
                    "Factor             : "
                    f"{result['factor']}"
                ),
                (
                    "Scaling            : "
                    f"{result['scaling']}"
                ),
                (
                    "Generated tokens   : "
                    f"{result['generated_tokens']}"
                ),
                (
                    "300 token cap      : "
                    f"{result['hit_max_new_tokens']}"
                ),
                (
                    "im_end positions   : "
                    f"{result['im_end_positions']}"
                ),
                (
                    "Loop               : "
                    f"{result['loop']}"
                ),
                (
                    "Ngram              : "
                    f"{result['ngram_size']}"
                ),
                (
                    "Coverage           : "
                    f"{result['coverage']}"
                ),
                (
                    "Repeat count       : "
                    f"{result['max_count']}"
                ),
                (
                    "Repeat example     : "
                    f"{result['repeat_example']}"
                ),
                (
                    "Matches reference  : "
                    f"{result['matches_reference']}"
                ),
                (
                    "Reference diff     : "
                    f"{result['reference_first_diff']}"
                ),
                (
                    "Matches first 100  : "
                    f"{result['matches_first_100']}"
                ),
                (
                    "First 100 diff     : "
                    f"{result['first_100_diff']}"
                ),
                "",
                "ASSISTANT",
                "-" * 100,
                result["assistant"],
                "",
            ]
        )

    REPORT_TXT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_TXT.write_text(
        "\n".join(
            report_lines
        ),
        encoding="utf-8",
    )

    REPORT_JSON.write_text(
        json.dumps(
            {
                "benchmark_id": (
                    TARGET_ID
                ),
                "reference_tokens": (
                    len(reference_ids)
                ),
                "original_scaling": (
                    original_scaling
                ),
                "final_reset_scaling": (
                    final_reset_scaling
                ),
                "scale_test_valid": (
                    scale_test_valid
                ),
                "results": (
                    results
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(
        f"TXT  : {REPORT_TXT}"
    )

    print(
        f"JSON : {REPORT_JSON}"
    )

    print()
    print("=" * 90)
    print(
        "DIAGNOSTIC TAMAMLANDI"
    )
    print("=" * 90)


if __name__ == "__main__":
    main()