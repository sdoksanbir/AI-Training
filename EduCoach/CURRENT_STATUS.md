# EduCoach — Current Status

**Son güncelleme:** 5 Ekim 2026

## Ürün ve kapsam

EduCoach, farklı eğitim ve sınav senaryolarına uzmanlaşabilen genel öğrenme ve eğitim koçluğu platformudur. YKS önemli bir Specialty Profile'dır; ürünün tamamı değildir.

Genel çekirdek `Learner` ve `Learner Memory` terminolojisini kullanır. Sınıf, sınav ve dil öğrenimine özgü davranışlar `school_5`–`school_12`, `lgs`, `yks`, `kpss`, `ales`, `yds`, `yokdil`, `toefl`, `ielts`, `general_english` gibi Specialty Profile'larda tanımlanacaktır.

## Aktif mimari

```text
Learner Memory
+ Specialty Profiles
+ Backend Rules
+ RAG / Knowledge
+ LLM Provider
+ Response Validator
+ Orchestrator
```

LLM doğal dil ve muhakeme sağlar. Kesin kurallar, learner gerçekleri, ortak eğitim bilgisi ve çıktı doğrulaması ayrı katmanlarda tutulur.

## Gerçek kod durumu

- Domain modelleri: learner/context, goal, availability, assessment/result, evidence, study plan/task/session, preference ve coaching state.
- Persistence: SQLAlchemy ve SQLite şeması.
- Repositories: tüm mevcut Learner Memory ana modelleri.
- Services: transaction kontrollü learner, assessment, study plan ve study session akışları; learner-scoped `LearnerMemorySnapshot` read modeli.
- Specialty Profiles: versioned registry, context/family doğrulama, JSON loader ve dört builtin package resource.
- LLM: ortak provider sözleşmesi, fake provider, Ollama provider, health/model kontrolü.
- RAG: JSONL/katalog yükleme, deterministic in-memory lexical retrieval, title/IDF-aware ranking, Türkçe normalization, metadata filtreleri, global/program scope ve sürümlü retrieval evaluation.
- Knowledge Base: source/document manifestleri, Source → Document → Chunk provenance validation, active-only production catalog ve 5 gerçek kaynağa bağlı 14 sürümlü Türkçe knowledge chunk.
- Backend Rules: immutable rule contract'ları; learner, context, assessment ve plan fact projection'ları; availability çözümleme; günlük plan yükü ve `PLAN_AVAILABLE_TIME_LIMIT` evaluator'ı.
- Response Validator: typed report/action contract'ı; legacy BLOCK kontrolleri; memory, personalization, assessment, context/specialty, plan-budget, repetition ve guarantee validation; deterministik action precedence.
- Orchestrator: user validation, memory load, final context routing, intent detection, RAG need gating, context filtreli optional retrieval, LLM çağrısı, snapshot aktarımı, opsiyonel specialty registry ve response validation.
- StudyPlan write-back: immutable proposal/report contract'ı, deterministic ownership/context/goal/budget pre-flight validation ve yalnız `VALID` proposal'ları mevcut transaction servisine ileten persistence gateway.
- Active context/specialty resolution: explicit context seçimi veya tek-context çözümü ve authoritative specialty registry kullanımı.
- Typed multi-intent contract: dokümante edilmiş 11 intent, `RESOLVED/UNRESOLVED` ayrımı, immutable çoklu intent sonucu ve deterministik canonical ordering.
- Conservative intent detection v0.1: yedi açık intent için deterministic Türkçe kalıplar, multi-intent üretimi ve güvenli `UNRESOLVED` fallback'i.
- Context Selection Evidence v0.1: ACTIVE context'lere bağlı ACTIVE goal/plan kayıtlarından immutable, deterministic ve conflict-aware memory evidence projection'ı.
- Context Routing Terminology + Message Evidence v0.1: authoritative Specialty Profile configuration'ından okunan typed terminoloji ile tek kelimeyi yeterli saymayan, deterministic ve conflict-aware message evidence projection'ı.
- Final Context Selection Policy + Runtime Integration v0.1: explicit seçim → active context yapısı → current-message evidence → goal/plan memory evidence precedence'ı; authoritative specialty resolution, seçilen programa özel RAG scope'u ve unresolved multi-context durumda RAG/LLM/validator çağırmayan generic deterministic clarification.
- Full RAG Need Gating v0.1: immutable `REQUIRED/NOT_REQUIRED/UNRESOLVED` contract'ı, required-intent precedence'ı ve sınırlı high-precision external-knowledge sinyalleri; runtime'da `REQUIRED → retrieve`, `NOT_REQUIRED → skip`, `UNRESOLVED → conservative retrieve` davranışı.
- CLI ve deterministik core regression komutu.

## Faz özeti

- Faz 0 ve 1: **TAMAMLANDI**
- Faz 2: **TAMAMLANDI**
- Faz 3: **TAMAMLANDI**
- Faz 4: **TAMAMLANDI**
- Faz 5: **TAMAMLANDI**
- Faz 6: **TAMAMLANDI**
- Faz 7: **TAMAMLANDI**
- Faz 8: **TAMAMLANDI**
- Faz 9: **KISMİ**
- Faz 10: **BAŞLANGIÇ**
- Faz 11, 12 ve 14: **BAŞLANMADI**
- Faz 13 ve 15: **BEKLEMEDE**

## Fine-tuning araştırma geçmişi

Qwen3-4B üzerinde QLoRA v0.1–v0.6 deneyleri yapıldı. Learning rate, LoRA kapasitesi, attention-only hedef modüller, veri temizleme, sampling, repetition penalty, system prompt, epoch ve adapter scaling incelendi.

Tekrarlama döngüleri, yanlış sayısal çıkarımlar ve güvenilmez kişiselleştirme üretim kalitesini sınırladı. Assistant-only loss, stop token ve truncation ana neden olarak görünmedi. Mevcut gold veri, eğitim ayarları, adapter çıktıları ve evaluation raporları repository'de frozen research archive olarak korunmaktadır.

Ayrıntılı deney özeti [FINE_TUNING_HISTORY.md](docs/FINE_TUNING_HISTORY.md) dosyasında korunmaktadır.

Yeni fine-tuning çalışması dondurulmuştur. Fine-tuning ancak çalışan ürün mimarisinde ölçülmüş ve diğer katmanlarla çözülemeyen bir problem kalırsa yeniden değerlendirilecektir.

`evaluations/holdout/benchmark_v0.2.jsonl` final unseen set değildir; regression/diagnostic set olarak değerlendirilir.

## Bilinen ana eksikler

- Structured LLM proposal generation, validator action orchestration, controlled regeneration, conversation-history routing ve StudyPlan dışındaki memory write-back türleri
- Typed Specialty `rag_policy` schema ve policy entegrasyonu
- İleride ihtiyaçla doğrulanacak persistent index
- Geniş regression ve ayrı development evaluation seti
- Gerçek learner senaryoları

## Aktif sıradaki iş

FAZ 9 kapsamında LLM structured proposal generation, validator action orchestration ve controlled regeneration geliştirmek; conversation-history routing'i authoritative runtime contract oluşana kadar ertelemek.

## Doğrulama baseline'ı

- Full pytest: **755 passed**
- Knowledge Base tests: **20/20 passed**
- Core regression: **3/3 PASS**
- RAG retrieval evaluation: **Recall@3 %100, Top-1 accuracy %100, forbidden violation 0**
