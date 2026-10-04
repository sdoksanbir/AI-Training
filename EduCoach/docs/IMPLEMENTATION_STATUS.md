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
- JSONL tabanlı knowledge yükleme ve deterministic in-memory lexical retrieval.
- Term-frequency ve IDF-aware title/text ranking, Türkçe Unicode normalization ve `chunk_id` tie-break.
- Metadata filtreleri, açık global/program knowledge sözleşmesi, duplicate ID ve limit doğrulaması.
- Sürümlü retrieval evaluation seti ve Recall@3/Top-1 ölçüm scripti.
- Strict source ve document manifest contract'ları ile Source → Document → Chunk provenance validation.
- Beş gerçek kaynağa bağlı 6 document ve 14 kısa Türkçe paraphrase knowledge chunk.
- `learning_method`, `study_planning`, `metacognition`, `exam_rule` kategorileri; `global` ve `yks` scope'ları.
- Aktif pedagojik kaynaklardan ayrılan `archived` 2026-YKS lifecycle örneği.
- Archived ve superseded kayıtları history'de koruyup normal retrieval'dan çıkaran active production catalog loader'ı.
- Ollama provider sağlık kontrolü ve model yüklülük doğrulaması.
- `educoach` terminal giriş komutu.
- Deterministik core regression komutu.
- `SpecialtyProfile` domain sözleşmesi, versioned registry ve context/family doğrulaması.
- JSON loader ile paketlenen `school_7`, `yks`, `ales` ve `general_english` builtin profilleri.

## Doğrulama

Son test paketi: 463 test başarılı.

Knowledge Base testleri: 20/20 PASS.

Core regression: 3/3 PASS.

RAG retrieval evaluation: Recall@3 %100, Top-1 accuracy %100, forbidden violation 0.

Ollama üzerinde `qwen3:14b` ile gerçek uçtan uca cevap üretimi doğrulandı.

## Faz durumu

- Mimari ve ürün kapsamı: tamamlandı.
- Uygulama çekirdeği: tamamlandı.
- Learner Memory Core: tamamlandı.
- LLM Provider v0.1: tamamlandı.
- Specialty Profiles Runtime: tamamlandı.
- Backend Rules v0.1: tamamlandı.
- Response Validator v0.1: tamamlandı.
- RAG v0.1: tamamlandı.
- Knowledge Base v0.1: tamamlandı.
- Regression Evaluation: başlangıç seviyesinde.
- Orchestrator v1: kısmi.

## Sıradaki üretim işleri

1. Orchestrator v1 kapsamında intent, active specialty resolution, RAG gating ve regeneration retry/action orchestration.
2. Geniş regression ve ayrı development evaluation seti.
3. Katalog ölçeği ve ölçümler gerektirdiğinde persistent index değerlendirmesi.

## Response Validator v0.1 sınırları

- Semantic parser dar ve deterministik Türkçe kalıplar kullanır.
- Assessment claim eşleştirmesi belirli sınav/tarih disambiguation yapmaz.
- Tanımlı olmayan context/specialty alias'ları tahmin edilmez.
- Plan parser yalnız açık ISO tarihli, satır bazlı plan bloklarını işler ve gerekli bilgiler kesin çözülebildiğinde backend evaluator'ı çağırır.
- UNKNOWN/AMBIGUOUS availability ihlal veya başarı kanıtı sayılmaz.
- `REGENERATE` action mevcuttur; retry/regeneration loop FAZ 9 Orchestrator v1 kapsamındadır.

HTTP API ve authentication, core davranış sözleşmeleri olgunlaştıktan sonra ele alınacaktır.
