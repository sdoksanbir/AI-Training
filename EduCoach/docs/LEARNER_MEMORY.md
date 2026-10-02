# EduCoach — Learner Memory v0.1

**Tarih:** 2 Ekim 2026
**Durum:** Mimari Tasarım

---

# 1. Amaç

Learner Memory, EduCoach'un bir kullanıcı hakkında bildiği gerçek ve kullanılabilir bilgileri yapılandırılmış biçimde saklayan katmandır.

EduCoach yalnızca sınava hazırlanan öğrencileri desteklemeyecektir.

Sistem;

- 5, 6 ve 7. sınıf öğrencileri,
- LGS öğrencileri,
- 9, 10 ve 11. sınıf öğrencileri,
- YKS öğrencileri,
- mezun öğrenciler,
- KPSS adayları,
- ALES adayları,
- YDS adayları,
- YÖKDİL adayları,
- TOEFL adayları,
- IELTS adayları,
- ileride eklenecek diğer öğrenme ve sınav profilleri

için aynı temel hafıza mimarisini kullanabilmelidir.

Bu nedenle ana kavram:

```text
Student
```

değil:

```text
Learner
```

olacaktır.

---

# 2. Temel İlke

EduCoach'un çekirdeği herhangi bir sınava veya sınıf seviyesine bağımlı olmayacaktır.

```text
Learner
&#x20;  ↓
Learning Context
&#x20;  ↓
Goal
&#x20;  ↓
Assessment / Learning Evidence
&#x20;  ↓
Plan
&#x20;  ↓
Study Activity
&#x20;  ↓
Progress
```

YKS, LGS, KPSS, ALES veya İngilizce sınavları bu çekirdeğin üzerine eklenen uzmanlık alanlarıdır.

---

# 3. Learner Memory Ne Değildir?

Learner Memory:

- RAG değildir,
- sohbet geçmişi değildir,
- model context'i değildir,
- bilgi bankası değildir,
- bütün mesajların ham olarak saklandığı yer değildir.

Örneğin:

```text
"TYT kaç sorudan oluşur?"
```

bilgisi Learner Memory'de tutulmaz.

Bu RAG / Knowledge Base bilgisidir.

Ancak:

```text
"Bu öğrenci son TYT denemesinde 72 net yaptı."
```

Learner Memory bilgisidir.

---

# 4. En Önemli Veri Kuralı

EduCoach üç tür bilgiyi birbirine karıştırmayacaktır.

## 4.1 Gerçek / Bildirilmiş Bilgi

Öğrencinin veya yetkili bir kaynağın açıkça verdiği bilgi.

Örnek:

```text
"Matematikte zorlanıyorum."
```

Kaynak:

```text
learner\_reported
```

---

## 4.2 Ölçülmüş Bilgi

Bir sınav, deneme, yazılı veya başka ölçüm sonucundan gelen bilgi.

Örnek:

```text
Son üç matematik denemesi:
12 net
14 net
13 net
```

Kaynak:

```text
assessment\_derived
```

---

## 4.3 Sistem Çıkarımı

EduCoach'un mevcut verilerden yaptığı yorum.

Örnek:

```text
"Matematik performansında son üç denemede belirgin artış görünmüyor."
```

Kaynak:

```text
coach\_inferred
```

Bu çıkarım doğrudan gerçek bilgi gibi kaydedilmeyecektir.

---

# 5. Bilinmeyen Bilgi Kuralı

EduCoach için:

```text
NULL = bilinmiyor
```

demektir.

Bilinmeyen alanlar tahmin edilerek doldurulmayacaktır.

Örneğin öğrenci:

```text
"TYT 78 net yapıyorum."
```

dediyse sistem:

```text
TYT toplam net = 78
```

bilgisini bilir.

Ancak:

```text
Türkçe = 32
Matematik = 24
Fen = 12
Sosyal = 10
```

gibi bir dağılım üretemez.

---

# 6. Ana Veri Modeli

Learner Memory v0.1 aşağıdaki ana yapılardan oluşacaktır.

```text
Learner
│
├── LearningContext
├── Goal
├── Availability
├── Assessment
├── LearningEvidence
├── StudyPlan
├── StudyTask
├── StudySession
├── Preferences
└── CoachingState
```

---

# 7. Learner

