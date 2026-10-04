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

Mevcut: user validation → memory load → RAG → LLM call → response validation. FAZ 9.1 kapsamında `StudyPlanWriteProposal`, `VALID/REJECTED/INCONCLUSIVE` validation report'u, deterministic ownership/context/goal ve günlük budget kontrolleri ile yalnız `VALID` proposal'ları mevcut `LearnerMemoryService.save_study_plan()` transaction sınırına ileten validated write-back gateway'i tamamlandı. FAZ 9.2 kapsamında typed active context resolution, authoritative specialty resolution, keyword-only explicit context seçimi ve ambiguous durumda global-only RAG scope'u tamamlandı.

Eksikler: intent/context selection, tam RAG gating, LLM structured proposal generation, validator action orchestration, controlled regeneration ve diğer memory write-back türleri.

Doğrulama baseline'ı: 501 test başarılı, core regression 3/3 PASS.

### FAZ 10 — Regression Evaluation

**Durum: BAŞLANGIÇ**

Mevcut: `scripts/run_core_regression.py`. Eksik: geçmiş fine-tuning problemlerini yeni mimaride kapsayan geniş regression suite.

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

StudyPlan validated write-back boundary ile Active Context & Specialty Resolution v0.1 tamamlandı. Mevcut akış üzerinde intent/context selection, tam RAG gating, LLM structured proposal generation ve validator action orchestration geliştirilecektir.
