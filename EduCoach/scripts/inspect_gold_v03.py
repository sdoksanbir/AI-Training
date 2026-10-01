import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SOURCE_FILE = ROOT / "data" / "gold" / "gold_v0.3.jsonl"
OUTPUT_FILE = ROOT / "data" / "gold" / "gold_v0.3_review.txt"


def main():
    rows = []

    with SOURCE_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))

    print(f"Toplam örnek: {len(rows)}")

    with OUTPUT_FILE.open("w", encoding="utf-8") as out:
        for index, row in enumerate(rows, start=1):
            messages = row["messages"]

            user_messages = [
                message["content"]
                for message in messages
                if message.get("role") == "user"
            ]

            assistant_messages = [
                message["content"]
                for message in messages
                if message.get("role") == "assistant"
            ]

            out.write("=" * 80 + "\n")
            out.write(f"ÖRNEK {index}\n")
            out.write(f"Mesaj sayısı: {len(messages)}\n")
            out.write(
                f"Tür: {'çok turlu' if len(messages) > 3 else 'tek turlu'}\n"
            )
            out.write("\n")

            for number, text in enumerate(user_messages, start=1):
                out.write(f"KULLANICI {number}:\n{text}\n\n")

            for number, text in enumerate(assistant_messages, start=1):
                out.write(f"ASİSTAN {number}:\n{text}\n\n")

    print(f"İnceleme dosyası oluşturuldu:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()