# EduCoach — Current Status
**Son Güncelleme:** 2 Ekim 2026
## 1. Proje
**EduCoach**
İlk ürün odağı:
**YKS Eğitim Koçu**
Hedef kullanıcılar:
- 11. sınıf öğrencileri
- 12. sınıf öğrencileri
- Mezun öğrenciler
- TYT hazırlanan öğrenciler
- AYT hazırlanan öğrenciler
LGS desteği ilk sürümün kapsamı dışındadır. Daha sonra ayrı bir uzmanlık profili olarak değerlendirilecektir.
---
## 2. Temel Ürün Amacı
EduCoach'un amacı yalnızca öğrenciye soru çözen veya genel tavsiye veren bir sohbet botu oluşturmak değildir.
Sistem:
- öğrenciyi tanımalı,
- öğrencinin geçmiş verilerini hatırlamalı,
- mevcut durumunu analiz etmeli,
- gerçekçi çalışma planları üretmeli,
- TYT / AYT dengesini yönetmeli,
- deneme sonuçlarını analiz etmeli,
- net değişimlerini takip etmeli,
- güçlü ve zayıf alanları belirlemeli,
- önceki planların gerçekleşme durumunu değerlendirmeli,
- yeni plana gerçek öğrenci verilerine göre karar vermeli,
- gerektiğinde bilgi kaynaklarına başvurmalı,
- uydurma kişiselleştirme yapmamalıdır.
---
## 3. Aktif Mimari Kararı
İlk yaklaşımda eğitim koçluğu davranışının büyük kısmının fine-tuning ile Qwen3-4B modeline kazandırılması hedeflenmişti.
Yapılan deneylerden sonra bu yaklaşım **ana üretim mimarisi olmaktan çıkarılmıştır**.
Yeni aktif mimari:
```text
Kullanıcı
   ↓
Backend / Orchestrator
   ├── Student Memory
   ├── Backend Rules
   ├── RAG / Knowledge
   └── LLM Provider
            ↓
      Coach Response
            ↓
     Response Validator
            ↓
          Öğrenci
```
Ana bileşenler:
### LLM / Coach Brain
LLM'in görevi:
- verilen gerçekleri anlamlandırmak,
- öğrenciye doğal ve anlaşılır cevap vermek,
- koçluk iletişimini yürütmek,
- sağlanan öğrenci verisi ve bilgi kaynaklarını kullanarak öneri üretmek.
LLM tek başına bütün kararların sahibi olmayacaktır.
### RAG / Knowledge
RAG tarafı bilgi için kullanılacaktır.
Örnek içerikler:
- YKS sistemi
- TYT / AYT yapısı
- dersler
- konular
- müfredat
- konu ön koşulları
- çalışma yöntemleri
- deneme analizi yöntemleri
- zaman yönetimi yöntemleri
- gerektiğinde kaynak bilgileri
Bilgi mümkün olduğunca model ağırlıklarına ezberletilmeyecektir.
### Student Memory
Öğrenciye ait gerçek bilgiler veritabanında tutulacaktır.
Örnek alanlar:
- sınıf / mezuniyet durumu
- alan
- hedef
- TYT geçmişi
- AYT geçmişi
- ders bazlı netler
- deneme geçmişi
- güçlü dersler
- zayıf dersler
- konu eksikleri
- günlük / haftalık çalışma süresi
- okul / dershane düzeni
- verilen ödevlar
- tamamlanan çalışmalar
- önceki çalışma programları
- program gerçekleşme oranı
- öğrencinin çalışma alışkanlıkları
LLM'in bunları tahmin etmesi yerine gerçek veri kullanılacaktır.
### Backend Rules
Bazı kararlar yalnızca LLM'e bırakılmayacaktır.
Örnek kurallar:
- 5 saatlik program toplamda 5 saati aşamaz.
- TYT neti puan değildir.
- AYT neti puan değildir.
- TYT ve AYT netleri rastgele toplanarak YKS puanı üretilemez.
- Öğrencinin söylemediği ders neti uydurulamaz.
- Öğrencinin söylemediği hedef net uydurulamaz.
- Bilinmeyen konu eksikleri gerçekmiş gibi sunulamaz.
- Verilmiş öğrenci bilgisi gereksiz yere tekrar sorulamaz.
- Programdaki sürelerin toplamı doğrulanmalıdır.
- Model tarafından üretilen kritik sayısal öneriler doğrulanmalıdır.
### Response Validator
LLM cevabı doğrudan kullanıcıya gönderilmeden önce belirli kontrollerden geçirilebilecektir.
Örnek kontroller:
- toplam süre
- uydurma sayı
- net / puan karışıklığı
- öğrenci profilindeki bilgilerle çelişme
- tekrar döngüsü
- aşırı uzun cevap
- kritik eksik veri
- modelin bilmediği bilgiyi kesin gerçek gibi sunması
---
## 4. Fine-Tuning Durumu
Fine-tuning çalışmaları **silinmemiştir**.
Ancak yeni bir fine-tuning deneyi başlatılması şu anda **dondurulmuştur**.
Mevcut çalışmalar deney ve araştırma arşivi olarak korunmaktadır.
Temel model:
```text
Qwen/Qwen3-4B
```
Kullanılan yöntem:
```text
QLoRA
4-bit
BF16
RTX 5070 Ti 16 GB
```
Fine-tuning'in amacı ders bilgisini ezberletmek değil, koçluk davranışını geliştirmekti.
---
## 5. Tamamlanan Fine-Tuning Deneyleri
### v0.1
- 38 eğitim örneği
- 3 epoch
- learning rate: 2e-4
- LoRA rank: 16
- LoRA alpha: 32
Teknik olarak eğitim başarılı oldu.
Ancak davranış kalitesi bozuldu.
Başlıca problemler:
- tekrar döngüleri
- net / puan karışıklığı
- yanlış varsayımlar
- verilen bilgiyi yanlış kullanma
- gereksiz tekrar
- bazı senaryolarda base modelden daha kötü cevap
### v0.2
Gold Dataset genişletildi.
```text
120 örnek
70 single-turn
50 multi-turn
170 assistant mesajı
```
Ayarlar:
- 2 epoch
- learning rate: 1e-4
- rank: 16
- alpha: 32
- dropout: 0.05
Deneyler içinde en güçlü fine-tuned sürümlerden biri oldu ancak tekrar döngüleri devam etti.
### v0.3
Kontrollü deney:
```text
learning rate:
1e-4 → 5e-5
```
Sonuç iyileşmedi.
Daha düşük learning rate hipotezi tek başına çözüm olmadı.
### v0.4
Kontrollü deney:
```text
rank:
16 → 8
alpha:
32 → 16
```
Sonuç iyileşmedi.
Daha düşük LoRA kapasitesi tek başına çözüm olmadı.
### v0.5
LoRA yalnız attention katmanlarına sınırlandı:
```text
q_proj
k_proj
v_proj
o_proj
```
Sonuç v0.2'yi geçmedi.
Attention-only LoRA hipotezi çözüm olmadı.
### v0.6
Gold v0.5 ile kontrollü veri deneyi yapıldı.
Model ayarları v0.2 ile aynı bırakıldı.
Amaç yalnızca eğitim verisi değişikliğinin etkisini ölçmekti.
Sonuç:
- cevaplar bir miktar kısaldı,
- token sınırına vuran cevap sayısı azaldı,
- ancak tekrar döngülerinin toplam sayısı anlamlı biçimde azalmadı.
---
## 6. Gold Dataset Durumu
Mevcut aktif eğitim verisi:
```text
data/gold/gold_v0.5.jsonl
```
İçerik:
```text
120 örnek
170 assistant mesajı
```
Gold v0.5 oluşturulurken bazı hatalı davranış sinyalleri temizlendi.
Özellikle:
- bilinmeyen dersleri rastgele seçme,
- eksik bilgiyle aşırı kişiselleştirme,
- gereksiz varsayımlar
azaltılmaya çalışıldı.
Gold v0.4 referans olarak korunmaktadır.
Gold v0.5 de değiştirilmeden mevcut haliyle korunacaktır.
Fine-tuning yeniden ele alınırsa mevcut dataset doğrudan nihai veri seti olarak kabul edilmeyecektir.
---
## 7. Kritik Tanı Bulguları
Fine-tuning probleminin kaynağını bulmak için çok sayıda kontrollü deney yapıldı.
### Assistant-only loss doğrulandı
TRL'nin assistant-only loss mekanizması gerçek eğitim template'i ile incelendi.
120 Gold örneğin tamamında:
```text
assistant mask hatası                     : 0
assistant im_end loss dışı                : 0
system/user im_end loss içinde            : 0
2048 tokenı aşan örnek                    : 0
truncation ile assistant cevabı kesilen   : 0
```
En uzun Gold örnek yaklaşık:
```text
945 token
```
Sonuç:
**Loss mask, stop token veya sequence truncation ana problem olarak görünmemektedir.**
### Base ve fine-tuned model farkı
Özellikle sorunlu 8 diagnostic senaryoda:
```text
BASE greedy
→ 0 / 8 davranışsal loop
V06 checkpoint-15
→ 7 / 8 loop
V06 final
→ 8 / 8 loop
```
Bu sonuç fine-tuning adapterının loop davranışını oluşturduğuna dair güçlü kanıt sağladı.
### System prompt deneyi
V06 adapterı system prompt olmadan da test edildi.
Sonuç:
```text
7 / 8 loop
```
Uzun system prompt ana neden değildir.
### Sampling deneyi
Sampling:
```text
temperature = 0.7
top_p = 0.9
```
seçili 8 senaryoda loop sayısını:
```text
8 → 2
```
seviyesine düşürdü.
Ancak:
- yanlış matematik,
- uydurma netler,
- uydurma süreler,
- güvenilmez çıkarımlar
arttı.
Sampling çözüm olarak kabul edilmedi.
### Repetition penalty deneyi
```text
repetition_penalty = 1.05
```
bazı tekrarları azalttı.
Ancak genel cevap kalitesi güvenilir biçimde iyileşmedi.
Bu nedenle ana çözüm olarak kabul edilmedi.
### Token olasılık analizi
H002 üzerinde BASE, V06 checkpoint-15 ve V06 final karşılaştırıldı.
Fine-tuning ilerledikçe:
- seçilen tokenlara güven arttı,
- entropy azaldı,
- top-1 / top-2 farkı büyüdü,
- tekrar daha erken başladı.
Örnek:
```text
                 BASE      1 epoch     2 epoch
chosen prob      0.769     0.851       0.899
entropy          0.904     0.802       0.519
```
Bu, adapterın bazı bağlamlarda modeli düşük çeşitlilikli ve kendini güçlendiren üretim yollarına taşıdığını göstermektedir.
### LoRA scaling deneyi
V06 final adapterı H002 üzerinde farklı inference scaling değerlerinde test edildi.
```text
%100 → ağır loop
%75  → loop yok, 110 tokende im_end
%50  → loop + uydurma sayısal çıkarımlar
%25  → loop yok ancak 300 token sınırı ve içerik sorunları
```
Sonuç monoton değildir.
Sadece adapter gücünü azaltmak güvenilir bir çözüm değildir.
Scaling, modelin hangi üretim yoluna girdiğini ciddi biçimde değiştirmektedir.
---
## 8. Benchmark v0.2 Hakkındaki Kritik Karar
Mevcut dosya:
```text
evaluations/holdout/benchmark_v0.2.jsonl
```
artık **final unseen holdout olarak kabul edilmemektedir**.
İki neden vardır.
### Training-data overlap
Bazı holdout örnekleri Gold eğitim örneklerine çok benzerdir.
Özellikle:
```text
H001 ↔ Gold 39
H002 ↔ Gold 40
H003 ↔ Gold 64
H007 ↔ Gold 104
```
H002 ile Gold 40 özellikle çok yakın senaryolardır.
### Evaluation reuse
Benchmark v0.2;
- v0.2,
- v0.3,
- v0.4,
- v0.5,
- v0.6,
- repetition penalty,
- sampling,
- no-system,
- checkpoint,
- LoRA scaling
gibi birçok deney sırasında tekrar tekrar incelendi.
Bu nedenle benchmark v0.2 artık:
```text
REGRESSION / DIAGNOSTIC SET
```
olarak kullanılacaktır.
Final genelleme ölçümü için yeni ve gerçekten görülmemiş bir holdout daha sonra oluşturulacaktır.
---
## 9. Fine-Tuning Hakkındaki Mevcut Karar
Şu aşamada yeni:
```text
v0.7
v0.8
...
```
eğitimleri başlatılmayacaktır.
Çünkü şu ana kadar yapılan kontrollü deneyler:
- learning rate,
- rank,
- alpha,
- target modules,
- veri temizleme,
- repetition penalty,
- sampling,
- system prompt,
- epoch,
- LoRA scaling
üzerinde basit bir ayarla çözülebilecek istikrarlı bir problem göstermemiştir.
Fine-tuning tekrar ele alınırsa:
- daha büyük ve daha çeşitli veri,
- daha düşük senaryo tekrar oranı,
- gerçek kullanım örnekleri,
- bağımsız development set,
- gerçek unseen final holdout
ile yeniden tasarlanacaktır.
---
## 10. Yeni Ürün Stratejisi
Aktif ürün geliştirme sırası:
```text
1. Temel uygulama mimarisi
2. LLM provider katmanı
3. Student Memory
4. Backend Rules
5. Response Validator
6. RAG altyapısı
7. Knowledge Base
8. Koçluk orchestrator
9. Regression testleri
10. Gerçek öğrenci akışları
11. Gerekirse fine-tuning
```
Fine-tuning artık başlangıç noktası değil, gerekirse daha sonraki optimizasyon aşamasıdır.
---
## 11. LLM Stratejisi
İlk prototipte mevcut Qwen3-4B yerel model referans olarak kullanılabilir.
Ancak uygulama tek modele bağlı tasarlanmayacaktır.
LLM katmanı değiştirilebilir olmalıdır.
İleride:
- yerel model,
- daha büyük yerel model,
- OpenAI,
- Gemini,
- başka sağlayıcılar
aynı üst seviye EduCoach mimarisi tarafından kullanılabilmelidir.
Amaç model değiştirmek için ürünün geri kalanını yeniden yazmak zorunda kalmamaktır.
---
## 12. Maliyet Stratejisi
Geliştirme mümkün olduğunca düşük maliyetli yürütülecektir.
Çalışma biçimi:
```text
Basit işlem
→ kullanıcı terminalde çalıştırır
Analiz / mimari / teşhis
→ ChatGPT ile yapılır
Büyük repository incelemesi
→ gerektiğinde Codex
Editör içi orta ölçekli çalışma
→ gerektiğinde Cursor
```
Codex ve Cursor gereksiz yere kullanılmayacaktır.
Önce gerçek dosyalar incelenecek, sonra görev verilecektir.
---
## 13. Repo Durumu
Ana proje dizini:
```text
C:\AI-Training\EduCoach
```
Git repository ve GitHub kullanılmaktadır.
Mevcut ana alanlar:
```text
data/
docs/
evaluations/
notes/
prompts/
scripts/
training/
```
Fine-tuning deneyleri:
```text
training/
```
altında korunacaktır.
Mevcut değerlendirme ve diagnostic araçları:
```text
evaluations/
```
altında korunacaktır.
Yeni üretim sistemi mevcut deney yapısını bozmadan ayrı bir uygulama katmanı olarak eklenecektir.
---
## 14. Şu Anda Bulunduğumuz Aşama
**MİMARİ GEÇİŞ AŞAMASI**
Fine-tuning araştırması geçici olarak donduruldu.
Şimdi amaç:
```text
LLM
+
RAG
+
Student Memory
+
Backend Rules
+
Response Validator
```
tabanlı gerçek EduCoach uygulama mimarisini kurmaktır.
Henüz yeni uygulama klasörleri oluşturulmamıştır.
Önce mimari kesinleştirilecektir.
---
## 15. Sıradaki İş
Bir sonraki adım:
**Yeni üretim mimarisini kod yazmadan tasarlamak.**
Karar verilmesi gerekenler:
1. `app/` yapısı nasıl olacak?
2. Orchestrator ne yapacak?
3. Student Memory hangi verileri tutacak?
4. Backend Rules hangi kararları kontrol edecek?
5. Response Validator hangi hataları engelleyecek?
6. RAG hangi bilgi türlerini içerecek?
7. Knowledge Base hangi formatta tutulacak?
8. İlk prototip hangi LLM provider ile çalışacak?
9. Veritabanı ne olacak?
10. Regression ve final evaluation nasıl ayrılacak?
Bu mimari kararı verilmeden büyük kodlama yapılmayacaktır.
---
## 16. Çalışma İlkesi
EduCoach geliştirmesinde bundan sonra:
**Kanıt görmeden kod durumu hakkında varsayım yapılmayacaktır.**
Bir değişiklik gerektiğinde:
```text
Gerçek dosyayı incele
→ mevcut davranışı doğrula
→ değişiklik planını çıkar
→ küçük ve kontrollü değişiklik yap
→ test et
→ sonucu kaydet
```
yaklaşımı kullanılacaktır.
Basit terminal işlemleri doğrudan kullanıcı tarafından yapılacaktır.
Birden fazla dosyanın derin şekilde incelenmesi, büyük refactor veya geniş uygulama işleri gerektiğinde Codex veya Cursor kullanılabilir.
---
## 17. Yeni Sohbette Devam Etmek İçin
Öncelikle şu dosyalar okunmalıdır:
```text
README.md
CURRENT_STATUS.md
docs/ROADMAP.md
docs/CORE_SYSTEM_PROMPT.md
notes/decisions.md
```
Fine-tuning geçmişinin ayrıntıları gerektiğinde:
```text
training/configs/
evaluations/reports/
evaluations/post_training/
data/gold/
```
incelenmelidir.
Aktif geliştirme yönü için esas kaynak:
```text
CURRENT_STATUS.md
```
olmalıdır.
