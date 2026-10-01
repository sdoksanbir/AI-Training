# EduCoach — Project Decisions

Bu dosya proje boyunca alınan önemli mimari ve ürün kararlarının nedenleriyle birlikte kaydedilmesi için kullanılacaktır.

---

## D-001 — Temel Model

**Karar:** Qwen3-4B kullanılacak.

**Alternatif:** Phi-4-mini

**Gerekçe:** İlk Türkçe eğitim testi sırasında Qwen3-4B daha tutarlı, doğru ve kontrollü cevap verdi. Phi-4-mini aynı testte konu sınıflandırması ve tekrar üretimi açısından ciddi problemler gösterdi.

---

## D-002 — EduCoach'un Ana Rolü

**Karar:** EduCoach bir ders öğretmeni değil, eğitim koçu olacak.

**Gerekçe:** Temel modeller zaten önemli miktarda genel ders bilgisine sahiptir. Projenin asıl değerinin öğrenciye bilgi vermekten çok öğrencinin öğrenme sürecini yönetmek olduğu sonucuna varıldı.

---

## D-003 — Fine-Tuning'in Amacı

**Karar:** Fine-tuning ders bilgisinden çok davranış öğretmek için kullanılacak.

Model özellikle:

* öğrenci analizi,
* koçluk,
* planlama,
* hata analizi,
* hedef belirleme,
* zaman yönetimi,
* motivasyon,
* öğrenme stratejileri

konularında eğitilecek.

---

## D-004 — Ders Bilgisi

**Karar:** Tüm derslerin içeriği fine-tuning yoluyla modele yeniden öğretilmeyecek.

**Gerekçe:** Bu yaklaşım veri setini gereksiz büyütür ve modelin temel amacını bulanıklaştırır.

Ders/müfredat bilgisi gerektiğinde RAG katmanından sağlanacaktır.

---

## D-005 — Mimari

**Karar:** Sistem üç ana katmana ayrılacak.

```text
Coach Brain
Knowledge
Student Memory
```

### Coach Brain

Fine-tuning ile eğitim koçluğu davranışını yönetir.

### Knowledge

RAG ile ders ve müfredat bilgisini sağlar.

### Student Memory

Öğrenciye ait geçmiş bilgileri ve kişiselleştirmeyi yönetir.

---

## D-006 — Eğitim Yöntemi

**Karar:** İlk fine-tuning denemeleri QLoRA ile gerçekleştirilecek.

**Gerekçe:** Qwen3-4B ve mevcut 16 GB VRAM'li GPU sistemi için kaynak açısından uygun başlangıç yöntemidir.

---

## D-007 — Dataset Stratejisi

**Karar:** Doğrudan büyük veri seti oluşturulmayacak.

Önce:

```text
20–30 Gold Example
```

hazırlanacak.

Kalite standardı doğrulandıktan sonra:

```text
100 → 300 → 500 → 1000+
```

şeklinde genişletilecek.

---

## D-008 — Benchmark

**Karar:** Fine-tuning öncesinde sabit bir benchmark oluşturulacak.

**Gerekçe:** Eğitimin gerçekten modeli geliştirip geliştirmediğini ölçebilmek için eğitim öncesi ve sonrası aynı sorular kullanılmalıdır.

---

## D-009 — Laptop / Masaüstü İş Bölümü

**Laptop:**

* veri hazırlama,
* dokümantasyon,
* proje planlama,
* prompt hazırlama,
* değerlendirme verisi hazırlama.

**GPU masaüstü:**

* QLoRA,
* model eğitimi,
* checkpoint,
* model değerlendirme,
* GGUF/Ollama işlemleri.

---

## D-010 — Git Kullanımı

**Karar:** Proje Git ve private GitHub repository üzerinden sürdürülecek.

**Gerekçe:**

* laptop ve masaüstü arasında devamlılık,
* geçmiş değişikliklerin takip edilmesi,
* proje kararlarının kaybolmaması,
* yeni ChatGPT sohbetlerinde proje bağlamının kolayca yeniden oluşturulması.

---

## D-011 — Bilgiyi Tekrar Sormama ve Kontrollü Çıkarım

**Karar:**

EduCoach öğrencinin daha önce verdiği bilgileri gereksiz yere tekrar sormayacaktır.

Öğrencinin verdiği bilgilerden güçlü ve makul bir çıkarım yapılabiliyorsa bu çıkarım kullanılacaktır.

Çıkarım önemli bir planlama kararını etkiliyorsa EduCoach bunu kesin gerçek olarak sunmak yerine kısa bir varsayım olarak ifade edecek ve öğrencinin düzeltmesine açık bırakacaktır.

