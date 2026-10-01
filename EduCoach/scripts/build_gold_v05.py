import copy
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SOURCE = ROOT / "data" / "gold" / "gold_v0.4.jsonl"
OUTPUT = ROOT / "data" / "gold" / "gold_v0.5.jsonl"

REPORT = (
    ROOT
    / "evaluations"
    / "reports"
    / "gold_v05_changes.txt"
)


# Anahtar:
# (1-based gold örnek numarası, 0-based messages index)
REPLACEMENTS = {
    (1, 4): (
        "Başlangıç için yeterli bilgi var. İlk hafta günlük 5 saati "
        "2 saat ana geliştirme bloğu, 1,5 saat ikinci çalışma bloğu, "
        "1 saat TYT koruma ve 30 dakika yanlış analizi/kısa tekrar "
        "olarak kullan. Ana bloklara hangi derslerin gireceğini son "
        "denemendeki en büyük kayba göre seç; bunu bilmediğim için "
        "rastgele ders adı belirlemiyorum. Haftada en az bir TYT "
        "denemesi yap ve sonuçlarını ders bazında kaydet. İlk haftadan "
        "sonra dağılımı gerçek sonuçlarına göre değiştiririz."
    ),

    (39, 2): (
        "Başlangıç için yeterli bilgimiz var. Hafta içi 3 saati çok "
        "fazla parçalamayalım: yaklaşık 2 saati okul/12. sınıf ve AYT "
        "tarafındaki ana çalışma bloğuna, 1 saati TYT korumaya ayır. "
        "Ana blokta o gün okulda işlenen veya geride olduğun alanı seç. "
        "Hangi dersinin daha zayıf olduğunu bilmediğim için belirli bir "
        "dersi öncelikli ilan etmiyorum. Hafta sonundaki süreni henüz "
        "bilmediğim için hafta sonuna ayrıntılı saat yazmıyorum."
    ),

    (39, 4): (
        "O zaman hafta içindeki 3 saatlik iskeleti koruyup hafta sonunu "
        "daha uzun çalışmalar için kullanalım. Cumartesi 3 saat ana "
        "geliştirme bloğu, 2 saat ikinci geliştirme bloğu ve 1 saat "
        "yanlış analizi/tekrar yap. Ana blokları son denemelerde veya "
        "hafta içinde en çok zorlandığın alanlardan seç. Pazar günü bir "
        "TYT denemesi ve analizinden sonra kalan süreyi hafta boyunca "
        "yetişmeyen okul/AYT görevlerine ayır. Böylece ders önceliğini "
        "varsayımla değil kendi sonuçlarına göre belirlemiş oluruz."
    ),

    (41, 4): (
        "Hafta içi 2,5 saatin yaklaşık 1,5 saatini 11. sınıf okul "
        "derslerine, kalan 1 saatini TYT temel çalışmasına ayır. "
        "Hafta sonu 5 saatte 3 saat okul/11. sınıf çalışması, "
        "1,5 saat TYT ve 30 dakika haftalık tekrar kullanabilirsin. "
        "Bu aşamada amaç 12. sınıf öğrencisi gibi yoğun TYT programı "
        "yapmak değil; 11. sınıf konularını sağlam tutarken TYT "
        "temelini düzenli biçimde ilerletmek."
    ),

    (42, 2): (
        "TYT sonuçların son üç denemede 69'dan 75'e doğru ilerlerken "
        "AYT 32 civarında kalmış ve sen de AYT'yi artırmak istiyorsun; "
        "bu nedenle çalışma ağırlığını AYT'ye kaydırmak mantıklı. "
        "Günlük 6 saatin yaklaşık 4 saatini AYT geliştirme çalışmalarına, "
        "1-1,5 saatini TYT'yi korumaya, kalan süreyi yanlış analizine "
        "ayırarak başlayabilirsin. AYT içindeki ders dağılımını ise "
        "branş netlerin ve tekrarlayan yanlışların belirlesin; hangi "
        "branşın daha zayıf olduğunu bilmeden rastgele öncelik vermeyelim."
    ),

    (44, 2): (
        "Verdiğin bilgiler başlangıç için yeterli. Fizik en zayıf dersin "
        "olduğu için günlük 7 saatin yaklaşık 2 saatini doğrudan fiziğe "
        "ayır. Yaklaşık 2 saati AYT'deki ikinci geliştirme alanına ver; "
        "bu alanı son denemelerde en fazla kayıp yaşadığın branştan seç. "
        "1,5 saati TYT korumaya, 1 saati yanlış analizi ve tekrara, "
        "kalan 30 dakikayı kısa tekrar veya ertesi gün planına ayır. "
        "Böylece fizik önceliğini kullanırken diğer dersleri veri olmadan "
        "rastgele sıralamamış oluruz."
    ),

    (73, 2): (
        "2 saat içinde üç alanı da her gün ayrıntılı çalışmak programı "
        "fazla parçalar. Daha gerçekçi olan, bir ana alan ve bir kısa "
        "koruma çalışması seçmek. Örneğin 80 dakika okul/AYT ana çalışma "
        "ve 40 dakika TYT koruma bloğu kullanabilirsin. Ana alanı o gün "
        "en acil okul konusu veya geride olduğun AYT alanından seç. "
        "Ertesi gün ana alanı değiştirebilirsin."
    ),

    (92, 2): (
        "Elindeki bilgiler bugün için başlangıç iskeleti kurmaya yeterli. "
        "5 saati 2 saat ana geliştirme bloğu, 90 dakika ikinci geliştirme "
        "bloğu, 60 dakika TYT koruma ve 30 dakika yanlış analizi şeklinde "
        "kullan. Ana ve ikinci geliştirme bloklarına hangi derslerin "
        "gireceğini son denemendeki en büyük kayıplara göre seç. "
        "Zayıf derslerini söylemediğin için bugün rastgele ders adı "
        "belirlemiyorum; başlamak için bunu beklememize de gerek yok."
    ),

    (93, 4): (
        "Başlamak için yeterli. Günlük 4 saati 90 dakika ana geliştirme "
        "bloğu, 60 dakika ikinci çalışma bloğu, 60 dakika TYT koruma ve "
        "30 dakika yanlış analizi şeklinde kullan. Ana blokları son "
        "denemelerinde veya mevcut çalışmalarında en çok zorlandığın "
        "alanlardan seç. Hangi dersinin zayıf olduğunu bilmediğim için "
        "belirli bir dersi öncelikli ilan etmiyorum. İlk üç gün bu "
        "iskeleti uygula, sonra gerçek sonuçlarına göre ayrıntıyı değiştir."
    ),

    (96, 2): (
        "Bu bilgilerle başlayabiliriz. Günlük 6 saati yaklaşık 2 saat "
        "ana geliştirme bloğu, 1,5 saat ikinci geliştirme bloğu, "
        "1,5 saat TYT koruma ve 1 saat yanlış analizi/tekrar şeklinde "
        "kullan. Eşit ağırlık alanındaki derslerin hangisinde daha fazla "
        "kayıp yaşadığını söylemediğin için belirli bir dersi zayıf veya "
        "öncelikli ilan etmiyorum. İlk hafta bu iskeleti kullan; sonra "
        "deneme sonuçlarına göre blokların içini kişiselleştiririz."
    ),

    (97, 4): (
        "İlk gün için 5 saati 2 saat ana geliştirme bloğu, 90 dakika "
        "ikinci çalışma bloğu, 60 dakika TYT koruma ve 30 dakika yanlış "
        "analizi şeklinde kullan. Ana bloklara hangi sayısal derslerin "
        "gireceğini mevcut eksiklerinden veya son denemendeki en büyük "
        "kayıptan seç. Zayıf ders bilgisi olmadığı için rastgele ders "
        "adı vermiyorum. İlk gün için daha fazla bilgi toplamaya gerek "
        "yok; uyguladıktan sonra ikinci günü sonuca göre ayarlarız."
    ),

    (98, 2): (
        "İlk iskeleti hemen kuralım. Günlük 4 saatin 90 dakikasını "
        "okulda işlenen 12. sınıf konularına, 90 dakikasını ana geliştirme "
        "bloğuna ve 60 dakikasını TYT korumaya ayır. Ana geliştirme "
        "bloğunu şu an en çok geride olduğun alandan seç. Hangi dersin "
        "zayıf olduğunu söylemediğin için belirli bir ders adı vermiyorum. "
        "Okul çalışması ile ana geliştirme alanı aynı gün örtüşürse bu "
        "blokları birleştirip kalan zamanı soru çözümü ve yanlış analizine "
        "aktarabilirsin. Şu an planı başlatmak için daha fazla ayrıntıya "
        "ihtiyacımız yok."
    ),

    (110, 4): (
        "Bu 10 günde okul sınavlarını ana öncelik yapıp YKS'yi koruma "
        "moduna alabiliriz. Her gün 30-60 dakikalık kısa bir YKS koruma "
        "bloğu yeterli olabilir. Bu bloğu o dönemde en çabuk gerileyen "
        "veya en çok tekrar gerektiren alanından seç; hangi ders olduğunu "
        "bilmediğim için rastgele ders adı belirlemiyorum. Okul sınavında "
        "çalıştığın konular YKS ile örtüşüyorsa aynı içeriği ayrıca iki kez "
        "çalışmana gerek yok. Yazılılar bittikten sonra normal YKS "
        "düzenine geri dön."
    ),

    (113, 4): (
        "O bir saati küçümsemeyelim. Hafta içi her akşam tek bir net "
        "görev yap. O günün görevini haftanın en acil eksiği, okul/"
        "dershane ihtiyacı veya son denemendeki tekrarlayan hataya göre "
        "seç. Böylece beş günde yaklaşık 5 saatlik yükü hafta sonundan "
        "almış olursun. Cumartesi ve pazarı daha uzun ana çalışmalar, "
        "deneme ve analiz için kullan; bütün haftayı iki güne sıkıştırma."
    ),
}


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as file:
        for row in rows:
            file.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                )
                + "\n"
            )