Kişinin çekirdek profili.

Bu tablo mümkün olduğunca küçük tutulacaktır.

Önerilen alanlar:

```text
learner\_id
display\_name
education\_status
preferred\_language
timezone
created\_at
updated\_at
```

### education\_status örnekleri

```text
middle\_school
high\_school
graduate
university
working
other
unknown
```

Yaş veya doğum tarihi yalnız gerçekten gerekli olduğu durumda tutulacaktır.

Gereksiz kişisel veri toplanmayacaktır.

---

# 8. Learning Context

Learner Memory'nin en önemli yapılarından biridir.

Bir kişinin hangi eğitim veya sınav bağlamında çalıştığını gösterir.

Bir kullanıcı aynı anda birden fazla aktif Learning Context'e sahip olabilir.

Örneğin:

```text
11\. sınıf okul dersleri
+
YKS hazırlığı
```

veya:

```text
KPSS
+
YDS
```

aynı kişide birlikte bulunabilir.

Önerilen alanlar:

```text
context\_id
learner\_id
context\_type
program\_code
grade\_level
track
exam\_year
status
started\_at
ended\_at
```

### context\_type örnekleri

```text
school
entrance\_exam
public\_exam
academic\_exam
language\_exam
other
```

### program\_code örnekleri

```text
school\_5
school\_6
school\_7
lgs
school\_9
school\_10
school\_11
school\_12
yks
kpss
ales
yds
yokdil
toefl
ielts
```

Yeni programların eklenmesi Learner Memory şemasını değiştirmeyi gerektirmemelidir.

---

# 9. Goal

Kullanıcının hedefleri ayrı kayıtlar halinde tutulacaktır.

Bir kişi aynı anda birden fazla hedefe sahip olabilir.

Önerilen alanlar:

```text
goal\_id
learner\_id
context\_id
goal\_type
description
target\_value
target\_unit
target\_date
priority
status
created\_at
updated\_at
```

### Örnekler

6\. sınıf:

```text
Matematik yazılı notunu yükseltmek
```

8\. sınıf:

```text
LGS matematik netini geliştirmek
```

YKS:

```text
Sayısalda ilk 50.000
```

ALES:

```text
ALES Sayısal 80+
```

YDS:

```text
YDS 70+
```

Hedef türü sistem tarafından rastgele oluşturulmayacaktır.

---

# 10. Availability

Planlama yapabilmek için kişinin gerçek çalışma kapasitesi tutulacaktır.

Önerilen bilgiler:

```text
availability\_id
learner\_id
day\_of\_week
available\_minutes
start\_time
end\_time
availability\_type
effective\_from
effective\_until
source\_type
notes
```

### availability\_type

```text
available
unavailable
fixed\_commitment
```

Örneğin:

```text
Pazartesi
16:00–18:00
available
```

veya:

```text
Salı
18:00–20:00
fixed\_commitment
özel ders
```

Bu yapı sayesinde model yalnızca:

```text
"Günde 5 saat çalış."
```

demeyecek; kişinin gerçek zamanına göre plan yapabilecektir.

---

# 11. Assessment

Her türlü akademik ölçüm aynı temel yapı içinde tutulacaktır.

Assessment yalnızca deneme sınavı anlamına gelmez.

Örnekler:

```text
okul yazılısı
konu tarama testi
ödev değerlendirmesi
branş denemesi
LGS denemesi
TYT denemesi
AYT denemesi
KPSS denemesi
ALES denemesi
YDS denemesi
IELTS practice test
```

Ana kayıt:

```text
assessment\_id
learner\_id
context\_id
assessment\_type
assessment\_name
assessment\_date
source\_type
notes
```

Alt sonuçlar:

```text
assessment\_result\_id
assessment\_id
area\_type
area\_code
correct
incorrect
blank
net
score
percentage
grade
duration\_minutes
```

Bütün alanların dolması gerekmez.

Örneğin okul yazılısında:

```text
grade = 78
```

bulunabilir.

TYT denemesinde:

```text
correct
incorrect
blank
net
```

kullanılabilir.

IELTS denemesinde:

```text
score
```

kullanılabilir.

Böylece sistem tek bir ölçüm sistemine kilitlenmez.

---

# 12. Learning Evidence