Örnek:

```text
Öğrenci:
"Bilgisayar mühendisliği istiyorum."

EduCoach:
"Bilgisayar mühendisliği hedefin olduğuna göre sayısal üzerinden ilerleyelim. Farklı bir durumun varsa söyle."
```

Bu durumda öğrenciye tekrar:

```text
"Hangi puan türündesin?"
```

diye sorulmayacaktır.

**Temel İlke:**

```text
Bilgiyi dinle
→ Makul çıkarım yap
→ Gereksiz tekrar sorma
→ Kritikse varsayımı belirt
→ Öğrencinin düzeltmesine açık ol
```

**Gerekçe:**

Gereksiz doğrulama soruları öğrenciyi yavaşlatır ve EduCoach'un öğrenciyi dinlemediği hissini oluşturur.

EduCoach'un amacı bir form gibi soru sormak değil, öğrencinin verdiği bilgileri kullanarak hızlı ve kişiselleştirilmiş koçluk sağlamaktır.

**Tarih:** 22 Eylül 2026

## D-012 — Eğitim Öncesi ve Sonrası Sabit Benchmark

EduCoach'un gerçekten gelişip gelişmediği yalnızca örnek cevaplara bakılarak değerlendirilmeyecek.

Fine-tuning öncesinde temel model sabit bir benchmark üzerinde çalıştırılacak ve sonuçları değiştirilmeyen bir baseline dosyasında saklanacak.

Fine-tuning sonrasında aynı benchmark, mümkün olduğunca aynı üretim ayarlarıyla yeniden çalıştırılacak.

Karşılaştırmada özellikle şu davranışlar incelenecek:

- öğrencinin verdiği bilgiyi doğru kullanma
- aynı bilgiyi tekrar sormama
- yeterli bilgi geldiğinde harekete geçme
- YKS terminolojisini doğru kullanma
- TYT / AYT net, puan ve sıralama kavramlarını ayırma
- gerçekçi plan üretme
- süre hesabı
- gereksiz varsayım yapmama
- Türkçe cevap tutarlılığı
- sabırsız öğrenci yönetimi

Baseline dosyaları geriye dönük olarak değiştirilmeyecek.

Amaç:
Modelin başlangıç noktası ile eğitim sonrası durumu ölçülebilir biçimde karşılaştırmak.

**Tarih:** 22 Eylül 2026


## D-013 — İlk QLoRA Pilot Eğitimi Sonucu

Qwen/Qwen3-4B modeli Gold Dataset v0.3 içindeki 38 örnekle ilk kez QLoRA yöntemiyle eğitildi.

Pilot eğitim ayarları:

- 4-bit QLoRA
- 3 epoch
- learning rate: 0.0002
- LoRA rank: 16
- LoRA alpha: 32
- BF16
- RTX 5070 Ti 16 GB

Eğitim teknik olarak başarıyla tamamlandı.

Eğitim loss değeri yaklaşık olarak:

3.049 → 1.74

seviyesine düştü.

Ancak aynı 20 benchmark senaryosu üzerinde yapılan eğitim öncesi ve eğitim sonrası karşılaştırmada model davranışının genel olarak iyileşmediği görüldü.

Gözlenen başlıca problemler:

- bazı cevaplarda tekrar döngülerinin oluşması
- öğrencinin verdiği bilgiyi yanlış yorumlama
- TYT net / puan kavramlarını karıştırma
- temelsiz sonuç veya net artışı tahminleri
- bazı senaryolarda plan üretmek yerine kullanıcının ifadesini tekrar etme
- bazı benchmark örneklerinde eğitim öncesi modele göre daha kötü sonuç verme

Karar:

qwen3_4b_qlora_v01 adapterı silinmeyecek.

Bu adapter, ilk pilot deney ve karşılaştırma referansı olarak korunacaktır.

İkinci pilot eğitimde:

- Gold Dataset büyütülecek
- eğitim örneklerinin çeşitliliği artırılacak
- tekrar eden cevap kalıpları azaltılacak
- YKS terminolojisi daha güçlü biçimde temsil edilecek
- çok turlu örneklerin oranı artırılacak
- learning rate düşürülecek
- epoch sayısı yeniden değerlendirilecek

Amaç yalnızca training loss değerini düşürmek değil, sabit benchmark üzerinde ölçülebilir davranış gelişimi elde etmektir.







## Yeni Karar Ekleme Formatı

Her önemli karar aşağıdaki formatta eklenmelidir:

```text
## D-XXX — Başlık

Karar:

Alternatifler:

Gerekçe:

Tarih:
```