def words(text: str) -> list[str]:
    return re.findall(
        r"[0-9a-zA-ZçğıöşüÇĞİÖŞÜ]+",
        text.lower(),
    )


def has_loop(text: str) -> bool:
    tokens = words(text)

    for n in range(5, 9):
        if len(tokens) < n:
            continue

        grams = [
            tuple(tokens[i:i + n])
            for i in range(
                len(tokens) - n + 1
            )
        ]

        counts = Counter(grams)

        repeated = {
            gram: count
            for gram, count in counts.items()
            if count >= 2
        }

        if not repeated:
            continue

        covered = set()

        for i, gram in enumerate(grams):
            if gram in repeated:
                covered.update(
                    range(
                        i,
                        min(i + n, len(tokens)),
                    )
                )

        coverage = (
            len(covered) / len(tokens)
            if tokens
            else 0.0
        )

        max_count = max(
            repeated.values()
        )

        if (
            max_count >= 3
            or (
                max_count >= 2
                and coverage >= 0.20
            )
        ):
            return True

    return False


def count_assistant(rows: list[dict]) -> int:
    return sum(
        1
        for row in rows
        for message in row["messages"]
        if message["role"] == "assistant"
    )


def main():
    source_before = SOURCE.read_bytes()

    original = load_jsonl(SOURCE)

    if len(original) != 120:
        raise ValueError(
            f"Kaynak 120 ornek olmali, bulunan: {len(original)}"
        )

    rows = copy.deepcopy(original)

    changed_messages = []

    for (
        example_no,
        message_index
    ), new_content in REPLACEMENTS.items():

        row_index = example_no - 1

        messages = rows[row_index]["messages"]

        if message_index >= len(messages):
            raise IndexError(
                f"Ornek {example_no}: "
                f"mesaj {message_index} yok."
            )

        if (
            messages[message_index]["role"]
            != "assistant"
        ):
            raise ValueError(
                f"Ornek {example_no}, "
                f"mesaj {message_index} "
                "assistant degil."
            )

        old_content = (
            messages[message_index]["content"]
        )

        messages[message_index]["content"] = (
            new_content
        )

        changed_messages.append(
            {
                "example": example_no,
                "message_index": message_index,
                "old": old_content,
                "new": new_content,
            }
        )

    # Temel yapısal doğrulamalar
    if len(rows) != 120:
        raise AssertionError(
            "Cikti ornek sayisi 120 degil."
        )

    original_assistant_count = (
        count_assistant(original)
    )

    new_assistant_count = (
        count_assistant(rows)
    )

    if original_assistant_count != 170:
        raise AssertionError(
            "Kaynak assistant mesaj sayisi "
            f"170 degil: {original_assistant_count}"
        )

    if new_assistant_count != 170:
        raise AssertionError(
            "Yeni assistant mesaj sayisi "
            f"170 degil: {new_assistant_count}"
        )

    # Tüm system promptlar aynı mı?
    system_prompts = []

    for row in rows:
        systems = [
            message["content"]
            for message in row["messages"]
            if message["role"] == "system"
        ]

        if len(systems) != 1:
            raise AssertionError(
                "Her ornekte tam bir system "
                "mesaji bulunmali."
            )

        system_prompts.append(
            systems[0]
        )

    if len(set(system_prompts)) != 1:
        raise AssertionError(
            "System promptlar ayni degil."
        )

    # Sadece izin verilen mesajlar değişmiş mi?
    allowed = set(REPLACEMENTS.keys())

    actual_changed = set()

    for row_index, (
        old_row,
        new_row,
    ) in enumerate(
        zip(original, rows),
        start=1,
    ):
        if len(old_row["messages"]) != len(
            new_row["messages"]
        ):
            raise AssertionError(
                f"Ornek {row_index}: "
                "mesaj sayisi degisti."
            )

        for message_index, (
            old_message,
            new_message,
        ) in enumerate(
            zip(
                old_row["messages"],
                new_row["messages"],
            )
        ):
            if (
                old_message
                != new_message
            ):
                actual_changed.add(
                    (
                        row_index,
                        message_index,
                    )
                )

                if (
                    old_message["role"]
                    != "assistant"
                    or new_message["role"]
                    != "assistant"
                ):
                    raise AssertionError(
                        "Assistant disinda mesaj "
                        "degistirildi."
                    )

    if actual_changed != allowed:
        raise AssertionError(
            "Beklenmeyen degisiklik var.\n"
            f"Beklenen: {sorted(allowed)}\n"
            f"Gercek  : {sorted(actual_changed)}"
        )

    # Loop kontrolü
    loop_items = []

    for example_no, row in enumerate(
        rows,
        start=1,
    ):
        for message_index, message in enumerate(
            row["messages"]
        ):
            if (
                message["role"] == "assistant"
                and has_loop(message["content"])
            ):
                loop_items.append(
                    (
                        example_no,
                        message_index,
                    )
                )

    if loop_items:
        raise AssertionError(
            "Gold v0.5 icinde loop adayi bulundu: "
            f"{loop_items}"
        )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    write_jsonl(
        OUTPUT,
        rows,
    )

    # Kaynak dosyanın değişmediğini doğrula
    source_after = SOURCE.read_bytes()

    if source_before != source_after:
        raise AssertionError(
            "HATA: gold_v0.4.jsonl degisti."
        )

    report_lines = [
        "=" * 100,
        "GOLD v0.5 DEGISIKLIK RAPORU",
        "=" * 100,
        "",
        f"Kaynak               : {SOURCE}",
        f"Cikti                : {OUTPUT}",
        f"Gold ornek           : {len(rows)}",
        (
            "Assistant mesaj      : "
            f"{new_assistant_count}"
        ),
        (
            "Degisen gold ornegi  : "
            f"{len(set(x['example'] for x in changed_messages))}"
        ),
        (
            "Degisen assistant    : "
            f"{len(changed_messages)}"
        ),
        (
            "System prompt sayisi : "
            f"{len(system_prompts)}"
        ),
        (
            "Unique system prompt : "
            f"{len(set(system_prompts))}"
        ),
        (
            "Loop adayi           : "
            f"{len(loop_items)}"
        ),
        "Kaynak v0.4 degisti mi  : HAYIR",
        "",
    ]

    for change in changed_messages:
        report_lines.extend(
            [
                "=" * 100,
                (
                    f"ORNEK {change['example']} "
                    f"| MESAJ {change['message_index']}"
                ),
                "",
                "ESKI:",
                change["old"],
                "",
                "YENI:",
                change["new"],
                "",
            ]
        )

    REPORT.write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    print("=" * 70)
    print("GOLD v0.5 OLUSTURULDU")
    print("=" * 70)
    print(f"Gold ornek           : {len(rows)}")
    print(
        f"Assistant mesaj      : {new_assistant_count}"
    )
    print(
        "Degisen gold ornegi  : "
        f"{len(set(x['example'] for x in changed_messages))}"
    )
    print(
        "Degisen assistant    : "
        f"{len(changed_messages)}"
    )
    print(
        "Unique system prompt : "
        f"{len(set(system_prompts))}"
    )
    print(
        f"Loop adayi           : {len(loop_items)}"
    )
    print("Kaynak v0.4 degisti  : HAYIR")
    print()
    print(f"Cikti : {OUTPUT}")
    print(f"Rapor : {REPORT}")


if __name__ == "__main__":
    main()