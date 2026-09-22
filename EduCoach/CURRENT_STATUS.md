# EduCoach — Current Status

**Son Güncelleme:** 22 Eylül 2026

## Proje

EduCoach

## Temel Model

Qwen3-4B

## Temel Amaç

Yerel olarak çalışabilecek, öğrencinin akademik gelişimini takip eden ve kişiselleştirilmiş eğitim koçluğu sağlayan bir yapay zekâ geliştirmek.

## Modelin Rolü

EduCoach bir ders öğretmeni veya yalnızca soru çözme modeli değildir.

Ana rolü:

* öğrenciyi tanımak,
* ihtiyaçlarını analiz etmek,
* hedef belirlemek,
* çalışma programı hazırlamak,
* deneme sonuçlarını analiz etmek,
* eksikleri belirlemek,
* çalışma stratejileri önermek,
* gelişimi takip etmek,
* öğrencinin durumuna göre planını değiştirmek.

## Mimari

```text
Coach Brain
→ Fine-Tuning / QLoRA
→ Eğitim koçluğu davranışı

Knowledge
→ RAG
→ Ders, müfredat ve kaynak bilgileri

Student Memory
→ Database
→ Öğrenci profili ve geçmişi
```

## Fine-Tuning

Planlanan yöntem:

```text
QLoRA
```

Fine-tuning'in ana hedefi ders bilgisini modele ezberletmek değil, eğitim koçluğu davranışını geliştirmektir.

## Tamamlanan İşler

* [x] Qwen3-4B indirildi ve test edildi.
* [x] Phi-4-mini indirildi ve test edildi.
* [x] Qwen3-4B ile Phi-4-mini karşılaştırıldı.
* [x] Başlangıç modeli olarak Qwen3-4B seçildi.
* [x] EduCoach proje klasörü oluşturuldu.
* [x] EduCoach proje planı hazırlandı.
* [x] Eğitim koçluğu yönü belirlendi.
* [x] Coach Brain / RAG / Student Memory mimarisi belirlendi.
* [x] Git repository oluşturuldu.
* [x] GitHub remote bağlantısı kuruldu.
* [x] `main` branch GitHub ile senkronize edildi.

## Şu Anda Bulunduğumuz Aşama

```text
FAZ 1 → FAZ 2
```

EduCoach davranış standardının kesinleştirilmesi ve Gold Dataset hazırlığı.

## Sıradaki İş

İlk:

```text
20–30 adet Gold Dataset örneği
```

hazırlanacak.

Bu veri hemen toplu olarak üretilmeyecek.

Önce birkaç örnek hazırlanacak, öğretmen gözüyle kalite kontrolü yapılacak ve kabul edilen format daha sonra veri setinin geri kalanına uygulanacak.

## Sonraki Adımlar

1. Davranış kategorilerini kesinleştir.
2. Gold Dataset formatını belirle.
3. İlk 5 örneği oluştur.
4. Örnekleri kalite açısından kontrol et.
5. 20–30 Gold Example'a tamamla.
6. Qwen3-4B baseline benchmark oluştur.
7. Eğitim veri setini genişlet.
8. GPU masaüstünde QLoRA ortamını kur.
9. EduCoach v0.1 eğit.
10. Öncesi/sonrası benchmark yap.

## Yeni Sohbette Devam Etmek İçin

Öncelikle şu dosyalar okunmalıdır:

```text
README.md
CURRENT_STATUS.md
notes/DECISIONS.md
docs/ROADMAP.md
docs/BEHAVIOR_SPEC.md
```

Ardından `CURRENT_STATUS.md` içerisindeki **Sıradaki İş** bölümünden devam edilmelidir.
