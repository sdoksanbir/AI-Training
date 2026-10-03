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

## Doğrulama

Son test paketi: 133 test başarılı.

Ollama üzerinde `qwen3:14b` ile gerçek uçtan uca cevap üretimi doğrulandı.

## Sıradaki üretim işleri

1. Knowledge dosyalarını kaynak ve program metadata’sıyla düzenlemek.
2. Orchestrator’da program/context metadata’sını retriever filtrelerine bağlamak.
3. Sayısal iddialar ve desteklenmeyen kişiselleştirme için daha güçlü response validation.
4. Gerçek kullanım senaryoları için regression evaluation komutları.
5. CLI veya API giriş katmanı.
