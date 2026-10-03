# EduCoach Uygulama Durumu

Son güncelleme: 3 Ekim 2026

## Ürün kapsamı

EduCoach yalnız YKS uygulaması değildir. Genel çekirdek farklı eğitim alanlarına Specialty Profiles ile uzmanlaşır ve `Learner` / `Learner Memory` terminolojisini kullanır.

## Tamamlanan çekirdek parçalar

- Learner Memory modelleri, SQLite persistence ve transaction servisleri.
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

## Doğrulama

Son test paketi: 145 test başarılı.

Ollama üzerinde `qwen3:14b` ile gerçek uçtan uca cevap üretimi doğrulandı.

## Faz durumu

- Mimari ve ürün kapsamı: tamamlandı.
- Uygulama çekirdeği: tamamlandı.
- Learner Memory Core: büyük ölçüde tamamlandı.
- LLM Provider v0.1: tamamlandı.
- Specialty Profiles Runtime: başlanmadı.
- Backend Rules: başlangıç seviyesinde.
- Response Validator: kısmi.
- RAG: temel sürüm çalışıyor.
- Knowledge Base ve Regression Evaluation: başlangıç seviyesinde.
- Orchestrator v1: kısmi.

## Sıradaki üretim işleri

1. Eksiksiz kontrollü `LearnerMemorySnapshot` read model.
2. Specialty Profiles runtime registry ve profile modeli.
3. Backend Rules v0.1 ve gelişmiş Response Validator.
4. Geniş regression ve development evaluation seti.
5. Kaynaklı Knowledge Base ve retrieval evaluation.

HTTP API ve authentication, core davranış sözleşmeleri olgunlaştıktan sonra ele alınacaktır.
