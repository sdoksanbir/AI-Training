# EduCoach — Current Status

**Son Güncelleme:** 22 Eylül 2026

## Proje

EduCoach

## Sürüm Odağı

EduCoach v0.1 = **YKS Eğitim Koçu**

İlk sürüm YKS hazırlık sürecine odaklanacaktır.

Hedef kitle:

* 11. sınıf öğrencileri
* 12. sınıf öğrencileri
* Mezun öğrenciler
* TYT hazırlanan öğrenciler
* AYT hazırlanan öğrenciler

LGS desteği daha sonraki aşamada ayrı bir uzmanlık profili olarak ele alınacaktır.

## Temel Model

Qwen3-4B

## Temel Amaç

Yerel olarak çalışabilecek, öğrencinin YKS hazırlık sürecini takip eden ve kişiselleştirilmiş eğitim koçluğu sağlayan bir yapay zekâ geliştirmek.

## Modelin Rolü

EduCoach bir ders öğretmeni veya yalnızca soru çözme modeli değildir.

Ana rolü:

* öğrenciyi tanımak,
* ihtiyaçlarını analiz etmek,
* hedef belirlemek,
* çalışma programı hazırlamak,
* TYT / AYT dengesini yönetmek,
* deneme sonuçlarını analiz etmek,
* net değişimlerini takip etmek,
* eksikleri belirlemek,
* çalışma stratejileri önermek,
* gelişimi takip etmek,
* öğrencinin durumuna göre planını değiştirmek.

## Mimari

```text
Coach Brain
→ Fine-Tuning / QLoRA
→ Eğitim koçluğu davranışı

Knowledge
→ RAG
→ Ders, müfredat ve kaynak bilgileri

Student Memory
→ Database
→ Öğrenci profili ve geçmişi
```

## Fine-Tuning

Planlanan yöntem:

```text
QLoRA
```

Fine-tuning'in ana hedefi ders bilgisini modele ezberletmek değil, eğitim koçluğu davranışını geliştirmektir.

## Temel Koçluk Yaklaşımı

EduCoach öğrenciyi gereksiz yere uzun bir sorguya sokmamalıdır.

Özellikle sabırsız öğrencilerde yaklaşım şu olmalıdır:

```text
Minimum gerekli bilgi
→ Hızlı başlangıç
→ İlk uygulanabilir plan
→ Süreç içinde ek veri toplama
→ Planı kişiselleştirme
```

Öğrenci:

```text
"Bana hemen program yap."
"Uzun uzun soru sorma."
"Bugün ne çalışacağımı direkt söyle."
"Çok vaktim yok."
```

gibi taleplerde bulunduğunda EduCoach:

* öğrenciyi bekletmemeli,
* ilk aşamada yalnızca gerekli 3–5 bilgiyi istemeli,
* eksik veriyle sahte kişiselleştirme yapmamalı,
* hızlı bir başlangıç planı sunmalı,
* öğrenciyi sakin ve sabırlı biçimde sürece yönlendirmeli,
* gerçekçi olmayan hedefleri küçümsemeden yeniden çerçevelemelidir.

## Gold Dataset

Gold Dataset v0.1 ilk taslak olarak tamamlandı.

```text
gold_v0.1.jsonl
30 örnek

Kalite kontrolü sonrasında ikinci sürüm oluşturuldu:
gold_v0.2.jsonl
30 örnek

Baseline değerlendirmesi sonrasında üçüncü sürüm oluşturuldu:
gold_v0.3.jsonl
38 örnek

v0.3 sürümünde baseline sırasında görülen şu davranış problemlerine yönelik yeni örnekler eklendi:

TYT net, puan ve sıralama kavramlarını karıştırmama
öğrencinin söylediğini ters anlamama
süre bilgisini doğru yorumlama
öğrencinin belirtmediği eksik konuları uydurmama
temelsiz başarı garantisi vermeme
yeterli bilgi varsa tekrar soru sormama
çalışma süresi hesaplarını kontrol etme
sınava yakın dönemde aşırı yüklenmeyi engelleme

Gold Dataset v0.1 ve v0.2 referans sürümleri korunmaktadır.
```

## Tamamlanan İşler

