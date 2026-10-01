from __future__ import annotations

import json
from pathlib import Path

import torch
import yaml
from datasets import load_dataset
from peft import LoraConfig, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)
from trl import SFTConfig, SFTTrainer


# ---------------------------------------------------------
# PROJE YOLLARI
# ---------------------------------------------------------

SCRIPT_FILE = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_FILE.parents[2]

CONFIG_FILE = (
    PROJECT_ROOT
    / "training"
    / "configs"
    / "qwen3_4b_qlora_v01.yaml"
)


# ---------------------------------------------------------
# YARDIMCI FONKSIYONLAR
# ---------------------------------------------------------

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"Ayar dosyasi bulunamadi: {CONFIG_FILE}"
        )

    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_project_path(relative_path: str) -> Path:
    return PROJECT_ROOT / Path(relative_path)


def check_environment() -> None:
    print("=" * 60)
    print("EduCoach QLoRA Pilot Egitimi")
    print("=" * 60)

    print(f"Proje klasoru : {PROJECT_ROOT}")
    print(f"Config dosyasi: {CONFIG_FILE}")

    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA GPU bulunamadi. "
            "Bu egitimi NVIDIA GPU bulunan masaustu bilgisayarda calistir."
        )

    print(f"GPU            : {torch.cuda.get_device_name(0)}")
    print(
        f"CUDA           : {torch.version.cuda}"
    )
    print(
        f"BF16 destegi   : {torch.cuda.is_bf16_supported()}"
    )
    print()


def validate_dataset(dataset_file: Path, expected_count: int) -> None:
    if not dataset_file.exists():
        raise FileNotFoundError(
            f"Dataset bulunamadi: {dataset_file}"
        )

    rows = []

    with dataset_file.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"JSON hatasi. Satir: {line_number}"
                ) from exc

            if "messages" not in item:
                raise ValueError(
                    f"Satir {line_number}: 'messages' alani yok."
                )

            messages = item["messages"]

            if not isinstance(messages, list) or len(messages) < 3:
                raise ValueError(
                    f"Satir {line_number}: messages yapisi gecersiz."
                )

            roles = [message.get("role") for message in messages]

            if "user" not in roles:
                raise ValueError(
                    f"Satir {line_number}: user mesaji yok."
                )

            if "assistant" not in roles:
                raise ValueError(
                    f"Satir {line_number}: assistant mesaji yok."
                )

            rows.append(item)

    print(f"Dataset ornek sayisi: {len(rows)}")

    if len(rows) != expected_count:
        raise ValueError(
            f"Dataset ornek sayisi beklenenden farkli. "
            f"Beklenen: {expected_count}, bulunan: {len(rows)}"
        )

    print("Dataset kontrolu: OK")
    print()


# ---------------------------------------------------------
# ANA EGITIM
# ---------------------------------------------------------