Öğrencinin hangi ders, konu veya beceride ne durumda olduğunu temsil eder.

Bu bilgi doğrudan:

```text
strong\_subjects
weak\_subjects
```

şeklinde sabit listeler halinde tutulmayacaktır.

Kanıt tabanlı kayıt kullanılacaktır.

Önerilen alanlar:

```text
evidence\_id
learner\_id
context\_id
area\_type
area\_code
state
source\_type
confidence
assessment\_id
observed\_at
valid\_until
notes
```

### area\_type örnekleri

```text
subject
unit
topic
skill
question\_type
language\_skill
habit
```

### state örnekleri

```text
strong
adequate
developing
weak
unknown
```

### source\_type

```text
learner\_reported
teacher\_reported
assessment\_derived
coach\_inferred
system\_observed
```

---

# 13. Neden Kaynak Bilgisi Tutuyoruz?

Örnek:

Öğrenci:

```text
"Matematiğim çok iyi."
```

diyor.

Bu:

```text
state = strong
source\_type = learner\_reported
```

olarak kaydedilebilir.

Ancak son üç sınavda matematik performansı düşükse:

```text
state = weak
source\_type = assessment\_derived
```

şeklinde başka bir kanıt bulunabilir.

EduCoach bunlardan birini sessizce silmeyecektir.

Sistemin görevi çelişkiyi fark etmektir.

---

# 14. Study Plan

EduCoach'un oluşturduğu planlar kalıcı kayıt olacaktır.

Önerilen alanlar:

```text
plan\_id
learner\_id
context\_id
goal\_id
title
plan\_type
start\_date
end\_date
planned\_minutes
status
created\_at
```

### plan\_type

```text
daily
weekly
exam\_preparation
recovery
revision
custom
```

---

# 15. Study Task

Plan içerisindeki gerçek çalışma görevleri.

Önerilen alanlar:

```text
task\_id
plan\_id
context\_id
task\_date
area\_type
area\_code
task\_type
description
planned\_minutes
priority
status
completed\_at
actual\_minutes
```

### task\_type örnekleri

```text
study
practice
revision
exam
reading
vocabulary
homework
analysis
```

---

# 16. Study Session

Öğrencinin gerçekte yaptığı çalışmalar planlardan ayrı tutulacaktır.

Plan:

```text
ne yapması gerekiyordu?
```

Study Session:

```text
gerçekte ne yaptı?
```

sorusunun cevabıdır.

Önerilen alanlar:

```text
session\_id
learner\_id
context\_id
task\_id
started\_at
ended\_at
duration\_minutes
area\_type
area\_code
completion\_level
learner\_note
created\_at
```

Bu ayrım ileride EduCoach'un:

```text
Plan neden uygulanmadı?
```

sorusuna daha gerçekçi cevap verebilmesini sağlar.

---

# 17. Preferences

Her kullanıcı aynı şekilde çalışmaz veya iletişim kurmaz.

Önerilen alanlar:

```text
preference\_id
learner\_id
preference\_key
preference\_value
source\_type
updated\_at
```

Örnekler:

```text
preferred\_session\_minutes = 40
preferred\_study\_period = evening
response\_style = concise
question\_tolerance = low
```

Ancak bu tercihler sistem tarafından uydurulmayacaktır.

---

# 18. Coaching State

EduCoach'un o kullanıcıyla yürüttüğü aktif koçluk sürecini tutar.

Önerilen alanlar:

```text
learner\_id
active\_context\_id
active\_goal\_id
active\_plan\_id
next\_followup\_at
last\_review\_at
updated\_at
```

Burada öğrenci hakkında yeni akademik gerçekler saklanmayacaktır.

Bu tablo yalnızca:

```text
Şu anda hangi süreci yönetiyoruz?
```

sorusuna cevap verir.

---

# 19. Sohbet Geçmişi ve Learner Memory Ayrımı

Kullanıcı şunu yazabilir:

```text
"Bugün çok yoruldum, matematiği yarına bırakalım."
```

Mesaj sohbet geçmişinde tutulabilir.

Fakat Learner Memory'ye otomatik olarak:

```text
matematik sevmiyor
matematik çalışamıyor
matematik zayıf
```

şeklinde bilgi yazılmaz.

Sohbetten Learner Memory'ye bilgi aktarılması kontrollü olacaktır.

