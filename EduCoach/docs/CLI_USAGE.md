# EduCoach CLI Kullanımı

## Kurulum

Proje kökünde sanal ortamı etkinleştirdikten sonra paket kurulabilir:

```text
pip install -e .
```

Ollama çalışmalı ve seçilen model yüklü olmalıdır. Varsayılan model `qwen3:14b` değeridir.

## Yeni veritabanı

İlk çalıştırmada şema oluşturmak için:

```text
educoach --database data/educoach.db --create-schema --learner-id LEARNER_UUID "Bugün ne çalışmalıyım?"
```

Learner kaydı yoksa önce uygulama servisleriyle bir learner oluşturulmalıdır.

## Model seçimi

```text
educoach --database data/educoach.db --model qwen3:14b --learner-id LEARNER_UUID "YKS için plan yap"
```

CLI isteği göndermeden önce Ollama sağlık kontrolü yapar. Servis veya model hazır değilse güvenli bir hata ile durur.

## Core regression

Model çağrısı yapmadan deterministik çekirdek kontrollerini çalıştırmak için:

```text
python scripts/run_core_regression.py
```

Knowledge dosyaları `data/knowledge/` altında JSONL olarak tutulur ve kaynak, sürüm ve kategori metadata’sı taşımalıdır.
