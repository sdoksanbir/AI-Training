# EduCoach — Specialty Profiles v0.1

**Tarih:** 2 Ekim 2026
**Durum:** Mimari Tasarım

---

# 1. Amaç

EduCoach tek bir sınava veya sınıf düzeyine göre tasarlanmayacaktır.

Ana ürün:

> **Farklı eğitim ve sınav senaryolarına uzmanlaşabilen genel bir öğrenme ve eğitim koçluğu platformudur.**

Bu nedenle:

```text
EduCoach Core
```

genel kalacak;

```text
Specialty Profile
```

katmanı ise belirli eğitim veya sınav alanının özelliklerini sisteme tanıtacaktır.

---

# 2. Temel Mimari

```text
&#x20;                    EduCoach Core
&#x20;                         │
&#x20;       ┌─────────────────┼─────────────────┐
&#x20;       │                 │                 │
&#x20;Learner Memory       Planning           Coaching
&#x20;       │                 │                 │
&#x20;       └─────────────────┼─────────────────┘
&#x20;                         │
&#x20;                Specialty Profile
&#x20;                         │
&#x20;      ┌──────────────────┼──────────────────┐
&#x20;      │                  │                  │
&#x20;  School 7             YKS               ALES
&#x20;      │                  │                  │
&#x20;Curriculum          TYT / AYT        Exam Structure
&#x20;Assessment           Subjects          Skills
&#x20;Rules                 Rules            Rules
&#x20;Knowledge             Knowledge        Knowledge
```

Specialty Profile yeni bir yapay zekâ modeli değildir.

Specialty Profile:

```text
EduCoach'a
"Bu kullanıcı hangi eğitim bağlamında çalışıyor?"
ve
"Bu bağlamda hangi kurallar ve bilgiler geçerli?"
```

sorularının cevabını verir.

---

# 3. Core ve Specialty Ayrımı

## EduCoach Core'un sorumlulukları

Her kullanıcıda ortak olan sistemler:

```text
Learner Memory
Goal Management
Planning
Study Task Tracking
Study Session Tracking
Assessment History
Progress Analysis
Coach Orchestrator
LLM Provider
RAG
Backend Rules Engine
Response Validator
```

Bunlar YKS, LGS veya KPSS'ye özel değildir.

---

## Specialty Profile'ın sorumlulukları

Uzmanlık alanına özgü bilgiler:

```text
hangi dersler var?
hangi beceriler takip edilir?
hangi değerlendirme türleri vardır?
hangi sonuç metrikleri kullanılır?
hangi terminoloji kullanılır?
hangi RAG kaynakları aranmalıdır?
hangi özel kurallar uygulanmalıdır?
hangi validator kontrolleri devreye girmelidir?
```

---

# 4. Ana İlke

Yanlış yaklaşım:

```text
if exam == "YKS":
&#x20;   ...
elif exam == "LGS":
&#x20;   ...
elif exam == "KPSS":
&#x20;   ...
elif exam == "ALES":
&#x20;   ...
```

Bu yaklaşım zamanla büyük ve kırılgan bir sisteme dönüşür.

Doğru yaklaşım:

```text
EduCoach Core
&#x20;     ↓
Specialty Profile Registry
&#x20;     ↓
Aktif Profil / Profiller
```

Yeni uzmanlık alanı mümkün olduğunca yeni çekirdek kod yazılmadan eklenebilmelidir.

---

# 5. İlk Specialty Profile Ailesi

EduCoach başlangıçta aşağıdaki profil ailelerini destekleyecek şekilde tasarlanacaktır.

## Okul Eğitim Profilleri

```text
school\_5
school\_6
school\_7
school\_8
school\_9
school\_10
school\_11
school\_12
```

Bunlar öğrencinin okul öğrenme sürecini temsil eder.

---

## Merkezi Sınav Profilleri

```text
lgs
yks
kpss
ales
```

