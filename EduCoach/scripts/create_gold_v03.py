import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SOURCE_FILE = ROOT / "data" / "gold" / "gold_v0.2.jsonl"
OUTPUT_FILE = ROOT / "data" / "gold" / "gold_v0.3.jsonl"

with SOURCE_FILE.open("r", encoding="utf-8") as f:
    examples = [json.loads(line) for line in f if line.strip()]

if len(examples) != 30:
    raise ValueError(
        f"gold_v0.2.jsonl dosyasında 30 örnek bekleniyordu, bulunan: {len(examples)}"
    )

SYSTEM_PROMPT = examples[0]["messages"][0]["content"]

new_examples = [

    # 31 — TYT net / puan karıştırmama
    {
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": "TYT'de 79 net yapıyorum ama son iki denemede 75'e düştüm. Çok geriledim mi?"
            },
            {
                "role": "assistant",
                "content": (
                    "79 netten 75 nete düşmek tek başına kalıcı bir gerileme olduğunu göstermez. "
                    "Buradaki 79 ve 75 değerleri TYT netlerin; bunları puan veya sıralamayla karıştırmadan değerlendirelim. "
                    "Önce son iki denemede kaybın hangi derslerden geldiğine bak. "
                    "Örneğin Türkçe sabit kalıp matematik 4 net düştüyse çalışma önceliğimiz farklı olur; "
                    "düşüş bütün derslere yayılmışsa süre, dikkat veya deneme koşullarını da incelemek gerekir. "
                    "İki denemelik düşüşe bakıp çalışma düzenini tamamen değiştirme. "
                    "Son 4-5 denemeyi birlikte değerlendir ve tekrar eden hata türlerini çıkar."
                )
            }
        ]
    },

    # 32 — Öğrencinin söylediğini ters anlamama
    {
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": (
                    "Programı pazartesi ve salı uyguluyorum ama çarşamba yorulunca tamamen bırakıyorum. "
                    "Sonra diğer günler de çalışmıyorum."
                )
            },
            {
                "role": "assistant",
                "content": (
                    "Sorun çarşambayı dinlenme günü yapman değil; çarşamba aksayınca bütün haftayı bırakman. "
                    "Bunu değiştirelim. Bir gün program bozulursa kaçırdığın görevleri ertesi güne yığma. "
                    "Ertesi gün doğrudan o günün planına dön. "
                    "Ayrıca programında her gün için üç zorunlu görev belirle; kalan görevler ek çalışma olsun. "
                    "İlk hedefin 7 gün kusursuz gitmek değil, haftanın en az 5 gününde ana görevleri tamamlamak olsun. "
                    "Böylece tek bir kötü gün bütün haftayı bozmaz."
                )
            }
        ]
    },

    # 33 — Süre bilgisini doğru yorumlama
    {
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": (
                    "TYT'de Türkçe yaklaşık 55 dakika sürüyor, matematikte de çok oyalanıyorum. "
                    "Bu yüzden fene yalnızca 15-20 dakika kalıyor."
                )
            },
            {
                "role": "assistant",
                "content": (
                    "Buradaki temel sorun fene ayırmak istediğin sürenin 15-20 dakika olması değil; "
                    "Türkçe ve özellikle matematikte fazla zaman harcadığın için sınavın sonunda fene yalnızca bu kadar süre kalması. "
                    "İlk hedefimiz Türkçeyi bir anda çok hızlandırmak değil, süreyi kontrollü biçimde azaltmak ve matematikte takıldığın soruyu bırakabilmek. "
                    "Bir hafta boyunca Türkçe branş denemelerinde süre tut. "
                    "Matematikte ilk turda 2-3 dakikayı aşan soruları işaretleyip geç. "
                    "Her denemede Türkçe, matematik ve fene başladığın saati ayrıca kaydet. "
                    "Böylece sürenin tam olarak nerede kaybolduğunu ölçebiliriz."
                )
            }
        ]
    },

    # 34 — Eksik konu uydurmama
    {
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": (
                    "Sayısal mezunum. TYT matematiğim diğer derslere göre çok zayıf. "
                    "Bugün matematiğe 3 saat ayırabilirim. Bana ne yapacağımı söyle."
                )
            },
            {
                "role": "assistant",
                "content": (
                    "Hangi matematik konularında eksik olduğunu söylemediğin için sana rastgele konu adı vermeyeceğim. "
                    "Bugünkü 3 saati şöyle kullan: "
                    "İlk 30 dakikada son TYT denemendeki matematik yanlış ve boşlarını konu türlerine ayır. "
                    "Sonraki 75 dakikada en çok tekrar eden eksik tür üzerinde konu tekrarı ve örnek çözümü yap. "
                    "15 dakika ara ver. "
                    "Ardından 45 dakika aynı konudan süreli soru çöz ve son 15 dakikada yanlışlarını tekrar incele. "
                    "Böylece bugünkü çalışma varsayıma değil kendi deneme verine dayanır."
                )
            }
        ]
    },

    # 35 — Temelsiz garanti vermeme
    {
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": (
                    "TYT'de 64 net yapıyorum. Bana iki haftada 80 nete çıkaracak kesin bir program verir misin?"
                )
            },
            {
                "role": "assistant",
                "content": (
                    "İki haftada 64 netten 80 nete çıkacağını garanti eden bir program vermek doğru olmaz. "
                    "Ama iki haftayı verimli kullanıp hangi alanlarda hızlı kazanım sağlayabileceğimizi belirleyebiliriz. "
                    "Bunun için ilk gün son 3 denemendeki yanlış ve boşları derslere ve hata türlerine ayır. "
                    "Sonraki 12 gün en sık tekrar eden iki zayıf alana öncelik ver; her 3-4 günde bir TYT denemesi yap. "
                    "Son gün yeni konu açmak yerine deneme sonuçlarını karşılaştır. "
                    "Hedefimiz 'kesin 80' demek değil, ölçülebilir biçimde hataları azaltmak ve net trendini yukarı çevirmek olsun."
                )
            }
        ]
    },

    # 36 — Yeterli bilgi varsa tekrar soru sormama
    {
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": (
                    "12. sınıf sayısal öğrencisiyim. TYT 73, AYT 41. "
                    "Hafta içi 3 saat, hafta sonu 6 saat çalışabiliyorum. "
                    "AYT fizik ve matematik zayıf. Bana haftalık düzen çıkar."
                )
            },
            {
                "role": "assistant",
                "content": (
                    "Verdiğin bilgiler başlangıç planı için yeterli. "
                    "Hafta içi 3 saatin yaklaşık 2 saatini AYT'ye, 1 saatini TYT korumaya ayıralım. "
                    "Pazartesi ve perşembe AYT matematik; salı ve cuma AYT fizik; çarşamba ise haftanın eksik kalan AYT konusu olsun. "
                    "Her hafta içi son 45-60 dakikada TYT problem, Türkçe veya kısa branş çalışması yap. "
                    "Cumartesi 3 saat AYT matematik + 2 saat fizik + 1 saat yanlış analizi; "
                    "pazar ise bir TYT denemesi, analizi ve hafta boyunca yetişmeyen AYT görevleri için kullanılsın. "
                    "İki hafta sonra fizik ve matematikte tamamlanan görev oranına göre dağılımı yeniden ayarlarız."
                )
            }
        ]
    },

    # 37 — Saat hesabını kontrol etme
    {
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": (
                    "Bugün toplam 4 saat çalışabilirim. Matematik ve fiziğe ağırlık vermek istiyorum "
                    "ama biraz da Türkçe çözmem gerekiyor."
                )
            },
            {
                "role": "assistant",
                "content": (
                    "Toplam 4 saati aşmadan şöyle bölelim: "
                    "90 dakika matematik, 15 dakika ara, 75 dakika fizik, 15 dakika ara, "
                    "45 dakika Türkçe ve son 30 dakika matematik-fizik yanlış analizi. "
                    "Aktif çalışma süresi toplam 4 saattir; aralar buna dahil değildir. "
                    "Eğer '4 saat' derken aralar dahil toplam zamanını kastediyorsan çalışma bloklarını biraz kısaltmamız gerekir."
                )
            }
        ]
    },

    # 38 — Sınava yakın dönemde aşırı yüklenmeyi engelleme
    {
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": (
                    "YKS'ye bir hafta kaldı. AYT matematikte eksiklerim var. "
                    "Gece 3'e kadar çalışıp yeni bir kampı baştan sona bitirmeyi düşünüyorum."
                )
            },
            {
                "role": "assistant",
                "content": (
                    "Son bir haftada bütün eksikleri kapatmaya çalışmak ve uykuyu ciddi biçimde azaltmak yerine "
                    "bildiğin konuları koruyup seçilmiş eksikleri tamamlamak daha kontrollü olur. "
                    "Yeni kampı baştan sona bitirmeye çalışma. "
                    "Son denemelerinde en sık karşılaştığın 2-3 AYT matematik eksiğini seç ve sadece bunlara odaklan. "
                    "Her gün kısa bir tekrar, seçilmiş soru çalışması ve yanlış analizi yap. "
                    "Uyku düzenini sınav saatine yaklaştır; gece 3'e kadar çalışmayı rutin hâle getirme. "
                    "Bu haftanın amacı yeni bir sistem kurmak değil, mevcut performansını sınav gününe mümkün olduğunca sağlam taşımak."
                )
            }
        ]
    }
]

examples.extend(new_examples)

with OUTPUT_FILE.open("w", encoding="utf-8") as f:
    for example in examples:
        json.dump(example, f, ensure_ascii=False)
        f.write("\n")

print(f"gold_v0.3.jsonl oluşturuldu.")
print(f"Toplam örnek: {len(examples)}")
print(f"Yeni eklenen örnek: {len(new_examples)}")
print(f"Dosya: {OUTPUT_FILE}")