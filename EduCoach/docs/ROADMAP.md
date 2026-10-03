# EduCoach — Product & Architecture Roadmap

**Güncelleme:** 3 Ekim 2026

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

**Durum: BAŞLANGIÇ SEVİYESİNDE**

Eksikler: availability/time budget, plan süre doğrulama, unknown bilgi uydurmama, net/score/grade ayrımı, profile/context kuralları ve deterministik sayısal kısıtlar.

### FAZ 6 — Response Validator v0.1

**Durum: KISMİ**

Mevcut: boş cevap, maksimum cevap uzunluğu ve doğrulanmamış dış link kontrolü.

Eksikler: unsupported numerical claims, memory contradiction, unsupported personalization, plan structure, kritik varsayımlar ve rule engine entegrasyonu.

### FAZ 7 — RAG v0.1

**Durum: TEMEL SÜRÜM ÇALIŞIYOR**

Mevcut: JSONL yükleme, klasör kataloğu, in-memory retriever, metadata filtreleri, Türkçe token normalizasyonu, program/context filtreleme ve orchestrator entegrasyonu.

Eksikler: retrieval evaluation, daha güçlü retrieval/index stratejisi ve ileride kalıcı index.

### FAZ 8 — Knowledge Base v0.1

**Durum: BAŞLANGIÇ**

Mevcut: `data/knowledge/learning_methods_v1.jsonl`.

Eksik: gerçek kaynaklara bağlı, sürümlü, kapsamlı ve metadata'lı bilgi tabanı.

### FAZ 9 — Orchestrator v1

**Durum: KISMİ**

Mevcut: user validation → memory load → RAG → LLM call → response validation.

Eksikler: intent, active specialty resolution, rules, RAG gating, structured memory update proposals, validated write-back ve `PASS/AUTO_FIX/REGENERATE/BLOCK` benzeri action flow.

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

**FAZ 5 — Backend Rules v0.1**

Availability/time budget, plan süre doğrulama, bilinmeyen bilgi üretmeme ve profile/context kuralları için deterministik backend kontrolleri geliştirilecektir.