* [x] Qwen3-4B indirildi ve test edildi.
* [x] Phi-4-mini indirildi ve test edildi.
* [x] Qwen3-4B ile Phi-4-mini karşılaştırıldı.
* [x] Başlangıç modeli olarak Qwen3-4B seçildi.
* [x] EduCoach proje klasörü oluşturuldu.
* [x] EduCoach proje planı hazırlandı.
* [x] Eğitim koçluğu yönü belirlendi.
* [x] Coach Brain / RAG / Student Memory mimarisi belirlendi.
* [x] Git repository oluşturuldu.
* [x] GitHub remote bağlantısı kuruldu.
* [x] `main` branch GitHub ile senkronize edildi.
* [x] EduCoach v0.1'in YKS odaklı olması kararlaştırıldı.
* [x] LGS desteğinin sonraki aşamaya bırakılması kararlaştırıldı.
* [x] Sabırsız öğrenci / hızlı başlangıç davranışı tanımlandı.
* [x] İlk 5 Gold Dataset örneği oluşturuldu.
* [x] İlk 5 Gold Dataset örneği öğretmen gözüyle onaylandı.


## Şu Anda Bulunduğumuz Aşama

FAZ 3 — Baseline tamamlandı / İlk eğitim hazırlığı

Qwen3-4B temel modeli 20 sabit YKS koçluk benchmark senaryosu üzerinde test edildi.

Eğitim öncesi baseline sonuçları kaydedildi:

evaluations/baseline/qwen3_4b_baseline_v0.1.jsonl

Baseline sonucunda temel modelde özellikle şu problemler görüldü:

- YKS terminolojisini zaman zaman yanlış yorumlama
- net ve puan kavramlarını karıştırma
- öğrencinin verdiği bilgiyi zaman zaman yanlış anlama
- yeterli bilgi varken tekrar soru sorma
- öğrencinin belirtmediği eksik konuları varsayma
- gerçekçi olmayan başarı veya gelişim tahminleri üretme
- süre ve çalışma planı hesaplarında hata
- Türkçe cevap tutarlılığının bozulması

Bu bulgular doğrultusunda:

- Core System Prompt güçlendirildi.
- Gold Dataset v0.3 oluşturuldu.
- Dataset 30 örnekten 38 örneğe çıkarıldı.

## Sıradaki İş

Gold Dataset v0.1 kalite kontrolü tamamlandı.

Mevcut durum:

```text
30 / 30 Gold Example hazırlandı
```

Ancak mevcut 30 örnek henüz nihai Gold Dataset olarak kilitlenmedi.

Tespit edilen geliştirme alanları:

* System promptlar örneğe fazla özel.
* 30 örneğin tamamı tek turlu konuşma.
* Modelin bilgi aldıktan sonra harekete geçtiği örnekler yetersiz.
* Bazı cevaplar gereğinden fazla benzer uzunlukta.
* Öğrencinin daha önce verdiği bilgiyi tekrar sormama davranışı güçlendirilmeli.
* Makul çıkarım yapma davranışı eklenmeli.
* Gerçek çalışma programı üretme örnekleri artırılmalı.

Bir sonraki sürüm:

```text
gold_v0.2.jsonl
```

olacaktır.

Plan:

1. Ortak EduCoach Core System Prompt oluştur.
2. Mevcut 30 örneğin system promptlarını ortak prompt ile değiştir.
3. 20 örneği tek turlu bırak.
4. 10 örneği çok turlu koçluk konuşmasına dönüştür.
5. Öğrencinin verdiği bilgileri tekrar sormama kuralını uygula.
6. Yeterli bilgi geldiğinde yeni soru sormak yerine eyleme geçmesini öğret.
7. Cevap uzunluklarını çeşitlendir.
8. Revize edilmiş dosyayı `gold_v0.2.jsonl` olarak kaydet.
9. v0.2 kalite kontrolünden sonra baseline benchmark aşamasına geç.


## Yeni Sohbette Devam Etmek İçin

Öncelikle şu dosyalar okunmalıdır:

```text
README.md
CURRENT_STATUS.md
notes/DECISIONS.md
docs/ROADMAP.md
docs/BEHAVIOR_SPEC.md
data/gold/gold_v0.1.jsonl
```

Ardından `CURRENT_STATUS.md` içerisindeki **Sıradaki İş** bölümünden devam edilmelidir.
