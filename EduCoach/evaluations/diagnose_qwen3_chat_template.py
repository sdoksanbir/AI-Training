import json
from pathlib import Path

from transformers import AutoTokenizer


ROOT = Path(__file__).resolve().parent.parent

DATA_FILE = (
    ROOT
    / "data"
    / "gold"
    / "gold_v0.4.jsonl"
)

MODEL = "Qwen/Qwen3-4B"


def main():
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL,
        trust_remote_code=True,
    )

    with DATA_FILE.open("r", encoding="utf-8") as f:
        first_example = json.loads(
            next(line for line in f if line.strip())
        )

    messages = first_example["messages"]

    default_text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False,
    )

    no_thinking_text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False,
        enable_thinking=False,
    )

    template = tokenizer.chat_template or ""

    print("=" * 80)
    print("QWEN3 CHAT TEMPLATE TESHISI")
    print("=" * 80)
    print()

    print(
        "DEFAULT == THINKING_FALSE:",
        default_text == no_thinking_text,
    )

    print(
        "DEFAULT KARAKTER:",
        len(default_text),
    )

    print(
        "THINKING_FALSE KARAKTER:",
        len(no_thinking_text),
    )

    print()

    print(
        "DEFAULT <think> SAYISI:",
        default_text.count("<think>"),
    )

    print(
        "THINKING_FALSE <think> SAYISI:",
        no_thinking_text.count("<think>"),
    )

    print()

    print(
        "DEFAULT </think> SAYISI:",
        default_text.count("</think>"),
    )

    print(
        "THINKING_FALSE </think> SAYISI:",
        no_thinking_text.count("</think>"),
    )

    print()

    print(
        "CHAT TEMPLATE GENERATION BLOCK:",
        "{% generation" in template,
    )

    print()

    print(
        "EOS TOKEN:",
        repr(tokenizer.eos_token),
    )

    print(
        "EOS TOKEN ID:",
        tokenizer.eos_token_id,
    )

    print(
        "IM_END TOKEN ID:",
        tokenizer.convert_tokens_to_ids("<|im_end|>"),
    )

    print()

    print("-" * 80)
    print("DEFAULT SON 800 KARAKTER")
    print("-" * 80)
    print(default_text[-800:])

    print()

    print("-" * 80)
    print("THINKING_FALSE SON 800 KARAKTER")
    print("-" * 80)
    print(no_thinking_text[-800:])


if __name__ == "__main__":
    main()