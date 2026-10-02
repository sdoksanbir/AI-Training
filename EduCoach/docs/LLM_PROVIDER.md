# EduCoach — LLM Provider Architecture v0.1
**Tarih:** 2 Ekim 2026
**Durum:** Mimari Tasarım
---
# 1. Amaç
EduCoach'un ana uygulama mimarisini herhangi bir LLM sağlayıcısına veya belirli bir modele bağımlı olmaktan çıkarmak.
EduCoach Core doğrudan:
```text
Qwen
OpenAI
Gemini
```
çağırmayacaktır.
Bunun yerine ortak bir:
```text
LLMProvider
```
sözleşmesi kullanacaktır.
Temel yapı:
```text
EduCoach Core
      ↓
Orchestrator
      ↓
LLM Provider Interface
      ↓
┌──────────────┬──────────────┬──────────────┐
│ Local Qwen   │ OpenAI       │ Gemini       │
└──────────────┴──────────────┴──────────────┘
```
Yeni provider eklenmesi EduCoach Core'un yeniden yazılmasını gerektirmemelidir.
---
# 2. Temel İlke
EduCoach'ta üç kavram birbirinden ayrılacaktır:
```text
Provider
Model
Task / Capability
```
Örnek:
```text
Provider:
OpenAI
Model:
belirli bir OpenAI modeli
Task:
coach_response
```
veya:
```text
Provider:
Local
Model:
Qwen3-4B
Task:
fact_extraction
```
Bu kavramlar birbirine sabitlenmeyecektir.
---
# 3. Provider Nedir?
Provider model çağrısını gerçekleştiren teknik adaptördür.
Örnek provider türleri:
```text
LocalQwenProvider
OpenAIProvider
GeminiProvider
```
İleride:
```text
AnthropicProvider
OllamaProvider
vLLMProvider
CustomProvider
```
gibi başka sağlayıcılar eklenebilir.
---
# 4. Model Nedir?
Model, provider üzerinden kullanılan gerçek LLM'dir.
Örneğin aynı provider birden fazla modeli destekleyebilir.
```text
provider = openai
model = model_a
```
ve:
```text
provider = openai
model = model_b
```
aynı provider üzerinden çalışabilir.
Bu nedenle model adı uygulama kodunun farklı yerlerine dağılmayacaktır.
---
# 5. Task Nedir?
EduCoach her LLM çağrısını aynı amaçla yapmayacaktır.
İlk görev aileleri:
```text
coach_response
intent_classification
context_routing
memory_fact_extraction
query_rewrite
structured_plan_generation
response_repair
conversation_summary
```
Her task aynı modele veya aynı ayarlara ihtiyaç duymayabilir.
---
# 6. Tek Model Zorunluluğu Olmayacak
İlk prototip bir modelle başlayabilir.
Ancak mimari:
```text
Bütün görevler = aynı model
```
varsayımına bağlanmayacaktır.
İleride örneğin:
```text
küçük / hızlı model
→ intent ve fact extraction
daha güçlü model
→ koçluk ve planlama
```
kullanılabilir.
Bu optimizasyon ilk sürüm için zorunlu değildir.
---
# 7. Orchestrator Provider Bilmemeli
Yanlış yaklaşım:
```text
if provider == "openai":
    ...
if provider == "gemini":
    ...
```
Orchestrator içinde provider'a özel kod bulunmamalıdır.
Doğru yaklaşım:
```text
provider.generate(request)
```
şeklindeki ortak sözleşmedir.
---
# 8. LLM Request
Provider'a verilen giriş yapılandırılmış olmalıdır.
Kavramsal olarak:
```text
LLMRequest
```
aşağıdaki bilgileri taşıyabilir:
```text
request_id
task_type
system_instructions
messages
context_blocks
output_mode
output_schema
temperature
max_output_tokens
timeout_seconds
metadata
```
Bütün alanlar her çağrıda kullanılmak zorunda değildir.
---
# 9. Context Blocks
Learner Memory, RAG ve Rules aynı metin yığınına karıştırılmamalıdır.
LLMRequest içinde kavramsal olarak ayrı bloklar bulunabilir:
```text
learner_facts
soft_signals
active_context
active_goal
hard_constraints
retrieved_knowledge
recent_conversation
output_requirements
```
Provider bunları kullandığı model formatına çevirebilir.
---
# 10. Hard Facts ve Instructions Ayrımı
Şu bilgi:
```text
Öğrenci 11. sınıfta.
```
bir fact'tir.
Şu bilgi:
```text
Öğrencinin sınıf seviyesini uydurma.
```
bir instruction'dır.
Provider katmanında bunlar birbirine karıştırılmamalıdır.
---
# 11. LLM Response
Provider'ın cevabı yalnız string olmak zorunda değildir.
Kavramsal çıktı:
```text
LLMResponse
```
şu alanlara sahip olabilir:
```text
request_id
provider
model
content
structured_output
finish_reason
usage
latency
provider_request_id
warnings
```
---
# 12. Structured Output
EduCoach'un kritik işlemlerinde mümkün olduğunca yapılandırılmış çıktı kullanılacaktır.
Örneğin:
```text
memory_fact_extraction
```
sonucu serbest paragraf yerine:
```text
facts:
  - field: grade_level
    value: 11
    evidence_type: explicit
```
gibi yapılandırılmış olabilir.
---
# 13. Plan Üretimi
Çalışma programı üretirken de LLM'in yalnızca kullanıcıya gösterilecek metni üretmesi tercih edilmeyecektir.
Önce:
```text
Structured Study Plan
```
oluşturulabilir.
Örneğin:
```text
tasks:
  - area_code: ...
    task_type: practice
    planned_minutes: 45
    priority: high
```
Backend bunu doğrular.
Daha sonra kullanıcıya gösterilecek doğal dil oluşturulur.
---
# 14. Structured Output Neden Önemli?
Şu kontrolleri kolaylaştırır:
```text
toplam süre
geçersiz alan
olmayan context
uydurma task
eksik alan
yanlış veri tipi
```
Serbest metin üzerinden bütün bunları güvenilir biçimde çıkarmaya çalışmak daha kırılgandır.
---
# 15. JSON Schema Benzeri Sözleşme
Provider yapılandırılmış çıktı destekliyorsa mümkün olduğunca schema kullanılacaktır.
Desteklemiyorsa:
```text
model çıktısı
↓
parser
↓
schema validation
```
yaklaşımı kullanılabilir.
Ancak parse edilemeyen çıktı sessizce kabul edilmeyecektir.
---
# 16. Provider Capabilities
Her provider / model aynı özelliği desteklemeyebilir.
Bu nedenle capability kaydı bulunmalıdır.
Örnek:
```text
supports_structured_output
supports_streaming
supports_tools
supports_system_instructions
supports_json_schema
supports_temperature
supports_seed
supports_usage_reporting
supports_reasoning_control
context_window
max_output_tokens
```
---
# 17. Capability Kontrolü
Orchestrator belirli bir özelliğin mevcut olduğunu varsaymayacaktır.
Örneğin görev:
```text
strict structured output
```
gerektiriyorsa seçilen provider/model bunu destekliyor mu kontrol edilmelidir.
---
# 18. Model Descriptor
Her kullanılabilir model için yapılandırılmış tanım tutulabilir.
Örnek:
```text
provider
model_id
display_name
enabled
context_window
max_output_tokens
capabilities
cost_profile
privacy_profile
task_allowlist
```
---
# 19. Model ID'leri Koda Dağılmayacak
Yanlış:
```text
model="qwen3-4b"
```
değerinin onlarca Python dosyasına yazılması.
Doğru:
```text
application configuration
↓
model registry
↓
provider
```
---
# 20. Model Registry
Kavramsal yapı:
```text
ModelRegistry
├── local_qwen
├── openai_primary
├── gemini_primary
└── ...
```
Her kayıt:
```text
provider
model
capabilities
enabled
task policies
```
bilgisini sağlayabilir.
---
# 21. Task Routing
İleride bir:
```text
ModelRouter
```
bulunabilir.
Görevi:
```text
Bu task hangi aktif model ile çalıştırılmalı?
```
sorusunu cevaplamaktır.
Ancak ModelRouter:
```text
öğrenciye ne tavsiye verilmeli?
```
sorusunu cevaplamaz.
Bu Orchestrator / LLM işidir.
---
# 22. v0.1 Model Routing
İlk sürüm basit olacaktır.
Örneğin:
```text
default_model = ...
```
ve gerekirse birkaç task override:
```text
memory_fact_extraction → ...
coach_response → ...
```
kullanılabilir.
Karmaşık otomatik model seçimi ilk sürümde yapılmayacaktır.
---
# 23. Provider Configuration
Provider bağlantı ayarları kod içine gömülmeyecektir.
Örneğin:
```text
provider type
base URL
model ID
timeout
API key environment variable
enabled
```
configuration üzerinden yönetilebilir.
---
# 24. Secret Yönetimi
API anahtarları:
```text
source code
Git
Markdown dokümanları
loglar
```
içine yazılmayacaktır.
Secret'lar environment veya uygun secret management mekanizması üzerinden sağlanacaktır.
---
# 25. Local ve Cloud Ayrımı
EduCoach hem:
```text
local LLM
```
hem:
```text
cloud LLM
```
kullanabilecek şekilde tasarlanacaktır.
Bu iki kullanımın özellikleri farklıdır.
---
# 26. Local Provider
Yerel model kullanımında avantajlar:
```text
API token maliyeti yok
daha fazla veri kontrolü
offline çalışma ihtimali
```
Dezavantajlar:
```text
donanım ihtiyacı
daha düşük model kapasitesi ihtimali
inference hızı
bakım
```
---
# 27. Cloud Provider
Bulut modellerinde avantajlar:
```text
daha güçlü model seçenekleri
sunucu tarafında ölçeklenebilirlik
yerel GPU gerektirmeme
```
Dezavantajlar:
```text
API maliyeti
internet bağımlılığı
veri işleme politikalarının dikkate alınması
rate limit
provider bağımlılığı riski
```
Mimari iki seçeneğe de izin verecektir.
---
# 28. Privacy Profile
Her provider/model için veri kullanımına ilişkin teknik politika tutulabilir.
Örneğin kavramsal olarak:
```text
LOCAL
CLOUD_ALLOWED
RESTRICTED
```
Bu değerler ürünün gerçek veri politikaları kesinleştiğinde ayrıntılandırılacaktır.
---
# 29. Minimum Necessary Context
Cloud veya local fark etmeksizin modele gereksiz kullanıcı verisi gönderilmeyecektir.
Orchestrator yalnız görev için gerekli bilgileri seçmelidir.
Örneğin:
```text
matematik programı oluşturma
```
için kullanıcının tüm yıllara ait sohbet geçmişini göndermek gereksiz olabilir.
---
# 30. Çocuk Kullanıcılar
EduCoach 5. sınıf gibi yaş gruplarını da destekleyeceğinden provider'a gönderilen kişisel veri konusunda minimum veri ilkesi özellikle önemlidir.
Model çağrılarında yalnız eğitim görevi için gerekli veri kullanılacaktır.
---
# 31. Provider'a Ham Veritabanı Gönderilmeyecek
LLM provider'a:
```text
SELECT * FROM learners
```
gibi bütün veri yapısı aktarılmayacaktır.
Orchestrator'ın Context Builder katmanı gerekli alanları seçer.
---
# 32. Model Öğrenci Veritabanına Doğrudan Yazamaz
LLM şu komutu kendi başına uygulayamaz:
```text
Bu öğrencinin hedefini değiştir.
```
Model yalnız yapılandırılmış bir:
```text
proposed_memory_update
```
üretebilir.
Gerçek kayıt işlemini backend doğrular ve yapar.
---
# 33. Tool Calling
Bazı provider'lar tool calling destekleyebilir.
Ancak EduCoach v0.1 şu prensibi kullanacaktır:
> LLM'in tool calling yeteneği sistem kontrolünün yerine geçmez.
Araç çağrılarının:
```text
izin verilen tool
parametre doğrulama
yetkilendirme
sonuç doğrulama
```
kontrolleri backend tarafında yapılmalıdır.
---
# 34. İlk Sürümde Agent Serbestliği Yok
LLM'e:
```text
istediğin kadar araç çağır
istediğin işlemi yap
kendin karar ver
```
şeklinde sınırsız agent yetkisi verilmeyecektir.
Orchestrator hangi adımların mümkün olduğunu sınırlar.
---
# 35. Text Generation
Temel provider yeteneği:
```text
generate(request)
→ LLMResponse
```
olacaktır.
İlk v0.1 için bu yetenek yeterlidir.
---
# 36. Structured Generation
Gerekirse ikinci bir kavramsal yetenek:
```text
generate_structured(request, schema)
```
olabilir.
Ancak provider interface'in gereksiz yere iki ayrı sistem haline gelmemesi için implementasyon sırasında sade tasarım tercih edilebilir.
Tek `generate()` çağrısında:
```text
output_mode
output_schema
```
kullanılması yeterli olabilir.
---
# 37. Streaming
Streaming kullanıcı deneyimini geliştirebilir.
Ancak kritik yapılandırılmış işlemler için streaming her zaman gerekli değildir.
Örneğin:
```text
memory fact extraction
```
streaming gerektirmez.
Kullanıcıya gösterilen uzun koçluk cevabında ileride kullanılabilir.
v0.1'in çalışması streaming'e bağımlı olmayacaktır.
---
# 38. Timeout
Her provider çağrısında timeout bulunmalıdır.
Sistem sonsuza kadar model cevabı beklememelidir.
Timeout provider/model türüne göre configuration üzerinden ayarlanabilir.
---
# 39. Retry
Geçici teknik hatalarda sınırlı retry uygulanabilir.
Örneğin:
```text
network timeout
temporary provider error
rate limiting
```
Ancak:
```text
invalid request
schema violation
authentication failure
```
gibi hatalarda kör retry yapılmamalıdır.
---
# 40. Retry Sınırı
Retry sonsuz olmayacaktır.
Örneğin:
```text
max_retries = 1 veya 2
```
gibi kontrollü bir değer kullanılabilir.
Gerçek değer implementasyon aşamasında ölçülecektir.
---
# 41. Retry ile Regeneration Ayrımı
Bunlar aynı şey değildir.
```text
Retry
→ teknik çağrı başarısız oldu
Regeneration
→ model cevap verdi ancak validator reddetti
```
Ayrı sayaçlar ve ayrı loglar kullanılmalıdır.
---
# 42. Error Taxonomy
Provider katmanı farklı API hata biçimlerini ortak hata sınıflarına dönüştürmelidir.
Örneğin:
```text
LLM_TIMEOUT
LLM_AUTH_ERROR
LLM_RATE_LIMIT
LLM_CONTEXT_LIMIT
LLM_INVALID_REQUEST
LLM_PROVIDER_UNAVAILABLE
LLM_INVALID_RESPONSE
LLM_UNKNOWN_ERROR
```
Orchestrator provider'a özgü hata kodlarını bilmek zorunda kalmaz.
---
# 43. Context Limit
Provider çağrısından önce yaklaşık context boyutu kontrol edilebilmelidir.
Sistem:
```text
context_window
```
değerini bilmeli.
Aşım durumunda:
```text
daha az RAG chunk
daha kısa conversation summary
yalnız gerekli memory facts
```
seçilebilir.
---
# 44. Context Limitte Bilgi Atma Sırası
Kritik bilgiler rastgele kesilmemelidir.
Genel öncelik:
```text
system / hard rules
↓
kritik learner facts
↓
aktif context / goal
↓
gerekli RAG
↓
yakın konuşma
↓
daha düşük öncelikli yardımcı bilgiler
```
şeklinde olabilir.
Gerçek politika task bazında ayarlanacaktır.
---
# 45. Output Token Limiti
Her task aynı output uzunluğuna ihtiyaç duymaz.
Örneğin:
```text
intent classification
```
çok kısa olabilir.
```text
weekly study plan
```
daha uzun çıktı gerektirebilir.
Task configuration üzerinden farklı limitler kullanılabilir.
---
# 46. Temperature
Temperature gibi sampling parametreleri bütün task'ler için ortak olmak zorunda değildir.
Özellikle yapılandırılmış ve deterministik görevlerde:
```text
daha kontrollü üretim
```
tercih edilebilir.
Koçluk dilinde daha doğal varyasyon gerekebilir.
---
# 47. Sampling Güvenilirlik Aracı Değildir
Geçmiş fine-tuning deneylerinde sampling loop sayısını azaltmasına rağmen uydurma ve sayısal hataları artırdı.
Bu nedenle:
```text
temperature değiştir
→ problem çözülür
```
varsayımı kullanılmayacaktır.
Doğruluk Rules ve Validator ile korunacaktır.
---
# 48. Determinism
Destekleyen modellerde bazı teknik görevler mümkün olduğunca deterministik çalıştırılabilir.
Örnek:
```text
intent classification
memory fact extraction
query rewrite
```
Ancak provider'lar arasında tam determinism garanti edilmeyebilir.
---
# 49. Usage
Provider cevaplarında mümkün olduğunda kullanım bilgisi tutulacaktır.
Örneğin:
```text
input_tokens
output_tokens
total_tokens
cached_tokens
```
Provider bu veriyi vermiyorsa alanlar boş kalabilir.
---
# 50. Cost Tracking
Bulut modellerinde maliyet izlenebilmelidir.
Ama fiyat bilgileri uygulama koduna kalıcı olarak gömülmemelidir.
Çünkü provider fiyatları değişebilir.
Kavramsal olarak:
```text
Usage
+
Pricing Configuration
→ Estimated Cost
```
hesaplanabilir.
---
# 51. Yerel Model Maliyeti
Local model:
```text
API cost = 0
```
olabilir.
Ancak sistem için:
```text
latency
GPU kullanımı
inference süresi
```
gibi teknik metrikler yine önemlidir.
---
# 52. Latency
Her çağrıda mümkün olduğunda:
```text
latency_ms
```
ölçülmelidir.
Bu sayede farklı model/provider seçenekleri gerçek veriye göre karşılaştırılabilir.
---
# 53. Observability
Her LLM çağrısı için teknik kayıt:
```text
request_id
task_type
provider
model
start_time
latency
finish_reason
usage
retry_count
error_type
validator_result
```
gibi bilgiler içerebilir.
---
# 54. Prompt İçeriğini Loglama
Promptlarda kişisel bilgi bulunabileceğinden bütün promptların olduğu gibi kalıcı loglanması varsayılan davranış olmamalıdır.
Gerekirse geliştirme ortamında kontrollü debug politikası kullanılacaktır.
---
# 55. Provider Request ID
Cloud provider bir request ID döndürüyorsa teknik hata araştırmasında kullanılmak üzere saklanabilir.
Bu ID learner'ın kişisel kimliği olarak kullanılmaz.
---
# 56. Fallback Provider
İleride sistem birincil provider çalışmazsa ikinci provider'a geçebilir.
Örneğin:
```text
Primary
↓ fail
Fallback
```
Ancak bu davranış ilk sürümde zorunlu değildir.
---
# 57. Fallback ve Privacy
Cloud'a gönderilmemesi gereken bir istek:
```text
local provider başarısız oldu
```
diye otomatik şekilde cloud provider'a gönderilmemelidir.
Fallback politikası veri politikasını dikkate almalıdır.
---
# 58. Fallback ve Capability
Fallback model seçildiğinde gereken capability mevcut olmalıdır.
Örneğin strict structured output gereken task:
```text
structured output desteklemeyen
```
bir modele kör biçimde yönlendirilmemelidir.
---
# 59. Model Selection Policy
İleride model seçiminde şu sinyaller kullanılabilir:
```text
task_type
required_capabilities
privacy_policy
cost_limit
latency_target
quality_requirement
provider_health
```
Ancak v0.1'de bu kadar karmaşık router gerekli değildir.
---
# 60. Quality Tier
İleride görevler kavramsal olarak:
```text
FAST
STANDARD
HIGH_QUALITY
```
gibi kalite seviyelerine ayrılabilir.
Örneğin basit sınıflandırma için büyük model kullanmak gereksiz olabilir.
Ama bu optimizasyon ancak gerçek ölçümlerden sonra yapılacaktır.
---
# 61. Provider Health
Provider'ın çalışıp çalışmadığı izlenebilir.
Örnek durum:
```text
HEALTHY
DEGRADED
UNAVAILABLE
```
Bu bilgi gelecekte ModelRouter tarafından kullanılabilir.
---
# 62. Provider Health LLM'e Sorulmayacak
Bir provider'ın erişilebilir olup olmadığı teknik health check ile belirlenmelidir.
LLM:
```text
sanırım provider çalışıyor
```
gibi bir karar vermez.
---
# 63. Local Qwen
Mevcut Qwen3-4B modeli ilk yerel provider deneylerinde kullanılabilir.
Ancak:
```text
EduCoach = Qwen3-4B
```
şeklinde mimari bağımlılık kurulmayacaktır.
Qwen yalnızca provider/model seçeneklerinden biridir.
---
# 64. Fine-Tuned Adapter
Mevcut QLoRA adapter'ları araştırma amacıyla korunacaktır.
İleride provider configuration aracılığıyla:
```text
base model
+
adapter
```
seçeneği deneysel olarak çalıştırılabilir.
Ancak aktif ürün mimarisinin çalışması fine-tuned adapter'a bağlı olmayacaktır.
---
# 65. Base ve Fine-Tuned Karşılaştırması
İleride aynı task:
```text
base model
fine-tuned model
cloud model
```
üzerinde aynı provider sözleşmesiyle karşılaştırılabilir.
Bu benchmark sisteminin modelden bağımsız kalmasını sağlar.
---
# 66. Prompt Builder Provider İçinde Olmamalı
EduCoach'a özgü:
```text
learner facts
rules
specialty context
RAG knowledge
```
birleştirme mantığı provider'ın sorumluluğu değildir.
Bu:
```text
Orchestrator / Context Builder
```
sorumluluğudur.
Provider yalnız ortak request'i ilgili model formatına dönüştürür.
---
# 67. Chat Template
Yerel modellerin özel chat template'leri olabilir.
Örneğin Qwen'in kendi template'i.
Bunun teknik uygulanması provider adapter'ın sorumluluğundadır.
EduCoach Core chat template ayrıntısını bilmemelidir.
---
# 68. Stop Token
Modelin özel stop token veya EOS davranışı provider katmanında yönetilir.
Core:
```text
Qwen im_end
```
gibi model özel ayrıntılara bağlı olmamalıdır.
---
# 69. Tokenizer
Tokenizer da provider/model katmanının teknik ayrıntısıdır.
Orchestrator gerekirse:
```text
estimate_tokens()
```
gibi soyut bir yetenek kullanabilir.
Doğrudan Qwen tokenizer'ına bağlanmamalıdır.
---
# 70. Local Model Loading
Yerel modellerde model yükleme maliyetli olabilir.
Provider:
```text
load
generate
unload
health
```
gibi yaşam döngüsünü yönetebilir.
Ancak v0.1'de gereksiz karmaşık model havuzu oluşturulmayacaktır.
---
# 71. Concurrency
İleride çok sayıda kullanıcı olduğunda provider aynı anda birden fazla isteği yönetebilmelidir.
Bu konu:
```text
EduCoach Core
```
ile model serving altyapısının birbirine karıştırılmaması için önemlidir.
Örneğin gelecekte local model:
```text
vLLM
```
gibi ayrı serving altyapısında çalışabilir.
Core değişmek zorunda kalmamalıdır.
---
# 72. Provider Interface ve Serving Ayrımı
Örneğin:
```text
LocalQwenProvider
```
doğrudan modeli Python process içinde yükleyebilir.
İleride aynı model:
```text
HTTP inference server
```
üzerinden çalışabilir.
Provider arayüzü bu değişimin Core'u etkilemesini önlemelidir.
---
# 73. Model Server
İlk prototip için ayrı model server zorunlu değildir.
Önce çalışan basit provider geliştirilebilir.
Ürün ölçeği büyüdüğünde inference serving ayrıştırılabilir.
---
# 74. Validation Provider'ın İşi Değildir
Provider:
```text
cevap kaliteli mi?
süre doğru mu?
net ile puan karışmış mı?
```
kontrollerinden sorumlu değildir.
Bunlar:
```text
Response Validator
```
sorumluluğudur.
---
# 75. RAG Provider'ın İşi Değildir
Provider kendi başına Knowledge Base'den rastgele belge çekmeyecektir.
RAG gerekip gerekmediğine Orchestrator karar verir.
Retriever gerekli bilgiyi getirir.
Provider yalnız verilen knowledge context'i kullanır.
---
# 76. Learner Memory Provider'ın İşi Değildir
Provider veritabanından öğrenci aramaz.
Learner Memory katmanı gerekli veriyi sağlar.
Context Builder yalnız gerekli bilgileri LLMRequest'e koyar.
---
# 77. Specialty Provider'ın İşi Değildir
Provider:
```text
YKS nedir?
school_7 ne demek?
```
gibi ürün domain yapılarını yönetmez.
Specialty Profile bu bağlamı sağlar.
---
# 78. Provider Testleri
Her provider için ortak contract testleri bulunmalıdır.
Örnek:
1. Basit text generation çalışıyor mu?
2. Timeout doğru hata tipini veriyor mu?
3. Invalid model doğru hata veriyor mu?
4. Structured output destekleniyorsa parse edilebiliyor mu?
5. Usage bilgisi doğru normalize ediliyor mu?
6. Provider özel hata Core'a sızıyor mu?
7. Model adı registry üzerinden geliyor mu?
---
# 79. Fake Provider
Testlerde gerçek LLM çağırmak zorunda olmamak için:
```text
FakeLLMProvider
```
oluşturulabilir.
Bu provider önceden belirlenmiş cevapları döndürür.
Böylece Orchestrator testlerinin çoğu:
```text
API maliyeti olmadan
GPU kullanmadan
deterministik
```
çalışabilir.
---
# 80. Neden Fake Provider Önemli?
Örneğin şu testi:
```text
LLM 190 dakikalık plan döndürürse validator ne yapıyor?
```
gerçek modele ihtiyaç duymadan test edebiliriz.
Bu test:
```text
Orchestrator + Rules + Validator
```
davranışını ölçer.
---
# 81. Provider Benchmark
Gerçek modeller karşılaştırılırken aynı test seti kullanılmalıdır.
Ölçülebilecek alanlar:
```text
answer quality
structured output success
rule violation count
latency
token usage
estimated cost
regeneration rate
```
---
# 82. Model Kalitesi Tek Başına Yeterli Değildir
Bir model daha iyi metin yazabilir fakat:
```text
structured output
latency
cost
privacy
```
açısından uygun olmayabilir.
EduCoach model seçimini yalnız genel benchmark skoruna göre yapmayacaktır.
---
# 83. Task Bazlı Değerlendirme
Model kalitesi EduCoach görevlerinde ölçülmelidir.
Örneğin:
```text
memory extraction accuracy
context routing accuracy
plan validity
coach response quality
unsupported claim rate
```
genel sohbet benchmark'larından daha değerlidir.
---
# 84. Eğitimsel Kalite
Koçluk cevabının eğitimsel kalitesini yalnız otomatik teknik metriklerle değerlendiremeyiz.
Öğretmen değerlendirmesi özellikle:
```text
plan gerçekçi mi?
öncelik doğru mu?
öğrenci seviyesine uygun mu?
pedagojik yaklaşım mantıklı mı?
```
sorularında gerekli olacaktır.
---
# 85. Provider Bağımsız Evaluation
Evaluation kayıtlarında:
```text
provider
model
configuration
prompt_version
knowledge_version
```
bilgileri tutulmalıdır.
Böylece iki model adil şekilde karşılaştırılabilir.
---
# 86. Prompt Version
Core system behavior ve task promptları sürümlenmelidir.
Örneğin:
```text
coach_prompt_v1
memory_extraction_v1
```
Model değişikliği ile prompt değişikliği birbirinden ayrılmalıdır.
---
# 87. Provider'a Özel Prompt
Mümkün olduğunca ortak prompt kullanılacaktır.
Ancak bazı modeller format açısından küçük uyarlamalar gerektirebilir.
Bu teknik uyarlama provider adapter içinde olabilir.
Pedagojik davranış provider'a özel kopyalanmamalıdır.
---
# 88. Configuration Örneği
Kavramsal olarak:
```text
models:
  local_qwen:
    provider: local_qwen
    model: Qwen3-4B
    enabled: true
tasks:
  coach_response:
    model: local_qwen
```
gibi bir configuration olabilir.
Gerçek format implementasyon aşamasında kesinleştirilecektir.
---
# 89. Environment Ayrımı
Development ve production aynı model configuration'ını kullanmak zorunda değildir.
Örneğin:
```text
development
→ local model
production
→ farklı serving / cloud model
```
olabilir.
Core kod aynı kalmalıdır.
---
# 90. Maliyet Limiti
İleride bir isteğin maksimum LLM maliyeti için politika konabilir.
Örneğin:
```text
max_model_calls_per_request
max_regenerations
```
gibi sınırlar gereksiz maliyeti engeller.
---
# 91. Model Call Budget
Bir öğrenci mesajı için:
```text
intent
fact extraction
RAG rewrite
coach answer
validator model
```
diye gereksiz yere beş ayrı LLM çağrısı yapmak varsayılan yaklaşım olmayacaktır.
Mümkün olduğunca:
```text
deterministik kod
+
az sayıda gerekli model çağrısı
```
kullanılacaktır.
---
# 92. Küçük Görevleri Birleştirme
Uygun olduğunda:
```text
intent
+
fact extraction
+
context suggestion
```
tek yapılandırılmış LLM çağrısında birleştirilebilir.
Ancak bu yalnız güvenilirlik ölçüldükten sonra yapılmalıdır.
---
# 93. LLM Olmadan Yapılabilecek İş
Öncelikle LLM gerekip gerekmediği düşünülmelidir.
Örneğin:
```text
toplam süre hesaplama
database lookup
aktif context listesi
assessment geçmişi
```
için model çağrısı gereksizdir.
---
# 94. İlk Uygulama Stratejisi
LLM Provider implementasyonunda önerilen sıra:
```text
1. Ortak request / response modelleri
2. Provider interface
3. FakeLLMProvider
4. İlk gerçek provider
5. Provider registry
6. Model registry
7. Contract testleri
8. Timeout / error normalization
9. Structured output desteği
10. Usage / latency ölçümü
11. Orchestrator entegrasyonu
```
İkinci ve üçüncü gerçek provider daha sonra eklenebilir.
---
# 95. İlk Gerçek Provider
İlk gerçek provider seçiminde hedef:
```text
en güçlü modeli seçmek
```
değil:
```text
mimarinin uçtan uca doğru çalıştığını göstermek
```
olacaktır.
Mevcut yerel Qwen3-4B bu amaçla kullanılabilir.
Ancak mimari ona özel yazılmayacaktır.
---
# 96. Cloud Provider Zamanı
OpenAI veya Gemini entegrasyonu ilk çekirdek akış çalıştıktan sonra eklenebilir.
Böylece aynı EduCoach senaryosu:
```text
local model
vs
cloud model
```
üzerinde doğrudan karşılaştırılabilir.
---
# 97. v0.1'de Yapmayacağımız Şeyler
İlk sürümde:
- onlarca provider eklenmeyecek,
- otomatik en ucuz model algoritması yapılmayacak,
- çok ajanlı LLM orkestrasyonu kurulmayacak,
- model kendi kendine sınırsız provider değiştirmeyecek,
- karmaşık model marketplace yapılmayacak,
- bütün task'ler için ayrı model kullanılmayacak,
- production ölçek problemi daha oluşmadan ağır serving altyapısı kurulmayacak.
Önce küçük, değiştirilebilir ve test edilebilir bir provider katmanı oluşturulacaktır.
---
# 98. İlk Minimum Interface
Kavramsal olarak ilk sözleşme şu kadar basit olabilir:
```text
LLMProvider
generate(request) -> LLMResponse
health() -> ProviderHealth
capabilities() -> ProviderCapabilities
```
Gerekli olmadığı sürece interface büyütülmeyecektir.
---
# 99. Başarı Kriterleri
LLM Provider v0.1 başarılı kabul edilmek için:
1. Orchestrator belirli provider'ı doğrudan bilmemeli.
2. Model ID'leri Core koduna dağılmamalı.
3. Local ve cloud modeller aynı temel sözleşmeyle çalışabilmeli.
4. Provider hataları ortak hata tiplerine dönüştürülmeli.
5. Timeout uygulanabilmeli.
6. Structured output desteklenebilmeli.
7. Context / output limitleri bilinmeli.
8. Usage ve latency mümkün olduğunda ölçülmeli.
9. Fake provider ile LLM'siz test yapılabilmeli.
10. Provider değiştirildiğinde Learner Memory, RAG, Rules ve Orchestrator yeniden yazılmamalı.
11. Model kişisel veritabanına doğrudan erişmemeli.
12. LLM'in bütün sistem üzerinde sınırsız tool yetkisi olmamalı.
13. Model seçimi gelecekte task bazlı geliştirilebilmeli.
14. Maliyet ve gizlilik politikaları provider seçiminden bağımsız olarak uygulanabilmeli.
---
# 100. Mimari Karar
EduCoach LLM katmanı şu prensiple geliştirilecektir:
> **EduCoach bir modele değil, bir LLM sözleşmesine bağlanacaktır.**
Böylece:
```text
Qwen bugün kullanılabilir.
Başka bir yerel model yarın kullanılabilir.
OpenAI kullanılabilir.
Gemini kullanılabilir.
Yeni bir sağlayıcı eklenebilir.
```
ancak:
```text
Learner Memory
Specialty Profiles
RAG / Knowledge
Backend Rules
Response Validator
Orchestrator
```
aynı ürün çekirdeği olarak kalır.
Temel ayrım:
```text
Orchestrator
→ hangi işi yapacağımızı belirler
Model Router
→ gerekiyorsa hangi modeli kullanacağımızı belirler
LLM Provider
→ model çağrısını gerçekleştirir
LLM
→ muhakeme ve dil üretir
Validator
→ sonucu kontrol eder
```
Bu ayrım EduCoach'un uzun vadede farklı model teknolojilerine geçebilmesini sağlayacaktır.
