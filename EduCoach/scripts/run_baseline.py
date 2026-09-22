import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BENCHMARK_FILE = ROOT / "evaluations" / "baseline" / "benchmark_v0.1.jsonl"
OUTPUT_FILE = ROOT / "evaluations" / "baseline" / "qwen3_4b_baseline_v0.1.jsonl"

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3:4b"

SYSTEM_PROMPT = """Sen EduCoach'sun. YKS'ye hazırlanan öğrencilere kişiselleştirilmiş eğitim koçluğu yaparsın.

Sakin, sabırlı, gerçekçi ve çözüm odaklı davranırsın. Öğrenciyi suçlamaz, küçümsemez veya boş motivasyon cümleleriyle geçiştirmezsin.

Öğrencinin verdiği bilgileri dikkatle kullanırsın. Daha önce verilmiş bir bilgiyi gereksiz yere tekrar sormazsın.

Karar vermek için yeterli bilgi yoksa yalnızca gerekli minimum bilgiyi istersin. Yeterli bilgi varsa doğrudan somut öneri veya plan üretirsin.

Gerçekçi olmayan hedefleri küçümsemeden uygulanabilir ara hedeflere dönüştürürsün.

Her öğrenciye aynı programı vermezsin."""

def ask_ollama(user_message):
    payload = {
        "model": MODEL,
        "stream": False,
        "think": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        "options": {
            "temperature": 0.2
        }
    }

    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=300) as response:
        result = json.loads(response.read().decode("utf-8"))

    return result


with BENCHMARK_FILE.open("r", encoding="utf-8") as f:
    tests = [json.loads(line) for line in f if line.strip()]

print(f"Toplam test: {len(tests)}")
print(f"Model: {MODEL}")
print()

results = []

for index, test in enumerate(tests, start=1):
    print(f"[{index}/{len(tests)}] {test['id']} - {test['category']}")

    try:
        response = ask_ollama(test["user"])

        message = response.get("message", {})
        answer = message.get("content", "")

        result = {
            "id": test["id"],
            "category": test["category"],
            "user": test["user"],
            "model": MODEL,
            "assistant": answer
        }

        results.append(result)

        print("  OK")

    except Exception as e:
        print(f"  HATA: {e}")

        results.append({
            "id": test["id"],
            "category": test["category"],
            "user": test["user"],
            "model": MODEL,
            "assistant": "",
            "error": str(e)
        })


with OUTPUT_FILE.open("w", encoding="utf-8") as f:
    for result in results:
        json.dump(result, f, ensure_ascii=False)
        f.write("\n")

print()
print("Baseline tamamlandı.")
print(f"Çıktı: {OUTPUT_FILE}")