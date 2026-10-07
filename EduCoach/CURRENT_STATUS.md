# EduCoach — Current Status

**Son güncelleme:** 7 Ekim 2026

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
- Orchestrator: user validation, memory load, final context routing, intent detection, RAG need gating, context filtreli optional retrieval, planning için strict structured StudyPlan proposal parsing/materialization, LLM çağrısı, snapshot aktarımı, opsiyonel specialty registry, response evaluation ve action orchestration.
- StudyPlan write-back: immutable proposal/report contract'ı, deterministic ownership/context/goal/budget pre-flight validation ve yalnız `VALID` proposal'ları mevcut transaction servisine ileten persistence gateway.
- Active context/specialty resolution: explicit context seçimi veya tek-context çözümü ve authoritative specialty registry kullanımı.
- Typed multi-intent contract: dokümante edilmiş 11 intent, `RESOLVED/UNRESOLVED` ayrımı, immutable çoklu intent sonucu ve deterministik canonical ordering.
- Conservative intent detection v0.1: yedi açık intent için deterministic Türkçe kalıplar, multi-intent üretimi ve güvenli `UNRESOLVED` fallback'i.
- Context Selection Evidence v0.1: ACTIVE context'lere bağlı ACTIVE goal/plan kayıtlarından immutable, deterministic ve conflict-aware memory evidence projection'ı.
- Context Routing Terminology + Message Evidence v0.1: authoritative Specialty Profile configuration'ından okunan typed terminoloji ile tek kelimeyi yeterli saymayan, deterministic ve conflict-aware message evidence projection'ı.
- Final Context Selection Policy + Runtime Integration v0.1: explicit seçim → active context yapısı → current-message evidence → goal/plan memory evidence precedence'ı; authoritative specialty resolution, seçilen programa özel RAG scope'u ve unresolved multi-context durumda RAG/LLM/validator çağırmayan generic deterministic clarification.
- Full RAG Need Gating v0.1: immutable `REQUIRED/NOT_REQUIRED/UNRESOLVED` contract'ı, required-intent precedence'ı ve sınırlı high-precision external-knowledge sinyalleri; runtime'da `REQUIRED → retrieve`, `NOT_REQUIRED → skip`, `UNRESOLVED → conservative retrieve` davranışı.
- Structured StudyPlan Proposal Generation v0.1: planning + resolved context için provider-independent tek JSON-envelope çağrısı, strict semantic schema ve system-owned learner/context/ID/status materialization'ı. Candidate `StudyPlanWriteProposal` otomatik validate veya persist edilmez.
- Validator Action Orchestration v0.1: `PASS` cevapları kabul edilir, `BLOCK` fail closed kalır, `REGENERATE` typed regeneration-required boundary ve `AUTO_FIX` typed auto-fix-required boundary üzerinden taşınır.
- Controlled Regeneration v0.1: yalnız `REGENERATE` action'ı aynı user message, snapshot ve memory+RAG context ile bir kez retry edilir; violation feedback system-owned prompt'a eklenir. İkinci `REGENERATE`, `ResponseRegenerationExhausted` üretir. Base prompt dış URL/www üretmemesi için validator ile hizalıdır; yalnız `external_link_not_verified` ihlali bounded regeneration alır, diğer legacy blocker'lar fail closed kalır. Generic deterministic fallback henüz yoktur.
- Deterministic Auto-Fix v0.1: yalnız `OUTPUT_REPETITION_LOOP`, `AUTO_FIX` üretir; üç veya daha fazla ardışık eşdeğer segment tek kopyaya indirilir ve sonuç yeniden validate edilir. AUTO_FIX provider retry değildir. `PLAN_AVAILABLE_TIME_LIMIT` hâlâ `REGENERATE` olur; authoritative plan-duration redistribution policy henüz yoktur.
- HTTP API boundary: public `/health`, authentication-required `/v1/coach/respond`, authenticated principal'dan authoritative learner ownership, optional context aktarımı, fail-closed foreign-context davranışı, sanitize edilmiş hata cevapları ve persist edilmeyen StudyPlan proposal serialization.
- Persistent learner authentication: Learner Memory'den ayrı 1:1 auth account, Argon2id password hash, normalize edilmiş unique login identifier, 12 saat TTL'li server-side opaque session, hash-only token persistence, expiry, logout/revocation ve 5 deneme/15 dakika account lockout policy'si.
- Real learner evaluation: production'dan bağımsız strict case/fact contract'ı, privacy/authorization guard, conservative identifier scanner, local-only private sınır, source-group-safe deterministic split tooling ve production `CoachOrchestrator` yolunu in-memory learner state ile kullanan development runner. Structured planning case'leri için private human-review artifact'ında identifier-free semantic proposal projection'ı bulunur.
- FAZ 12.1 development scenario coverage: repository-safe versioned taxonomy; exact `yks` + `school_7` required program scope'u; LGS out-of-scope kaydı; family/program bazında `COVERED/PARTIAL/MISSING` ve content-free açık slot raporu. Existing source-group split yeniden kullanılır; final unseen içerik tüketilmez.
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
- Faz 10: **TAMAMLANDI**
- Faz 11: **KISMİ**
- Faz 12: **KISMİ** — development scenario coverage contract tamamlandı; gerçek case intake ve human review henüz tamamlanmadı.
- Faz 14: **BAŞLANMADI** — final unseen boundary korunuyor ve final veri tüketilmedi.
- Faz 13: **TAMAMLANDI**
- Faz 15: **BEKLEMEDE**

