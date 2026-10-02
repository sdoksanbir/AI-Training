import gc
import json
import math
from pathlib import Path

import torch
from peft import PeftModel
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
)


ROOT = Path(__file__).resolve().parents[1]

BASE_MODEL = "Qwen/Qwen3-4B"

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

REPORT_TXT = (
    ROOT
    / "evaluations"
    / "reports"
    / "h002_token_probability_diagnostic.txt"
)

REPORT_JSON = (
    ROOT
    / "evaluations"
    / "reports"
    / "h002_token_probability_diagnostic.json"
)

MAX_NEW_TOKENS = 300
TARGET_ID = "H002"


MODEL_CONFIGS = [
    {
        "name": "BASE",
        "adapter": None,
    },
    {
        "name": "V06_CHECKPOINT15",
        "adapter": (
            ROOT
            / "training"
            / "outputs"
            / "qwen3_4b_qlora_v06"
            / "checkpoint-15"
        ),
    },
    {
        "name": "V06_FINAL",
        "adapter": (
            ROOT
            / "training"
            / "outputs"
            / "qwen3_4b_qlora_v06"
        ),
    },
]


def load_jsonl(path: Path) -> list[dict]:
    rows = []

    for line in path.read_text(
        encoding="utf-8"
    ).splitlines():
        if line.strip():
            rows.append(json.loads(line))

    return rows


def load_system_prompt() -> str:
    rows = load_jsonl(
        TRAINING_DATA_FILE
    )

    first_messages = rows[0]["messages"]

    for message in first_messages:
        if message["role"] == "system":
            return message["content"]

    raise RuntimeError(
        "System prompt bulunamadi."
    )


def load_target_test() -> dict:
    rows = load_jsonl(
        BENCHMARK_FILE
    )

    for row in rows:
        if row["id"] == TARGET_ID:
            return row

    raise RuntimeError(
        f"{TARGET_ID} benchmarkta bulunamadi."
    )