---

## Dil Sınavı Profilleri

```text
yds
yokdil
toefl
ielts
```

---

## Genel Öğrenme Profilleri

Örneğin:

```text
general\_english
```

İleride:

```text
dgs
msu
tus
dus
sat
gre
gmat
```

gibi yeni profiller eklenebilir.

Bu liste veritabanı şemasına sabitlenmeyecektir.

---

# 6. Okul ve Sınav Profilleri Ayrı Olmalıdır

Bir sınıf düzeyi ile sınav hazırlığı aynı şey değildir.

Örneğin:

```text
8\. sınıf öğrencisi
```

otomatik olarak:

```text
LGS öğrencisi
```

kabul edilmemelidir.

Aynı şekilde:

```text
12\. sınıf öğrencisi
```

otomatik olarak:

```text
YKS hazırlığı yapıyor
```

anlamına gelmez.

Bu nedenle aynı kullanıcıda:

```text
school\_8
+
lgs
```

veya:

```text
school\_11
+
yks
```

gibi iki ayrı aktif Learning Context bulunabilir.

---

# 7. Neden Bu Ayrım Önemli?

Örneğin 11. sınıf öğrencisinin iki ayrı ihtiyacı olabilir:

### Okul bağlamı

```text
Fizik yazılısı
Matematik performansı
Ödevler
Okul konuları
```

### YKS bağlamı

```text
TYT matematik
TYT Türkçe
Denemeler
Sınav stratejisi
```

EduCoach bunları birbirine karıştırmamalıdır.

---

# 8. Specialty Profile Kimliği

Her profile ait en az şu bilgiler bulunmalıdır:

```text
profile\_code
profile\_family
display\_name
profile\_version
status
effective\_from
effective\_until
```

Örnek:

```text
profile\_code = yks
profile\_family = entrance\_exam
display\_name = YKS
profile\_version = 1
status = active
```

---

# 9. Neden Versiyonlama Gerekiyor?

Müfredatlar ve sınav sistemleri zaman içinde değişebilir.

Bu nedenle:

```text
yks
```

tek ve değişmez bir bilgi paketi kabul edilmeyecektir.

Profile bağlı bilgiler sürümlenebilir olacaktır.

Örneğin:

```text
profile\_code = yks
profile\_version = 3
```

şeklinde kullanılabilir.

Aynı mantık okul müfredatları için de geçerlidir.

---

# 10. Profile İçeriği

Bir Specialty Profile aşağıdaki yapıların tümünü veya bir bölümünü tanımlayabilir:

```text
identity
capabilities
taxonomy
assessment\_schema
goal\_schema
planning\_policy
rag\_policy
rules
validators
prompt\_context
terminology
```

---

# 11. Capabilities

Her profil hangi özelliklere ihtiyaç duyduğunu bildirebilir.

Örneğin:

```text
supports\_assessment\_tracking = true
supports\_subject\_tracking = true
supports\_topic\_tracking = true
supports\_score\_tracking = true
supports\_net\_tracking = false
supports\_rank\_tracking = false
supports\_time\_tracking = true
```

Bu değerler yalnız örnektir.

Gerçek değerler ilgili uzmanlık profili hazırlanırken belirlenecektir.

---

# 12. Taxonomy

Specialty Profile kendi ders ve alan bilgisini veritabanında tekrar tekrar oluşturmayacaktır.

Bunun yerine Curriculum / Knowledge sistemindeki taksonomiye bağlanacaktır.

Örneğin:

```text
profile = school\_6
taxonomy = curriculum.school.tr.grade6
```

veya:

```text
profile = yks
taxonomy = exam.tr.yks
```

---

# 13. Assessment Schema

Her profilde performans aynı biçimde ölçülmez.

Bu nedenle profil hangi ölçüm türlerinin kullanılabileceğini tanımlayacaktır.

Örneğin okul profili:

