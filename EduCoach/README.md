# EduCoach

**EduCoach**, öğrencilerin çalışma süreçlerini kişiselleştiren, performanslarını analiz eden ve onlara sürdürülebilir çalışma alışkanlıkları kazandırmayı hedefleyen yerel bir yapay zekâ eğitim koçu projesidir.

Projenin amacı yalnızca soruları çözen veya ders anlatan başka bir yapay zekâ oluşturmak değildir. EduCoach'un temel görevi, öğrenciyi tanımak, doğru soruları sormak, ihtiyaçlarını belirlemek ve öğrencinin gelişimine göre çalışma sürecini yönetmektir.

---

## 🎯 Projenin Amacı

EduCoach öğrencinin:

* akademik hedeflerini belirlemesine,
* mevcut durumunu analiz etmesine,
* eksiklerini fark etmesine,
* günlük ve haftalık çalışma programı oluşturmasına,
* deneme sınavı sonuçlarını değerlendirmesine,
* ders ve konu önceliklerini belirlemesine,
* çalışma alışkanlıklarını geliştirmesine,
* motivasyon ve erteleme problemlerini yönetmesine,
* yaptığı hatalardan öğrenmesine,
* çalışma planını performansına göre sürekli güncellemesine

yardımcı olan kişisel bir eğitim koçu olarak tasarlanmaktadır.

EduCoach'un hedefi öğrencinin yerine karar vermek değil, öğrencinin **daha doğru kararlar verebilmesini sağlayan bir rehber** olmaktır.

---

# 🧠 Temel Mimari

EduCoach üç ana katmandan oluşacaktır.

```text
                    EduCoach
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   COACH BRAIN      KNOWLEDGE     STUDENT MEMORY
   Fine-Tuning         RAG           Database
        │              │              │
        │              │              │
 Koçluk davranışı   Ders bilgisi   Öğrenci profili
 Planlama           Müfredat       Deneme geçmişi
 Hata analizi       Kaynaklar      Çalışma geçmişi
 Motivasyon         Kazanımlar     Hedefler
```

## 1. Coach Brain

Temel dil modeli **Qwen3-4B** olacaktır.

Model QLoRA/Fine-Tuning yöntemiyle özellikle eğitim koçluğu davranışları konusunda geliştirilecektir.

Fine-tuning'in amacı modele bütün dersleri yeniden öğretmek değildir.

Model özellikle şunları öğrenmelidir:

* doğru soruları sormak,
* öğrencinin problemini teşhis etmek,
* çalışma planı hazırlamak,
* öncelik belirlemek,
* öğrencinin yanlış çalışma alışkanlıklarını fark etmek,
* gerektiğinde ipucu vermek,
* öğrenciyi düşündürmek,
* öğrencinin seviyesine göre iletişim kurmak,
* gerçekçi hedefler oluşturmak,
* geçmiş performansa göre önerilerini değiştirmek.

---

## 2. Knowledge — RAG

Ders ve müfredat bilgileri mümkün olduğunca modelin ağırlıklarına gömülmeyecektir.

Bunun yerine ilerleyen aşamalarda RAG sistemi kullanılacaktır.

Örnek bilgi kaynakları:

* Matematik
* Türkçe
* Fen Bilimleri
* Sosyal Bilgiler
* İngilizce
* LGS
* TYT
* AYT
* MEB kazanımları
* konu anlatımları
* ders notları
* formüller
* soru bankaları

Bu yaklaşım sayesinde bilgi kaynakları güncellendiğinde modeli yeniden eğitmek gerekmeyecektir.

---

## 3. Student Memory

EduCoach'un en önemli parçalarından biri kişiselleştirilmiş öğrenci hafızası olacaktır.

Örneğin sistem bir öğrenci için şunları tutabilir:

```text
Öğrenci: Ali

Sınıf: 8
Hedef: LGS 440+

Son denemeler:
Türkçe: 17 net
Matematik: 12 net
Fen: 16 net

Zayıf alan:
Matematik problemleri

Son çalışma:
Üslü ifadeler tamamlandı.

Sonraki hedef:
Problem çözme becerisi
```

Böylece öğrenci:

> Bugün ne çalışmalıyım?

diye sorduğunda model genel bir cevap vermek yerine öğrencinin geçmişine göre öneri oluşturabilir.

---

# 🤖 Temel Model

İlk geliştirme modeli:

```text
Qwen3-4B
```

İlk karşılaştırmalarda:

```text
Qwen3-4B
Phi-4-mini
```

modelleri test edilmiştir.

Türkçe anlatım, talimat takibi ve genel cevap kalitesi açısından proje için başlangıç modeli olarak **Qwen3-4B** seçilmiştir.

---

# 🧪 Eğitim Yöntemi

İlk eğitim yöntemi:

```text
QLoRA
```

olacaktır.

Amaç düşük VRAM kullanımıyla temel modelin eğitim koçluğu davranışlarını geliştirmektir.

Planlanan ilk sürüm:

```text
Qwen3-4B
   +
QLoRA
   +
EduCoach Training Dataset
   =
EduCoach v0.1
```

---

# 📚 Eğitim Verisi Stratejisi

Doğrudan binlerce örnek üretmek yerine önce küçük fakat yüksek kaliteli bir **Gold Dataset** oluşturulacaktır.

İlk hedef:

```text
20–30 Gold Example
```

Bu örnekler proje için davranış standardını belirleyecektir.

Sonrasında kontrollü şekilde:

```text
30
 ↓
100
 ↓
300
 ↓
500
 ↓
1000+
```

örneğe çıkılması planlanmaktadır.

Eğitim verisinin ana kategorileri:

* öğrenci durumunu analiz etme,
* hedef belirleme,
* çalışma programı hazırlama,
* ders bazlı çalışma stratejileri,
* deneme analizi,
* yanlış analiz etme,
* eksik konu tespiti,
* zaman yönetimi,
* motivasyon,
* erteleme problemi,
* öğrenciyi düşündürme,
* gerektiğinde ipucu verme,
* öğrenci seviyesine göre konuşma,
* gerçekçi olmayan hedefleri düzenleme,
* çalışma programını performansa göre değiştirme.

---

# ❌ EduCoach Ne Olmayacak?

EduCoach yalnızca:

```text
"Soruyu gönder, cevabını vereyim."
```

şeklinde çalışan bir soru çözme botu olmayacaktır.

Ayrıca bütün ders bilgilerini fine-tuning yoluyla modele ezberletmek hedeflenmemektedir.

Örneğin öğrencinin:

> Matematik netim 8. Nasıl yükseltebilirim?

sorusunda amaç yalnızca matematik konusu anlatmak değildir.

EduCoach önce öğrencinin:

* hangi konularda hata yaptığını,
* soru çözüp çözmediğini,
* süre problemi olup olmadığını,
* konu eksiği bulunup bulunmadığını,
* deneme sonuçlarının nasıl değiştiğini

anlamaya çalışmalıdır.

---

# 📊 Değerlendirme

Fine-tuning öncesinde temel Qwen modeli sabit bir benchmark setiyle test edilecektir.

Aynı testler eğitim sonrasında EduCoach modeline uygulanacaktır.

Karşılaştırılacak başlıca ölçütler:

* Türkçe kalitesi
* koçluk davranışı
* öğrenci seviyesine uygunluk
* doğru soru sorma
* problemi teşhis etme
* çalışma planı kalitesi
* gereksiz uzunluk
* talimata uyma
* tutarlılık
* kişiselleştirme

Amaç yalnızca eğitim kaybının düşmesi değil, gerçek kullanıcı deneyiminde ölçülebilir iyileşme sağlamaktır.

---

# 🔁 Geliştirme Döngüsü

