# EduCoach — Product & Architecture Roadmap

**Güncelleme:** 5 Ekim 2026

## Ürün kapsamı

EduCoach, farklı eğitim ve sınav senaryolarına uzmanlaşabilen genel öğrenme ve eğitim koçluğu platformudur. Genel çekirdek sınava özgü alanları `Learner` modeline gömmez; farklı kullanım alanları Specialty Profile üzerinden eklenir.

Aktif mimari:

```text
Learner Memory
+ Specialty Profiles
+ Backend Rules
+ RAG / Knowledge
+ LLM Provider
+ Response Validator
+ Orchestrator
```

Fine-tuning üretim mimarisinin zorunlu bileşeni değildir. QLoRA v0.1–v0.6 çalışmaları frozen research archive olarak korunur.

## Fazlar

### FAZ 0 — Mimari ve ürün kapsamı

**Durum: TAMAMLANDI**

Genel çekirdek, Learner terminolojisi, Specialty Profile yaklaşımı ve bileşen sorumlulukları tasarım belgelerinde tanımlandı.

### FAZ 1 — Uygulama çekirdeği

**Durum: TAMAMLANDI**

Python paketi, domain modelleri, persistence, repositories, services, LLM, RAG, rules, validators, orchestrator ve CLI modülleri mevcut.

### FAZ 2 — Learner Memory Core

**Durum: TAMAMLANDI**

Domain modelleri, SQLite persistence, repositories, ownership bütünlüğü, transaction servisleri, learner/context kaydı, assessment/result/evidence ve study plan/task/session akışları ile learner-scoped `LearnerMemorySnapshot` read model mevcut.

### FAZ 3 — LLM Provider v0.1

**Durum: TAMAMLANDI**

`LLMProvider`, `FakeLLMProvider`, `OllamaProvider`, health ve model kontrolü mevcut. OpenAI/Gemini gelecekte adapter olabilir; v0.1 için zorunlu değildir.

### FAZ 4 — Specialty Profiles Runtime

**Durum: TAMAMLANDI**

`SpecialtyProfile` sözleşmesi, versioned registry, `LearningContext` çözümleme ve family doğrulama, JSON loader, package resources ile `school_7`, `yks`, `ales` ve `general_english` builtin profilleri mevcut.

### FAZ 5 — Backend Rules v0.1

**Durum: TAMAMLANDI**

Immutable rule contract'ları, learner/context/assessment/planned-actual fact projection'ları, availability çözümleme, günlük plan yükü projection'ı, `PLAN_AVAILABLE_TIME_LIMIT` evaluator'ı ve backend rule registry mevcut.

### FAZ 6 — Response Validator v0.1

**Durum: TAMAMLANDI**

Typed `ResponseValidationReport` ile `PASS`, `AUTO_FIX`, `REGENERATE` ve `BLOCK` action contract'ı mevcut. Action precedence `BLOCK > REGENERATE > AUTO_FIX > PASS` olarak deterministiktir.

Validator; boş cevap, maksimum uzunluk ve doğrulanmamış dış link kontrollerinin yanında açık learner-memory çelişkilerini, desteklenmeyen kişiselleştirmeyi, recorded assessment numeric claim'lerini, context/specialty tutarsızlığını, multi-context fact contamination'ı, açık plan bloklarında `PLAN_AVAILABLE_TIME_LIMIT` ihlalini, repetition loop'larını ve desteklenmeyen sonuç garantilerini denetler. `validate_response` ve `ResponseValidationError` backward-compatible kalmıştır; orchestrator snapshot ve opsiyonel `SpecialtyProfileRegistry` aktarır.

Assessment metrikleri `correct`, `incorrect`, `blank`, `net`, `score`, `percentage`, `grade` ve `duration_minutes` olarak ayrı doğrulanır; aralarında dönüşüm yapılmaz.

v0.1 semantic parser'ı bilinçli olarak dar ve deterministik Türkçe kalıplarla sınırlıdır. Assessment claim'leri belirli sınav/tarih disambiguation yapmaz; tanımlanmamış specialty alias'ları tahmin edilmez. Plan validation yalnız açık ISO tarihli, satır bazlı bloklarda ve gerekli bilgiler kesin çözülebildiğinde çalışır. UNKNOWN/AMBIGUOUS availability ihlal veya başarı kanıtı sayılmaz. `REGENERATE` retry döngüsü FAZ 9 kapsamındadır.

Doğrulama baseline'ı: 416 test başarılı, core regression 3/3 PASS.

### FAZ 7 — RAG v0.1

**Durum: TAMAMLANDI**