```text
written\_exam
quiz
homework
project
practice\_test
teacher\_evaluation
```

Sınav profili:

```text
mock\_exam
section\_test
topic\_test
```

Dil profili:

```text
practice\_test
reading\_test
listening\_test
writing\_assessment
speaking\_assessment
```

Assessment'ın gerçek alanları genel Learner Memory yapısında tutulacaktır.

---

# 14. Sonuç Metrikleri

Profile özgü sonuç türleri tanımlanabilir.

Örnek metrik aileleri:

```text
correct
incorrect
blank
net
score
percentage
grade
rank
duration
accuracy
```

Her profil bütün metrikleri kullanmak zorunda değildir.

Örneğin bir okul yazılısında:

```text
grade
```

önemli olabilir.

Bir dil öğrenme bağlamında:

```text
skill\_level
accuracy
```

daha anlamlı olabilir.

---

# 15. Goal Schema

Her profil kendi anlamlı hedef türlerini tanımlayabilir.

Örnek okul hedefleri:

```text
grade\_improvement
topic\_mastery
homework\_consistency
study\_habit
```

Örnek sınav hedefleri:

```text
score\_target
net\_target
rank\_target
section\_improvement
time\_management
```

Örnek dil öğrenme hedefleri:

```text
language\_level
vocabulary\_growth
reading\_improvement
speaking\_improvement
exam\_score
```

---

# 16. Planning Policy

Her profile aynı çalışma programı mantığı uygulanmayacaktır.

Örneğin:

```text
6\. sınıf
```

ile:

```text
KPSS adayı
```

aynı süre blokları ve aynı çalışma yoğunluğu ile planlanmamalıdır.

Specialty Profile;

```text
uygun çalışma blokları
dinlenme yaklaşımı
ödev önceliği
tekrar mantığı
deneme kullanım biçimi
```

gibi profile özgü planlama politikalarına katkı sağlayabilir.

Ancak son plan:

```text
Specialty Profile
+
Learner Memory
+
Availability
+
Goal
+
Current Progress
```

birlikte değerlendirilerek oluşturulacaktır.

---

# 17. Yaşa Göre Kör Planlama Yapılmayacaktır

Sistem:

```text
"6. sınıf = kesin 30 dakika çalışmalı"
```

gibi katı varsayımlar kullanmamalıdır.

Yaş ve sınıf seviyesi önemli bir bağlamdır ancak gerçek plan:

```text
öğrencinin durumu
ödev yükü
hedefleri
alışkanlıkları
müsait zamanı
performansı
```

ile birlikte belirlenmelidir.

---

# 18. RAG Policy

Specialty Profile RAG aramasını daraltabilmelidir.

Örneğin kullanıcının aktif profili:

```text
school\_7
```

ise RAG öncelikle ilgili:

```text
sınıf düzeyi
ders
müfredat
konu
```

kaynaklarında arama yapmalıdır.

Aktif profil:

```text
ales
```

ise okul müfredatı belgeleri varsayılan bilgi kaynağı olmamalıdır.

---

# 19. RAG Metadata

Knowledge Base belgelerinde ileride aşağıdaki tür metadata kullanılabilir:

```text
country
education\_system
profile\_code
grade\_level
exam\_code
subject
unit
topic
skill
curriculum\_version
source
source\_date
effective\_from
effective\_until
```

Bütün belgeler bütün alanları taşımak zorunda değildir.

---

# 20. Değişebilir Sınav Bilgileri Kod İçine Gömülmeyecektir

Örneğin:

```text
soru sayısı
sınav süresi
puan hesaplama ayrıntıları
ders dağılımları
başvuru kuralları
```

gibi zaman içinde değişebilecek bilgiler Python kodunun içine sabit değer olarak yazılmamalıdır.

Bunlar mümkün olduğunca:

```text
versioned knowledge
+
profile configuration
```

üzerinden yönetilmelidir.

---

