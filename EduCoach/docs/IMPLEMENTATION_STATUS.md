# EduCoach Uygulama Durumu

Son güncelleme: 3 Ekim 2026

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

Son test paketi: 140 test başarılı.

Ollama üzerinde `qwen3:14b` ile gerçek uçtan uca cevap üretimi doğrulandı.

## Sıradaki üretim işleri

1. Sayısal iddialar ve desteklenmeyen kişiselleştirme için daha güçlü response validation.
2. Gerçek kullanım senaryoları için Ollama regression değerlendirmeleri.
3. HTTP API giriş katmanı ve kimlik doğrulama.
4. Kalıcı knowledge index ve daha gelişmiş retrieval.