Deterministik lexical retriever; JSONL ve klasör kataloğu yükleme, ranking öncesi metadata filtreleme, Unicode ve Türkçe harf normalizasyonu, term-frequency ve IDF-aware title/text scoring ile açık `chunk_id` tie-break davranışını destekler.

`metadata.program = "global"` genel bilgi sözleşmesidir. Orchestrator, learner programlarıyla birlikte global bilgiyi kabul eder ve diğer programlara özgü bilgiyi dışlar. Duplicate chunk ID reddi ile sıfır/negatif limit sözleşmeleri tanımlıdır.

Sürümlü retrieval evaluation; title ağırlığı, nadir terim, Türkçe normalization ve global/program filtreleme senaryolarında Recall@3 %100, Top-1 accuracy %100 ve 0 forbidden violation sonucunu verir. Doğrulama baseline'ı: 443 test başarılı, core regression 3/3 PASS.

Kalıcı index bilinçli olarak sonraya bırakılmıştır; v0.1 küçük ve yerel in-memory katalog için tasarlanmıştır.

### FAZ 8 — Knowledge Base v0.1

**Durum: TAMAMLANDI**

Source → Document → Chunk provenance sözleşmesi, strict source/document manifest modelleri ve deterministik katalog doğrulaması mevcuttur. Duplicate kimlikler ve exact duplicate metin; orphan veya tutarsız provenance; eksik metadata; geçersiz status, kategori ve scope değerleri reddedilir.

Knowledge Base v0.1; 5 gerçek source, 6 document ve 14 kısa Türkçe paraphrase chunk içerir. `learning_method`, `study_planning`, `metacognition` ve `exam_rule` kategorileri ile `global` ve `yks` scope'ları temsil edilir. Akademik pedagojik kaynaklar aktif, 2026-YKS resmî kılavuzu tarihsel kullanım için `archived` durumundadır. Active production catalog yalnız `status=active` chunk'ları retrieval'a açar; archived ve superseded kayıtlar provenance/history için korunur.

Doğrulama baseline'ı: Knowledge Base testleri 20/20, full pytest 463 başarılı, RAG evaluation Recall@3 %100 / Top-1 accuracy %100 / 0 forbidden violation ve core regression 3/3 PASS.

### FAZ 9 — Orchestrator v1

**Durum: KISMİ**

Mevcut: user validation → memory load → final context routing → resolved/ambiguous/unavailable handling → intent detection → RAG need gating → optional retrieval → LLM call → optional strict StudyPlan proposal parsing/materialization → response evaluation → action orchestration. FAZ 9.1 kapsamında `StudyPlanWriteProposal`, `VALID/REJECTED/INCONCLUSIVE` validation report'u, deterministic ownership/context/goal ve günlük budget kontrolleri ile yalnız `VALID` proposal'ları mevcut `LearnerMemoryService.save_study_plan()` transaction sınırına ileten validated write-back gateway'i tamamlandı. FAZ 9.2 kapsamında typed active context resolution, authoritative specialty resolution ve keyword-only explicit context seçimi tamamlandı. FAZ 9.3a kapsamında dokümante edilmiş 11 intent için immutable, deterministik ve multi-intent destekli typed contract tamamlandı. FAZ 9.3b kapsamında planning, assessment analysis, study advice, goal setting, motivation support, knowledge question ve general conversation için conservative deterministic detector tamamlandı. FAZ 9.3c kapsamında ACTIVE context-scoped goal ve planlardan final seçim yapmadan memory evidence üreten Context Selection Evidence v0.1 tamamlandı. FAZ 9.3d kapsamında Specialty Profile configuration'ından okunan typed Context Routing Terminology ile tek kelimeyi yeterli saymayan, immutable ve conflict-aware Message Context Evidence v0.1 tamamlandı. FAZ 9.3e kapsamında explicit seçim, active context yapısı, current-message evidence ve goal/plan memory evidence'ı kesin precedence ile birleştiren Final Context Selection Policy + Runtime Integration v0.1 tamamlandı. Current-message consistent evidence memory'den güçlüdür; message conflict memory ile bastırılmaz. Multi-active unresolved durumda generic deterministic clarification döner ve RAG/LLM/validator çalışmaz. Registry olmadan explicit, zero/single-active ve memory routing backward-compatible çalışır. FAZ 9.4 kapsamında Full RAG Need Gating v0.1 tamamlandı: `KNOWLEDGE_QUESTION`/`STUDY_ADVICE` ve sınırlı high-precision external-knowledge sinyalleri `REQUIRED`, yalnız local memory/rule intent'leri `NOT_REQUIRED`, detector coverage dışı mesajlar `UNRESOLVED` olur. Runtime `REQUIRED → retrieve`, `NOT_REQUIRED → skip`, `UNRESOLVED → conservative retrieve` uygular; retrieval gerektiğinde 9.3e program scope'u aynen korunur. FAZ 9.5 kapsamında Structured StudyPlan Proposal Generation v0.1 tamamlandı: planning + resolved context için text-only provider'dan tek strict JSON envelope istenir, semantic proposal parse edilir ve learner/context/ID/status alanları authoritative sistem verileriyle `StudyPlanWriteProposal` olarak materialize edilir. Proposal otomatik validate veya persist edilmez; raw JSON yerine yalnız `response_text` mevcut response validator'a ve kullanıcıya gider. FAZ 9.6 kapsamında Validator Action Orchestration v0.1 tamamlandı: `PASS` kabul edilir, `BLOCK` mevcut fail-closed exception contract'ını korur, `REGENERATE` ve `AUTO_FIX` ayrı typed required-boundary exception'larıyla taşınır. FAZ 9.7 kapsamında Controlled Regeneration v0.1 tamamlandı: yalnız `REGENERATE`, aynı user message/snapshot/memory+RAG context ile bir system-owned feedback retry'ı tetikler. İkinci `REGENERATE`, `ResponseRegenerationExhausted` üretir; maksimum provider çağrısı ikidir. Generic fallback veya deterministic AUTO_FIX yoktur.