HTTP boundary, persistent learner login, opaque session authentication ve authenticated principal ownership tamamlandı.

Real learner intake contract ve development evaluation runner hazır; 10-case gerçek-anonim pilot intake doğrulandı ancak development sonuçları henüz human review ile puanlanmadı ve final unseen set oluşturulmadı.

Real learner development evaluation, `external_link_not_verified` generation/validation mismatch'ini ortaya çıkardı. Base prompt dış URL üretmemesi için hizalandı; validator fail-closed güvenlik bariyeri olarak korunurken yalnız bu ihlal mevcut controlled regeneration bütçesiyle düzeltilebilir hale getirildi.

Private `dev-pilot-v0.3` sonucu 6 completed, 4 not-run, 0 failed ve 2 proposal'dır. RL0002 fresh-runtime stability probe'u 5/5 başarılı, external-link failure 0/5 ve other failure 0/5 sonuçlandı. Development cevapları hâlâ human review ile puanlanmadı.

Structured planning human review sırasında proposal içeriğinin görünmediği tespit edildi. Plan ve task semantic alanlarını açık allowlist ile taşıyan, runtime identifier içermeyen proposal review projection'ı eklendi; final human review henüz tamamlanmadı.

## Fine-tuning araştırma geçmişi

Qwen3-4B üzerinde QLoRA v0.1–v0.6 deneyleri yapıldı. Learning rate, LoRA kapasitesi, attention-only hedef modüller, veri temizleme, sampling, repetition penalty, system prompt, epoch ve adapter scaling incelendi.

Tekrarlama döngüleri, yanlış sayısal çıkarımlar ve güvenilmez kişiselleştirme üretim kalitesini sınırladı. Assistant-only loss, stop token ve truncation ana neden olarak görünmedi. Mevcut gold veri, eğitim ayarları, adapter çıktıları ve evaluation raporları repository'de frozen research archive olarak korunmaktadır.

Ayrıntılı deney özeti [FINE_TUNING_HISTORY.md](docs/FINE_TUNING_HISTORY.md) dosyasında korunmaktadır.

Yeni fine-tuning çalışması dondurulmuştur. Fine-tuning ancak çalışan ürün mimarisinde ölçülmüş ve diğer katmanlarla çözülemeyen bir problem kalırsa yeniden değerlendirilecektir.

`evaluations/holdout/benchmark_v0.2.jsonl` final unseen set değildir; regression/diagnostic set olarak değerlendirilir.

## Bilinen ana eksikler

- Plan-budget deterministic redistribution policy, conversation-history routing ve StudyPlan dışındaki structured proposal/write-back türleri
- Typed Specialty `rag_policy` schema ve policy entegrasyonu
- İleride ihtiyaçla doğrulanacak persistent index
- Human review ile puanlanmış gerçek-anonim development evaluation sonuçları ve bağımsız final unseen set
- Gerçek learner senaryoları

## Aktif sıradaki iş

FAZ 9 kapsamında authoritative plan-budget deterministic redistribution policy'sini değerlendirmek; diğer proposal/write-back türleri ile conversation-history routing'i ilgili authoritative contract'lar oluşana kadar ertelemek.

## Doğrulama baseline'ı

- Full pytest: **1205 passed**
- Knowledge Base tests: **20/20 passed**
- Core regression: **8/8 PASS**
- RAG retrieval evaluation: **Recall@3 %100, Top-1 accuracy %100, forbidden violation 0**
