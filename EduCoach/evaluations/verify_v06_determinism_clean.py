import json
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

REPORT_FILE = (
    ROOT
    / "evaluations"
    / "reports"
    / "h002_v06_clean_determinism.txt"
)

TARGET_ID = "H002"
MAX_NEW_TOKENS = 300


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


def get_scaling_values(
    model,
) -> list[float]:
    values = []

    for module in model.modules():
        if not isinstance(
            module,
            LoraLayer,
        ):
            continue

        for adapter_name in (
            module.active_adapters
        ):
            if (
                adapter_name
                not in module.scaling
            ):
                continue

            values.append(
                float(
                    module.scaling[
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
        outputs = model.generate(
            **model_inputs,
            max_new_tokens=(
                MAX_NEW_TOKENS
            ),
            do_sample=False,
            temperature=None,
            top_p=None,
            return_dict_in_generate=True,
            output_scores=True,
        )

    prompt_length = (
        model_inputs[
            "input_ids"
        ].shape[1]
    )

    generated_ids = (
        outputs.sequences[
            0,
            prompt_length:,
        ]
        .tolist()
    )

    text = tokenizer.decode(
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
        index
        for index, token_id
        in enumerate(generated_ids)
        if token_id == im_end_id
    ]

    return {
        "ids": generated_ids,
        "text": text,
        "count": len(
            generated_ids
        ),
        "im_end_positions": (
            im_end_positions
        ),
        "hit_cap": (
            len(generated_ids)
            >= MAX_NEW_TOKENS
        ),
    }


def main():
    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA bulunamadi."
        )

    if not ADAPTER_PATH.exists():
        raise FileNotFoundError(
            f"Adapter yok: "
            f"{ADAPTER_PATH}"
        )

    if not REFERENCE_FILE.exists():
        raise FileNotFoundError(
            f"Referans JSON yok: "
            f"{REFERENCE_FILE}"
        )

    print("=" * 90)
    print(
        "V06 FINAL CLEAN DETERMINISM DENETIMI"
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

    print()
    print(
        "Temel model yukleniyor..."
    )

    base_model = (
        AutoModelForCausalLM
        .from_pretrained(
            BASE_MODEL,
            torch_dtype=torch.bfloat16,
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

    scaling_values = (
        get_scaling_values(
            model
        )
    )

    print(
        f"LoRA scaling: "
        f"{scaling_values}"
    )

    print()
    print(
        "RUN 1 basliyor..."
    )

    run1 = generate_once(
        model,
        tokenizer,
        inputs,
    )

    print(
        f"RUN 1 token        : "
        f"{run1['count']}"
    )

    print(
        f"RUN 1 im_end       : "
        f"{run1['im_end_positions']}"
    )

    print(
        f"RUN 1 300 cap      : "
        f"{run1['hit_cap']}"
    )

    print()
    print(
        "RUN 2 basliyor..."
    )

    run2 = generate_once(
        model,
        tokenizer,
        inputs,
    )

    print(
        f"RUN 2 token        : "
        f"{run2['count']}"
    )

    print(
        f"RUN 2 im_end       : "
        f"{run2['im_end_positions']}"
    )

    print(
        f"RUN 2 300 cap      : "
        f"{run2['hit_cap']}"
    )

    same_runs = (
        run1["ids"]
        == run2["ids"]
    )

    run_diff = first_difference(
        run1["ids"],
        run2["ids"],
    )

    print()
    print(
        f"RUN1 == RUN2       : "
        f"{same_runs}"
    )

    print(
        f"Ilk fark step      : "
        f"{run_diff}"
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

    run1_vs_reference = (
        run1["ids"]
        == reference_ids
    )

    run2_vs_reference = (
        run2["ids"]
        == reference_ids
    )

    ref_diff1 = first_difference(
        run1["ids"],
        reference_ids,
    )

    ref_diff2 = first_difference(
        run2["ids"],
        reference_ids,
    )

    print()
    print(
        "REFERANS KARSILASTIRMASI"
    )
    print("-" * 90)

    print(
        f"Referans token      : "
        f"{len(reference_ids)}"
    )

    print(
        f"RUN1 == referans    : "
        f"{run1_vs_reference}"
    )

    print(
        f"RUN1 ilk fark       : "
        f"{ref_diff1}"
    )

    print(
        f"RUN2 == referans    : "
        f"{run2_vs_reference}"
    )

    print(
        f"RUN2 ilk fark       : "
        f"{ref_diff2}"
    )

    report_lines = [
        "=" * 90,
        "V06 FINAL CLEAN DETERMINISM DENETIMI",
        "=" * 90,
        "",
        f"GPU               : "
        f"{torch.cuda.get_device_name(0)}",
        f"LoRA scaling      : "
        f"{scaling_values}",
        "",
        "RUN 1",
        "-" * 90,
        f"Token             : "
        f"{run1['count']}",
        f"im_end positions  : "
        f"{run1['im_end_positions']}",
        f"300 cap           : "
        f"{run1['hit_cap']}",
        "",
        "RUN 2",
        "-" * 90,
        f"Token             : "
        f"{run2['count']}",
        f"im_end positions  : "
        f"{run2['im_end_positions']}",
        f"300 cap           : "
        f"{run2['hit_cap']}",
        "",
        "DETERMINISM",
        "-" * 90,
        f"RUN1 == RUN2      : "
        f"{same_runs}",
        f"Ilk fark step     : "
        f"{run_diff}",
        "",
        "REFERANS",
        "-" * 90,
        f"Referans token    : "
        f"{len(reference_ids)}",
        f"RUN1 == referans  : "
        f"{run1_vs_reference}",
        f"RUN1 ilk fark     : "
        f"{ref_diff1}",
        f"RUN2 == referans  : "
        f"{run2_vs_reference}",
        f"RUN2 ilk fark     : "
        f"{ref_diff2}",
        "",
        "RUN 1 CEVAP",
        "-" * 90,
        run1["text"],
        "",
        "RUN 2 CEVAP",
        "-" * 90,
        run2["text"],
        "",
    ]

    REPORT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_FILE.write_text(
        "\n".join(
            report_lines
        ),
        encoding="utf-8",
    )

    print()
    print(
        f"Rapor: "
        f"{REPORT_FILE}"
    )

    print()
    print("=" * 90)
    print(
        "DENETIM TAMAMLANDI"
    )
    print("=" * 90)


if __name__ == "__main__":
    main()