---

# 20. Memory Update Kuralları

## Kural 1

Açıkça verilen bilgi güvenli biçimde kaydedilebilir.

```text
"11. sınıfım."
```

↓

```text
grade\_level = 11
```

---

## Kural 2

Çıkarım gerçek bilgiye dönüştürülmez.

```text
"Son iki matematik denemesi düştü."
```

↓

Sistem bunu inceleyebilir.

Ancak:

```text
"Matematik temeli yok."
```

şeklinde kesin bilgi yazamaz.

---

## Kural 3

Çelişen bilgi sessizce ezilmez.

Örneğin:

```text
Eski kayıt:
günde 3 saat

Yeni kullanıcı mesajı:
artık günde 5 saat çalışabilirim
```

Yeni bilgi tarihçesiyle birlikte güncellenmelidir.

---

## Kural 4

Zamana bağlı bilgiler tarihsiz tutulmaz.

Örneğin:

```text
TYT = 78
```

yerine:

```text
TYT assessment
date = ...
net = 78
```

tercih edilmelidir.

---

## Kural 5

Geçmiş ölçümler silinmez.

Son net değiştiğinde eski netin üzerine yazılmayacaktır.

Bu sayede gelişim grafiği oluşturulabilir.

---

# 21. Örnek — 6. Sınıf

```text
LEARNER
education\_status = middle\_school

CONTEXT
program\_code = school\_6
grade\_level = 6

GOAL
Matematik yazılı performansını geliştirmek

LEARNING EVIDENCE
Matematik
state = weak
source = learner\_reported

ASSESSMENT
Matematik yazılısı
grade = 55
```

Burada TYT, AYT veya net kavramlarına ihtiyaç yoktur.

---

# 22. Örnek — 11. Sınıf + YKS

Aynı kişi iki bağlama sahip olabilir.

```text
CONTEXT 1
program\_code = school\_11

CONTEXT 2
program\_code = yks
exam\_year = 2028
```

Böylece EduCoach:

- okul derslerini,
- yazılıları,
- TYT hazırlığını,
- ileride AYT hazırlığını

aynı öğrencide birlikte yönetebilir.

---

# 23. Örnek — KPSS + YDS

```text
LEARNER
education\_status = graduate

CONTEXT 1
program\_code = kpss

CONTEXT 2
program\_code = yds

GOAL 1
KPSS hedefi

GOAL 2
YDS 70+
```

İki hazırlık süreci birbirine karıştırılmadan aynı Learner Memory altında tutulabilir.

---

# 24. Örnek — İngilizce Öğrenme

EduCoach yalnız sınav amacıyla da kullanılmak zorunda değildir.

Örneğin:

```text
CONTEXT
context\_type = language\_learning
program\_code = general\_english

GOAL
B1 seviyesinden B2 seviyesine ilerlemek
```

Learning Evidence:

```text
reading
listening
writing
speaking
vocabulary
grammar
```

üzerinden tutulabilir.

Bu nedenle çekirdek sistem yalnız sınav sonuçlarına bağlı olmayacaktır.

---

# 25. Programlara Özel Bilgiler

YKS, LGS, KPSS, ALES veya IELTS'e özel bütün alanlar ana Learner tablosuna eklenmeyecektir.

Yanlış yaklaşım:

```text
learner.tyt\_net
learner.ayt\_net
learner.kpss\_score
learner.ielts\_score
```

Doğru yaklaşım:

```text
Learner
&#x20;  ↓
LearningContext
&#x20;  ↓
Assessment
```

Bu sayede yeni bir eğitim alanı eklemek için ana veritabanı yapısını değiştirmek gerekmez.

---

# 26. Ders / Konu Taksonomisi

Learner Memory:

```text
Matematik nedir?
6\. sınıf matematik konuları nelerdir?
AYT matematik konuları nelerdir?
```

bilgisinin ana kaynağı olmayacaktır.

Ders:

```text
subject
unit
topic
skill
learning\_outcome
```

hiyerarşisi ayrı bir Curriculum / Knowledge katmanında tanımlanacaktır.

Learner Memory bu kayıtların kimliklerini kullanacaktır.

Örneğin:

```text
area\_code = math.functions
```

Bu sayede aynı konu adı farklı yerlerde tekrar tekrar yazılmaz.