FAZ 9.8 kapsamında Deterministic Auto-Fix v0.1 tamamlandı: yalnız `OUTPUT_REPETITION_LOOP`, `AUTO_FIX` üretir; üç veya daha fazla ardışık normalized-equivalent segment tek kopyaya indirilir ve fixed text yeniden validate edilir. Structured proposal ile plan task'ları değiştirilmez. `PLAN_AVAILABLE_TIME_LIMIT` `REGENERATE` kalır; plan-duration redistribution policy henüz authoritative değildir.

Specialty Profile `rag_policy` alanı açık `JsonValue` olarak kaldığından 9.4 generic gate bu alanı kullanmaz; typed authoritative specialty RAG policy ayrı bir gelecek contract'ıdır. Provider-level native structured-output capability eklenmemiştir; 9.5 orchestration text-only provider contract'ını korur.

Eksikler: plan-budget deterministic redistribution policy, diğer structured proposal/memory write-back türleri ve authoritative recent-conversation contract sonrasında conversation-history routing.

Doğrulama baseline'ı: 885 test başarılı, core regression 3/3 PASS.

### FAZ 10 — Regression Evaluation

**Durum: TAMAMLANDI**

Deterministic core regression suite; learner context/isolation, program-scoped retrieval, historical repetition-loop protection, numeric-claim regeneration, bounded regeneration ve ambiguous-context fail-safe davranışlarını korur.

Doğrulama baseline'ı: 886 test başarılı, core regression 8/8 PASS.

### FAZ 11 — Development Evaluation Set

**Durum: BAŞLANMADI**

### FAZ 12 — Gerçek Learner Senaryoları

**Durum: BAŞLANMADI**

### FAZ 13 — HTTP API + Authentication

**Durum: BEKLEMEDE**

Core davranış sözleşmeleri oturmadan API/auth çalışmaları öne çekilmeyecek.

### FAZ 14 — Final Unseen Evaluation

**Durum: BAŞLANMADI**

### FAZ 15 — Fine-Tuning Karar Noktası

**Durum: BEKLEMEDE**

Fine-tuning yalnız prompt + rules + memory + RAG ile çözülemeyen ölçülmüş bir davranış problemi kalırsa yeniden değerlendirilecek.

## Aktif sıradaki iş

**FAZ 9 — Orchestrator v1**

StudyPlan validated write-back boundary, Active Context & Specialty Resolution v0.1, Typed Multi-Intent Contract, Conservative Intent Detection v0.1, Context Selection Evidence v0.1, Context Routing Terminology + Message Evidence v0.1, Final Context Selection Policy + Runtime Integration v0.1, Full RAG Need Gating v0.1, Structured StudyPlan Proposal Generation v0.1, Validator Action Orchestration v0.1, Controlled Regeneration v0.1 ve Deterministic Auto-Fix v0.1 tamamlandı. Plan-budget redistribution yalnız authoritative deterministic policy tanımlanırsa eklenecektir. Diğer proposal/write-back türleri ile conversation-history routing, authoritative contract'ları oluşana kadar eklenmeyecektir.