def decode_token(
    tokenizer,
    token_id: int,
) -> str:
    text = tokenizer.decode(
        [token_id],
        skip_special_tokens=False,
    )

    return (
        text
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def find_first_repeated_token_ngram(
    token_ids: list[int],
    min_n: int = 4,
    max_n: int = 12,
):
    """
    Ilk kez daha once gorulmus bir token n-graminin
    tekrarlandigi generated-token step'ini bulur.

    Bu, behavior metric'teki kelime n-gram detectoru
    ile ayni sey degildir. Burada amac logit analizi
    icin tekrar baslangicina yakin token step'ini
    bulmaktir.
    """

    seen = {
        n: {}
        for n in range(
            min_n,
            max_n + 1,
        )
    }

    for end_index in range(
        len(token_ids)
    ):
        for n in range(
            min_n,
            max_n + 1,
        ):
            start = (
                end_index - n + 1
            )

            if start < 0:
                continue

            gram = tuple(
                token_ids[
                    start:end_index + 1
                ]
            )

            previous = seen[n].get(
                gram
            )

            if previous is not None:
                return {
                    "step": start,
                    "detected_at_step": (
                        end_index
                    ),
                    "ngram_size": n,
                    "previous_start": (
                        previous
                    ),
                    "token_ids": list(
                        gram
                    ),
                }

            seen[n][gram] = start

    return None


def calculate_step_stats(
    tokenizer,
    scores,
    generated_ids: list[int],
    im_end_id: int,
) -> list[dict]:
    stats = []

    for step, (
        score_tensor,
        chosen_id,
    ) in enumerate(
        zip(
            scores,
            generated_ids,
            strict=False,
        )
    ):
        logits = score_tensor[
            0
        ].float()

        log_probs = torch.log_softmax(
            logits,
            dim=-1,
        )

        chosen_log_prob = (
            log_probs[chosen_id].item()
        )

        chosen_prob = math.exp(
            chosen_log_prob
        )

        top_values, top_indices = (
            torch.topk(
                log_probs,
                k=2,
            )
        )

        top1_id = int(
            top_indices[0].item()
        )

        top2_id = int(
            top_indices[1].item()
        )

        top1_prob = math.exp(
            top_values[0].item()
        )

        top2_prob = math.exp(
            top_values[1].item()
        )

        probs = torch.exp(
            log_probs
        )

        entropy = float(
            -torch.sum(
                probs * log_probs
            ).item()
        )

        im_end_log_prob = (
            log_probs[im_end_id].item()
        )

        im_end_prob = math.exp(
            im_end_log_prob
        )

        im_end_logit = logits[
            im_end_id
        ]

        im_end_rank = int(
            (
                logits > im_end_logit
            ).sum().item()
            + 1
        )

        stats.append(
            {
                "step": step,
                "chosen_id": (
                    int(chosen_id)
                ),
                "chosen_token": (
                    decode_token(
                        tokenizer,
                        int(chosen_id),
                    )
                ),
                "chosen_prob": (
                    chosen_prob
                ),
                "top1_id": top1_id,
                "top1_token": (
                    decode_token(
                        tokenizer,
                        top1_id,
                    )
                ),
                "top1_prob": (
                    top1_prob
                ),
                "top2_id": top2_id,
                "top2_token": (
                    decode_token(
                        tokenizer,
                        top2_id,
                    )
                ),
                "top2_prob": (
                    top2_prob
                ),
                "top1_top2_margin": (
                    top1_prob
                    - top2_prob
                ),
                "entropy": entropy,
                "im_end_prob": (
                    im_end_prob
                ),
                "im_end_rank": (
                    im_end_rank
                ),
            }
        )

    return stats


def summarize_model(
    generated_ids: list[int],
    step_stats: list[dict],
    repeat_info,
    im_end_id: int,
) -> dict:
    generated_count = len(
        generated_ids
    )

    stopped_by_im_end = (
        bool(generated_ids)
        and generated_ids[-1]
        == im_end_id
    )

    if step_stats:
        avg_chosen_prob = sum(
            item["chosen_prob"]
            for item in step_stats
        ) / len(step_stats)

        avg_entropy = sum(
            item["entropy"]
            for item in step_stats
        ) / len(step_stats)

        avg_margin = sum(
            item["top1_top2_margin"]
            for item in step_stats
        ) / len(step_stats)

        max_im_end_prob = max(
            item["im_end_prob"]
            for item in step_stats
        )

        best_im_end_rank = min(
            item["im_end_rank"]
            for item in step_stats
        )
    else:
        avg_chosen_prob = 0.0
        avg_entropy = 0.0
        avg_margin = 0.0
        max_im_end_prob = 0.0
        best_im_end_rank = 0

    return {
        "generated_tokens": (
            generated_count
        ),
        "stopped_by_im_end": (
            stopped_by_im_end
        ),
        "hit_max_new_tokens": (
            generated_count
            >= MAX_NEW_TOKENS
        ),
        "avg_chosen_prob": (
            avg_chosen_prob
        ),
        "avg_entropy": (
            avg_entropy
        ),
        "avg_top1_top2_margin": (
            avg_margin
        ),
        "max_im_end_prob": (
            max_im_end_prob
        ),
        "best_im_end_rank": (
            best_im_end_rank
        ),
        "repeat_info": repeat_info,
    }


def append_window(
    lines: list[str],
    step_stats: list[dict],
    center_step: int | None,
    before: int = 8,
    after: int = 20,
):
    if not step_stats:
        lines.append(
            "Step verisi yok."
        )
        return

    if center_step is None:
        start = max(
            0,
            len(step_stats) - 25,
        )

        end = len(
            step_stats
        )
    else:
        start = max(
            0,
            center_step - before,
        )

        end = min(
            len(step_stats),
            center_step + after + 1,
        )

    lines.append(
        (
            "step | token | chosen_p | "
            "top2_p | margin | entropy | "
            "im_end_p | im_end_rank"
        )
    )

    lines.append(
        "-" * 125
    )

    for item in step_stats[
        start:end
    ]:
        marker = "   "

        if (
            center_step is not None
            and item["step"]
            == center_step
        ):
            marker = ">>>"

        token_text = (
            item["chosen_token"]
        )

        if len(token_text) > 26:
            token_text = (
                token_text[:23]
                + "..."
            )

        lines.append(
            (
                f"{marker} "
                f"{item['step']:03d} | "
                f"{token_text!r:<28} | "
                f"{item['chosen_prob']:.6f} | "
                f"{item['top2_prob']:.6f} | "
                f"{item['top1_top2_margin']:.6f} | "
                f"{item['entropy']:.4f} | "
                f"{item['im_end_prob']:.8f} | "
                f"{item['im_end_rank']}"
            )
        )


def load_model(
    adapter_path: Path | None,
):
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

    if adapter_path is None:
        model = base_model

    else:
        if not adapter_path.exists():
            raise FileNotFoundError(
                f"Adapter bulunamadi: "
                f"{adapter_path}"
            )

        print(
            f"Adapter yukleniyor: "
            f"{adapter_path}"
        )

        model = (
            PeftModel.from_pretrained(
                base_model,
                str(adapter_path),
            )
        )

    model.eval()

    return model


def unload_model(model):
    del model

    gc.collect()

    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def main():
    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA GPU bulunamadi."
        )

    if not BENCHMARK_FILE.exists():
        raise FileNotFoundError(
            f"Benchmark bulunamadi: "
            f"{BENCHMARK_FILE}"
        )

    if not TRAINING_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Gold bulunamadi: "
            f"{TRAINING_DATA_FILE}"
        )

    REPORT_TXT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 80)
    print(
        "H002 TOKEN OLASILIK DIAGNOSTIC"
    )
    print("=" * 80)

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

    target = load_target_test()

    system_prompt = (
        load_system_prompt()
    )

    print(
        f"Benchmark ID : {target['id']}"
    )

    print(
        f"Kategori     : "
        f"{target['category']}"
    )

    print(
        f"System chars : "
        f"{len(system_prompt)}"
    )

    print()

    messages = [
        {
            "role": "system",
            "content": (
                system_prompt
            ),
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

    im_end_token = "<|im_end|>"

    im_end_id = (
        tokenizer
        .convert_tokens_to_ids(
            im_end_token
        )
    )

    if im_end_id is None:
        raise RuntimeError(
            "<|im_end|> ID bulunamadi."
        )

    all_results = {}

    report_lines = [
        "=" * 100,
        "H002 TOKEN OLASILIK DIAGNOSTIC",
        "=" * 100,
        "",
        f"Benchmark ID : {target['id']}",
        f"Kategori     : {target['category']}",
        f"User         : {target['user']}",
        f"System chars : {len(system_prompt)}",
        f"Max new      : {MAX_NEW_TOKENS}",
        f"im_end ID    : {im_end_id}",
        "",
    ]

    for config in MODEL_CONFIGS:
        name = config["name"]

        adapter_path = (
            config["adapter"]
        )

        print()
        print("=" * 80)
        print(name)
        print("=" * 80)

        model = load_model(
            adapter_path
        )

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

        generated_tensor = (
            outputs.sequences[
                0,
                prompt_length:,
            ]
        )

        generated_ids = [
            int(token_id)
            for token_id
            in generated_tensor.tolist()
        ]

        generated_text = (
            tokenizer.decode(
                generated_ids,
                skip_special_tokens=True,
            ).strip()
        )

        repeat_info = (
            find_first_repeated_token_ngram(
                generated_ids
            )
        )

        step_stats = (
            calculate_step_stats(
                tokenizer,
                outputs.scores,
                generated_ids,
                im_end_id,
            )
        )

        summary = summarize_model(
            generated_ids,
            step_stats,
            repeat_info,
            im_end_id,
        )

        all_results[name] = {
            "adapter": (
                None
                if adapter_path
                is None
                else str(
                    adapter_path
                )
            ),
            "generated_text": (
                generated_text
            ),
            "generated_ids": (
                generated_ids
            ),
            "summary": summary,
            "steps": step_stats,
        }

        print(
            f"Generated token : "
            f"{summary['generated_tokens']}"
        )

        print(
            f"im_end ile durdu: "
            f"{summary['stopped_by_im_end']}"
        )

        print(
            f"300 limite vurdu: "
            f"{summary['hit_max_new_tokens']}"
        )

        print(
            "Ilk token tekrar : "
            f"{repeat_info}"
        )

        print(
            "Ort chosen prob  : "
            f"{summary['avg_chosen_prob']:.6f}"
        )

        print(
            "Ort entropy      : "
            f"{summary['avg_entropy']:.4f}"
        )

        print(
            "Ort top1-top2    : "
            f"{summary['avg_top1_top2_margin']:.6f}"
        )

        print(
            "Max im_end prob  : "
            f"{summary['max_im_end_prob']:.8f}"
        )

        print(
            "Best im_end rank : "
            f"{summary['best_im_end_rank']}"
        )

        report_lines.extend(
            [
                "=" * 100,
                name,
                "=" * 100,
                (
                    "Adapter             : "
                    f"{adapter_path}"
                ),
                (
                    "Generated tokens    : "
                    f"{summary['generated_tokens']}"
                ),
                (
                    "Stopped by im_end   : "
                    f"{summary['stopped_by_im_end']}"
                ),
                (
                    "Hit 300 token cap   : "
                    f"{summary['hit_max_new_tokens']}"
                ),
                (
                    "Avg chosen prob     : "
                    f"{summary['avg_chosen_prob']:.8f}"
                ),
                (
                    "Avg entropy         : "
                    f"{summary['avg_entropy']:.6f}"
                ),
                (
                    "Avg top1-top2 margin: "
                    f"{summary['avg_top1_top2_margin']:.8f}"
                ),
                (
                    "Max im_end prob     : "
                    f"{summary['max_im_end_prob']:.10f}"
                ),
                (
                    "Best im_end rank    : "
                    f"{summary['best_im_end_rank']}"
                ),
                (
                    "Repeat info         : "
                    f"{repeat_info}"
                ),
                "",
                "URETILEN CEVAP",
                "-" * 100,
                generated_text,
                "",
                "TEKRAR BASLANGICI CEVRESI",
                "-" * 100,
            ]
        )

        repeat_step = None

        if repeat_info is not None:
            repeat_step = (
                repeat_info["step"]
            )

            repeated_text = (
                tokenizer.decode(
                    repeat_info[
                        "token_ids"
                    ],
                    skip_special_tokens=False,
                )
            )

            report_lines.append(
                (
                    "Tekrar token dizisi: "
                    f"{repeated_text!r}"
                )
            )

            report_lines.append(
                (
                    "Onceki baslangic    : "
                    f"{repeat_info['previous_start']}"
                )
            )

            report_lines.append(
                (
                    "Yeni baslangic      : "
                    f"{repeat_info['step']}"
                )
            )

            report_lines.append(
                (
                    "Tespit step         : "
                    f"{repeat_info['detected_at_step']}"
                )
            )

            report_lines.append("")

        append_window(
            report_lines,
            step_stats,
            repeat_step,
        )

        report_lines.append("")
        report_lines.append("")

        unload_model(
            model
        )

    REPORT_JSON.write_text(
        json.dumps(
            {
                "benchmark_id": (
                    target["id"]
                ),
                "user": (
                    target["user"]
                ),
                "system_prompt_chars": (
                    len(system_prompt)
                ),
                "max_new_tokens": (
                    MAX_NEW_TOKENS
                ),
                "im_end_id": (
                    im_end_id
                ),
                "models": (
                    all_results
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    REPORT_TXT.write_text(
        "\n".join(
            report_lines
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print("DIAGNOSTIC TAMAMLANDI")
    print("=" * 80)
    print(
        f"TXT  : {REPORT_TXT}"
    )
    print(
        f"JSON : {REPORT_JSON}"
    )


if __name__ == "__main__":
    main()