---

# 27. Veri Gizliliği İlkesi

EduCoach özellikle çocuk kullanıcıları da destekleyeceği için gereksiz kişisel veri toplanmayacaktır.

Learner Memory'nin amacı:

```text
eğitim koçluğu için gerekli bilgi
```

saklamaktır.

Aşağıdaki bilgiler ihtiyaç yoksa tutulmamalıdır:

- açık adres,
- kimlik numarası,
- gereksiz doğum bilgileri,
- gereksiz aile bilgileri,
- eğitim koçluğu için gerekli olmayan özel bilgiler.

Yetkilendirme, veli ilişkileri ve veri erişim politikaları uygulama katmanında ayrıca tasarlanacaktır.

---

# 28. SQLite Kararı

İlk prototipte:

```text
SQLite
```

kullanılacaktır.

Nedenleri:

- ücretsiz,
- kurulumu kolay,
- yerel geliştirmeye uygun,
- prototip için yeterli,
- test edilmesi kolay,
- ileride PostgreSQL'e taşınabilir.

Veri modeli SQLite'a özel tasarlanmayacaktır.

---

# 29. RAG ile Kesin Ayrım

```text
Learner Memory
→ Bu kişi hakkında ne biliyoruz?
```

```text
RAG
→ Eğitim alanı hakkında ne biliyoruz?
```

Örnek:

```text
"Öğrenci 7. sınıfta."
→ Learner Memory

"7. sınıf matematik müfredatında hangi konular var?"
→ RAG / Curriculum

"Öğrenci oran-orantıda zorlanıyor."
→ Learner Memory

"Oran-orantı için hangi ön bilgiler gerekir?"
→ RAG
```

Bu iki sistem birbirine karıştırılmayacaktır.

---

# 30. v0.1 İçin Bilinçli Olarak Yapmayacağımız Şeyler

İlk sürümde:

- vector database ile öğrenci hafızası tutulmayacak,
- bütün konuşmalar embedding yapılıp memory kabul edilmeyecek,
- yüzlerce profil alanı oluşturulmayacak,
- sınavlara özel kolonlar ana Learner tablosuna eklenmeyecek,
- AI çıkarımları otomatik gerçek bilgiye dönüştürülmeyecek,
- PostgreSQL ile başlanmayacak,
- gereksiz mikroservis mimarisi kurulmayacak.

Önce küçük ve güvenilir çekirdek oluşturulacaktır.

---

# 31. Learner Memory v0.1 Ana Tabloları

İlk uygulama için hedeflenen tablolar:

```text
learners
learning\_contexts
goals
availability
assessments
assessment\_results
learning\_evidence
study\_plans
study\_tasks
study\_sessions
preferences
coaching\_state
```

Bunlar ilk implementasyondan önce tekrar gözden geçirilecektir.

---

# 32. Başarı Kriterleri

Learner Memory v0.1 başarılı kabul edilmek için şu davranışları sağlamalıdır:

1\. Kullanıcının daha önce verdiği temel bilgi gereksiz yere tekrar sorulmamalı.
2\. Bilinmeyen bilgi uydurulmamalı.
3\. Aynı kişi birden fazla eğitim hedefi taşıyabilmeli.
4\. YKS dışındaki kullanıcılar sisteme doğal biçimde uyabilmeli.
5\. Geçmiş sınav ve çalışma verileri kaybolmamalı.
6\. Gerçek bilgi ile AI çıkarımı ayrılmalı.
7\. Planlanan çalışma ile gerçekleşen çalışma ayrılmalı.
8\. Yeni sınav veya öğrenme türü eklemek ana veri modelini bozmamalı.
9\. RAG ile kişisel hafıza birbirine karışmamalı.
10\. Sistem ileride PostgreSQL'e taşınabilir olmalı.

---

# 33. Mimari Karar

EduCoach Learner Memory şu ilkeye göre geliştirilecektir:

> **Kullanıcıyı bir sınav türüne göre değil, zaman içinde değişen hedefleri, öğrenme durumu, performansı ve çalışma davranışı olan bir öğrenen olarak modelle.**

Bu ilke EduCoach'un bütün eğitim ve sınav uzmanlıklarının ortak hafıza altyapısını oluşturacaktır.
