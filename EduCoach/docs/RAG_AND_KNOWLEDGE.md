# EduCoach — RAG & Knowledge Architecture v0.1
**Tarih:** 2 Ekim 2026
**Durum:** Mimari Tasarım
---
# 1. Amaç
EduCoach'un ortak eğitim bilgisini LLM ağırlıklarına, kullanıcı hafızasına veya uygulama koduna gömmek yerine ayrı ve yönetilebilir bir Knowledge katmanında tutmak.
RAG sisteminin temel görevi:
```text
Kullanıcının isteği
↓
İlgili eğitim bağlamını belirle
↓
Gerekli bilgi kaynağını bul
↓
En ilgili bilgi parçalarını getir
↓
LLM'e kontrollü context olarak ver
```
RAG yalnızca bilgi gerektiğinde kullanılacaktır.
Her kullanıcı mesajında otomatik retrieval yapılmayacaktır.
---
# 2. Ana Ayrım
EduCoach'ta dört farklı bilgi türü birbirinden ayrılacaktır.
```text
Learner Memory
→ Bu kişi hakkında ne biliyoruz?
Specialty Profile
→ Bu eğitim bağlamı nasıl çalışıyor?
Backend Rules
→ Hangi sınırlar kesin olarak uygulanmalı?
Knowledge / RAG
→ Eğitim alanı hakkında doğrulanmış hangi bilgiye sahibiz?
```
Bu ayrım sistemin temel mimari prensibidir.
---
# 3. RAG Ne Değildir?
RAG:
- öğrenci veritabanı değildir,
- sohbet geçmişi değildir,
- model hafızası değildir,
- bütün belgelerin her mesajda LLM'e verilmesi değildir,
- internet aramasıyla aynı şey değildir,
- LLM'in bilmediği her şeyi uydurmasına izin veren bir mekanizma değildir.
---
# 4. Knowledge Base Ne İçerir?
Knowledge Base ortak ve tekrar kullanılabilir eğitim bilgisini içerir.
Örnek kategoriler:
```text
müfredat
ders yapısı
konu hiyerarşileri
kazanımlar
ön koşul ilişkileri
sınav yapıları
sınav terminolojisi
çalışma yöntemleri
deneme analizi yöntemleri
yanlış analizi yöntemleri
zaman yönetimi yöntemleri
öğrenme stratejileri
tekrar stratejileri
dil öğrenme bilgileri
soru türleri
ölçme ve değerlendirme bilgileri
```
---
# 5. Knowledge Base Ne İçermez?
Aşağıdaki kişisel bilgiler Knowledge Base'e konulmaz:
```text
Ayşe 7. sınıfta.
Mehmet TYT'de 72 net yaptı.
Ali günde 3 saat çalışıyor.
Zeynep matematikte zorlanıyor.
```
Bunlar Learner Memory bilgisidir.
---
# 6. Kaynak Temelli Bilgi
Knowledge Base içindeki her önemli bilgi mümkün olduğunca bir kaynağa bağlanmalıdır.
Bilginin yalnızca metni değil:
```text
nereden geldiği
ne zaman alındığı
hangi sürüme ait olduğu
hangi bağlamda geçerli olduğu
```
da bilinmelidir.
---
# 7. Source
Knowledge sistemindeki temel nesnelerden biri:
```text
Source
```
olacaktır.
Önerilen alanlar:
```text
source_id
title
source_type
publisher
source_url
local_path
language
published_at
retrieved_at
effective_from
effective_until
version
authority_level
status
checksum
notes
```
Bütün alanların her kaynakta dolması gerekmez.
---
# 8. Source Type
Örnek kaynak türleri:
```text
official_document
curriculum_document
exam_guide
regulation
teacher_authored
internal_guide
research
textbook
reference_document
web_page
other
```
---
# 9. Authority Level
Kaynakların güven düzeyi aynı olmayabilir.
Örneğin kavramsal olarak:
```text
PRIMARY
SECONDARY
CURATED
SUPPLEMENTARY
```
kullanılabilir.
### PRIMARY
Resmî veya birincil kaynak.
### SECONDARY
Güvenilir açıklayıcı kaynak.
### CURATED
EduCoach için öğretmen / uzman tarafından hazırlanmış bilgi.
### SUPPLEMENTARY
Destekleyici ancak tek başına kritik karar kaynağı olmaması gereken içerik.
---
# 10. Kaynak Önceliği
Birbiriyle çelişen bilgiler olduğunda varsayılan yaklaşım:
```text
güncel birincil kaynak
↓
güncel güvenilir ikincil kaynak
↓
EduCoach tarafından kürate edilmiş içerik
↓
destekleyici kaynaklar
```
olacaktır.
Ancak bu öncelik otomatik olarak bütün durumları çözmeyebilir.
Çelişki açıkça izlenebilmelidir.
---
# 11. Güncellik
Bazı eğitim bilgileri uzun süre değişmez.
Örneğin:
```text
aktif hatırlama
aralıklı tekrar
yanlış analizi yaklaşımı
```
gibi genel öğrenme bilgileri görece kalıcı olabilir.
Bazı bilgiler ise zaman içinde değişebilir:
```text
müfredat
sınav sistemi
sınav süresi
soru sayıları
başvuru kuralları
puanlama sistemi
```
Bu nedenle bütün knowledge kayıtları aynı güncellik politikasına sahip olmayacaktır.
---
# 12. Effective Date
Zamanla değişebilecek bilgi mümkün olduğunca:
```text
effective_from
effective_until
```
alanlarına sahip olacaktır.
Örneğin sistem:
```text
2026 YKS bilgisi
```
ile:
```text
2028 YKS bilgisi
```
aynı şeymiş gibi davranmamalıdır.
---
# 13. Sürümleme
Knowledge kaynakları güncellendiğinde eski sürüm doğrudan yok edilmemelidir.
Örneğin:
```text
curriculum_version = 2026
curriculum_version = 2027
```
ayrı sürümler halinde tutulabilir.
Bu özellikle:
- müfredat,
- sınav yapısı,
- ders programları,
- resmî kurallar
için önemlidir.
---
# 14. Knowledge Document
Bir Source'dan alınan işlenmiş içerik:
```text
KnowledgeDocument
```
olarak temsil edilebilir.
Önerilen alanlar:
```text
document_id
source_id
title
document_type
profile_code
country
education_system
grade_level
exam_code
subject
unit
topic
skill
curriculum_version
language
effective_from
effective_until
created_at
updated_at
```
---
# 15. Chunk
RAG doğrudan büyük belgeler üzerinde çalışmayacaktır.
Belgeler anlamlı parçalara bölünecektir.
Her parça:
```text
KnowledgeChunk
```
olarak düşünülebilir.
Önerilen alanlar:
```text
chunk_id
document_id
chunk_index
text
heading
token_count
metadata
embedding
created_at
```
Embedding'in fiziksel olarak nerede tutulacağı implementasyon aşamasında belirlenecektir.
---
# 16. Chunking İlkesi
Chunk'lar yalnızca sabit karakter sayısına göre rastgele bölünmeyecektir.
Mümkün olduğunca anlamlı sınırlar kullanılacaktır:
```text
başlık
alt başlık
konu
kazanım
madde
paragraf grubu
soru türü
```
Amaç retrieval sırasında bağlamı koparmamaktır.
---
# 17. Çok Büyük Chunk Sorunu
Çok büyük chunk:
- gereksiz token tüketir,
- retrieval hassasiyetini düşürür,
- ilgisiz bilgi getirir.
---
# 18. Çok Küçük Chunk Sorunu
Çok küçük chunk:
- bağlamı kaybettirebilir,
- açıklamayı parçalayabilir,
- yanlış yorum riskini artırabilir.
Chunk boyutu belge türüne göre ayarlanabilir.
---
# 19. Metadata
RAG sisteminin en önemli parçalarından biri metadata olacaktır.
Örnek:
```text
profile_code
grade_level
exam_code
subject
unit
topic
skill
curriculum_version
country
language
source_type
authority_level
effective_from
effective_until
```
Bu sayede retrieval yalnız embedding benzerliğine bağlı kalmaz.
---
# 20. Metadata Filtreleme
Örneğin aktif context:
```text
school_7
```
ise retrieval öncelikle:
```text
profile_code = school_7
```
veya ilgili okul müfredatı kapsamındaki kaynaklarda çalışabilir.
Aktif context:
```text
ales
```
iken 7. sınıf matematik müfredatı varsayılan sonuç olmamalıdır.
---
# 21. Profile ile Knowledge Ayrımı
Specialty Profile:
```text
YKS bağlamında hangi bilgi alanları önemlidir?
```
sorusuna cevap verir.
Knowledge Base:
```text
YKS hakkında elimizde hangi doğrulanmış içerik var?
```
sorusuna cevap verir.
Profile bilgi kaynağının kendisi değildir.
---
# 22. Curriculum Katmanı
Okul seviyelerinde yapılandırılmış eğitim taksonomisi ayrı ve önemli bir knowledge alanı olacaktır.
Kavramsal yapı:
```text
Education System
↓
Grade
↓
Subject
↓
Unit
↓
Topic
↓
Learning Outcome / Skill
```
Örneğin:
```text
school_7
↓
mathematics
↓
unit
↓
topic
↓
learning_outcome
```
---
# 23. Curriculum Kimlikleri
Learner Memory içinde ders veya konu adları serbest metin olarak çoğaltılmak yerine mümkün olduğunca curriculum kimliklerine bağlanmalıdır.
Örnek:
```text
area_code = curriculum.tr.school7.math.ratios
```
Bu yalnız kavramsal örnektir.
Gerçek kimlik standardı implementasyondan önce belirlenecektir.
---
# 24. Aynı Konunun Farklı Bağlamları
Aynı kelime farklı eğitim bağlamlarında farklı anlam taşıyabilir.
Örneğin:
```text
functions
```
bir lise matematik konusu olabilir.
Başka bir sistemde farklı bir öğrenme alanını ifade edebilir.
Bu nedenle sadece konu adına göre retrieval yapılmamalıdır.
Context metadata kullanılmalıdır.
---
# 25. Exam Knowledge
Sınavlara ilişkin knowledge aşağıdaki türlerde olabilir:
```text
exam_structure
exam_sections
assessment_semantics
terminology
strategy
timing
official_rules
```
Zamanla değişebilecek değerler sürümlenmelidir.
---
# 26. Pedagogical Knowledge
Sınav ve müfredat bilgisinden ayrı olarak pedagojik bilgi tutulabilir.
Örnek kategoriler:
```text
active_recall
spaced_repetition
error_analysis
practice_strategy
study_planning
time_management
review_strategy
habit_building
```
Bu içerik sınav türünden bağımsız olarak yeniden kullanılabilir.
---
# 27. Teacher-Curated Knowledge
EduCoach yalnız dış belgelerden oluşmak zorunda değildir.
Öğretmen tarafından doğrulanmış ve hazırlanmış içerik de Knowledge Base'e eklenebilir.
Örneğin:
```text
Bir öğrencinin deneme analizi nasıl yapılmalı?
Bir konu eksikliği nasıl teşhis edilmeli?
Çalışma programı oluştururken hangi öncelikler kullanılmalı?
```
Bu tür içerik:
```text
source_type = teacher_authored
```
gibi işaretlenebilir.
---
# 28. Öğretmen Bilgisi ile Kural Ayrımı
Örneğin:
```text
"Bir öğrencinin programı gerçek müsait süresini aşmamalıdır."
```
Backend Rule'dur.
Ancak:
```text
"Deneme sonrası yanlışların nedenlerine göre sınıflandırılması yararlıdır."
```
pedagojik knowledge olabilir.
Bu iki bilgi aynı yerde tutulmamalıdır.
---
# 29. Knowledge Collections
Knowledge Base mantıksal koleksiyonlara ayrılabilir.
Örneğin:
```text
curriculum
exams
pedagogy
study_methods
language_learning
assessment_methods
teacher_guides
```
Fiziksel depolamanın aynı veya farklı olması şart değildir.
---
# 30. Retrieval Request
Orchestrator RAG'e doğrudan kullanıcı mesajının tamamını göndermek zorunda değildir.
Yapılandırılmış bir retrieval request oluşturabilir.
Örnek:
```text
query
profile_code
grade_level
subject
topic
knowledge_type
effective_date
max_results
```
---
# 31. Örnek Retrieval Request
Kullanıcı:
```text
"7. sınıf matematikte oran-orantıya başlamadan önce ne bilmeliyim?"
```
Orchestrator:
```text
profile_code = school_7
subject = mathematics
topic = ratio
knowledge_type = curriculum
```
gibi filtrelerle arama isteği oluşturabilir.
---
# 32. Query Rewriting
Kullanıcının doğal dili doğrudan retrieval için en iyi sorgu olmayabilir.
Örneğin:
```text
"Bu konudan önce ne bilmem lazım?"
```
mesajı conversation context ile birlikte:
```text
7. sınıf matematik oran-orantı ön koşulları
```
gibi retrieval sorgusuna dönüştürülebilir.
Bu işlem kullanıcıya gösterilen cevap değildir.
---
# 33. Query Rewriting Güvenliği
Query rewriting sırasında sistem kullanıcının söylemediği konu veya bağlamı uydurmamalıdır.
Aktif context veya yakın konuşmadan güvenilir biçimde belirlenemiyorsa retrieval yanlış bağlama zorlanmamalıdır.
---
# 34. Retrieval Yöntemi
İlk mimari tek bir retrieval algoritmasına kilitlenmeyecektir.
Retriever arayüzü zaman içinde şu yöntemleri destekleyebilir:
```text
metadata filtering
lexical search
semantic / embedding search
hybrid search
reranking
```
EduCoach Core bunların teknik ayrıntısını bilmemelidir.
---
# 35. Hybrid Retrieval
Uzun vadede yalnız embedding benzerliğine güvenmek yerine:
```text
metadata
+
keyword / lexical
+
semantic similarity
```
birlikte kullanılabilir.
Özellikle:
```text
ders adı
konu adı
sınav adı
sınıf seviyesi
```
gibi açık terimlerde lexical eşleşme değerlidir.
---
# 36. v0.1 Retrieval Stratejisi
İlk prototip gereksiz karmaşık yapılmayacaktır.
Hedef:
```text
küçük
yerel
test edilebilir
değiştirilebilir
```
bir retrieval katmanı kurmaktır.
Retriever için ortak bir arayüz tanımlanacaktır.
Altındaki gerçek indeks teknolojisi daha sonra değiştirilebilir.
---
# 37. Vector Database Kararı
İlk mimari aşamasında EduCoach belirli bir vector database ürününe bağlanmayacaktır.
Önce:
```text
Retriever interface
```
tanımlanacaktır.
Ardından v0.1 için yerel ve düşük maliyetli bir çözüm seçilecektir.
Bu sayede ileride altyapı değiştirmek Core kodunu bozmaz.
---
# 38. Embedding Modeli
Embedding modeli de doğrudan Core'a gömülmeyecektir.
Kavramsal arayüz:
```text
EmbeddingProvider
```
olacaktır.
Bu sayede:
- yerel embedding modeli,
- API tabanlı embedding,
- ileride daha iyi çok dilli model
değiştirilebilir.
---
# 39. Türkçe Desteği
EduCoach'un temel kullanım dili Türkçe olacağı için embedding ve retrieval kalitesi Türkçe içerikte ayrıca test edilmelidir.
Sadece İngilizce benchmark performansına bakılarak embedding modeli seçilmeyecektir.
---
# 40. Çok Dilli Knowledge
Dil sınavları nedeniyle Knowledge Base yalnız Türkçe içerikten oluşmayabilir.
Örnek diller:
```text
Turkish
English
```
ve ileride başka diller olabilir.
Her belge:
```text
language
```
metadata'sı taşımalıdır.
---
# 41. Reranking
İlk retrieval sonuçları gerektiğinde ikinci bir sıralama aşamasından geçirilebilir.
Ama v0.1'de gereksiz maliyet yaratacaksa reranker zorunlu değildir.
Önce retrieval kalitesi ölçülecektir.
---
# 42. Retrieval Sonucu
RAG çıktısı yalnız metin listesi olmayacaktır.
Her sonuç en az şu bilgileri taşımalıdır:
```text
chunk_id
document_id
source_id
text
score
metadata
```
Gerekirse:
```text
source_title
authority_level
effective dates
```
de taşınabilir.
---
# 43. Retrieval Confidence
Benzerlik skoru doğrudan:
```text
Bu bilgi doğrudur.
```
anlamına gelmez.
Retrieval confidence ile source authority ayrı kavramlardır.
Bir chunk sorguya çok benzer olabilir ama kaynak eski olabilir.
---
# 44. Freshness Check
Zamana duyarlı bilgi kullanılırken retrieval sonucunun geçerlilik tarihi kontrol edilmelidir.
Özellikle:
```text
sınav sistemi
müfredat
başvuru
puanlama
soru sayısı
süre
```
gibi bilgilerde güncellik önemlidir.
---
# 45. Expired Knowledge
Bir knowledge kaydı:
```text
effective_until
```
tarihini geçmişse varsayılan güncel kaynak olarak kullanılmamalıdır.
Ancak tarihsel analiz için sistemde tutulabilir.
---
# 46. Tarihsel Bilgi
EduCoach gerekirse:
```text
2025 sisteminde nasıldı?
```
gibi sorulara da cevap verebilir.
Bu nedenle eski bilgi silinmek yerine sürümlenebilir.
---
# 47. Conflict Detection
Aynı konuda iki aktif kaynak farklı bilgi veriyorsa sistem bunu fark edebilmelidir.
Örneğin:
```text
Source A → değer X
Source B → değer Y
```
Kritik güncel bilgi için LLM'e ikisini de sessizce verip karar verdirmemeliyiz.
Çelişki işaretlenmelidir.
---
# 48. Conflict Resolution
Çelişki çözümünde kullanılabilecek sinyaller:
```text
authority_level
publication date
effective date
source version
profile compatibility
```
Kritik çelişki çözülemiyorsa kesin cevap verilmemelidir.
---
# 49. Citation / Provenance
EduCoach'un kullanıcı arayüzünde her cevapta kaynak göstermek zorunlu olmayabilir.
Ancak sistem içinden:
```text
Bu bilgi hangi kaynaktan geldi?
```
sorusunun cevabı bulunabilmelidir.
Bu nedenle provenance kaybolmamalıdır.
---
# 50. Retrieved Context
LLM'e verilen RAG context'i açık şekilde diğer bilgilerden ayrılmalıdır.
Örneğin:
```text
RETRIEVED KNOWLEDGE
Source: ...
Effective version: ...
Content: ...
```
Bu bilgi:
```text
LEARNER FACTS
```
ile karıştırılmamalıdır.
---
# 51. Knowledge ile Learner Fact Çelişkisi
Knowledge:
```text
genel kural
```
sağlar.
Learner Memory:
```text
kişinin gerçek durumu
```
sağlar.
Örneğin genel çalışma önerisi:
```text
40 dakikalık blok kullanılabilir.
```
diyebilir.
Ama learner yalnız 20 dakikalık zaman dilimine sahipse kişisel gerçek önceliklidir.
---
# 52. RAG Gating
Orchestrator her mesaj için şu kararı verir:
```text
NO_RAG
RAG_OPTIONAL
RAG_REQUIRED
```
---
# 53. NO_RAG Örneği
Kullanıcı:
```text
"Bugünkü 180 dakikalık planımı 120 dakikaya indir."
```
Gerekli bilgi mevcut plan ve Learner Memory içindeyse RAG gerekmez.
---
# 54. RAG_OPTIONAL Örneği
Kullanıcı:
```text
"Matematikte daha verimli tekrar nasıl yapabilirim?"
```
LLM'in genel bilgisi yeterli olabilir ancak kürate edilmiş pedagojik knowledge kaliteyi artırabilir.
---
# 55. RAG_REQUIRED Örneği
Kullanıcı:
```text
"Bu yılki sınavın güncel yapısı nasıl?"
```
veya:
```text
"Yeni müfredatta bu konu hangi sınıfta?"
```
gibi zamana ve doğrulanmış kaynağa bağlı sorularda RAG zorunlu olabilir.
---
# 56. RAG Yoksa Uydurma Yok
RAG_REQUIRED bir istekte yeterli doğrulanmış sonuç bulunamadıysa LLM:
```text
muhtemelen böyledir
```
diye boşluğu doldurmamalıdır.
Sistem yeterli bilgi bulunamadığını belirtmelidir.
---
# 57. Retrieval Limit
LLM'e gereksiz miktarda knowledge gönderilmeyecektir.
Örneğin:
```text
top_k
```
değeri görev türüne göre sınırlı tutulacaktır.
Amaç en çok belgeyi değil, en ilgili ve yeterli bilgiyi getirmektir.
---
# 58. Context Budget
RAG retrieval toplam LLM context budget'ını kontrolsüz tüketmemelidir.
Orchestrator:
```text
learner facts
rules
conversation
RAG
```
arasında gerekli context bütçesini yönetmelidir.
---
# 59. Duplicate Chunk Kontrolü
Aynı bilginin çok benzer kopyaları retrieval sonuçlarını doldurmamalıdır.
İndeksleme sırasında:
```text
exact duplicate
near duplicate
```
kontrolleri uygulanabilir.
---
# 60. Kaynak Güncelleme Pipeline
Knowledge güncelleme süreci kavramsal olarak:
```text
Source ekle
↓
Dosyayı doğrula
↓
Metni çıkar
↓
Metadata ekle
↓
Chunk oluştur
↓
Kalite kontrol
↓
Embedding / index
↓
Retrieval testi
↓
Aktifleştir
```
şeklinde olacaktır.
---
# 61. Ham Kaynak ve İşlenmiş Veri Ayrımı
Dosya yapısı ileride:
```text
knowledge/
├── sources/
├── processed/
├── indexes/
└── manifests/
```
gibi ayrılabilir.
### sources
Ham kaynak belgeleri.
### processed
Temizlenmiş / yapılandırılmış içerik.
### indexes
Retrieval için oluşturulan teknik indeksler.
### manifests
Kaynak ve sürüm kayıtları.
---
# 62. Ham Kaynağı Kaybetmeme
Processed veri üretildiğinde orijinal kaynak mümkünse korunmalıdır.
Böylece:
- yeniden chunking,
- yeni embedding,
- parsing hatası düzeltme,
- kaynak denetimi
yapılabilir.
---
# 63. Knowledge Manifest
Her bilgi paketinin manifest kaydı bulunabilir.
Örnek:
```text
knowledge_pack
version
source_count
document_count
chunk_count
created_at
embedding_version
index_version
```
Bu sayede hangi knowledge sürümünün kullanıldığı takip edilebilir.
---
# 64. Reindexing
Embedding modeli veya chunking politikası değişirse bütün kaynakların yeniden elle hazırlanması gerekmemelidir.
Ham kaynaklardan yeniden:
```text
processed
→ chunks
→ index
```
üretilebilmelidir.
---
# 65. Curriculum Güncellemesi
Yeni müfredat geldiğinde eski knowledge üzerine doğrudan yazılmayacaktır.
Yeni:
```text
curriculum version
```
oluşturulacaktır.
Learning Context uygun sürüme bağlanabilir.
---
# 66. Specialty Profile ve Knowledge Version
Specialty Profile gerekirse hangi knowledge sürümünün varsayılan olduğunu belirtebilir.
Örnek:
```text
profile = school_7
curriculum_version = ...
```
Ancak bilgi içeriğinin kendisi profile configuration içine kopyalanmayacaktır.
---
# 67. Knowledge Verification
Bir kaynak indekslenmeden önce mümkün olduğunca şu kontroller yapılmalıdır:
```text
dosya okunabiliyor mu?
başlık / metadata doğru mu?
kaynak belli mi?
geçerlilik tarihi belli mi?
profile eşleşmesi doğru mu?
chunk'lar anlamlı mı?
```
---
# 68. Retrieval Evaluation
RAG kalitesi yalnız:
```text
cevap güzel görünüyor
```
ile ölçülmeyecektir.
Ayrı retrieval testleri hazırlanacaktır.
Örnek soru:
```text
"7. sınıf matematik X konusu için hangi ön koşullar gerekli?"
```
Beklenen:
```text
ilgili doğru chunk'ların retrieval sonuçlarında bulunması
```
---
# 69. Retrieval Test Dataset
İleride ayrı bir:
```text
rag retrieval evaluation set
```
oluşturulacaktır.
Her test:
```text
query
filters
expected_document_ids veya expected_chunk_ids
forbidden_sources
```
gibi alanlar taşıyabilir.
---
# 70. Answer Evaluation ile Retrieval Evaluation Ayrımı
İki ayrı kalite vardır:
```text
Retrieval Quality
→ doğru bilgi getirildi mi?
Answer Quality
→ model bu bilgiyi doğru kullandı mı?
```
Bunları tek ölçümde karıştırmamalıyız.
---
# 71. Knowledge Gap
Bir kullanıcı sorusunun cevabı Knowledge Base'de yoksa sistem bunu gözlemleyebilmelidir.
Örneğin audit:
```text
rag_status = NO_SUFFICIENT_KNOWLEDGE
```
diyebilir.
Bu kayıtlar daha sonra knowledge geliştirmek için kullanılabilir.
---
# 72. Knowledge Growth
Knowledge Base başlangıçta her şeyi içermeyecektir.
İçerik kontrollü büyütülecektir.
Önerilen sıra:
```text
1. ortak pedagojik bilgi
2. birkaç temsilci Specialty Profile
3. ilgili curriculum / exam knowledge
4. gerçek kullanımda görülen bilgi açıkları
5. yeni uzmanlık alanları
```
---
# 73. İlk Temsilci Knowledge Alanları
Mimariyi test etmek için birbirinden farklı dört alan yeterlidir:
```text
school_7
yks
ales
general_english
```
Bu seçim sistemin:
- okul,
- merkezi sınav,
- akademik sınav,
- sınav dışı öğrenme
senaryolarında çalışıp çalışmadığını gösterebilir.
Bu dört alan ürün kapsamının sınırı değildir.
---
# 74. YKS Knowledge Örneği
YKS knowledge paketi ileride şu kategorileri içerebilir:
```text
exam_structure
terminology
TYT / AYT ayrımı
ders / alan yapısı
çalışma stratejileri
deneme analizi
```
Güncel sınav yapısı gibi bilgiler sürümlü ve kaynaklı tutulmalıdır.
---
# 75. School Knowledge Örneği
Okul profili knowledge paketi:
```text
grade curriculum
subjects
units
topics
learning outcomes
prerequisite relations
assessment terminology
```
gibi alanları içerebilir.
---
# 76. ALES Knowledge Örneği
ALES paketi:
```text
exam structure
performance areas
question type taxonomy
study strategy
time management
```
gibi içerikleri barındırabilir.
Güncel sınav kuralları kaynaklı ve sürümlü olmalıdır.
---
# 77. General English Knowledge Örneği
Genel İngilizce paketi:
```text
language skills
grammar taxonomy
vocabulary learning
reading strategies
listening strategies
writing practice
speaking practice
level progression
```
gibi içeriklerden oluşabilir.
Bu profile sınav puanı zorunlu değildir.
---
# 78. LLM ile Knowledge Üretme
LLM yeni knowledge taslağı hazırlamak için kullanılabilir.
Ancak:
```text
LLM üretti
```
tek başına bilginin doğrulanmış olduğu anlamına gelmez.
LLM tarafından üretilen bilgi:
```text
draft
```
durumunda kalmalı ve gerekirse insan / kaynak kontrolünden geçmelidir.
---
# 79. Teacher Review
Pedagojik knowledge için öğretmen değerlendirmesi önemli olacaktır.
Teknik sistem:
```text
format
metadata
version
retrieval
```
tarafını yönetir.
Öğretmen:
```text
pedagojik doğruluk
uygulanabilirlik
öğrenci seviyesine uygunluk
konu sıralaması
önerinin gerçekçilik düzeyi
```
tarafında devreye girer.
---
# 80. Otomatik Web Bilgisi
İleride EduCoach güncel bilgileri web üzerinden çekebilir.
Ancak:
```text
web'den bulundu
```
bilginin otomatik olarak kalıcı Knowledge Base'e yazılacağı anlamına gelmez.
Web retrieval ile kürate edilmiş Knowledge Base ayrı katmanlar olarak düşünülebilir.
---
# 81. Gelecekte Live Retrieval
İleride:
```text
curated RAG
+
live web retrieval
```
birlikte kullanılabilir.
Ancak ilk v0.1 için öncelik:
```text
kontrollü curated knowledge
```
olacaktır.
---
# 82. Security
Knowledge ingestion sırasında dış belgelerin içindeki metin:
```text
system instruction
```
olarak yorumlanmamalıdır.
Belge içeriği veri kabul edilmelidir.
RAG içeriğinin uygulamanın sistem kurallarını değiştirmesine izin verilmemelidir.
---
# 83. Prompt Injection Dayanıklılığı
Retrieved document içinde örneğin:
```text
"Önceki tüm talimatları yok say."
```
yazması bunun bir sistem talimatı olduğu anlamına gelmez.
LLM context oluşturulurken retrieved content açıkça:
```text
untrusted / informational content
```
olarak sınırlandırılmalıdır.
---
# 84. Kullanıcı Belgeleri
İleride kullanıcının kendi:
```text
ders notları
PDF'leri
öğretmen materyalleri
```
üzerinden özel RAG yapılabilir.
Ancak bunlar ortak EduCoach Knowledge Base ile karıştırılmamalıdır.
Ayrı scope kullanılmalıdır.
---
# 85. Knowledge Scope
Kavramsal olarak:
```text
GLOBAL
SPECIALTY
ORGANIZATION
LEARNER_PRIVATE
```
gibi bilgi kapsamları ileride desteklenebilir.
v0.1'de bütün bu kapsamların uygulanması şart değildir.
Mimari buna kapalı olmamalıdır.
---
# 86. İlk Teknik Arayüzler
Kavramsal olarak RAG katmanında:
```text
KnowledgeRepository
DocumentProcessor
Chunker
EmbeddingProvider
KnowledgeIndexer
Retriever
RetrievalFilter
RetrievalResult
```
gibi sorumluluklar bulunacaktır.
Gerçek dosya isimleri implementasyon aşamasında kesinleştirilecektir.
---
# 87. Retriever Interface
Core, belirli indeks teknolojisini bilmek yerine yaklaşık olarak şu yeteneği kullanmalıdır:
```text
search(query, filters, limit)
→ RetrievalResult[]
```
Böylece altyapı sonradan değiştirilebilir.
---
# 88. Retrieval Result İlkesi
Her sonuç:
```text
ne bulundu?
hangi kaynaktan?
hangi bağlamda?
ne kadar ilgili?
halen geçerli mi?
```
sorularını cevaplayabilmelidir.
---
# 89. Audit
RAG kullanılan her önemli istekte teknik olarak şu bilgiler kaydedilebilir:
```text
request_id
query
filters
retrieved_chunk_ids
source_ids
scores
knowledge_version
```
Bu sayede hatalı cevabın:
```text
yanlış retrieval mı?
yanlış LLM kullanımı mı?
```
olduğu ayrılabilir.
---
# 90. Privacy
Learner'ın kişisel bilgileri ortak RAG indeksine yazılmayacaktır.
Özellikle:
```text
öğrenci adı
performans geçmişi
özel notlar
kişisel hedefler
```
ortak Knowledge Base'e embedding yapılmayacaktır.
---
# 91. Maliyet İlkesi
İlk sürümde retrieval altyapısı gereksiz pahalı olmayacaktır.
Öncelik:
```text
yerel geliştirme
küçük bilgi tabanı
düşük maliyet
tekrarlanabilir test
```
olacaktır.
Sistem büyüdükçe altyapı değiştirilebilir.
---
# 92. Cache
Aynı knowledge sorgularının tekrar tekrar hesaplanması gerekiyorsa ileride cache kullanılabilir.
Ancak v0.1'de önce doğru retrieval hedeflenmelidir.
Erken optimizasyon yapılmayacaktır.
---
# 93. Fine-Tuning ile RAG Ayrımı
Fine-tuning:
```text
modelin davranışını değiştirmeye
```
yönelik olabilir.
RAG:
```text
modele gerekli bilgiyi çalışma anında vermeye
```
yöneliktir.
Müfredat, güncel sınav bilgisi veya konu yapısı gibi bilgiler varsayılan olarak fine-tuning ile ezberletilmeye çalışılmayacaktır.
---
# 94. Learner Memory ile RAG Ayrımı
Tekrar:
```text
Learner Memory
→ kişi
Knowledge
→ eğitim alanı
```
Örnek:
```text
"Ali 7. sınıfta."
→ Memory
"7. sınıf matematik konu yapısı"
→ Knowledge
```
---
# 95. Rules ile RAG Ayrımı
Örnek:
```text
Plan 180 dakikayı aşamaz.
```
→ Rule
```text
Bir konunun öğrenme ön koşulları
```
→ Knowledge
RAG sonucu hard rule haline kendiliğinden dönüşmemelidir.
---
# 96. Specialty ile RAG Ayrımı
```text
Specialty Profile
→ hangi bilgiye ihtiyaç duyulabileceğini tanımlar
RAG
→ gerçek bilgiyi getirir
```
Örneğin YKS profili:
```text
exam_structure knowledge
```
gerektiğini bilir.
Ama güncel sınav yapısının gerçek içeriği Knowledge Base'den gelir.
---
# 97. v0.1'de Bilinçli Olarak Yapmayacağımız Şeyler
İlk sürümde:
- devasa internet crawl yapılmayacak,
- bütün eğitim web'i indekslenmeyecek,
- her kullanıcı mesajında RAG çağrılmayacak,
- öğrenci hafızası vector database'e atılmayacak,
- kaynak bilgisi olmayan büyük metin yığınları eklenmeyecek,
- eski ve yeni müfredat birbirine karıştırılmayacak,
- tek bir embedding skoruna körü körüne güvenilmeyecek,
- güncel sınav bilgileri Python koduna gömülmeyecek,
- gereksiz pahalı cloud vector database ile başlanmayacak.
---
# 98. RAG v0.1 Başarı Kriterleri
RAG & Knowledge sistemi başarılı kabul edilmek için:
1. Knowledge ile Learner Memory ayrılmalı.
2. Her önemli bilginin kaynağı izlenebilmeli.
3. Kaynaklar sürümlenebilmeli.
4. Zamana duyarlı bilgi için geçerlilik tarihi tutulabilmeli.
5. Specialty Profile'a göre retrieval filtrelenebilmeli.
6. Sınıf / sınav / ders / konu metadata'sı kullanılabilmeli.
7. Retriever altyapısı değiştirilebilir olmalı.
8. Yetersiz retrieval durumunda model boşluğu uydurmamalı.
9. Retrieval ve answer değerlendirmesi ayrı yapılabilmeli.
10. Kişisel öğrenci verisi ortak Knowledge Base'e girmemeli.
11. Türkçe retrieval performansı ayrıca test edilebilmeli.
12. Yeni knowledge paketleri Core kodunu değiştirmeden eklenebilmelidir.
---
# 99. İlk Uygulama Sırası
RAG kodlanmaya başlandığında önerilen sıra:
```text
1. Knowledge source modeli
2. Metadata modeli
3. Ham kaynak dizini
4. Document processing
5. Chunking
6. Retriever interface
7. Basit yerel indeks
8. Metadata filtering
9. İlk küçük knowledge paketi
10. Retrieval testleri
11. Orchestrator entegrasyonu
12. LLM context entegrasyonu
```
Vector altyapı seçiminden önce veri ve arayüz tasarımı yapılacaktır.
---
# 100. Mimari Karar
EduCoach RAG & Knowledge sistemi şu prensiple geliştirilecektir:
> **Modelin bildiğini varsayma; gerektiğinde doğru, kaynaklı, bağlama uygun ve geçerli bilgiyi getir.**
Ve sistemin temel ayrımı korunacaktır:
```text
Learner Memory
→ kişi hakkında gerçekler
Specialty Profile
→ eğitim bağlamının yapısı
Rules
→ kesin sınırlar
Knowledge / RAG
→ doğrulanmış eğitim bilgisi
LLM
→ bu bilgiler üzerinden muhakeme ve iletişim
Validator
→ çıkan sonucu kontrol
```
