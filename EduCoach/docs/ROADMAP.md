# EduCoach — Product & Architecture Roadmap

**Güncelleme:** 2 Ekim 2026

## Amaç

EduCoach'un ilk üretim sürümünü aşağıdaki mimari üzerine kurmak:

```text
LLM
+
Student Memory
+
Backend Rules
+
RAG / Knowledge
+
Response Validator
```

Fine-tuning şu aşamada aktif geliştirme yolu değildir. Mevcut QLoRA deneyleri araştırma ve karşılaştırma amacıyla korunacaktır.

\---

# FAZ 0 — Mimariyi Kilitle

**Durum:** Aktif

Amaç:

Kod yazmaya başlamadan önce sistem bileşenlerinin sorumluluklarını kesinleştirmek.

Karar verilecek konular:

\- uygulama klasör yapısı
\- orchestrator sorumlulukları
\- LLM provider arayüzü
\- Student Memory veri modeli
\- backend kuralları
\- response validator
\- RAG sınırları
\- knowledge base formatı
\- ilk veritabanı
\- evaluation stratejisi

Çıkış kriteri:

```text
Her bileşenin ne yaptığı ve ne yapmadığı açıkça tanımlanmış olacak.
```

\---

# FAZ 1 — Uygulama İskeleti

Amaç:

Fine-tuning kodundan bağımsız çalışan gerçek EduCoach uygulama katmanını oluşturmak.

Planlanan ana yapı:

```text
app/
├── orchestrator/
├── llm/
├── student\_memory/
├── rules/
├── validators/
├── rag/
└── models/
```

İlk aşamada:

\- web arayüzü yapılmayacak,
\- mobil uygulama yapılmayacak,
\- yalnız backend çekirdeği oluşturulacak.

Çıkış kriteri:

Basit bir terminal komutuyla EduCoach çekirdeğine kullanıcı mesajı gönderilebilmeli ve cevap alınabilmeli.

\---

# FAZ 2 — LLM Provider Katmanı

Amaç:

EduCoach'u tek modele bağımlı olmaktan çıkarmak.

Örnek provider yapısı:

```text
LLMProvider
├── LocalQwenProvider
├── OpenAIProvider
├── GeminiProvider
└── FutureProvider
```

İlk prototipte yalnız bir provider aktif olabilir.

Ancak orchestrator doğrudan belirli modele bağlı yazılmayacaktır.

Çıkış kriteri:

Provider değiştirmek için EduCoach'un diğer bileşenlerinin değiştirilmesine gerek kalmamalı.

\---

# FAZ 3 — Student Memory

Amaç:

Öğrencinin gerçek durumunu modelin sohbet hafızasına bırakmamak.

İlk öğrenci profili alanları:

```text
student\_id
grade\_status
field
target
daily\_available\_minutes
weekly\_schedule
tyt\_current
ayt\_current
subject\_performance
strong\_areas
weak\_areas
constraints
preferences
```

Zamanla eklenecek veriler:

```text
exam\_history
study\_history
assignments
completed\_tasks
study\_plans
plan\_completion
mistake\_patterns
topic\_progress
```

İlk prototip için mümkün olduğunca basit bir veritabanı kullanılacaktır.

Çıkış kriteri:

Öğrencinin daha önce verdiği temel bilgiler yeni mesajlarda yeniden sorulmadan kullanılabilmeli.

\---

# FAZ 4 — Backend Rules

Amaç:

Kesin ve hesaplanabilir kuralları LLM'in insafına bırakmamak.

İlk kurallar:

### Süre doğrulama

```text
Kullanıcı 5 saat diyorsa:
plan toplamı <= 300 dakika
```

### Net / puan ayrımı

```text
TYT net != TYT puan
AYT net != AYT puan
```

### Bilinmeyen veriyi uydurmama

Model şu tür değerleri kendiliğinden üretememeli:

```text
bilinmeyen ders neti
bilinmeyen deneme sonucu
bilinmeyen çalışma süresi
bilinmeyen hedef net
bilinmeyen konu eksikleri
```

### Öğrenci profilini koruma

Örneğin:

```text
eşit ağırlık öğrencisini sayısal öğrenci gibi planlama
mezun öğrenciyi 12. sınıf gibi değerlendirme
```

Çıkış kriteri:

Kritik yanlışlar LLM cevabından bağımsız şekilde tespit edilebilmeli.

\---

# FAZ 5 — Response Validator

Amaç:

LLM çıktısını doğrudan öğrenciye göndermeden önce kontrol etmek.

İlk kontroller:

\- süre toplamı
\- tekrar döngüsü
\- aşırı uzun cevap
\- uydurma sayılar
\- net / puan karışıklığı
\- öğrenci profiliyle çelişki
\- mevcut Student Memory ile çelişki
\- kritik varsayımlar
\- eksik veya bozuk plan yapısı

Validator mümkün olduğunca deterministik olacaktır.

Her hatada yeniden LLM çağrısı yapmak zorunlu değildir.

Bazı hatalar backend tarafından düzeltilebilir.

Çıkış kriteri:

Daha önce fine-tuning deneylerinde görülen temel hataların büyük bölümü otomatik yakalanabilmeli.

\---

# FAZ 6 — İlk RAG Altyapısı

Amaç:

Bilgi ile öğrenci hafızasını birbirinden ayırmak.

RAG'in görevi:

```text
"Bu öğrenci kim?"
```

sorusunu cevaplamak değildir.

Bu Student Memory'nin görevidir.

RAG şu tür sorular için kullanılacaktır:

```text
YKS sistemi nedir?
TYT / AYT yapısı nedir?
Bir konunun ön koşulları nelerdir?
Deneme analizi nasıl yapılır?
Bir çalışma yöntemi hangi durumda kullanılmalıdır?
```