EduCoach sürekli aşağıdaki döngüyle geliştirilecektir:

```text
MODEL
  ↓
TEST
  ↓
HATA ANALİZİ
  ↓
YENİ / DÜZELTİLMİŞ VERİ
  ↓
EĞİTİM
  ↓
TEKRAR TEST
```

Başarısız cevaplar özellikle saklanacak ve sonraki eğitim sürümlerinde veri üretmek için kullanılacaktır.

---

# 🗂️ Proje Yapısı

```text
AI-Training/
│
└── EduCoach/
    │
    ├── README.md
    ├── CURRENT_STATUS.md
    │
    ├── configs/
    │
    ├── data/
    │   ├── gold/
    │   ├── train/
    │   ├── validation/
    │   └── test/
    │
    ├── docs/
    │   ├── ROADMAP.md
    │   └── BEHAVIOR_SPEC.md
    │
    ├── evaluations/
    │
    ├── notes/
    │   └── DECISIONS.md
    │
    ├── prompts/
    │
    └── scripts/
```

---

# 💻 Geliştirme Ortamı

Proje iki bilgisayar arasında Git/GitHub üzerinden geliştirilmektedir.

### Laptop

Temel olarak:

* proje tasarımı,
* veri hazırlama,
* veri inceleme,
* prompt geliştirme,
* dokümantasyon,
* benchmark hazırlama

işleri için kullanılacaktır.

### GPU Masaüstü

Temel olarak:

* QLoRA eğitimi,
* GPU testleri,
* model değerlendirme,
* checkpoint üretme,
* model dönüştürme,
* Ollama entegrasyonu

için kullanılacaktır.

---

# 🔐 Repository

Repository private olarak tutulmaktadır.

Büyük model dosyaları, checkpointler ve geçici eğitim çıktıları Git repository içerisine eklenmeyecektir.

Git temel olarak:

* kaynak kod,
* eğitim verisi,
* config dosyaları,
* değerlendirme sonuçları,
* dokümantasyon,
* proje kararları

için kullanılacaktır.

---

# 🗺️ Yol Haritası

```text
FAZ 0 — Proje altyapısı
         ✅ Git repository
         ✅ Klasör yapısı

FAZ 1 — EduCoach davranış şartnamesi
         ✅ Temel yön belirlendi

FAZ 2 — Gold Dataset
         ⏳ 20–30 kaliteli örnek

FAZ 3 — Baseline Benchmark
         ⏳ Qwen3-4B başlangıç ölçümü

FAZ 4 — Dataset genişletme
         ⏳ 100–1000+ örnek

FAZ 5 — İlk QLoRA eğitimi
         ⏳ EduCoach v0.1

FAZ 6 — Eğitim sonrası benchmark

FAZ 7 — Hata analizi

FAZ 8 — EduCoach v0.2

FAZ 9 — RAG

FAZ 10 — Student Memory

FAZ 11 — Uygulama entegrasyonu
```

---

# 🚧 Mevcut Durum

Şu anda proje:

```text
FAZ 1 → FAZ 2 geçişinde
```

bulunmaktadır.

Bir sonraki ana görev:

> EduCoach'un koçluk davranışını temsil eden ilk 20–30 Gold Dataset örneğini oluşturmak.

Güncel ilerleme için:

```text
CURRENT_STATUS.md
```

dosyasına bakılmalıdır.

Önemli mimari kararlar için:

```text
notes/DECISIONS.md
```

dosyası kullanılmaktadır.

---

## Vizyon

EduCoach'un nihai hedefi öğrenciye yalnızca bilgi veren bir yapay zekâ olmak değildir.

Amaç;

**öğrenciyi tanıyan, gelişimini takip eden, ne zaman ne çalışması gerektiğini anlayan ve zaman içerisinde öğrenciyi daha bağımsız bir öğrenen haline getiren kişisel bir eğitim koçu oluşturmaktır.**