# 21. Rules

Specialty Profile kendi ek kurallarını sisteme verebilir.

Örneğin genel Core kuralı:

```text
bilinmeyen sayıyı uydurma
```

her profil için geçerlidir.

Ama bazı profile özgü kontroller de bulunabilir.

Örneğin:

```text
YKS bağlamında net ve puanı birbirine karıştırma.
```

veya:

```text
Okul yazılı notunu sınav neti gibi değerlendirme.
```

---

# 22. Genel Kurallar Profil İçine Taşınmayacaktır

Aşağıdaki gibi kurallar Core'da kalmalıdır:

```text
toplam planlanan süre müsait zamanı aşmasın
bilinmeyen bilgi uydurulmasın
Learner Memory ile çelişen bilgi kullanılmasın
planlanan ve gerçekleşen çalışma ayrıştırılsın
```

Çünkü bunlar bütün profillerde geçerlidir.

---

# 23. Validators

Specialty Profile cevaba özel ek kontroller sağlayabilir.

Örneğin:

```text
allowed\_metric\_types
required\_context\_fields
forbidden\_metric\_confusions
profile\_specific\_numeric\_checks
```

Ancak validator'ın temel altyapısı Core'da olacaktır.

---

# 24. Prompt Context

Profile özgü bilgi gerektiğinde LLM context'ine küçük bir uzmanlık bölümü eklenebilir.

Örneğin:

```text
Aktif uzmanlık: ALES
```

ve profile özgü temel davranış bilgisi.

Ancak devasa sınav bilgisi system prompt içine doldurulmayacaktır.

Ayrıntılı bilgiler gerektiğinde RAG'den alınacaktır.

---

# 25. Prompt ile Knowledge Ayrımı

Prompt:

```text
nasıl davranılacağını
```

söyler.

Knowledge:

```text
gerçek eğitim bilgisini
```

sağlar.

Örneğin:

```text
"Kullanıcının belirtmediği sonucu uydurma."
```

bir davranış kuralıdır.

Ancak:

```text
"Bu sınavın güncel yapısı nedir?"
```

Knowledge / RAG sorusudur.

---

# 26. Birden Fazla Aktif Profil

Bir kullanıcı aynı anda birden fazla profile sahip olabilir.

Örneğin:

```text
school\_11
+
yks
```

veya:

```text
kpss
+
yds
```

Orchestrator mesajın hangi bağlamla ilgili olduğunu belirlemelidir.

---

# 27. Context Routing

Örnek:

Kullanıcı:

```text
"Yarın matematik yazılım var."
```

11\. sınıf öğrencisinde öncelikli bağlam:

```text
school\_11
```

olabilir.

Kullanıcı:

```text
"TYT matematik denemesinde süre yetişmedi."
```

aynı öğrencide bağlam:

```text
yks
```

olmalıdır.

Bu seçim yalnız profile göre değil, kullanıcının mesajına göre yapılacaktır.

---

# 28. Belirsiz Bağlam

Mesaj birden fazla profile uyuyorsa sistem hemen gereksiz soru sormamalıdır.

Önce:

```text
Learner Memory
aktif hedef
yakın geçmiş
aktif plan
mesaj içeriği
```

kullanılmalıdır.

Gerçekten karar verilemiyorsa kısa bir açıklayıcı soru sorulabilir.

---

# 29. Okul Profilleri

İlk okul profili ailesi:

```text
school\_5
school\_6
school\_7
school\_8
school\_9
school\_10
school\_11
school\_12
```

Takip edilebilecek alanlar:

```text
dersler
konular
kazanımlar
yazılılar
ödevler
projeler
çalışma alışkanlıkları
konu ilerlemesi
performans değişimi
```

Bu profile yalnız sınav mantığı uygulanmamalıdır.

---

# 30. LGS Profili

LGS ayrı bir uzmanlık profilidir.

LGS profili:

```text
lgs
```

okul bağlamından bağımsız olarak etkinleştirilebilir.

LGS'ye özel:

```text
değerlendirme yapısı
performans metrikleri
çalışma stratejileri
deneme analizi
zaman yönetimi
```

profile özgü yapı üzerinden yönetilecektir.

Güncel sınav ayrıntıları kod içine gömülmeyecektir.

---

# 31. YKS Profili

YKS profili:

```text
yks
```

olarak tanımlanacaktır.

TYT / AYT gibi alt bağlamlar profile ait domain yapısında temsil edilebilir.

YKS'ye özel:

```text
alan bilgisi
TYT / AYT bağlamı
net takibi
deneme analizi
zaman yönetimi
hedef takibi
```

gibi özellikler bulunabilir.

Bunlar ana Learner tablosuna kolon olarak eklenmeyecektir.

---

# 32. KPSS Profili

KPSS:

```text
kpss
```

profil ailesi altında yönetilecektir.

KPSS'nin farklı aday veya sınav türleri olması durumunda bunlar:

```text
profile variant
```

veya profile metadata ile temsil edilebilir.

Ana EduCoach çekirdeğinin değiştirilmesi gerekmemelidir.

---

# 33. ALES Profili

ALES:

```text
ales
```

olarak tanımlanacaktır.

Profile özgü performans alanları ve değerlendirme metrikleri profile configuration üzerinden tanımlanacaktır.

Örneğin:

```text
sayısal performans
sözel performans
süre kullanımı
soru türü performansı
```

gibi ölçümler desteklenebilir.

---

# 34. Dil Sınavları

İlk dil sınavı profilleri:

```text
yds
yokdil
toefl
ielts
```

olacaktır.

Ortak dil becerisi taksonomisi mümkün olduğunca paylaşılacaktır.

Örneğin:

```text
reading
listening
writing
speaking
grammar
vocabulary
```

Ancak her sınav aynı becerileri veya aynı değerlendirme biçimini kullanmak zorunda değildir.

---

# 35. Genel İngilizce

```text
general\_english
```

bir sınav profili değildir.

Ama EduCoach'un aynı çekirdeğiyle yönetilebilir.

Örnek hedefler:

```text
kelime gelişimi
okuma
dinleme
yazma
konuşma
genel dil seviyesi
```

Bu, sistemin yalnız sınav hazırlığına bağlı olmadığını gösteren önemli bir kullanım alanıdır.

---

# 36. Profile Registry

Sistem aktif profilleri merkezi bir registry üzerinden bulacaktır.

Kavramsal örnek:

```text
SpecialtyProfileRegistry

school\_5
school\_6
school\_7
school\_8
school\_9
school\_10
school\_11
school\_12
lgs
yks
kpss
ales
yds
yokdil
toefl
ielts
general\_english
```

Registry profile ait configuration'ı döndürür.

---

# 37. Profile Configuration

İlk sürümde profile bilgilerini Python koduna dağıtmak yerine yapılandırılmış dosyalarda tutmayı hedefleyeceğiz.

Örneğin ileride:

```text
specialties/
├── school/
├── exams/
└── languages/
```

altında profile configuration bulunabilir.

Format implementasyon aşamasında kesinleştirilecektir.

YAML veya JSON kullanılabilir.

---

# 38. Örnek Kavramsal Profile

Örnek:

```text
profile\_code: school\_7
family: school
version: 1

capabilities:
&#x20; assessment\_tracking: true
&#x20; topic\_tracking: true
&#x20; study\_planning: true

rag:
&#x20; curriculum\_scope: school\_7

rules:
&#x20; use\_school\_assessment\_semantics: true
```

Bu yalnız kavramsal örnektir.

Henüz gerçek configuration formatı değildir.

---

# 39. Uzmanlık Profili Kullanıcıyı Tanımlamaz

Çok önemli ayrım:

```text
Learner
```

