import json
import re
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

BASELINE_FILE = (
    ROOT
    / "evaluations"
    / "holdout"
    / "qwen3_4b_hf_baseline_v0.2.jsonl"
)

V02_FILE = (
    ROOT
    / "evaluations"
    / "post_training"
    / "educoach_v0.2_holdout_results.jsonl"
)

REPORT_FILE = (
    ROOT
    / "evaluations"
    / "reports"
    / "holdout_v02_comparison.txt"
)


def load_jsonl(path):
    rows = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))

    return rows


def word_count(text):
    return len(text.split())


def normalize(text):
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def repetition_score(text):
    sentences = [
        sentence.strip()
        for sentence in re.split(r"[.!?]+", normalize(text))
        if sentence.strip()
    ]

    if len(sentences) < 2:
        return 0.0

    highest = 0.0

    for i in range(len(sentences)):
        for j in range(i + 1, len(sentences)):
            ratio = SequenceMatcher(
                None,
                sentences[i],
                sentences[j],
            ).ratio()

            highest = max(highest, ratio)

    return highest


def count_questions(text):
    return text.count("?")


def risky_flags(text):
    t = normalize(text)

    flags = []

    patterns = {
        "net_puan_karisimi": [
            r"\b\d+\s*net.{0,30}\b\d+\s*puan\b",
            r"\bnet\s*=\s*puan\b",
        ],
        "kesin_siralama": [
            r"kesin.{0,30}sıralama",
            r"sıralama.{0,30}kesin",
        ],
        "garanti": [
            r"\bgaranti\b",
            r"\bgaranti eder\b",
        ],
    }

    for label, regexes in patterns.items():
        for pattern in regexes:
            if re.search(pattern, t):
                flags.append(label)
                break

    return flags


def main():
    baseline = load_jsonl(BASELINE_FILE)
    v02 = load_jsonl(V02_FILE)

    if len(baseline) != 30:
        raise ValueError(
            f"Baseline 30 olmali, bulunan: {len(baseline)}"
        )

    if len(v02) != 30:
        raise ValueError(
            f"v02 30 olmali, bulunan: {len(v02)}"
        )

    baseline_by_id = {
        row["id"]: row
        for row in baseline
    }

    v02_by_id = {
        row["id"]: row
        for row in v02
    }

    if set(baseline_by_id) != set(v02_by_id):
        raise ValueError(
            "Baseline ve v02 ID listeleri ayni degil."
        )

    REPORT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    baseline_words = []
    v02_words = []

    baseline_questions = 0
    v02_questions = 0

    baseline_high_repeat = []
    v02_high_repeat = []

    baseline_risky = []
    v02_risky = []

    with REPORT_FILE.open(
        "w",
        encoding="utf-8",
    ) as report:

        report.write(
            "EDUCOACH v0.2 HOLDOUT KARSILASTIRMASI\n"
        )
        report.write("=" * 90 + "\n\n")

        for test_id in sorted(baseline_by_id):
            base = baseline_by_id[test_id]
            fine = v02_by_id[test_id]

            base_answer = base["assistant"]
            fine_answer = fine["assistant"]

            bw = word_count(base_answer)
            fw = word_count(fine_answer)

            bq = count_questions(base_answer)
            fq = count_questions(fine_answer)

            br = repetition_score(base_answer)
            fr = repetition_score(fine_answer)

            bf = risky_flags(base_answer)
            ff = risky_flags(fine_answer)

            baseline_words.append(bw)
            v02_words.append(fw)

            baseline_questions += bq
            v02_questions += fq

            if br >= 0.80:
                baseline_high_repeat.append(
                    (test_id, br)
                )

            if fr >= 0.80:
                v02_high_repeat.append(
                    (test_id, fr)
                )

            if bf:
                baseline_risky.append(
                    (test_id, bf)
                )

            if ff:
                v02_risky.append(
                    (test_id, ff)
                )

            report.write(
                "=" * 90 + "\n"
            )
            report.write(
                f"{test_id} | {base['category']}\n"
            )
            report.write(
                "=" * 90 + "\n\n"
            )

            report.write("KULLANICI:\n")
            report.write(
                base["user"] + "\n\n"
            )

            report.write(
                f"BASELINE "
                f"[kelime={bw}, "
                f"soru={bq}, "
                f"tekrar={br:.3f}, "
                f"risk={bf or 'yok'}]\n"
            )
            report.write(
                base_answer + "\n\n"
            )

            report.write(
                f"EDUCOACH v0.2 "
                f"[kelime={fw}, "
                f"soru={fq}, "
                f"tekrar={fr:.3f}, "
                f"risk={ff or 'yok'}]\n"
            )
            report.write(
                fine_answer + "\n\n"
            )

        avg_baseline = (
            sum(baseline_words)
            / len(baseline_words)
        )

        avg_v02 = (
            sum(v02_words)
            / len(v02_words)
        )

        report.write("\n")
        report.write(
            "#" * 90 + "\n"
        )
        report.write(
            "OTOMATIK OZET\n"
        )
        report.write(
            "#" * 90 + "\n\n"
        )

        report.write(
            f"Baseline ortalama kelime: "
            f"{avg_baseline:.1f}\n"
        )

        report.write(
            f"v0.2 ortalama kelime     : "
            f"{avg_v02:.1f}\n"
        )

        report.write(
            f"Baseline toplam soru     : "
            f"{baseline_questions}\n"
        )

        report.write(
            f"v0.2 toplam soru         : "
            f"{v02_questions}\n"
        )

        report.write(
            f"Baseline yuksek tekrar   : "
            f"{baseline_high_repeat}\n"
        )

        report.write(
            f"v0.2 yuksek tekrar       : "
            f"{v02_high_repeat}\n"
        )

        report.write(
            f"Baseline riskli eslesme  : "
            f"{baseline_risky}\n"
        )

        report.write(
            f"v0.2 riskli eslesme      : "
            f"{v02_risky}\n"
        )

    print("Karsilastirma tamamlandi.")
    print()
    print(
        f"Baseline ortalama kelime: "
        f"{sum(baseline_words) / len(baseline_words):.1f}"
    )
    print(
        f"v0.2 ortalama kelime     : "
        f"{sum(v02_words) / len(v02_words):.1f}"
    )
    print(
        f"Baseline toplam soru     : "
        f"{baseline_questions}"
    )
    print(
        f"v0.2 toplam soru         : "
        f"{v02_questions}"
    )
    print(
        f"Baseline yuksek tekrar   : "
        f"{baseline_high_repeat}"
    )
    print(
        f"v0.2 yuksek tekrar       : "
        f"{v02_high_repeat}"
    )
    print(
        f"Baseline riskli eslesme  : "
        f"{baseline_risky}"
    )
    print(
        f"v0.2 riskli eslesme      : "
        f"{v02_risky}"
    )
    print()
    print(f"Rapor: {REPORT_FILE}")


if __name__ == "__main__":
    main()