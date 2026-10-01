import json
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parent.parent

BENCHMARK_FILE = ROOT / "evaluations" / "holdout" / "benchmark_v0.2.jsonl"
OUTPUT_FILE = ROOT / "evaluations" / "post_training" / "educoach_v0.2_checkpoint15_results.jsonl"

BASE_MODEL = "Qwen/Qwen3-4B"
ADAPTER_PATH = (
    ROOT
    / "training"
    / "outputs"
    / "qwen3_4b_qlora_v02"
    / "checkpoint-15"
)
TRAINING_DATA_FILE = ROOT / "data" / "gold" / "gold_v0.4.jsonl"

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


def load_tests():
    with BENCHMARK_FILE.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU bulunamadi.")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    print("Tokenizer yukleniyor...")

    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL,
        trust_remote_code=True,
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print("Temel model yukleniyor...")

    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )

    print("EduCoach LoRA adapter yukleniyor...")

    model = PeftModel.from_pretrained(
        base_model,
        str(ADAPTER_PATH),
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
        print(f"[{index}/{len(tests)}] {test['id']} - {test['category']}")

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
            "model": "EduCoach-v0.2-checkpoint15",
            "base_model": BASE_MODEL,
            "adapter": str(ADAPTER_PATH),
            "assistant": answer,
        }

        results.append(result)

        print("  OK")

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        for result in results:
            json.dump(
                result,
                f,
                ensure_ascii=False,
            )
            f.write("\n")

    print()
    print("Post-training benchmark tamamlandi.")
    print(f"Cikti: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()