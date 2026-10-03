# EduCoach

EduCoach, farklı eğitim ve sınav senaryolarına uzmanlaşabilen genel öğrenme ve eğitim koçluğu platformudur.

Amaç yalnızca soru çözen bir sohbet botu yapmak değildir. Sistem learner'ı tanır, doğrulanmış geçmişini kullanır, eğitim bağlamına uygun bilgi getirir, deterministik kuralları uygular ve model cevabını kullanıcıya göndermeden önce doğrular.

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

- **Learner Memory:** learner'a ait gerçek ve kaynaklı veriler.
- **Specialty Profiles:** okul, sınav ve dil öğrenimi gibi bağlamlara özgü davranış ve terminoloji.
- **Backend Rules:** süre, sayısal tutarlılık ve context gibi deterministik kurallar.
- **RAG / Knowledge:** ortak ve kaynaklı eğitim bilgisi.
- **LLM Provider:** yerel veya gelecekte bulut modellerine ortak sözleşme.
- **Response Validator:** model çıktısındaki kritik ihlalleri denetler.
- **Orchestrator:** bileşenleri kontrollü bir akışta birleştirir.

Genel çekirdek YKS'ye veya başka tek bir sınava bağlı değildir. Örnek Specialty Profile'lar `school_5`–`school_12`, `lgs`, `yks`, `kpss`, `ales`, `yds`, `yokdil`, `toefl`, `ielts` ve `general_english` olabilir.

## Mevcut uygulama

- Pydantic domain modelleri
- SQLAlchemy/SQLite persistence ve repositories
- transaction kontrollü Learner Memory servisleri
- learner-scoped `LearnerMemorySnapshot` read modeli
- versioned Specialty Profile registry, JSON loader ve dört builtin profile
- model bağımsız LLM provider sözleşmesi
- Ollama provider ve health kontrolü
- JSONL tabanlı temel RAG
- temel rules ve response validation
- Coach Orchestrator
- CLI ve core regression komutu

Güncel faz durumları için [ROADMAP.md](docs/ROADMAP.md), gerçek uygulama özeti için [IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md) okunmalıdır.

## Fine-tuning geçmişi

İlk araştırma yaklaşımında Qwen3-4B üzerinde QLoRA v0.1–v0.6 deneyleri yapıldı. Eğitimler teknik olarak çalışsa da tekrarlama döngüleri ve güvenilmez sayısal çıkarımlar üretim kalitesini sınırladı.

Bu çalışmalar silinmemiştir; `training/`, `evaluations/` ve `data/gold/` altında frozen research archive olarak korunur. Fine-tuning aktif mimarinin başlangıç noktası veya zorunlu bileşeni değildir. İleride yalnız ölçülmüş ve diğer katmanlarla çözülemeyen bir davranış problemi için opsiyonel optimizasyon olarak değerlendirilebilir.

Deneylerin tarihsel özeti [FINE_TUNING_HISTORY.md](docs/FINE_TUNING_HISTORY.md) dosyasındadır.

## Geliştirme ve doğrulama

```text
python -m pytest
python scripts/run_core_regression.py
```

CLI kullanımı için [CLI_USAGE.md](docs/CLI_USAGE.md) dosyasına bakılabilir.

## Repository politikası

Kaynak kod, kontrollü veri, config, evaluation ve dokümantasyon Git'te tutulur. Büyük model dosyaları, checkpoint'ler ve geçici eğitim çıktıları repository'ye eklenmez.
