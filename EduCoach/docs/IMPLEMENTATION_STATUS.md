# EduCoach Uygulama Durumu

Son güncelleme: 4 Ekim 2026

## Ürün kapsamı

EduCoach yalnız YKS uygulaması değildir. Genel çekirdek farklı eğitim alanlarına Specialty Profiles ile uzmanlaşır ve `Learner` / `Learner Memory` terminolojisini kullanır.

## Tamamlanan çekirdek parçalar

- Learner Memory modelleri, SQLite persistence ve transaction servisleri.
- Tüm mevcut memory kategorilerini learner scope içinde birleştiren `LearnerMemorySnapshot` read modeli.
- Assessment, StudyPlan, StudyTask ve StudySession kayıt akışları.
- Çalışma oturumu ile görev durumu senkronizasyonu.
- Model bağımsız `LLMProvider` sözleşmesi ve `FakeLLMProvider`.
- Ollama `/api/chat` provider bağlantısı.
- Öğrenci hafızasını orkestratöre aktaran `CoachOrchestrator`.
- Immutable backend rule contract'ları; fact projection'ları; availability ve plan-budget evaluator'ları.
- Typed response validation report ve `PASS`, `AUTO_FIX`, `REGENERATE`, `BLOCK` action contract'ı.
- Legacy response kontrolleri ile memory contradiction, unsupported personalization, assessment numeric claim, context/specialty, plan-budget, repetition-loop ve unsupported guarantee validation.
- Assessment sonuçlarında `correct`, `incorrect`, `blank`, `net`, `score`, `percentage`, `grade` ve `duration_minutes` ayrımı.
- Deterministik `BLOCK > REGENERATE > AUTO_FIX > PASS` precedence.
- Backward-compatible `validate_response` / `ResponseValidationError` facade'ı.
- Orchestrator snapshot ve opsiyonel `SpecialtyProfileRegistry` entegrasyonu.
- Öğrenci hafızası izolasyonu ve prompt injection regresyon testleri.
- JSONL tabanlı knowledge yükleme, in-memory retrieval ve metadata filtreleri.
- Türkçe token normalizasyonu ve program bazlı context retrieval.
- Ollama provider sağlık kontrolü ve model yüklülük doğrulaması.
- `educoach` terminal giriş komutu.
- Deterministik core regression komutu.
- `SpecialtyProfile` domain sözleşmesi, versioned registry ve context/family doğrulaması.
- JSON loader ile paketlenen `school_7`, `yks`, `ales` ve `general_english` builtin profilleri.

## Doğrulama

Son test paketi: 416 test başarılı.

Core regression: 3/3 PASS.

Ollama üzerinde `qwen3:14b` ile gerçek uçtan uca cevap üretimi doğrulandı.

## Faz durumu

- Mimari ve ürün kapsamı: tamamlandı.
- Uygulama çekirdeği: tamamlandı.
- Learner Memory Core: tamamlandı.
- LLM Provider v0.1: tamamlandı.
- Specialty Profiles Runtime: tamamlandı.
- Backend Rules v0.1: tamamlandı.
- Response Validator v0.1: tamamlandı.
- RAG: temel sürüm çalışıyor.
- Knowledge Base ve Regression Evaluation: başlangıç seviyesinde.
- Orchestrator v1: kısmi.

## Sıradaki üretim işleri

1. RAG retrieval evaluation ve daha güçlü retrieval/index stratejisi.
2. Kaynaklı Knowledge Base ve geniş development evaluation seti.
3. Orchestrator v1 kapsamında regeneration retry/action orchestration.

## Response Validator v0.1 sınırları

- Semantic parser dar ve deterministik Türkçe kalıplar kullanır.
- Assessment claim eşleştirmesi belirli sınav/tarih disambiguation yapmaz.
- Tanımlı olmayan context/specialty alias'ları tahmin edilmez.
- Plan parser yalnız açık ISO tarihli, satır bazlı plan bloklarını işler ve gerekli bilgiler kesin çözülebildiğinde backend evaluator'ı çağırır.
- UNKNOWN/AMBIGUOUS availability ihlal veya başarı kanıtı sayılmaz.
- `REGENERATE` action mevcuttur; retry/regeneration loop FAZ 9 Orchestrator v1 kapsamındadır.

HTTP API ve authentication, core davranış sözleşmeleri olgunlaştıktan sonra ele alınacaktır.