İlk RAG kapsamı küçük tutulacaktır.

Çıkış kriteri:

EduCoach gerektiğinde ilgili bilgi parçasını bulup LLM bağlamına ekleyebilmeli.

\---

# FAZ 7 — Knowledge Base v0.1

İlk bilgi tabanı kontrollü ve küçük olacaktır.

Önerilen ilk alanlar:

```text
YKS temel yapısı
TYT / AYT ayrımı
eşit ağırlık / sayısal / sözel
ders ve konu hiyerarşileri
çalışma planlama prensipleri
deneme analizi
yanlış analizi
tekrar yöntemleri
zaman yönetimi
```

Kaynak bilgileri daha sonra eklenebilir.

Knowledge Base oluşturulurken:

\- kaynak kaydı tutulmalı,
\- belge sürümü tutulmalı,
\- mümkün olduğunca küçük parçalara bölünmeli,
\- metadata kullanılmalı.

Çıkış kriteri:

İlk gerçek RAG sorguları doğru parçaları getirmeli.

\---

# FAZ 8 — Orchestrator

Amaç:

Bütün bileşenleri tek akışta birleştirmek.

Örnek akış:

```text
1\. Kullanıcı mesajını al
2\. Öğrenci profilini yükle
3\. Mesajdan yeni gerçekleri çıkar
4\. Student Memory'yi güncelle
5\. İstek türünü belirle
6\. Gerekirse RAG çağır
7\. Backend kurallarını hazırla
8\. LLM context oluştur
9\. LLM cevabını üret
10\. Response Validator çalıştır
11\. Gerekirse düzelt
12\. Son cevabı kullanıcıya gönder
13\. Gerekli sonucu hafızaya kaydet
```

Çıkış kriteri:

Gerçek bir öğrenci konuşması uçtan uca çalışabilmeli.

\---

# FAZ 9 — Regression Evaluation

Mevcut:

```text
evaluations/holdout/benchmark\_v0.2.jsonl
```

artık final unseen benchmark değildir.

Yeni rolü:

```text
regression / diagnostic set
```

Bu set:

\- geçmiş hataların geri gelip gelmediğini,
\- loop davranışını,
\- öğrenci bilgisinin kullanımını,
\- net / puan hatalarını

kontrol etmek için kullanılacaktır.

Çıkış kriteri:

Yeni mimaride geçmişte bulunan hatalar sistematik olarak tekrar test edilebilmeli.

\---

# FAZ 10 — Development Evaluation Set

Yeni bir development benchmark hazırlanacaktır.

Bu set:

\- mimari geliştirme,
\- prompt değiştirme,
\- RAG ayarlama,
\- validator geliştirme

sırasında kullanılabilir.

Development set, final değerlendirme için kullanılmayacaktır.

\---

# FAZ 11 — Gerçek Öğrenci Senaryoları

Sistem şu senaryolarda test edilecektir:

\- ilk kez gelen öğrenci
\- sabırsız öğrenci
\- eksik bilgi veren öğrenci
\- geçmiş denemeleri olan öğrenci
\- çalışma süresi değişen öğrenci
\- hedef değiştiren öğrenci
\- programını uygulamayan öğrenci
\- düzenli ilerleyen öğrenci
\- sınava kısa süre kalan öğrenci
\- bir derste ciddi düşüş yaşayan öğrenci

Amaç tek cevap kalitesi değil, zaman içinde koçluk kalitesidir.

\---

# FAZ 12 — Final Unseen Evaluation

Bu aşama ancak:

\- mimari büyük ölçüde dondurulduğunda,
\- development kararları tamamlandığında,
\- regression testleri geçtiğinde

başlatılacaktır.

Final benchmark:

\- Gold Dataset'ten türetilmeyecek,
\- development benchmark ile örtüşmeyecek,
\- geliştirme sırasında sonuçları incelenmeyecek.

Amaç gerçek genelleme performansını ölçmektir.

\---

# FAZ 13 — Fine-Tuning Karar Noktası

Fine-tuning ancak sistem çalışır hale geldikten sonra yeniden değerlendirilecektir.

Sorulacak soru:

```text
Mevcut sistemde kalan hangi problem,
prompt + rules + memory + RAG ile çözülemiyor?
```

Eğer net bir davranış problemi kalırsa fine-tuning yeniden düşünülebilir.

Yeni fine-tuning yapılacaksa:

\- mevcut 120 örnek doğrudan yeterli kabul edilmeyecek,
\- near-duplicate analizi yapılacak,
\- daha çeşitli gerçek öğrenci konuşmaları kullanılacak,
\- development ve final setler eğitimden ayrı tutulacak,
\- küçük kontrollü deneylerle ilerlenilecek.

Fine-tuning ürün mimarisinin zorunlu parçası olmayacaktır.

\---

# Geliştirme İlkesi

Her faz için:

```text
Gerçek mevcut durumu incele
→ küçük değişiklik yap
→ test et
→ kanıt topla
→ commit et
→ sonraki faza geç
```

Büyük değişiklikler tek seferde yapılmayacaktır.

Basit işlemler terminal üzerinden yürütülecektir.

Büyük repository incelemeleri veya çok dosyalı refactor gerektiğinde Codex ya da Cursor kullanılabilir.

\---

# Şu Anki Aktif İş

```text
FAZ 0 — Mimariyi Kilitle
```

Bir sonraki kararlar:

1\. `app/` modül yapısı
2\. Student Memory veri modeli
3\. ilk veritabanı tercihi
4\. LLM provider sözleşmesi
5\. Backend Rules sınırı
6\. Response Validator sınırı
7\. RAG v0.1 kapsamı

Bu kararlar verilmeden büyük kodlama başlamayacaktır.