kişidir.

```text
Learning Context
```

kişinin aktif eğitim bağlamıdır.

```text
Specialty Profile
```

sistemin o bağlamı nasıl yorumlayacağını tanımlar.

Örneğin:

```text
Learner:
Ayşe

Learning Context:
11\. sınıf

Specialty Profile:
school\_11
```

Aynı Ayşe için ikinci context:

```text
Learning Context:
YKS hazırlığı

Specialty Profile:
yks
```

olabilir.

---

# 40. Specialty Profile İçine Koymayacağımız Şeyler

Profile içine:

- öğrenciye ait kişisel bilgiler,
- öğrencinin netleri,
- öğrencinin hedefleri,
- öğrencinin çalışma saatleri,
- sohbet geçmişi,
- aktif çalışma planı

konulmayacaktır.

Bunlar Learner Memory'nin sorumluluğudur.

---

# 41. Knowledge Base İçine Koymayacağımız Şeyler

Knowledge Base içine:

```text
Ayşe matematikte zayıf
Mehmet günde 4 saat çalışıyor
```

gibi kişisel bilgiler konulmayacaktır.

Knowledge Base ortak eğitim bilgisidir.

---

# 42. İlk Uygulamada Her Profili Tamamlamayacağız

Mimari bütün profilleri destekleyecek şekilde kurulacaktır.

Ancak ilk uygulama aşamasında bütün uzmanlıkların bütün bilgilerini doldurmak gereksizdir.

Önce birkaç temsilci profil ile altyapı doğrulanabilir.

Örneğin:

```text
school\_7
yks
ales
general\_english
```

gibi birbirinden farklı dört profil mimarinin gerçekten genel olup olmadığını test etmek için kullanılabilir.

Daha sonra diğer profiller eklenebilir.

---

# 43. Eğitimsel İçeriğin Doğrulanması

Teknik mimari ile eğitimsel doğruluk ayrı sorumluluklardır.

Teknik sistem:

```text
veriyi saklar
profili yükler
RAG'i filtreler
kuralları çalıştırır
```

Ancak:

```text
öğrenciye uygulanacak pedagojik strateji
çalışma süresi yaklaşımı
konu sıralaması
öğrenme yöntemi
planlama mantığı
```

öğretmen gözüyle ayrıca değerlendirilmelidir.

Bu noktalarda eğitim uzmanlığına göre profil içeriği gözden geçirilecektir.

---

# 44. Yeni Profil Ekleme Başarı Kriteri

Yeni bir profile örneğin:

```text
dgs
```

eklendiğinde mümkünse:

```text
Learner Memory schema
Core Orchestrator
LLM Provider
Study Plan schema
Assessment temel yapısı
```

değişmemelidir.

Eklenmesi gerekenler esas olarak:

```text
profile configuration
knowledge sources
taxonomy
profile-specific rules
profile-specific validators
```

olmalıdır.

Bu şart sağlanıyorsa mimari doğru yöndedir.

---

# 45. v0.1 Tasarım Kararı

EduCoach uzmanlık sistemi şu prensibe göre geliştirilecektir:

> **Çekirdek öğreneni yönetir; uzmanlık profili eğitim bağlamını açıklar.**

Başka bir ifadeyle:

```text
Learner Memory
→ Bu kişi hakkında ne biliyoruz?

Specialty Profile
→ Bu kişinin bulunduğu eğitim bağlamı nasıl çalışıyor?

Knowledge / RAG
→ Bu bağlam hakkında hangi doğrulanmış bilgiye sahibiz?

Orchestrator
→ Bunları kullanarak şimdi ne yapmalıyız?

LLM
→ Bunu kullanıcıya nasıl anlatmalıyız?

Validator
→ Üretilen cevap güvenli ve tutarlı mı?
```

Bu ayrım EduCoach'un uzun vadeli temel mimari ilkelerinden biri olacaktır.
