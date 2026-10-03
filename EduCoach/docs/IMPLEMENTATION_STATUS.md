# EduCoach Uygulama Durumu

Son güncelleme: 3 Ekim 2026

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
- Boş, aşırı uzun ve doğrulanmamış dış bağlantı içeren cevap kontrolleri.
- Öğrenci hafızası izolasyonu ve prompt injection regresyon testleri.
- JSONL tabanlı knowledge yükleme, in-memory retrieval ve metadata filtreleri.
- Türkçe token normalizasyonu ve program bazlı context retrieval.
- Ollama provider sağlık kontrolü ve model yüklülük doğrulaması.
- `educoach` terminal giriş komutu.
- Deterministik core regression komutu.
- `SpecialtyProfile` domain sözleşmesi, versioned registry ve context/family doğrulaması.
- JSON loader ile paketlenen `school_7`, `yks`, `ales` ve `general_english` builtin profilleri.

## Doğrulama

Son test paketi: 213 test başarılı.

Ollama üzerinde `qwen3:14b` ile gerçek uçtan uca cevap üretimi doğrulandı.

## Faz durumu

- Mimari ve ürün kapsamı: tamamlandı.
- Uygulama çekirdeği: tamamlandı.
- Learner Memory Core: tamamlandı.
- LLM Provider v0.1: tamamlandı.
- Specialty Profiles Runtime: tamamlandı.
- Backend Rules: başlangıç seviyesinde.
- Response Validator: kısmi.
- RAG: temel sürüm çalışıyor.
- Knowledge Base ve Regression Evaluation: başlangıç seviyesinde.
- Orchestrator v1: kısmi.

## Sıradaki üretim işleri

1. Backend Rules v0.1 ve gelişmiş Response Validator.
2. Geniş regression ve development evaluation seti.
3. Kaynaklı Knowledge Base ve retrieval evaluation.

HTTP API ve authentication, core davranış sözleşmeleri olgunlaştıktan sonra ele alınacaktır.
