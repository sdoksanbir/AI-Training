# EduCoach — Orchestrator v0.1
**Tarih:** 2 Ekim 2026
**Durum:** Mimari Tasarım
---
# 1. Amaç
Orchestrator, EduCoach'un ana karar akışını yöneten katmandır.
Orchestrator:
- LLM değildir,
- veritabanı değildir,
- RAG değildir,
- uzmanlık profili değildir,
- validator değildir.
Görevi bu bileşenlerin doğru sırada ve doğru veriyle çalışmasını sağlamaktır.
Temel akış:
```text
Kullanıcı mesajı
      ↓
Orchestrator
      ↓
Learner Memory
      ↓
Context / Specialty seçimi
      ↓
İstek analizi
      ↓
Gerekli kurallar
      ↓
Gerekirse RAG
      ↓
LLM
      ↓
Validator
      ↓
Memory güncelleme
      ↓
Kullanıcı cevabı
```
---
# 2. Ana Mimari İlkesi
EduCoach'ta LLM tek karar verici olmayacaktır.
Temel ayrım:
```text
Orchestrator
→ ne yapılacağını yönetir
LLM
→ verilen bağlam üzerinde yorum ve doğal dil üretir
Rules
→ kesin kuralları uygular
Learner Memory
→ kullanıcı hakkında doğrulanmış bilgiyi sağlar
Specialty Profile
→ eğitim bağlamının nasıl çalıştığını açıklar
RAG
→ ortak eğitim bilgisini getirir
Validator
→ üretilen cevabı kontrol eder
```
---
# 3. Orchestrator'ın Sorumlulukları
Orchestrator aşağıdaki sorumlulukları üstlenir:
1. Kullanıcı ve oturum bilgisini belirlemek.
2. Learner Memory'yi yüklemek.
3. Aktif Learning Context'leri bulmak.
4. Mesajın hangi bağlamla ilgili olduğunu belirlemek.
5. Kullanıcı mesajından yeni olası gerçekleri çıkarmak.
6. Bu bilgilerin Memory'ye yazılabilir olup olmadığını belirlemek.
7. Kullanıcının isteğinin türünü belirlemek.
8. RAG gerekip gerekmediğini belirlemek.
9. Uygulanacak Core ve Specialty kurallarını toplamak.
10. LLM'e verilecek bağlamı oluşturmak.
11. LLM cevabını almak.
12. Cevabı validator'lardan geçirmek.
13. Gerekirse güvenli düzeltme yapmak veya yeniden üretim istemek.
14. Kalıcı hale gelmesi gereken yeni bilgileri kaydetmek.
15. Son cevabı kullanıcıya göndermek.
---
# 4. Orchestrator'ın Yapmayacağı Şeyler
Orchestrator:
- kendi başına pedagojik içerik uydurmayacak,
- model gibi serbest metin üretmeyecek,
- bilinmeyen öğrenci bilgisini tahmin etmeyecek,
- sınav bilgilerini kod içine gömmeyecek,
- bütün sohbet geçmişini her istekte modele vermeyecek,
- her mesajda otomatik olarak RAG çağırmayacak,
- her LLM çıktısını olduğu gibi kullanıcıya göndermeyecek.
---
# 5. Request Pipeline
Her kullanıcı mesajı aşağıdaki işlem hattından geçecektir.
```text
1. Request alınır
2. Learner yüklenir
3. Aktif context'ler yüklenir
4. Mesaj analiz edilir
5. Context routing yapılır
6. Intent belirlenir
7. Memory facts çıkarılır
8. Gerekli memory verileri seçilir
9. Specialty Profile yüklenir
10. Rules hazırlanır
11. RAG ihtiyacı değerlendirilir
12. Gerekirse retrieval yapılır
13. LLM context oluşturulur
14. LLM çağrılır
15. Response Validator çalışır
16. Gerekirse düzeltme uygulanır
17. Memory update yapılır
18. Audit kaydı oluşturulur
19. Cevap döndürülür
```
---
# 6. Context Routing
Bir kullanıcının aynı anda birden fazla Learning Context'i olabilir.
Örnek:
```text
school_11
yks
```
veya:
```text
kpss
yds
```
Bu nedenle her mesaj için ilgili context seçilmelidir.
Örnek:
Kullanıcı:
```text
"Yarın matematik yazılım var."
```
Muhtemel context:
```text
school_11
```
Kullanıcı:
```text
"TYT matematik denemesinde son 10 soruya yetişemedim."
```
Context:
```text
yks
```
---
# 7. Context Seçiminde Kullanılacak Bilgiler
Orchestrator şu bilgileri birlikte değerlendirebilir:
```text
mesaj içeriği
aktif Learning Context'ler
aktif hedef
aktif çalışma planı
yakın konuşma bağlamı
Specialty Profile terminolojisi
```
Tek bir kelimeye bakarak context seçilmemelidir.
---
# 8. Belirsiz Context
Context kesin belirlenemiyorsa sistem şu sırayı izler:
```text
1. Mevcut Memory'yi kontrol et
2. Aktif hedefi kontrol et
3. Yakın konuşma bağlamını kontrol et
4. Yüksek olasılıkla tek context varsa kullan
5. Kritik yanlış risk varsa kısa açıklayıcı soru sor
```
EduCoach gereksiz yere her durumda soru sormamalıdır.
---
# 9. Intent
Mesajın ne istediği belirlenmelidir.
İlk intent ailesi:
```text
planning
progress_review
assessment_analysis
goal_setting
study_advice
knowledge_question
memory_update
task_update
motivation_support
clarification
general_conversation
```
Bu liste zamanla genişletilebilir.
Intent sistemin nasıl cevap vereceğini tek başına belirlemez.
---
# 10. Bir Mesaj Birden Fazla Intent İçerebilir
Örneğin:
```text
"Son denememde matematik düştü. Bu hafta ne çalışayım?"
```
şunları içerebilir:
```text
assessment_analysis
+
planning
```
Orchestrator birden fazla intent'i işleyebilmelidir.
---
# 11. Memory Fact Extraction
Kullanıcı mesajından yeni bilgiler çıkarılabilir.
Örnek:
```text
"11. sınıfım ve artık hafta içi sadece 2 saat çalışabiliyorum."
```
Aday facts:
```text
grade_level = 11
weekday_available_minutes = 120
```
Ancak LLM'in çıkardığı her bilgi doğrudan veritabanına yazılmayacaktır.
---
# 12. Fact Durumları
Memory'ye eklenmek üzere çıkarılan bilgiler şu durumlardan birinde olabilir:
```text
explicit
derived
inferred
uncertain
```
### explicit
Kullanıcı açıkça söyledi.
### derived
Kesin bir hesap veya yapılandırılmış kaynaktan elde edildi.
### inferred
Sistem yorumladı.
### uncertain
Birden fazla yoruma açık.
---
# 13. Memory Yazma Politikası
Varsayılan politika:
```text
explicit
→ yazılabilir
derived
→ kaynak güvenilir ise yazılabilir
inferred
→ gerçek bilgi olarak yazılmaz
uncertain
→ gerçek bilgi olarak yazılmaz
```
Bu politika alan türüne göre daha da sıkılaştırılabilir.
---
# 14. Memory Güncelleme Zamanı
Kalıcı Memory güncellemesi mümkün olduğunca:
```text
LLM cevabından önce aday olarak hazırlanır
ama
işlem başarıyla tamamlandıktan sonra commit edilir
```
Bu sayede yarım kalan veya hatalı işlem yanlış memory üretmez.
---
# 15. Mevcut Bilgiyi Tekrar Sormama
Orchestrator LLM çağrısından önce eksik bilgiler ile bilinen bilgileri ayırmalıdır.
Örneğin Learner Memory'de:
```text
grade_level = 11
field = equal_weight
daily_available_minutes = 180
```
zaten varsa LLM'e şu açıkça verilmelidir:
```text
Bu bilgiler bilinmektedir.
Kullanıcıdan tekrar isteme.
```
---
# 16. Minimum Necessary Information
EduCoach her görev için bütün kullanıcı profilini istemeyecektir.
Örneğin:
```text
"Bugün ne çalışayım?"
```
için gerekli bilgi ile:
```text
"6 aylık YKS programı hazırla."
```
için gerekli bilgi aynı değildir.
Her intent için:
```text
minimum_required_fields
useful_optional_fields
```
tanımlanabilir.
---
# 17. Eksik Bilgi Kararı
Eksik bilgi olduğunda üç seçenek vardır:
```text
ASK
ACT_WITH_ASSUMPTION
ACT_WITHOUT_PERSONALIZATION
```
### ASK
Kritik bilgi olmadan doğru cevap verilemez.
### ACT_WITH_ASSUMPTION
Makul ve düşük riskli varsayım yapılabilir.
Varsayım kullanıcıya açıkça belirtilmelidir.
### ACT_WITHOUT_PERSONALIZATION
Kişiselleştirme uydurmak yerine geçici genel plan verilir.
---
# 18. Örnek
Kullanıcı:
```text
"Bana bugün için çalışma programı yap."
```
Memory:
```text
daily_available_minutes = bilinmiyor
```
Burada toplam süre kritikse kısa bir soru gerekebilir.
Ancak kullanıcı:
```text
"Çok vaktim yok, bana hemen başlayabileceğim kısa bir plan ver."
```
derse Orchestrator:
```text
ACT_WITHOUT_PERSONALIZATION
```
seçebilir ve kısa başlangıç planı sunabilir.
---
# 19. RAG Gating
RAG her mesajda kullanılmayacaktır.
Orchestrator şu soruyu sorar:
```text
Bu cevabı vermek için dış eğitim bilgisine ihtiyaç var mı?
```
---
# 20. RAG Gerekmeyen Örnekler
```text
"Bugün 3 saatim var, programımı 3 saate indir."
```
Gerekli bilgiler Learner Memory ve mevcut plan içinde olabilir.
RAG gerekmeyebilir.
---
# 21. RAG Gereken Örnekler
```text
"Bu konuya başlamadan önce hangi konuları bilmeliyim?"
```
veya:
```text
"Bu sınavın güncel yapısı nedir?"
```
RAG gerekebilir.
---
# 22. RAG Arama Kapsamı
Orchestrator retrieval isteğine şu filtreleri ekleyebilir:
```text
active_profile
grade_level
exam
subject
topic
curriculum_version
source_validity
```
Bu sayede ilgisiz bilgi getirilmesi azaltılır.
---
# 23. RAG Sonucu Yoksa
RAG yeterli bilgi getirmediyse LLM'e bilinmeyen bilgiyi doldurtmayacağız.
Sistem:
```text
yeterli doğrulanmış bilgi yok
```
durumunu taşıyacaktır.
LLM bunu kesin bilgi gibi tamamlamamalıdır.
---
# 24. Rules Assembly
Orchestrator her istek için uygulanacak kuralları toplar.
Kaynaklar:
```text
Core Rules
+
Specialty Profile Rules
+
Intent Rules
+
Learner Constraints
```
Örnek:
```text
Core:
bilinmeyen bilgi uydurma
YKS:
net ile puanı karıştırma
Learner:
bugün maksimum 180 dakika
Planning:
toplam süre 180 dakikayı aşmasın
```
---
# 25. LLM Context Builder
LLM'e bütün veritabanı gönderilmeyecektir.
Yalnızca mevcut görev için gerekli bilgiler gönderilecektir.
Önerilen context bölümleri:
```text
SYSTEM BEHAVIOR
ACTIVE LEARNER FACTS
ACTIVE CONTEXT
GOAL
RECENT RELEVANT PERFORMANCE
CURRENT PLAN
HARD CONSTRAINTS
RETRIEVED KNOWLEDGE
USER MESSAGE
OUTPUT REQUIREMENTS
```
---
# 26. Hard Facts ve Soft Signals Ayrımı
LLM context'inde bunlar açıkça ayrılmalıdır.
Örnek:
```text
HARD FACTS
- 11. sınıf
- bugün 180 dakika müsait
- TYT son deneme 72 net
SOFT SIGNALS
- matematik performansında düşüş olabilir
- öğrenci son mesajlarda yorgunluk belirtti
```
Model soft signal'ı gerçek bilgi gibi kullanmamalıdır.
---
# 27. LLM'in Yapabileceği Kararlar
LLM şu alanlarda kullanılabilir:
```text
öğrenci mesajını anlamlandırma
koçluk dili oluşturma
plan önerisi taslağı üretme
öncelik önerme
verilen performans verilerini yorumlama
öğrenciye açıklama yapma
uygun soru biçimi oluşturma
motivasyon ve iletişim tonu
```
---
# 28. LLM'e Bırakılmayacak Kararlar
Mümkün olduğunca deterministik olarak yönetilecek alanlar:
```text
öğrenci kimliği
aktif context listesi
kesin müsait süre
mevcut kayıtlı net
mevcut kayıtlı puan
plan toplam süresi
bilginin kaynağı
assessment geçmişi
profile configuration
veri yazma işlemi
yetkilendirme
RAG kaynak filtresi
```
---
# 29. Plan Üretiminde Yapılandırılmış Çıktı
Plan oluşturma gibi kritik işlemlerde LLM'in yalnız serbest metin üretmesi tercih edilmeyecektir.
Örneğin LLM önce yapılandırılmış taslak üretebilir:
```text
tasks:
  - area: mathematics
    duration_minutes: 60
  - area: literature
    duration_minutes: 45
  - area: review
    duration_minutes: 30
```
Backend bu yapıyı doğrular.
Ardından kullanıcıya doğal dil cevabı oluşturulur.
---
# 30. Neden Yapılandırılmış Çıktı?
Şu tür hataları daha kolay yakalamak için:
```text
süre toplamı hatası
olmayan ders
olmayan context
uydurma sayı
geçersiz task type
eksik plan alanı
```
---
# 31. Response Validator
LLM çıktısı kullanıcıya gitmeden önce doğrulanacaktır.
Validator katmanları:
```text
Schema Validation
Rule Validation
Memory Consistency
Specialty Validation
Repetition Detection
Numeric Validation
Output Quality Checks
```
---
# 32. Validator Sonuçları
Validator şu sonuçlardan birini döndürebilir:
```text
PASS
AUTO_FIX
REGENERATE
BLOCK
```
### PASS
Cevap gönderilebilir.
### AUTO_FIX
Deterministik küçük hata backend tarafından düzeltilebilir.
### REGENERATE
LLM'den kontrollü yeniden üretim istenir.
### BLOCK
Güvenilir cevap üretilemedi.
---
# 33. Auto-Fix Örneği
LLM planı:
```text
60 + 60 + 75 = 195 dakika
```
Öğrencinin sınırı:
```text
180 dakika
```
Backend mümkünse süreleri belirlenmiş politika ile yeniden dağıtabilir.
Ancak pedagojik anlamı değiştirecek büyük düzenleme gerekiyorsa yeniden üretim daha doğru olabilir.
---
# 34. Regeneration Sonsuz Döngüye Girmeyecek
Controlled Regeneration v0.1 authoritative runtime policy'si:
```text
max_regeneration_attempts = 1
```
İlk generation ve en fazla bir regeneration ile request başına maksimum iki provider çağrısı yapılır. Yalnız `REGENERATE` action'ı retry tetikler; `BLOCK`, `AUTO_FIX`, structured parse hatası ve provider hatası retry edilmez. Retry aynı user message, snapshot ve memory+RAG context'i kullanır; validator violation ID/message feedback'i yalnız system prompt'a eklenir. İkinci `REGENERATE`, üçüncü çağrı yapmadan `ResponseRegenerationExhausted` üretir.
---
# 35. Fallback
Generic deterministic user-facing fallback henüz uygulanmamıştır. Güvenilir cevap tek controlled regeneration sonrasında da üretilemezse runtime fail-closed `ResponseRegenerationExhausted` boundary'sini kullanır. Fallback tasarımı ilgili intent'e özgü authoritative contract belirlendikten sonra ele alınacaktır.
---
# 36. Conversation Context
Learner Memory ile konuşma geçmişi aynı şey değildir.
Orchestrator modele gerektiğinde kısa bir yakın konuşma bağlamı verebilir.
Ancak bütün geçmiş konuşmalar her istekte kullanılmayacaktır.
---
# 37. Conversation Summary
Uzun konuşmalarda gerektiğinde:
```text
recent messages
+
structured conversation summary
```
kullanılabilir.
Bu özet Learner Memory'deki gerçeklerin yerine geçmez.
---
# 38. Audit Trail
Her önemli orchestrator çalışmasında minimum bir teknik kayıt tutulabilir.
Örnek:
```text
request_id
learner_id
selected_contexts
detected_intents
rag_used
rules_applied
validator_result
llm_provider
model
created_at
```
Bu kayıt model cevabının neden üretildiğini incelemek için değerlidir.
---
# 39. Gizli Model Muhakemesi Saklanmayacaktır
Audit sistemi LLM'in özel iç düşünce zincirini saklamaya çalışmayacaktır.
Saklanabilecek şeyler:
```text
hangi context seçildi
hangi kurallar uygulandı
hangi RAG belgeleri kullanıldı
hangi validator sonucu çıktı
```
gibi sistem seviyesinde açıklanabilir kararlardır.
---
# 40. LLM Provider Bağımsızlığı
Orchestrator:
```text
Qwen
OpenAI
Gemini
```
gibi belirli sağlayıcıları doğrudan bilmemelidir.
Bunun yerine:
```text
LLMProvider
```
arayüzünü kullanmalıdır.
---
# 41. Aynı Orchestrator Farklı Modellerle Çalışabilmeli
Örneğin:
```text
LocalQwenProvider
OpenAIProvider
GeminiProvider
```
aynı giriş sözleşmesini mümkün olduğunca desteklemelidir.
Bu sayede model değişikliği ürün mimarisini bozmaz.
---
# 42. Orchestrator State
Orchestrator mümkün olduğunca stateless tasarlanacaktır.
Kalıcı durum:
```text
database
```
içinde tutulacaktır.
Bir isteğin geçici işlem state'i bellekte bulunabilir ancak ürünün temel hafızası process memory'ye bağlı olmamalıdır.
---
# 43. Hata Yönetimi
Aşağıdaki bileşenlerin ayrı ayrı hata verebileceği kabul edilmelidir:
```text
database
RAG
LLM provider
validator
specialty registry
```
Bir bileşenin hatası tüm sistemi gereksiz yere çökertmemelidir.
---
# 44. RAG Çalışmazsa
Her istekte RAG zorunlu değildir.
RAG olmadan cevap verilebilecek bir istekse işlem devam edebilir.
RAG bilgisi kritikse kullanıcıya doğrulanmamış bilgi verilmemelidir.
---
# 45. LLM Çalışmazsa
LLM provider başarısız olduğunda ileride:
```text
retry
fallback provider
safe deterministic response
```
mekanizmaları desteklenebilir.
İlk prototipte basit hata yönetimi yeterlidir.
---
# 46. Örnek Akış — 6. Sınıf
Kullanıcı:
```text
"Yarın matematik yazılım var. Kesirlerde zorlanıyorum. Bu akşam 1,5 saatim var."
```
Orchestrator:
```text
Learner Memory
→ school_6 context
Yeni facts
→ kesirler: learner_reported weak
→ bugün 90 dakika available
Intent
→ planning + study_advice
Specialty
→ school_6
RAG
→ gerekirse kesirler konu yapısı
Rules
→ maksimum 90 dakika
LLM
→ çalışma taslağı
Validator
→ toplam süre <= 90
→ olmayan konu uydurulmuş mu?
Memory
→ gerekli explicit facts kaydedilir
```
---
# 47. Örnek Akış — YKS
Kullanıcı:
```text
"TYT'de 74 net yaptım. Matematikte süre yetişmedi."
```
Orchestrator:
```text
Context
→ yks
Facts
→ TYT total net = 74
→ matematik süre problemi learner_reported
Intent
→ assessment_analysis
Specialty
→ yks
Rules
→ net != puan
RAG
→ gerekiyorsa süre yönetimi bilgisi
LLM
→ analiz + öneri
Validator
→ uydurma ders neti var mı?
→ 74 net puan olarak yorumlanmış mı?
```
---
# 48. Örnek Akış — KPSS + YDS
Kullanıcının context'leri:
```text
kpss
yds
```
Mesaj:
```text
"Kelime çalışmasını bu hafta artırmak istiyorum."
```
Orchestrator bağlamı büyük olasılıkla:
```text
yds
```
olarak seçer.
KPSS çalışma planı gereksiz yere modele yüklenmez.
---
# 49. Örnek Akış — Belirsizlik
Kullanıcı:
```text
"Matematikte çok gerideyim."
```
Aktif context:
```text
school_11
yks
```
Bu bilgi tek başına hangi bağlamı kastettiğini kesin göstermeyebilir.
Yakın sohbet veya aktif plan bağlamı yoksa:
```text
"Okul matematiğini mi, TYT matematiğini mi kastediyorsun?"
```
gibi tek kısa soru gerekebilir.
---
# 50. Performans İlkesi
Her mesajda:
```text
bütün memory
+
bütün RAG
+
bütün sohbet
+
bütün uzmanlık bilgisi
```
modele gönderilmeyecektir.
Orchestrator yalnız gerekli context'i seçmelidir.
Bu:
- maliyeti,
- token kullanımını,
- cevap karmaşasını,
- yanlış bilgi kullanımını
azaltacaktır.
---
# 51. v0.1 İçin Bilinçli Olarak Yapmayacağımız Şeyler
İlk Orchestrator sürümünde:
- çok ajanlı sistem kurulmayacak,
- agent swarm yapılmayacak,
- LLM'in kendi başına sınırsız tool çağırması sağlanmayacak,
- her mesaj için karmaşık planner modeli kullanılmayacak,
- mikroservis mimarisi kurulmayacak,
- ayrı karar modeli eğitilmeyecek.
İlk hedef:
```text
küçük
deterministik
test edilebilir
açıklanabilir
```
bir orchestrator oluşturmaktır.
---
# 52. Orchestrator v0.1 Modülleri
İlk implementasyonda kavramsal olarak şu parçalar bulunabilir:
```text
orchestrator
├── request_context
├── context_router
├── intent_router
├── memory_fact_extractor
├── rag_gate
├── rule_assembler
├── prompt_context_builder
├── response_pipeline
└── audit
```
Gerçek dosya yapısı implementasyon başlamadan önce kesinleştirilecektir.
---
# 53. Test Edilmesi Gereken Ana Davranışlar
Orchestrator testleri en az şu senaryoları içermelidir:
1. Bilinen bilgiyi tekrar sormama.
2. Birden fazla context arasında doğru seçim.
3. Belirsiz context'te gereksiz varsayım yapmama.
4. RAG gerekmeyen istekte RAG çağırmama.
5. RAG gereken istekte doğru profile göre arama.
6. Bilinmeyen bilgiyi memory'ye yazmama.
7. LLM çıkarımını gerçek bilgi olarak kaydetmeme.
8. Süre kısıtını doğru aktarma.
9. Specialty rule'ları uygulama.
10. Validator hatasında kontrollü yeniden üretim.
11. Sonsuz regeneration döngüsüne girmeme.
12. Bir context'in verisini ilgisiz context'e taşımama.
---
# 54. Başarı Kriteri
Orchestrator v0.1 başarılı kabul edilmek için:
- LLM'den bağımsız kritik kararları yönetebilmeli,
- öğrenci verisini güvenilir kullanabilmeli,
- doğru Specialty Profile'ı seçebilmeli,
- gerektiğinde RAG çağırabilmeli,
- gereksiz RAG çağrılarını engelleyebilmeli,
- hard constraint'leri modele taşıyabilmeli,
- validator sonucunu yönetebilmeli,
- memory'yi kontrollü güncelleyebilmeli,
- farklı LLM sağlayıcılarıyla çalışabilecek şekilde tasarlanmalıdır.
---
# 55. Mimari Karar
EduCoach Orchestrator şu prensiple geliştirilecektir:
> **Model cevap üretir; sistem gerçeği, bağlamı, sınırları ve akışı yönetir.**
Böylece EduCoach'un doğruluğu yalnızca seçilen LLM'in davranışına bağlı olmayacaktır.