def main() -> None:
    config = load_config()

    check_environment()

    model_cfg = config["model"]
    dataset_cfg = config["dataset"]
    training_cfg = config["training"]
    precision_cfg = config["precision"]
    lora_cfg = config["lora"]
    output_cfg = config["output"]

    model_name = model_cfg["name"]

    dataset_file = resolve_project_path(
        dataset_cfg["train_file"]
    )

    output_dir = resolve_project_path(
        output_cfg["directory"]
    )

    logging_dir = resolve_project_path(
        output_cfg["logs"]
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    logging_dir.mkdir(parents=True, exist_ok=True)

    validate_dataset(
        dataset_file,
        dataset_cfg["total_examples"],
    )

    # -----------------------------------------------------
    # PRECISION
    # -----------------------------------------------------

    use_bf16 = (
        bool(precision_cfg.get("bf16", True))
        and torch.cuda.is_bf16_supported()
    )

    use_fp16 = not use_bf16

    compute_dtype = (
        torch.bfloat16
        if use_bf16
        else torch.float16
    )

    print(f"Kullanilan precision: {compute_dtype}")
    print()

    # -----------------------------------------------------
    # DATASET
    # -----------------------------------------------------

    print("Dataset yukleniyor...")

    train_dataset = load_dataset(
        "json",
        data_files=str(dataset_file),
        split="train",
    )

    print(
        f"Dataset yuklendi: {len(train_dataset)} ornek"
    )
    print()

    # -----------------------------------------------------
    # TOKENIZER
    # -----------------------------------------------------

    print(f"Tokenizer yukleniyor: {model_name}")

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=model_cfg.get(
            "trust_remote_code",
            True,
        ),
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    tokenizer.padding_side = "right"

    print("Tokenizer hazir.")
    print()

    # -----------------------------------------------------
    # 4-BIT QLORA
    # -----------------------------------------------------

    print("4-bit QLoRA model yukleniyor...")

    quantization_config = BitsAndBytesConfig(
        load_in_4bit=bool(
            precision_cfg.get("load_in_4bit", True)
        ),
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        trust_remote_code=model_cfg.get(
            "trust_remote_code",
            True,
        ),
        quantization_config=quantization_config,
        dtype=compute_dtype,
        device_map={"": 0},
    )

    model.config.use_cache = False

    model = prepare_model_for_kbit_training(
        model,
        use_gradient_checkpointing=True,
    )

    print("Model 4-bit olarak yuklendi.")
    print()

    # -----------------------------------------------------
    # LORA
    # -----------------------------------------------------

    peft_config = LoraConfig(
        r=int(lora_cfg["r"]),
        lora_alpha=int(lora_cfg["alpha"]),
        lora_dropout=float(lora_cfg["dropout"]),
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=list(
            lora_cfg["target_modules"]
        ),
    )

    # -----------------------------------------------------
    # TRAINING AYARLARI
    # -----------------------------------------------------

    training_args = SFTConfig(
        output_dir=str(output_dir),

        num_train_epochs=float(
            training_cfg["epochs"]
        ),

        learning_rate=float(
            training_cfg["learning_rate"]
        ),

        per_device_train_batch_size=int(
            training_cfg["per_device_train_batch_size"]
        ),

        gradient_accumulation_steps=int(
            training_cfg[
                "gradient_accumulation_steps"
            ]
        ),

        max_length=int(
            training_cfg["max_seq_length"]
        ),

        logging_steps=int(
            training_cfg["logging_steps"]
        ),

        save_strategy=str(
            training_cfg["save_strategy"]
        ),

        bf16=use_bf16,
        fp16=use_fp16,

        gradient_checkpointing=True,

        optim="paged_adamw_8bit",

        lr_scheduler_type="cosine",

        warmup_steps=1,

        weight_decay=0.01,

        report_to="none",

        remove_unused_columns=False,

        assistant_only_loss=True,

        packing=False,

        seed=42,
    )

    # -----------------------------------------------------
    # TRAINER
    # -----------------------------------------------------

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        processing_class=tokenizer,
        peft_config=peft_config,
    )

    print()
    print("=" * 60)
    print("EGITIM BASLIYOR")
    print("=" * 60)
    print(f"Model   : {model_name}")
    print(f"Dataset : {dataset_file}")
    print(f"Ornek   : {len(train_dataset)}")
    print(
        f"Epoch   : {training_cfg['epochs']}"
    )
    print(
        f"LoRA r  : {lora_cfg['r']}"
    )
    print(f"Cikti   : {output_dir}")
    print("=" * 60)
    print()

    train_result = trainer.train()

    # -----------------------------------------------------
    # KAYDET
    # -----------------------------------------------------

    print()
    print("LoRA adapter kaydediliyor...")

    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    metrics = train_result.metrics

    metrics_file = output_dir / "training_metrics.json"

    with metrics_file.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            metrics,
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    print()
    print("=" * 60)
    print("EGITIM TAMAMLANDI")
    print("=" * 60)
    print(f"Adapter: {output_dir}")
    print(f"Metrics: {metrics_file}")
    print()
    print(
        "Bu adapter egitim sonrasi benchmark icin "
        "kullanilabilir."
    )


if __name__ == "__main__":
    main()