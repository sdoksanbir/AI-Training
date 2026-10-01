import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


ROOT = Path(__file__).resolve().parent.parent

BENCHMARK_FILE = (
    ROOT
    / "evaluations"
    / "holdout"
    / "benchmark_v0.2.jsonl"
)

OUTPUT_FILE = (
    ROOT
    / "evaluations"
    / "holdout"
    / "qwen3_4b_hf_training_system_v0.2.jsonl"
)

TRAINING_DATA_FILE = (
    ROOT
    / "data"
    / "gold"
    / "gold_v0.4.jsonl"
)

MODEL = "Qwen/Qwen3-4B"


def load_tests():
    with BENCHMARK_FILE.open("r", encoding="utf-8") as f:
        return [
            json.loads(line)
            for line in f
            if line.strip()
        ]


def load_training_system_prompt():
    with TRAINING_DATA_FILE.open("r", encoding="utf-8") as f:
        first_line = next(
            line
            for line in f
            if line.strip()
        )

    first_example = json.loads(first_line)

    messages = first_example["messages"]

    if not messages:
        raise ValueError(
            "Ilk egitim orneginde messages bos."
        )

    if messages[0].get("role") != "system":
        raise ValueError(
            "Ilk egitim orneginin ilk mesaji system degil."
        )

    system_prompt = messages[0].get("content", "").strip()

    if not system_prompt:
        raise ValueError(
            "Egitim system prompt bos."
        )

    return system_prompt


def main():
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU bulunamadi.")

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("Tokenizer yukleniyor...")

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL,
        trust_remote_code=True,
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print("Temel model yukleniyor...")

    model = AutoModelForCausalLM.from_pretrained(
        MODEL,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )

    model.eval()

    tests = load_tests()
    system_prompt = load_training_system_prompt()

    print(f"Toplam benchmark: {len(tests)}")
    print(
        f"Egitim system prompt karakter: "
        f"{len(system_prompt)}"
    )

    results = []

    for index, test in enumerate(tests, start=1):
        print(
            f"[{index}/{len(tests)}] "
            f"{test['id']} - {test['category']}"
        )

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": test["user"],
            },
        ]

        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )

        inputs = tokenizer(
            text,
            return_tensors="pt",
        ).to(model.device)

        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=300,
                do_sample=False,
                temperature=None,
                top_p=None,
            )

        generated_ids = output_ids[
            0,
            inputs["input_ids"].shape[1]:,
        ]

        answer = tokenizer.decode(
            generated_ids,
            skip_special_tokens=True,
        ).strip()

        result = {
            "id": test["id"],
            "category": test["category"],
            "user": test["user"],
            "model": MODEL,
            "system_prompt_source": "gold_v0.4",
            "assistant": answer,
        }

        results.append(result)

        print("  OK")

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as f:
        for result in results:
            json.dump(
                result,
                f,
                ensure_ascii=False,
            )
            f.write("\n")

    print()
    print(
        "HF training-system benchmark tamamlandi."
    )
    print(f"Cikti: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()