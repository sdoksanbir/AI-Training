# EduCoach Fine-Tuning Research History

Bu belge, aktif üretim mimarisinden ayrılan Qwen3-4B QLoRA araştırma geçmişini korur. Eğitim config'leri, gold veri sürümleri, model çıktıları ve ayrıntılı raporlar `training/`, `data/gold/` ve `evaluations/` dizinlerindedir.

## Ortam ve amaç

- Temel model: `Qwen/Qwen3-4B`
- Yöntem: QLoRA, 4-bit, BF16
- Donanım: RTX 5070 Ti 16 GB
- Amaç: ders bilgisini ezberletmek yerine eğitim koçluğu davranışını geliştirmek

## Deneyler

- **v0.1:** 38 örnek, 3 epoch, learning rate `2e-4`, rank 16, alpha 32. Eğitim tamamlandı; tekrar döngüsü, net/puan karışıklığı ve yanlış varsayımlar görüldü.
- **v0.2:** 120 örnek, 170 assistant mesajı, 2 epoch, learning rate `1e-4`, rank 16, alpha 32, dropout 0.05. Güçlü sürümlerden biri oldu; loop sorunu sürdü.
- **v0.3:** Learning rate `5e-5` denendi; tek başına iyileşme sağlamadı.
- **v0.4:** Rank 8 ve alpha 16 denendi; düşük kapasite problemi çözmedi.
- **v0.5:** LoRA yalnız `q_proj`, `k_proj`, `v_proj`, `o_proj` katmanlarına uygulandı; v0.2'yi geçmedi.
- **v0.6:** Gold v0.5 ile kontrollü veri deneyi yapıldı. Cevaplar kısaldı; loop sayısı anlamlı biçimde azalmadı.

## Kritik tanı bulguları

Assistant-only loss 120 örnekte doğrulandı. Mask, stop token ve truncation ana problem görünmedi. Seçili sekiz senaryoda base greedy model 0/8 loop üretirken v0.6 checkpoint-15 7/8, final adapter 8/8 loop üretti.

System prompt kaldırıldığında 7/8 loop sürdü. Sampling loop sayısını düşürdü; yanlış matematik ve uydurma sayısal çıkarımları artırdı. Repetition penalty genel kaliteyi güvenilir biçimde iyileştirmedi. Token olasılık analizi fine-tuning ilerledikçe güvenin arttığını, entropy'nin azaldığını ve tekrarın erken başladığını gösterdi. LoRA scaling etkisi monoton değildi.

## Evaluation kararı

`evaluations/holdout/benchmark_v0.2.jsonl`, eğitim verisi benzerliği ve çok sayıda deneyde tekrar kullanılması nedeniyle final unseen holdout değildir. Regression/diagnostic set olarak korunur.

## Güncel karar

Yeni fine-tuning deneyi dondurulmuştur. Gold v0.5 ve adapter'lar araştırma arşividir; nihai üretim verisi veya zorunlu ürün bileşeni değildir.

Fine-tuning ancak çalışan mimaride prompt, rules, Learner Memory ve RAG ile çözülemeyen ölçülmüş bir problem kalırsa; daha çeşitli gerçek konuşmalar ve bağımsız development/final setlerle yeniden değerlendirilecektir.
