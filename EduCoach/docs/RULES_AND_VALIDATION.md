# EduCoach — Rules & Response Validation v0.1
**Tarih:** 2 Ekim 2026
**Durum:** Mimari Tasarım
---
# 1. Amaç
EduCoach yalnızca LLM cevabına güvenmeyecektir.
Sistemde iki ayrı güvenilirlik katmanı bulunacaktır:
```text
Backend Rules
→ işlem sırasında geçerli olan kesin kurallar ve sınırlar
Response Validator
→ LLM çıktısının bu kurallara ve bilinen gerçeklere uyup uymadığını kontrol eder
```
Amaç LLM'in:
- uydurma bilgi üretmesini,
- süre hesaplarını bozmasını,
- öğrenci profiliyle çelişmesini,
- yanlış sınav terminolojisi kullanmasını,
- bilinmeyen değerleri gerçekmiş gibi sunmasını,
- tekrar döngüsüne girmesini
mümkün olduğunca sistem seviyesinde engellemektir.
---
# 2. Temel İlke
EduCoach'ta:
```text
Kesin olarak hesaplanabilen şey
→ kod tarafından hesaplanmalıdır.
Kesin olarak doğrulanabilen şey
→ kod tarafından doğrulanmalıdır.
Pedagojik yorum gerektiren şey
→ LLM tarafından önerilebilir.
Kullanıcıya gönderilecek sonuç
→ Validator tarafından kontrol edilmelidir.
```
---
# 3. Rules ve Validator Farkı
Örnek kullanıcı bilgisi:
```text
Bugün 3 saat çalışabilirim.
```
Backend Rule:
```text
max_available_minutes = 180
```
LLM çıktısı:
```text
Matematik 70 dk
Türkçe 60 dk
Fen 60 dk
Toplam = 190 dk
```
Response Validator:
```text
FAIL
reason = PLAN_EXCEEDS_AVAILABLE_TIME
```
Burada 180 dakika sınırını LLM belirlemez.
Bu sınır Learner Memory ve Backend Rules tarafından belirlenir.
---
# 4. Rule Kaynakları
Bir istekte uygulanacak kurallar dört ana kaynaktan gelebilir:
```text
Core Rules
Specialty Rules
Intent Rules
Learner Constraints
```
---
# 5. Core Rules
Bütün EduCoach kullanım alanlarında geçerli kurallardır.
Örnek:
```text
bilinmeyen bilgiyi uydurma
kayıtlı gerçeklerle çelişme
müsait zamanı aşma
çıkarımı gerçek bilgi gibi sunma
planlanan ve gerçekleşen çalışmayı karıştırma
```
Core Rules her Specialty Profile için geçerlidir.
---
# 6. Specialty Rules
Belirli eğitim veya sınav bağlamına özgü kurallardır.
Örnek:
```text
YKS
→ net ile puanı karıştırma
Okul
→ yazılı notunu sınav neti gibi yorumlama
ALES
→ ALES'e özgü performans alanlarını başka sınav metriğiyle karıştırma
Dil sınavı
→ sınava ait olmayan beceri metriğini zorunlu varsayma
```
Bu kurallar Specialty Profile üzerinden yüklenir.
---
# 7. Intent Rules
İsteğin türüne bağlı kurallardır.
Örneğin:
```text
planning
→ toplam plan süresini kontrol et
assessment_analysis
→ kayıtlı assessment dışındaki sayıları uydurma
goal_setting
→ kullanıcı tarafından belirtilmeyen kesin hedef üretme
memory_update
→ inferred bilgiyi explicit fact gibi kaydetme
```
---
# 8. Learner Constraints
Kullanıcının gerçek durumundan gelen sınırlardır.
Örnek:
```text
bugün maksimum 120 dakika
çarşamba çalışamaz
akşam yalnız 19:00 sonrası müsait
aktif hedef = YDS
```
Bu bilgiler Learner Memory'den gelir.
---
# 9. Rule Önceliği
Çelişki durumunda genel öncelik:
```text
Safety / Privacy
↓
Hard Learner Constraints
↓
Core Rules
↓
Specialty Rules
↓
Intent Rules
↓
LLM Recommendation
```
LLM önerisi hiçbir hard rule'u geçersiz kılamaz.
---
# 10. Hard Rule ve Soft Rule
Kurallar iki ana gruba ayrılacaktır.
## Hard Rule
İhlal edildiğinde çıktı doğrudan kabul edilmez.
Örnek:
```text
müsait süreyi aşma
olmayan assessment sonucu üretme
TYT netini puan diye sunma
kayıtlı sınıf seviyesini değiştirme
```
## Soft Rule
Kaliteyi artırır ancak her ihlal kritik değildir.
Örnek:
```text
cevabı gereksiz uzatma
aynı öneriyi tekrar etme
çok fazla soru sorma
öğrencinin tercih ettiği iletişim tarzına uy
```
---
# 11. Rule Severity
Kurallara önem derecesi atanabilir:
```text
INFO
WARNING
ERROR
CRITICAL
```
Örnek:
```text
cevap biraz uzun
→ WARNING
plan 30 dakika fazla
→ ERROR
olmayan deneme sonucu uydurulmuş
→ CRITICAL
```
---
# 12. Bilinmeyen Bilgi Kuralı
Core hard rule:
> Bilinmeyen bilgi gerçekmiş gibi üretilemez.
Örneğin Learner Memory:
```text
TYT total net = 78
```
ancak ders dağılımı bilinmiyor.
LLM şunu söyleyemez:
```text
Türkçe 32
Matematik 24
Fen 12
Sosyal 10
```
Bu değerler kullanıcı veya doğrulanmış assessment tarafından sağlanmadıysa uydurmadır.
---
# 13. Explicit / Derived / Inferred Ayrımı
Validator bilgi kaynaklarını dikkate almalıdır.
```text
explicit
→ kullanıcı açıkça söyledi
derived
→ güvenilir veriden hesaplandı
inferred
→ sistem yorumu
uncertain
→ belirsiz
```
LLM:
```text
inferred
```
bir bilgiyi:
```text
kesin gerçek
```
gibi sunmamalıdır.
---
# 14. Sayısal Uydurma Kuralı
Özellikle aşağıdaki değerler kullanıcıdan veya güvenilir sistem kaydından gelmiyorsa dikkatle kontrol edilmelidir:
```text
net
puan
sıralama
not
yüzde
çalışma süresi
hedef değer
sınav sonucu
tamamlanma oranı
```
LLM pedagojik öneri olarak sayı önerecekse bunun:
```text
öneri
```
olduğu açık olmalıdır.
---
# 15. Süre Kuralı
Planlama sırasında backend:
```text
available_minutes
```
değerini bilir.
Planın tüm görev süreleri:
```text
sum(task.duration_minutes)
```
ile hesaplanır.
Hard rule:
```text
planned_minutes <= available_minutes
```
---
# 16. Zaman Çakışması Kuralı
Saat bazlı plan yapılırsa:
```text
task_start
task_end
```
aralıklarının:
- birbirleriyle,
- fixed commitments ile,
- unavailable zamanlarla
çakışmaması gerekir.
Bu kontrol LLM'e bırakılmayacaktır.
---
# 17. Negatif veya Geçersiz Süre
Aşağıdaki değerler geçersizdir:
```text
duration_minutes < 0
end_time < start_time
```
Ayrıca sıfır dakikalık gerçek study task varsayılan olarak geçersiz kabul edilebilir.
---
# 18. Planlanan ve Gerçekleşen Süre Ayrımı
EduCoach:
```text
planned_minutes
```
ile:
```text
actual_minutes
```
alanlarını karıştırmamalıdır.
Örneğin:
```text
Bugün 120 dakika planlandı.
```
demek:
```text
Bugün 120 dakika çalışıldı.
```
anlamına gelmez.
---
# 19. Assessment Gerçekliği
LLM yalnız kayıtlı assessment verilerini gerçek sonuç olarak kullanabilir.
Örneğin:
```text
Son matematik yazılısı = 55
```
kayıtlıysa kullanılabilir.
Ama:
```text
Muhtemelen önceki sınavın 70 civarındaydı.
```
gibi bir değer üretilemez.
---
# 20. Son Ölçüm ile Geçmiş Ölçümleri Karıştırmama
Bir assessment sonucu yenilendiğinde eski sonuç silinmez.
Validator:
```text
son sonuç
geçmiş sonuç
ortalama
trend
```
ifadelerinin doğru kayıtlara dayandığını kontrol edebilmelidir.
---
# 21. Trend Kuralı
Tek ölçümden trend çıkarılmamalıdır.
Örneğin tek sınav sonucuyla:
```text
Matematiğin sürekli düşüyor.
```
denemez.
Trend için minimum veri gereksinimi ilgili analiz politikasında tanımlanmalıdır.
---
# 22. Context Tutarlılığı
Cevap aktif Learning Context ile uyumlu olmalıdır.
Örneğin:
```text
active_context = school_7
```
iken ilgisiz biçimde:
```text
AYT matematik neti
```
üzerinden öneri oluşturulmamalıdır.
---
# 23. Çoklu Context Tutarlılığı
Bir kullanıcının:
```text
school_11
+
yks
```
context'leri varsa cevap gerekli olduğunda ikisini kullanabilir.
Ancak bir context'in verisi diğerine otomatik taşınmamalıdır.
Örneğin okul matematik yazılı performansı:
```text
TYT matematik neti
```
değildir.
---
# 24. Profile Terminoloji Kuralı
Her Specialty Profile kendi anlamlı terminolojisini kullanmalıdır.
Örneğin:
```text
school
→ yazılı, not, ödev, konu
yks
→ TYT, AYT, net, deneme
language_learning
→ reading, listening, vocabulary vb.
```
Terminoloji farklı profile ait kavramlarla rastgele karıştırılmamalıdır.
---
# 25. YKS Net / Puan Kuralı
YKS Specialty hard rule:
```text
net != score
```
Örneğin:
```text
TYT = 78 net
AYT = 44 net
```
verildiğinde:
```text
Toplam 122 puanın var.
```
denemez.
---
# 26. Hedef Uydurma Kuralı
Kullanıcı:
```text
Matematiğimi geliştirmek istiyorum.
```
dediyse sistem kendiliğinden:
```text
Hedefin 30 net olsun.
```
değerini gerçek hedef gibi kaydedemez.
Öneri olarak hedef sunulabilir:
```text
İstersen ilk ara hedefi birlikte belirleyebiliriz.
```
Ancak Memory'de gerçek hedef sayılmaz.
---
# 27. Ders / Konu Uydurma Kuralı
Learner Memory:
```text
Matematikte zorlanıyorum.
```
diyorsa sistem:
```text
Fonksiyonlarda eksiğin var.
```
diyemez.
Konu düzeyinde kanıt yoksa konu eksikliği bilinmiyor kabul edilir.
---
# 28. Pedagojik Çıkarım Kuralı
LLM pedagojik yorum yapabilir.
Örneğin:
```text
Son üç denemede aynı soru türünde hata yaptıysan bu alanı ayrıca incelemek yararlı olabilir.
```
Ancak bunu kesin teşhis gibi sunmamalıdır.
---
# 29. Tekrar Sorma Kuralı
Learner Memory'de güvenilir olarak bulunan bilgi gereksiz yere tekrar sorulmamalıdır.
Örneğin kayıtlı:
```text
grade_level = 11
```
ise:
```text
Kaçıncı sınıftasın?
```
yeniden sorulmamalıdır.
Ancak kayıt eski veya çelişkiliyse doğrulama sorusu gerekebilir.
---
# 30. Minimum Soru Kuralı
EduCoach öğrenciyi form doldurur gibi sorgulamamalıdır.
Bir görev için yalnız:
```text
kritik eksik bilgiler
```
sorulmalıdır.
Useful optional bilgiler daha sonra toplanabilir.
---
# 31. Hızlı Başlangıç Kuralı
Kullanıcı:
```text
Hemen bir plan ver.
Çok soru sorma.
```
gibi açık tercih bildirirse sistem mümkün olduğunca:
```text
minimum bilgi
→ uygulanabilir başlangıç
→ süreç içinde kişiselleştirme
```
yaklaşımını kullanmalıdır.
---
# 32. Tercih ile Güvenilirlik Çatışması
Kullanıcı soru sorulmasını istemese bile kritik bilgi olmadan güvenilir cevap üretilemiyorsa:
```text
tek kısa kritik soru
```
sorulabilir.
Kullanıcı tercihi hard doğruluk kurallarını geçersiz kılamaz.
---
# 33. Aşırı Kesinlik Kuralı
LLM kesin olmayan geleceğe ilişkin:
```text
Kesin 20 net artırırsın.
Kesin kazanırsın.
Bu programla mutlaka başarırsın.
```
gibi garantiler vermemelidir.
Bunun yerine:
```text
uygulanabilir hedef
olasılık
izlenecek gösterge
```
üzerinden konuşmalıdır.
---
# 34. Response Validator Pipeline
LLM çıktısı sırayla şu kontrollerden geçebilir:
```text
1. Schema Validation
2. Hard Constraint Validation
3. Memory Consistency
4. Context Validation
5. Specialty Validation
6. Numeric Validation
7. Repetition Validation
8. Hallucination Signal Validation
9. Output Quality Validation
```
---
# 35. Schema Validation
Yapılandırılmış çıktı gereken işlemlerde önce schema kontrol edilir.
Örneğin plan:
```text
tasks[]
duration_minutes
area_code
task_type
```
alanlarını gerektiriyorsa eksik veya geçersiz yapı kabul edilmez.
---
# 36. Hard Constraint Validation
Örnek kontroller:
```text
toplam süre
çalışılamayan zaman
aktif context
izin verilen task türleri
zorunlu alanlar
```
Hard constraint ihlalinde çıktı kullanıcıya doğrudan gönderilmez.
---
# 37. Memory Consistency Validation
Cevap Learner Memory ile karşılaştırılır.
Örnek:
Memory:
```text
grade_level = 7
```
Cevap:
```text
12. sınıf olduğun için...
```
Sonuç:
```text
FAIL
MEMORY_CONTRADICTION
```
---
# 38. Numeric Validation
Validator mümkün olan sayısal ifadeleri yapılandırılmış verilerle karşılaştıracaktır.
Örnek:
```text
available = 180
planned = 210
```
↓
```text
FAIL
PLAN_EXCEEDS_AVAILABLE_TIME
```
---
# 39. Repetition Validation
Fine-tuning deneylerinde gözlenen tekrar davranışı nedeniyle cevaplarda tekrar kontrolü bulunmalıdır.
Kontrol edilebilecek örnekler:
```text
aynı cümlenin tekrar edilmesi
aynı paragrafın tekrar edilmesi
yüksek n-gram tekrarı
aynı tavsiyenin döngü halinde yinelenmesi
```
---
# 40. Tekrar Kontrolü Tek Başına Karar Vermemelidir
Normal eğitim dilinde bazı kelimelerin tekrar etmesi doğaldır.
Bu nedenle:
```text
repetition score
```
tek başına her cevabı reddetmemelidir.
Açık loop davranışı ile doğal tekrar ayrılmalıdır.
---
# 41. Uydurma Sayı Sinyali
Cevapta geçen önemli sayılar:
```text
net
puan
süre
not
yüzde
sıralama
```
mümkün olduğunca bilinen veri veya yapılandırılmış öneri ile eşleştirilmelidir.
Kaynağı bulunamayan kritik sayı validator tarafından işaretlenebilir.
---
# 42. Önerilen Sayılar
Her sayı uydurma değildir.
Örneğin:
```text
İlk çalışma bloğunu 40 dakika yapabiliriz.
```
plan önerisidir.
Bunun kaynağı assessment olmak zorunda değildir.
Ancak yapılandırılmış planda:
```text
planned_minutes = 40
```
olarak görünmeli ve toplam süre kuralından geçmelidir.
---
# 43. Response Validator Sonuçları
Validator dört ana sonuç döndürür:
```text
PASS
AUTO_FIX
REGENERATE
BLOCK
```
---
# 44. PASS
Bütün kritik kontroller geçti.
Cevap kullanıcıya gönderilebilir.
---
# 45. AUTO_FIX
Hata deterministik olarak güvenli biçimde düzeltilebiliyorsa backend düzeltir.
Örnek:
```text
küçük biçim hatası
gereksiz boş alan
hesaplanabilir toplamın yanlış yazılması
```
Pedagojik içeriği değiştirecek düzeltmeler AUTO_FIX yapılmamalıdır.
---
# 46. REGENERATE
LLM çıktısının yeniden oluşturulması gerekir.
Örnek:
```text
Memory ile çelişen plan
önemli uydurma bilgi
süre kısıtına ciddi uyumsuzluk
açık tekrar döngüsü
```
LLM'e yalnız hata özeti ve gerekli düzeltme koşulları verilir.
---
# 47. BLOCK
Güvenilir cevap üretilemediğinde çıktı engellenir.
Sistem kontrollü fallback cevabı kullanabilir.
---
# 48. Validator Sonsuz Döngüye Girmeyecek
Regeneration sayısı sınırlı olacaktır.
Örneğin:
```text
max_regeneration_attempts = 1
```
veya gerekli görülürse:
```text
2
```
İlk sürümde gereksiz çoklu model çağrısı yapılmayacaktır.
---
# 49. Validation Report
Validator iç sistem için yapılandırılmış bir rapor döndürebilir.
Örnek:
```text
status = REGENERATE
violations:
- PLAN_EXCEEDS_AVAILABLE_TIME
- UNKNOWN_NUMERIC_CLAIM
severity = ERROR
```
Bu rapor kullanıcıya ham olarak gösterilmez.
---
# 50. Rule Kimlikleri
Kurallar insan tarafından okunabilir sabit kimliklere sahip olmalıdır.
Örnek:
```text
CORE_UNKNOWN_FACT
CORE_MEMORY_CONTRADICTION
PLAN_AVAILABLE_TIME_LIMIT
PLAN_TIME_OVERLAP
ASSESSMENT_UNKNOWN_RESULT
YKS_NET_SCORE_CONFUSION
OUTPUT_REPETITION_LOOP
```
Bu kimlikler:
- testlerde,
- loglarda,
- audit kayıtlarında,
- validator raporlarında
kullanılabilir.
---
# 51. Rule Registry
Kurallar merkezi bir registry üzerinden bulunabilir.
Kavramsal yapı:
```text
RuleRegistry
├── core
├── planning
├── assessment
├── specialty
└── output
```
Orchestrator yalnız ilgili kuralları çağırmalıdır.
---
# 52. Kural Konfigürasyonu
Her küçük kural Python koduna dağılmamalıdır.
Ancak bütün kuralları configuration dosyasına taşıma zorunluluğu da yoktur.
Genel yaklaşım:
```text
hesaplama / mantık
→ Python
değişebilir eşik / profile ayarı
→ configuration
güncel eğitim bilgisi
→ Knowledge / RAG
```
---
# 53. Koda Gömülmemesi Gereken Bilgiler
Özellikle zamanla değişebilecek:
```text
sınav süreleri
soru sayıları
puanlama ayrıntıları
müfredat içeriği
başvuru kuralları
```
Core Rules koduna sabit yazılmamalıdır.
---
# 54. Privacy Rules
Learner Memory'de gereksiz kişisel veri tutulmamalıdır.
Özellikle çocuk kullanıcılar düşünüldüğünde:
```text
minimum necessary data
```
ilkesi uygulanacaktır.
Rules katmanı ileride:
```text
data access
parent / learner permissions
data retention
```
gibi politikaları da destekleyebilir.
---
# 55. Yetkilendirme Kuralı
Bir kullanıcının başka bir learner kaydına erişimi yalnız izin sistemi üzerinden belirlenmelidir.
LLM:
```text
bu kullanıcı muhtemelen velidir
```
gibi bir çıkarımla erişim yetkisi veremez.
---
# 56. Teacher / Parent / Learner Ayrımı
İleride farklı roller eklendiğinde:
```text
learner
parent
teacher
coach
admin
```
erişim politikaları backend tarafından uygulanmalıdır.
Bu karar LLM'e bırakılmayacaktır.
---
# 57. Örnek — 6. Sınıf
Learner:
```text
school_6
bugün 90 dakika müsait
kesirlerde zorlandığını söyledi
```
LLM planı:
```text
40 dk kesirler
30 dk problem
30 dk tekrar
```
Toplam:
```text
100 dk
```
Validator:
```text
REGENERATE
PLAN_AVAILABLE_TIME_LIMIT
```
---
# 58. Örnek — YKS
Memory:
```text
TYT total net = 74
```
LLM:
```text
TYT puanın 74 olduğu için...
```
Validator:
```text
REGENERATE
YKS_NET_SCORE_CONFUSION
```
---
# 59. Örnek — Bilinmeyen Konu
Memory:
```text
matematik = weak
```
LLM:
```text
Fonksiyonlarda eksiğin olduğu için...
```
Validator:
```text
REGENERATE
CORE_UNKNOWN_FACT
```
çünkü konu düzeyinde kanıt yoktur.
---
# 60. Örnek — ALES
Memory:
```text
ALES hedef puanı = 80
```
Bu, öğrencinin mevcut puanının:
```text
80
```
olduğu anlamına gelmez.
Validator hedef ve mevcut performans alanlarını birbirinden ayırmalıdır.
---
# 61. Örnek — Okul Yazılısı
Assessment:
```text
Matematik yazılısı
grade = 65
```
LLM:
```text
Matematik netin 65.
```
Validator:
```text
REGENERATE
ASSESSMENT_METRIC_CONFUSION
```
---
# 62. Örnek — Plan ve Gerçekleşme
Study Plan:
```text
planned_minutes = 120
```
Study Sessions toplamı:
```text
actual_minutes = 70
```
LLM:
```text
Bugün 120 dakika çalıştın.
```
Validator:
```text
REGENERATE
PLAN_ACTUAL_CONFUSION
```
---
# 63. Öğretmenlik Kararları
Backend Rules pedagojik kararların tamamını katı kurallara dönüştürmeye çalışmamalıdır.
Örneğin:
```text
Bu öğrenci bugün matematik mi fizik mi çalışmalı?
```
çoğu durumda deterministik backend kuralı değildir.
Bu karar:
```text
Learner Memory
+
Goal
+
Performance
+
Specialty Knowledge
+
LLM reasoning
```
ile üretilebilir.
Backend yalnız sınırları kontrol eder.
---
# 64. Aşırı Kural Motorundan Kaçınma
EduCoach ilk sürümde yüzlerce karmaşık kural içeren expert system olmayacaktır.
Öncelik:
```text
yüksek etkili
kolay doğrulanabilir
sık hata üreten
kritik
```
kurallara verilecektir.
---
# 65. İlk Core Rule Set
v0.1 için önerilen ilk zorunlu kurallar:
```text
CORE_UNKNOWN_FACT
CORE_MEMORY_CONTRADICTION
CORE_CONTEXT_MISMATCH
PLAN_AVAILABLE_TIME_LIMIT
PLAN_TIME_OVERLAP
PLAN_ACTUAL_CONFUSION
ASSESSMENT_UNKNOWN_RESULT
ASSESSMENT_METRIC_CONFUSION
OUTPUT_REPETITION_LOOP
OUTPUT_UNSUPPORTED_GUARANTEE
```
---
# 66. İlk Specialty Rule Set
İlk temsilci profiller için örnek:
```text
YKS_NET_SCORE_CONFUSION
SCHOOL_GRADE_NET_CONFUSION
LANGUAGE_SKILL_METRIC_MISMATCH
```
ALES ve diğer profillerin gerçek kuralları ilgili profile hazırlanırken netleştirilecektir.
---
# 67. Test Stratejisi
Her rule için en az:
```text
1 passing case
1 failing case
```
olmalıdır.
Kritik kurallarda:
```text
edge cases
```
de eklenmelidir.
---
# 68. Deterministik Test
Rules ve Validator mümkün olduğunca aynı input için aynı sonucu üretmelidir.
Örneğin:
```text
available = 180
planned = 181
```
her çalıştırmada:
```text
FAIL
```
vermelidir.
---
# 69. LLM Gerektirmeyen Validator Testleri
Aşağıdaki testler LLM çağırmadan yapılabilir:
```text
süre toplamı
zaman çakışması
schema
context id
assessment metric
memory equality
```
Bu sayede testler hızlı ve ucuz olur.
---
# 70. LLM Gerektiren Kalite Testleri
Bazı kontroller:
```text
açık tekrar döngüsü
anlamsal çelişki
desteksiz kesin iddia
```
için ileride model tabanlı değerlendirme gerekebilir.
Ancak önce deterministik yöntem tercih edilecektir.
---
# 71. Audit
Her ihlal gerektiğinde audit log'a yazılabilir.
Örnek:
```text
request_id
rule_id
severity
validator_status
auto_fix_applied
regeneration_attempt
```
Bu kayıtlar sistem geliştirmede çok değerlidir.
---
# 72. Evaluation ile Bağlantı
Mevcut diagnostic benchmark'ta geçmişte bulunan sorunlar mümkün olduğunca rule / validator testlerine dönüştürülecektir.
Örneğin geçmiş problem:
```text
net → puan karışıklığı
```
artık yalnız benchmark'ta gözlemlemek yerine otomatik testle korunmalıdır.
---
# 73. Mimari Kazanım
Bu yaklaşım sayesinde EduCoach:
```text
Model doğru davranırsa çalışır.
```
seviyesinden:
```text
Model yanlış üretse bile kritik hataların önemli kısmı sistem tarafından yakalanır.
```
seviyesine geçer.
---
# 74. v0.1 Başarı Kriterleri
Rules & Validation sistemi başarılı kabul edilmek için:
1. Müsait süre ihlalini yakalamalı.
2. Plan / gerçekleşen çalışma ayrımını korumalı.
3. Bilinmeyen assessment değerlerini engellemeli.
4. Memory ile açık çelişkiyi yakalamalı.
5. Yanlış context kullanımını yakalayabilmeli.
6. En az temel metric karışıklıklarını engellemeli.
7. Açık tekrar loop'larını işaretleyebilmeli.
8. Validator sonucunu yapılandırılmış biçimde döndürmeli.
9. Regeneration sayısını sınırlandırmalı.
10. Her kritik rule otomatik test edilebilir olmalıdır.
---
# 75. Mimari Karar
EduCoach Rules & Validation sistemi şu prensiple geliştirilecektir:
> **LLM önerir; backend sınırları uygular; validator sonucu doğrular.**
Amaç LLM'in yaratıcılığını yok etmek değil, doğruluk gerektiren alanları model davranışından bağımsız hale getirmektir.
