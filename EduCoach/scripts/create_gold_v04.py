from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SOURCE_FILE = ROOT / "data" / "gold" / "gold_v0.3.jsonl"
OUTPUT_FILE = ROOT / "data" / "gold" / "gold_v0.4.jsonl"

TARGET_TOTAL_EXAMPLES = 120

CATEGORY_PLAN = {
    "bilgiyi_dogru_kullanma": 20,
    "yks_terminolojisi": 15,
    "gercekci_planlama": 15,
    "sure_yonetimi": 10,
    "erteleme_ve_surdurulebilirlik": 10,
    "sabirsiz_ogrenci": 10,
    "deneme_ve_yanlis_analizi": 10,
    "hedef_gercekciligi": 10,
    "okul_dershane_dengesi": 10,
    "sinava_yakin_donem_ve_baski": 10,
}

CONVERSATION_PLAN = {
    "single_turn": 70,
    "multi_turn": 50,
}

ANSWER_LENGTH_PLAN = {
    "short": 30,
    "medium": 60,
    "detailed": 30,
}

NEW_EXAMPLES = [

    # -----------------------------------------------------
    # BİLGİYİ DOĞRU KULLANMA — 1/19
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "12. sınıf sayısal öğrencisiyim. TYT 76 civarı geliyor. Hafta içi okuldan dolayı en fazla 3 saat çalışabiliyorum. Nasıl bir düzen kurmalıyım?"
            },
            {
                "role": "assistant",
                "content": (
                    "Başlangıç için yeterli bilgimiz var. Hafta içi 3 saati çok fazla derse bölmeyelim. "
                    "İlk etapta yaklaşık 2 saati AYT sayısal çalışmasına, 1 saati TYT'yi korumaya ayırabiliriz. "
                    "AYT bölümünde o gün okulda işlediğin veya geride olduğun matematik-fen derslerinden birini ana çalışma yap. "
                    "TYT bölümünü ise problem, Türkçe veya kısa branş çalışması şeklinde dönüşümlü kullan. "
                    "Hafta sonundaki süreni henüz bilmediğim için hafta sonuna ayrıntılı saat yazmıyorum; onu söylediğinde haftalık planı tamamlarız."
                )
            },
            {
                "role": "user",
                "content": "Hafta sonu iki gün de 6 saat çalışabiliyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "O zaman hafta içindeki 3 saatlik düzeni koruyup hafta sonunu daha uzun çalışmalar için kullanalım. "
                    "Cumartesi 3 saat AYT matematik, 2 saat fen ve 1 saat yanlış-tekrar çalışması yapabilirsin. "
                    "Pazar günü bir TYT denemesi ve analizi yaptıktan sonra kalan süreyi hafta boyunca yetişmeyen AYT görevlerine ayır. "
                    "Böylece okul günlerini aşırı yüklemeden hafta sonuyla denge kurmuş oluruz."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # BİLGİYİ DOĞRU KULLANMA — 2/19
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Mezunum, eşit ağırlığım. TYT 71, AYT 43 yapıyorum. Matematiğim edebiyattan daha zayıf. Günde 5 saat çalışıyorum. Bana nereden başlamam gerektiğini söyle."
            },
            {
                "role": "assistant",
                "content": (
                    "Verdiğin bilgiler başlangıç için yeterli. Eşit ağırlık öğrencisi olduğun ve matematiğin daha zayıf olduğu için "
                    "5 saatin daha büyük bölümünü matematiğe ayıralım. Örneğin 2 saat AYT matematik, 1 saat TYT matematik veya problem, "
                    "1 saat edebiyat ve 1 saat TYT koruma/yanlış analiziyle başlayabilirsin. "
                    "Edebiyatı tamamen bırakmıyoruz; güçlü tarafını korurken asıl gelişim alanına daha fazla süre veriyoruz. "
                    "Bir hafta sonra matematikte çözdüğün soru başarısına ve deneme sonuçlarına göre dağılımı yeniden ayarlarız."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # BİLGİYİ DOĞRU KULLANMA — 3/19
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "11. sınıf sayısalım. TYT'ye yeni başladım. Okul derslerimi de aksatmak istemiyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "11. sınıfta olduğun için bütün zamanı TYT'ye çevirmek yerine okul konularını güçlü tutup TYT'yi düzenli ama sınırlı biçimde eklemek daha doğru olur. "
                    "Hafta içi gerçekçi olarak kaç saat ayırabildiğini söylersen okul ve TYT arasında başlangıç dengesi kurabilirim."
                )
            },
            {
                "role": "user",
                "content": "Hafta içi 2,5 saat, hafta sonu 5 saat ayırabiliyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Hafta içi 2,5 saatin yaklaşık 1,5 saatini 11. sınıf matematik-fen konularına, kalan 1 saatini TYT temel çalışmasına ayır. "
                    "Hafta sonu 5 saatte 3 saat okul/11. sınıf çalışması, 1,5 saat TYT ve 30 dakika haftalık tekrar kullanabilirsin. "
                    "Bu aşamada amaç 12. sınıf öğrencisi gibi yoğun TYT programı yapmak değil; 11. sınıf konularını sağlam tutarken TYT temelini düzenli biçimde ilerletmek."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # BİLGİYİ DOĞRU KULLANMA — 4/19
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Sayısal mezunum. Son üç TYT denemem 69, 73 ve 75 geldi. AYT ise 32 civarında. Günde 6 saat çalışabiliyorum. AYT'yi artırmak istiyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "TYT sonuçların son üç denemede 69'dan 75'e doğru ilerlerken AYT 32 civarında kalmış; bu nedenle çalışma ağırlığını AYT'ye kaydırmak mantıklı. "
                    "Günlük 6 saatin yaklaşık 4 saatini AYT matematik ve fen derslerine, 1-1,5 saatini TYT'yi korumaya, kalan süreyi yanlış analizine ayırarak başlayabilirsin. "
                    "TYT'yi tamamen bırakma; ancak şu aşamada ana gelişim alanın AYT gibi görünüyor. "
                    "AYT'deki ders dağılımını belirlemek için sonraki adımda matematik, fizik, kimya ve biyoloji netlerini ayrı ayrı incelemek yeterli."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # BİLGİYİ DOĞRU KULLANMA — 5/19
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Dershaneye gidiyorum ve eve 19.30'da geliyorum. 12. sınıf sayısalım. Eve geldikten sonra 4 saat daha çalışmaya çalışıyorum ama iki gün sonra tükeniyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Günün zaten okul ve dershaneyle dolu olduğu için eve geldikten sonra her gün 4 saat eklemek sürdürülebilir görünmüyor. "
                    "Önce akşam çalışma süresini azaltıp düzeni koruyalım. Eve geldikten sonra yemek ve dinlenme dışında gerçekten kaç saatlik kullanılabilir zamanın kalıyor?"
                )
            },
            {
                "role": "user",
                "content": "Yaklaşık 2,5 saat rahat ayırabilirim."
            },
            {
                "role": "assistant",
                "content": (
                    "O zaman planı 4 saate göre değil, gerçekçi olan 2,5 saate göre kuralım. "
                    "Akşam bir ana ders için 90 dakika, ikinci kısa çalışma için 45 dakika ve son 15-30 dakikayı tekrar veya yanlış analizine ayırabilirsin. "
                    "Dershanede o gün işlenen konuyu tekrar etmek gerekiyorsa ana bloğu ona ver; gerekmiyorsa en zayıf AYT dersine kullan. "
                    "Amaç birkaç gün 4 saat çalışmak değil, okul ve dershane temposunun yanında haftalarca sürdürülebilecek bir akşam düzeni kurmak."
                )
            }
        ]
    },
    # -----------------------------------------------------
    # BİLGİYİ DOĞRU KULLANMA — 6/19
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Mezunum, sayısalım. TYT 81, AYT 47 yapıyorum. Fizik en zayıf dersim. Günde 7 saat çalışabiliyorum. Bana çalışma dağılımı yap."
            },
            {
                "role": "assistant",
                "content": (
                    "Verdiğin bilgiler başlangıç için yeterli. Günde 7 saatin yaklaşık 3 saatini AYT matematik ve fizik ağırlıklı çalışmaya, "
                    "2 saatini diğer AYT fen derslerine, 1 saatini TYT korumaya ve 1 saatini yanlış analizi ile tekrara ayırabiliriz. "
                    "Fizik en zayıf dersin olduğu için AYT bölümünde ona düzenli ve daha sık yer verelim. "
                    "TYT 81 seviyesini tamamen bırakmadan koruyacağız; ana gelişim alanımız ise AYT olacak."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # BİLGİYİ DOĞRU KULLANMA — 7/19
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Eşit ağırlığım. TYT 68 civarı. AYT matematikte zorlanıyorum ama edebiyatım iyi."
            },
            {
                "role": "assistant",
                "content": (
                    "Bu durumda çalışma ağırlığını AYT matematiğe vermek mantıklı. "
                    "Programı saatlere çevirebilmem için günlük gerçekçi çalışma süreni bilmem yeterli."
                )
            },
            {
                "role": "user",
                "content": "Hafta içi 4 saat, hafta sonu 7 saat çalışabiliyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Hafta içi 4 saatin yaklaşık 2 saatini AYT matematiğe, 1 saatini TYT matematik veya probleme, "
                    "1 saatini edebiyat ve TYT korumaya ayırabiliriz. "
                    "Hafta sonu 7 saatte AYT matematik için daha uzun iki blok kullanıp kalan sürede TYT denemesi, analiz ve edebiyat tekrarı yap. "
                    "Edebiyatın iyi olduğu için onu bırakmıyoruz ama matematik kadar zaman vermiyoruz."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # BİLGİYİ DOĞRU KULLANMA — 8/19
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "12. sınıf dil öğrencisiyim. TYT 74 civarı, YDT 58 geliyor. Okuldan sonra 3 saat çalışabiliyorum. YDT'yi yükseltmek istiyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "YDT'yi yükseltmek önceliğin olduğu için 3 saatin yaklaşık 2 saatini YDT çalışmalarına, "
                    "1 saatini TYT'yi korumaya ayırarak başlayabiliriz. "
                    "YDT bölümünde yalnızca kelime çalışmak yerine okuma, soru çözümü ve yanlış analizi arasında denge kur. "
                    "TYT 74 seviyesini tamamen bırakmak yerine kısa ama düzenli çalışmalarla koru. "
                    "Bir hafta sonra YDT'de en çok hata yaptığın soru türlerine göre iki saatlik bloğun iç dağılımını değiştirebiliriz."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # BİLGİYİ DOĞRU KULLANMA — 9/19
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Sayısalım. TYT matematik 28 net geliyor ama fen 9 net civarı. Ne yapmalıyım?"
            },
            {
                "role": "assistant",
                "content": (
                    "TYT matematik 28 netken fen 9 net civarında olduğuna göre ilk bakışta daha büyük gelişim alanın fen. "
                    "Ama sana günlük dağılım vermek için ne kadar süre çalışabildiğini bilmem gerekiyor."
                )
            },
            {
                "role": "user",
                "content": "Günde 5 saat çalışabiliyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Günlük 5 saatin yaklaşık 2 saatini TYT fen, 1,5 saatini AYT sayısal dersler, "
                    "1 saatini TYT matematik koruma ve 30 dakikayı yanlış analizine ayırarak başlayabilirsin. "
                    "Matematiği güçlü olduğu için bırakmıyoruz; sadece fen kadar ağırlık vermiyoruz. "
                    "Fen içindeki fizik, kimya ve biyoloji dağılımını ise son denemendeki branş sonuçlarına göre belirlemek daha doğru olur."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # BİLGİYİ DOĞRU KULLANMA — 10/19
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Mezunum. Sabah daha iyi çalışıyorum. Akşam 20.00'den sonra verimim çok düşüyor. Günde toplam 6 saat çalışabilirim. Matematik önceliğim."
            },
            {
                "role": "assistant",
                "content": (
                    "En verimli olduğun zaman sabah olduğu için en ağır matematik çalışmasını sabah bloklarına koymalıyız. "
                    "Günlük 6 saatin ilk 2-2,5 saatini matematiğe ayır. "
                    "Öğleden sonra ikinci ana ders ve soru çözümü yap; akşam 20.00'den sonrasını zor konu öğrenmeye değil kısa tekrar, yanlış analizi veya ertesi gün planına bırak. "
                    "Böylece programı yalnızca toplam saate göre değil, gün içindeki gerçek verimine göre kurmuş oluruz."
                )
            }
        ]
    },
        # -----------------------------------------------------
    # BİLGİYİ DOĞRU KULLANMA — 11/19
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "12. sınıf sayısal öğrencisiyim. TYT 78 civarı geliyor. AYT matematikte iyiyim ama fizik çok zayıf."
            },
            {
                "role": "assistant",
                "content": (
                    "Bu durumda AYT matematiği koruyup fizik tarafına daha fazla ağırlık vermemiz mantıklı. "
                    "Günlük ne kadar çalışabildiğini söylersen dağılımı netleştirebilirim."
                )
            },
            {
                "role": "user",
                "content": "Hafta içi 3,5 saat, hafta sonu 6 saat çalışabiliyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Hafta içi 3,5 saatin yaklaşık 1,5 saatini fiziğe, 1 saatini AYT matematik korumaya, "
                    "1 saatini diğer sayısal derslere ayırabilirsin. "
                    "Hafta sonunda fiziğe daha uzun iki blok verip bir TYT denemesi ve analiz ekleyelim. "
                    "Matematikte iyi olduğunu bildiğimiz için onu tamamen bırakmıyoruz ama fizik kadar zaman vermiyoruz."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # BİLGİYİ DOĞRU KULLANMA — 12/19
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Eşit ağırlık mezunuyum. TYT 77, AYT 49 yapıyorum. Edebiyatım güçlü, geometri çok zayıf. Günde 6 saat çalışabiliyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Güçlü ve zayıf tarafların belli olduğu için başlangıç dağılımını doğrudan kurabiliriz. "
                    "Günlük 6 saatin yaklaşık 2 saatini geometri ve matematik çalışmalarına, 1,5 saatini AYT matematiğe, "
                    "1 saatini TYT korumaya, 1 saatini edebiyat tekrarına ve 30 dakikayı yanlış analizine ayırabilirsin. "
                    "Edebiyatın güçlü olduğu için onu tamamen bırakmıyoruz fakat geometri kadar yoğun çalışmıyoruz."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # BİLGİYİ DOĞRU KULLANMA — 13/19
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Okulda öğleden sonra çok yoruluyorum. Eve gelince direkt çalışmaya başlayınca verim alamıyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Bu durumda eve gelir gelmez ağır çalışma koymak yerine kısa bir geçiş süresi kullanmak daha mantıklı olabilir. "
                    "Eve kaçta geldiğini ve akşam toplam ne kadar çalışabildiğini söylersen düzeni buna göre kurabiliriz."
                )
            },
            {
                "role": "user",
                "content": "17.30'da evde oluyorum. Toplam 3 saat ayırabiliyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "17.30'da eve geldiğinde önce 30-45 dakikalık yemek ve dinlenme alanı bırak. "
                    "Sonra 90 dakikalık ana çalışma, kısa mola, 60 dakikalık ikinci ders ve son 30 dakikada tekrar veya yanlış analizi yapabilirsin. "
                    "Toplam çalışma süren yine 3 saat olacak; yalnızca başlangıcı dinlenme ihtiyacına göre daha gerçekçi hale getiriyoruz."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # BİLGİYİ DOĞRU KULLANMA — 14/19
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Sayısal mezunum. TYT Türkçe 33, matematik 24, sosyal 15, fen 10 geliyor. Günde 5 saatim var. En çok nereyi geliştirmeliyim?"
            },
            {
                "role": "assistant",
                "content": (
                    "Verdiğin dağılımda en büyük gelişim alanı fen görünüyor; matematik de ikinci sırada. "
                    "Türkçen görece güçlü olduğu için onu tamamen bırakmadan kısa koruma çalışmaları yeterli olabilir. "
                    "Günlük 5 saatin yaklaşık 2 saatini fen, 1,5 saatini matematik, 1 saatini AYT sayısal çalışmaya ve 30 dakikayı yanlış analizine ayırarak başlayabilirsin. "
                    "Fen içinde hangi branşa ağırlık vereceğimizi fizik, kimya ve biyoloji netlerine göre belirlemek daha doğru olur."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # BİLGİYİ DOĞRU KULLANMA — 15/19
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Ben gece daha iyi çalışıyorum. Sabah erken kalkınca verim alamıyorum ama herkes sabah çalışmam gerektiğini söylüyor."
            },
            {
                "role": "assistant",
                "content": (
                    "Herkes için aynı çalışma saati doğru değil. Eğer gece gerçekten daha verimliysen programı buna göre kurabiliriz. "
                    "Ama uyku düzenini bozmamak için kaçta uyuyup kaçta kalktığını ve toplam çalışma süreni bilmem gerekiyor."
                )
            },
            {
                "role": "user",
                "content": "Genelde 01.00'de yatıp 09.00'da kalkıyorum. Günde 6 saat çalışıyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Yaklaşık 8 saat uyuduğun ve geç saatlerde daha verimli olduğunu söylediğin için çalışma bloklarını öğleden sonra ve akşam ağırlıklı kurabiliriz. "
                    "En zor dersi akşam ilk verimli bloğuna koy, daha hafif tekrar ve analiz çalışmalarını günün sonuna bırak. "
                    "Sırf başkaları sabah çalışıyor diye düzenini değiştirmemiz gerekmiyor; önemli olan uyku süreni koruyup verimli olduğun saatleri bilinçli kullanmak."
                )
            }
        ]
    },
        # -----------------------------------------------------
    # BİLGİYİ DOĞRU KULLANMA — 16/19
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "12. sınıf sözel öğrencisiyim. TYT 66 civarı geliyor. Edebiyatım iyi ama tarih ve coğrafyada çok hata yapıyorum. Hafta içi 3 saat çalışabiliyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Edebiyatın güçlü olduğu için onu koruma düzeyinde tutup tarih ve coğrafyaya daha fazla süre ayırabiliriz. "
                    "Hafta içi 3 saatin yaklaşık 90 dakikasını tarih-coğrafya çalışmalarına, 60 dakikasını TYT korumaya ve kalan 30 dakikayı yanlış analizi veya kısa edebiyat tekrarına ayırabilirsin. "
                    "Tarih ve coğrafya içinde hangi konuya öncelik vereceğini son denemelerde tekrar eden yanlışlarına göre belirlemek daha doğru olur."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # BİLGİYİ DOĞRU KULLANMA — 17/19
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Mezunum, sayısalım. Günde 6 saat çalışıyorum. Son zamanlarda AYT matematiğe çok yükleniyorum ama TYT netim düşmeye başladı."
            },
            {
                "role": "assistant",
                "content": (
                    "AYT matematiğe yüklenirken TYT'nin düşmeye başlaması, TYT'yi tamamen arka plana attığını gösterebilir. "
                    "Son üç TYT denemendeki yaklaşık netlerini söylersen TYT koruma payını daha doğru ayarlayabiliriz."
                )
            },
            {
                "role": "user",
                "content": "78, 74 ve 71 geldi."
            },
            {
                "role": "assistant",
                "content": (
                    "78'den 71'e doğru üç denemelik düşüş olduğu için TYT'yi sadece ara sıra çalışmak yerine günlük programa yeniden sabit bir koruma bloğu ekleyelim. "
                    "6 saatin yaklaşık 3,5-4 saatini AYT'ye, 1,5 saatini TYT branş çalışması veya deneme analizine, kalan süreyi yanlış tekrarına ayırabilirsin. "
                    "AYT matematiği bırakmıyoruz; yalnızca TYT düşüşünü durduracak kadar düzenli temas ekliyoruz."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # BİLGİYİ DOĞRU KULLANMA — 18/19
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "12. sınıf sayısalım. Hafta içi yalnızca pazartesi, çarşamba ve cuma 3 saat çalışabiliyorum. Salı ve perşembe dershaneden çok geç çıkıyorum. Matematik ve kimya önceliğim."
            },
            {
                "role": "assistant",
                "content": (
                    "Hafta içi her günü aynı programa zorlamak yerine çalışabildiğin üç günü ana çalışma günleri yapalım. "
                    "Pazartesi ve cuma matematiğe daha uzun blok, çarşamba kimyaya ana blok ayırabilirsin. "
                    "Bu üç günde 3 saatin yaklaşık 2 saatini öncelikli derse, kalan 1 saatini TYT koruma veya diğer sayısal derse ver. "
                    "Salı ve perşembe geç çıktığın için ağır görev eklemek yerine yalnızca kısa tekrar yapabiliyorsan yap; yapamıyorsan bu günleri zorla doldurmayalım."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # BİLGİYİ DOĞRU KULLANMA — 19/19
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "TYT netim 84 ama AYT'ye yeni yeni ağırlık vermeye başladım. Sayısal öğrencisiyim."
            },
            {
                "role": "assistant",
                "content": (
                    "TYT 84 seviyesinde olduğun için TYT'yi tamamen bırakmadan koruma modunda tutup AYT'ye daha fazla ağırlık verebiliriz. "
                    "Günlük çalışma süreni söylersen bunu saatlere çevirebilirim."
                )
            },
            {
                "role": "user",
                "content": "Günde 5,5 saat çalışabiliyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "5,5 saatin yaklaşık 3,5 saatini AYT matematik ve fen çalışmalarına, 1-1,5 saatini TYT korumaya, kalan süreyi yanlış analizi ve kısa tekrara ayırarak başlayabilirsin. "
                    "TYT 84 olduğu için onu sıfırlamıyoruz ama artık zamanın çoğunu AYT'ye vermek daha mantıklı. "
                    "AYT içindeki ders dağılımını ise ilk denemelerden sonra hangi branşta en çok kayıp olduğuna göre değiştirebiliriz."
                )
            }
        ]
    },
    # -----------------------------------------------------
    # YKS TERMİNOLOJİSİ — 1/13
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "TYT'de 82 net yapıyorum. Bu 82 puan mı demek?"
            },
            {
                "role": "assistant",
                "content": (
                    "Hayır. TYT'deki 82 değeri net sayını ifade eder; puanla aynı şey değildir. "
                    "YKS puanı yalnızca net sayısından oluşmaz ve farklı hesaplama bileşenleri vardır. "
                    "Bu yüzden '82 net = 82 puan' şeklinde yorum yapmamalıyız. "
                    "Çalışma planı açısından ise 82 neti ders dağılımıyla birlikte değerlendirip hangi alanda gelişim gerektiğine bakabiliriz."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # YKS TERMİNOLOJİSİ — 2/13
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "AYT'de 45 netim var. 45 puanım var yani, doğru mu?"
            },
            {
                "role": "assistant",
                "content": (
                    "Doğru değil. AYT'deki 45 değeri net sayını ifade eder; doğrudan 45 puan anlamına gelmez. "
                    "Net, puan ve başarı sırası farklı kavramlardır. "
                    "AYT performansını değerlendirirken önce hangi testlerden bu netlerin geldiğine bakmak daha anlamlıdır."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # YKS TERMİNOLOJİSİ — 3/13
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "TYT 76, AYT 39 yapıyorum. Sıralamam kaç gelir?"
            },
            {
                "role": "assistant",
                "content": (
                    "Sadece iki net bilgisinden kesin bir başarı sırası söylemek doğru olmaz. "
                    "Alanını bilmemiz gerekir ve başarı sırası yılın sınav zorluğu ile aday dağılımına göre değişebilir. "
                    "Alanını söylersen çalışma önceliğini netlerine göre değerlendirebilirim."
                )
            },
            {
                "role": "user",
                "content": "Sayısalım."
            },
            {
                "role": "assistant",
                "content": (
                    "Sayısal olduğunu bildiğimiz için TYT ve AYT sayısal performansını birlikte değerlendirebiliriz; "
                    "ancak yine de 76 TYT ve 39 AYT netinden kesin sıralama üretmem doğru olmaz. "
                    "Bunun yerine son denemelerde AYT matematik ve fen dağılımına bakıp hangi dersin sıralama hedefin açısından daha büyük gelişim alanı olduğunu belirleyelim."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # YKS TERMİNOLOJİSİ — 4/13
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Bilgisayar mühendisliği istiyorum. Hangi puan türünden hazırlanıyorum?"
            },
            {
                "role": "assistant",
                "content": (
                    "Bilgisayar mühendisliği hedefin olduğuna göre sayısal puan türü üzerinden ilerlemek gerekir. "
                    "Çalışma planında TYT'yi korurken özellikle AYT matematik ve fen derslerini merkeze almalısın. "
                    "Farklı bir hedef veya özel bir durumun varsa onu ayrıca belirtmen yeterli."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # YKS TERMİNOLOJİSİ — 5/13
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Hukuk istiyorum. Sayısal çalışmam gerekir mi?"
            },
            {
                "role": "assistant",
                "content": (
                    "Hukuk hedefi için eşit ağırlık puan türü üzerinden hazırlanırsın. "
                    "Bu nedenle TYT yanında AYT matematik ve Türk dili-edebiyatı/sosyal bilimler tarafı önemlidir. "
                    "Sayısal puan türü için hazırlanan AYT fen ağırlıklı bir program kurmana gerek yok."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # YKS TERMİNOLOJİSİ — 6/13
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "TYT netim 90 oldu. Bu durumda artık AYT önemli değil mi?"
            },
            {
                "role": "assistant",
                "content": (
                    "Hayır. TYT'de 90 net güçlü bir temel olabilir ama özellikle dört yıllık bölümlerde hedef puan türüne göre AYT performansı da önemlidir. "
                    "Alanını ve hedefini söylersen TYT'yi ne kadar koruyup AYT'ye ne kadar ağırlık vermenin mantıklı olduğunu konuşabiliriz."
                )
            },
            {
                "role": "user",
                "content": "Tıp istiyorum, sayısalım."
            },
            {
                "role": "assistant",
                "content": (
                    "Tıp hedefinde sayısal puan türü esas olduğu için AYT matematik ve fen performansı kritik olmaya devam eder. "
                    "TYT 90 seviyesini korurken çalışma süresinin daha büyük bölümünü AYT'ye ayırmak mantıklı olur. "
                    "TYT'yi tamamen bırakmak yerine düzenli deneme ve kısa branş çalışmalarıyla koruyabiliriz."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # YKS TERMİNOLOJİSİ — 7/13
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "TYT 70, AYT 50. Toplam 120 net yaptım, YKS netim 120 diyebilir miyim?"
            },
            {
                "role": "assistant",
                "content": (
                    "TYT ve AYT netlerini aritmetik olarak toplamak mümkün olsa da bunu tek başına 'YKS netim 120' diye kullanmak yanıltıcı olabilir. "
                    "TYT ve AYT farklı oturumlardır ve hedef puan türüne göre etkileri farklı değerlendirilir. "
                    "Bu yüzden çalışma takibinde TYT 70 ve AYT 50 şeklinde ayrı ayrı izlemek daha doğru olur."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # YKS TERMİNOLOJİSİ — 8/13
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "TYT'de 10 net artırırsam sıralamam kesin şu kadar yükselir mi?"
            },
            {
                "role": "assistant",
                "content": (
                    "Hayır, net artışını doğrudan sabit bir sıralama artışına çevirmek doğru olmaz. "
                    "Başarı sırası sınavın zorluğu, diğer adayların performansı ve puan türündeki dağılıma göre değişir. "
                    "10 netlik artışı hedeflemek anlamlı olabilir ama bunun kesin olarak belirli bir sıralama kazandıracağını garanti edemeyiz."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # YKS TERMİNOLOJİSİ — 9/13
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "AYT 35 net yapıyorum. Bu kötü mü?"
            },
            {
                "role": "assistant",
                "content": (
                    "35 AYT netini tek başına iyi veya kötü diye etiketlemek yerine hedefin, alanın ve ders dağılımınla birlikte değerlendirmek gerekir. "
                    "Hangi alandasın?"
                )
            },
            {
                "role": "user",
                "content": "Eşit ağırlığım ve psikoloji istiyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Eşit ağırlıkta olduğun için AYT matematik ile edebiyat-sosyal tarafının dağılımına bakmak gerekir. "
                    "35 netin hangi testlerden geldiğini görmeden yalnız toplam üzerinden karar vermek doğru olmaz. "
                    "Matematik ve edebiyat-sosyal netlerini ayrı yazarsan çalışma önceliğini daha doğru belirleyebiliriz."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # YKS TERMİNOLOJİSİ — 10/13
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "TYT puanım düştü diye netim de düşmüş müdür?"
            },
            {
                "role": "assistant",
                "content": (
                    "Bunu otomatik olarak söyleyemeyiz. Net ile puan aynı şey değildir. "
                    "Netlerini ayrı, puanını ayrı takip etmek gerekir. "
                    "Deneme analizinde çalışma açısından en sağlıklı veri ders bazlı doğru, yanlış, boş ve net dağılımıdır."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # YKS TERMİNOLOJİSİ — 11/13
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "AYT matematik 25, fizik 7, kimya 8, biyoloji 9 net. AYT puanım 49 mu oluyor?"
            },
            {
                "role": "assistant",
                "content": (
                    "Hayır. Bu değerleri topladığında 49 AYT neti elde edersin; bu 49 puan anlamına gelmez. "
                    "Çalışma açısından ise dağılım bize daha yararlı bilgi veriyor: matematik 25 net, fen toplamı 24 net. "
                    "Hangi fen branşında daha fazla gelişim alanı olduğunu ayrı ayrı takip etmek gerekir."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # YKS TERMİNOLOJİSİ — 12/13
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "İlk 20 bine girmek istiyorum. Kaç net yapmam lazım?"
            },
            {
                "role": "assistant",
                "content": (
                    "Tek bir sabit net sayısı vermek doğru olmaz; gerekli netler sınav yılına, puan türüne ve sınavın zorluğuna göre değişebilir. "
                    "Alanını ve mevcut TYT/AYT seviyeni söylersen hedefe göre çalışma açığını değerlendirebiliriz."
                )
            },
            {
                "role": "user",
                "content": "Sayısalım. TYT 79, AYT 42 civarı."
            },
            {
                "role": "assistant",
                "content": (
                    "Bu bilgilerle mevcut çalışma seviyeni değerlendirebiliriz ama 'ilk 20 bin için kesin şu net gerekir' demem doğru olmaz. "
                    "TYT 79'u korurken AYT 42'nin ders dağılımına bakıp en fazla kayıp yaşadığın matematik veya fen alanlarını yükseltmeye odaklanalım. "
                    "İlerlemeni sabit bir net garantisiyle değil, düzenli deneme trendiyle takip edelim."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # YKS TERMİNOLOJİSİ — 13/13
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "TYT netim arttı ama başarı sıram neden aynı kalmış olabilir?"
            },
            {
                "role": "assistant",
                "content": (
                    "Net artışı ile başarı sırası birebir ve sabit şekilde hareket etmez. "
                    "Başarı sırası diğer adayların performansından ve sınavın genel dağılımından da etkilenir. "
                    "Bu nedenle kendi gelişimini takip ederken önce ders bazlı net trendine, yanlış türlerine ve AYT/TYT dengesine bakmak daha sağlıklıdır."
                )
            }
        ]
    },
        # -----------------------------------------------------
    # GERÇEKÇİ PLANLAMA — 1/11
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Günde 3 saat çalışabiliyorum ama matematik, fizik, kimya, biyoloji, Türkçe ve sosyalin hepsini her gün çalışmak istiyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "3 saatte altı dersi her gün anlamlı biçimde çalışmaya zorlamak yerine günlere dağıtmak daha gerçekçi olur. "
                    "Bir günde en fazla 2 ana ders ve kısa bir tekrar kullanabiliriz. "
                    "Örneğin bugün 90 dakika matematik, 60 dakika fizik ve 30 dakika Türkçe; ertesi gün kimya, biyoloji ve kısa matematik tekrarı yapabilirsin. "
                    "Amaç her derse her gün dokunmak değil, haftanın sonunda önemli derslerin tamamına düzenli ve yeterli süre ayırmak."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # GERÇEKÇİ PLANLAMA — 2/11
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Mezunum ve günde 8 saat çalışmak istiyorum ama şu an en fazla 4 saat sürdürebiliyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Doğrudan 8 saate çıkmak yerine önce 4 saatlik düzeni istikrarlı hale getirmek daha doğru olur. "
                    "Son bir haftada 4 saati kaç gün sürdürebildin?"
                )
            },
            {
                "role": "user",
                "content": "Yaklaşık 5 gün."
            },
            {
                "role": "assistant",
                "content": (
                    "Bu durumda önce 4 saati 6-7 gün sürdürebilmeyi hedefleyelim. "
                    "Sonra çalışma süresini bir anda 8'e değil, 4,5-5 saate çıkar. "
                    "Yeni süreyi birkaç gün taşıyabiliyorsan 30-45 dakikalık artışlarla ilerle. "
                    "Hedefimiz en yüksek saat değil, haftalar boyunca korunabilen verimli çalışma süresi."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # GERÇEKÇİ PLANLAMA — 3/11
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Okuldan sonra 2 saatim var. Bana hem TYT hem AYT hem de okul tekrarını aynı gün bitirecek program yap."
            },
            {
                "role": "assistant",
                "content": (
                    "2 saat içinde üç alanı da her gün ayrıntılı çalışmak programı fazla parçalar. "
                    "Daha gerçekçi olan, bir ana alan ve bir kısa koruma çalışması seçmek. "
                    "Örneğin 80 dakika okul/AYT ana çalışma, 40 dakika TYT problem veya Türkçe yapabilirsin. "
                    "Ertesi gün ana alanı değiştirebiliriz. Böylece iki saati küçük parçalara bölmeden ilerlersin."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # GERÇEKÇİ PLANLAMA — 4/11
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Bu ay bütün AYT konularını bitirmek istiyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Bunun gerçekçi olup olmadığını söylemek için ne kadar eksiğin olduğunu ve günlük çalışma süreni bilmem gerekiyor."
                )
            },
            {
                "role": "user",
                "content": "Sayısalım. Matematiğin yarısı, fiziğin yarısı, kimyanın üçte biri ve biyolojinin birazı eksik. Günde 4 saat çalışabiliyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Bu kadar eksiği 4 saatlik günlük süreyle tek ayda eksiksiz bitirmeyi hedeflemek programı gereğinden ağırlaştırabilir. "
                    "Önceliği AYT matematik ve fizikte en temel ve sık kullandığın konulara verelim, kimya ve biyolojiyi ise daha küçük bloklarla ilerletelim. "
                    "Bir ayın hedefini 'her şeyi bitirmek' yerine belirli konu gruplarını tamamlamak ve bunlardan soru çözebilir hale gelmek olarak kuralım."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # GERÇEKÇİ PLANLAMA — 5/11
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Her gün 500 soru çözmek istiyorum. Günde 5 saatim var."
            },
            {
                "role": "assistant",
                "content": (
                    "500 soru sayısını tek başına hedef yapmak yerine 5 saati kaliteli çalışmaya göre planlamak daha doğru olur. "
                    "Soruların zorluk ve analiz süresi değişir; 500 soruyu yetiştirmek için yanlışları incelemeyi bırakmak verimi düşürebilir. "
                    "Günün bir bölümünü konu veya eksik tamamlamaya, bir bölümünü soru çözümüne ve mutlaka yanlış analizine ayır. "
                    "Günlük soru sayısını çalışma kalitesinin önüne koymayalım."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # GERÇEKÇİ PLANLAMA — 6/11
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Hafta içi 2 saat, hafta sonu 7 saat çalışabiliyorum. Her gün aynı programı uygulamak istiyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Hafta içi ve hafta sonu kullanılabilir süren çok farklı olduğu için aynı programı her güne kopyalamak verimli olmaz. "
                    "Hangi alandasın ve en zayıf iki dersin hangileri?"
                )
            },
            {
                "role": "user",
                "content": "Sayısalım, matematik ve fizik zayıf."
            },
            {
                "role": "assistant",
                "content": (
                    "Hafta içi 2 saati bir ana ders ve kısa koruma çalışması için kullan; örneğin bir gün matematik, ertesi gün fizik. "
                    "Hafta sonu 7 saatlik sürede ise daha uzun matematik-fizik blokları, deneme ve yanlış analizi ekleyebilirsin. "
                    "Programı aynı tutmak yerine haftanın günlerine göre yükü değiştirmek daha sürdürülebilir olur."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # GERÇEKÇİ PLANLAMA — 7/11
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Günde 6 saatim var ama 2 saatini yolda geçiriyorum. Bu 2 saatte de ağır matematik çalışsam olur mu?"
            },
            {
                "role": "assistant",
                "content": (
                    "Yol süresini çalışma süresine çevirmek mümkün olabilir ama ağır matematik için ortam uygun değilse bunu zorlamayalım. "
                    "Yolda kelime, kısa tekrar, yanlış notları veya dinleme gerektiren içerikler kullanabilirsin. "
                    "Odak isteyen matematik ve fizik çalışmalarını masa başındaki gerçek çalışma saatlerine bırakmak daha verimli olur."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # GERÇEKÇİ PLANLAMA — 8/11
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Bir günde üç deneme çözsem daha hızlı gelişir miyim?"
            },
            {
                "role": "assistant",
                "content": (
                    "Deneme sayısını artırmak tek başına daha hızlı gelişim sağlamaz. "
                    "Birden fazla denemeyi analiz etmeden çözmek aynı hataları tekrar etmene yol açabilir. "
                    "Çoğu durumda bir deneme çözüp yanlışlarını, boşlarını ve süre sorunlarını incelemek; ardından hedefli çalışma yapmak daha değerlidir. "
                    "Deneme sıklığını mevcut seviyene ve analiz sürene göre ayarlayalım."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # GERÇEKÇİ PLANLAMA — 9/11
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Haftalık programımda her güne 8 görev yazıyorum ama yarısı kalıyor."
            },
            {
                "role": "assistant",
                "content": (
                    "Görevlerin sürekli yarısı kalıyorsa program kapasitenin üzerinde olabilir. "
                    "Bir günde gerçekçi olarak kaç saat çalışıyorsun?"
                )
            },
            {
                "role": "user",
                "content": "Yaklaşık 4 saat."
            },
            {
                "role": "assistant",
                "content": (
                    "4 saat için 8 ayrı görev yerine 3 ana görev ve en fazla 1 küçük ek görev belirleyelim. "
                    "Her görevin yaklaşık süresini yaz ve toplam aktif çalışma süresini 4 saatin üzerine çıkarma. "
                    "Bir hafta boyunca bu sade düzeni dene; sürekli erken bitiriyorsan ancak o zaman görev sayısını artır."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # GERÇEKÇİ PLANLAMA — 10/11
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Pazar günü 10 saat çalışıp hafta içindeki bütün eksikleri kapatmayı düşünüyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Bir günde bütün haftanın eksiklerini yığmak yerine en önemli 2-3 görevi seçmek daha gerçekçi olur. "
                    "Pazar gününü telafi deposu haline getirirsen gün çok ağırlaşabilir ve yeni haftaya yorgun başlayabilirsin. "
                    "Öncelikli eksikleri tamamla, bir deneme veya analiz yap ve kalan görevleri yeni haftaya yeniden planla."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # GERÇEKÇİ PLANLAMA — 11/11
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Program yaparken molaları yazmıyorum çünkü zaman kaybı gibi geliyor."
            },
            {
                "role": "assistant",
                "content": (
                    "Molayı tamamen kaldırmak uzun çalışma bloklarında verimi düşürebilir. "
                    "Günde yaklaşık kaç saat çalışıyorsun?"
                )
            },
            {
                "role": "user",
                "content": "6 saat."
            },
            {
                "role": "assistant",
                "content": (
                    "6 saatlik çalışmayı kesintisiz planlamak yerine 60-90 dakikalık bloklar arasında kısa molalar kullan. "
                    "Molaları aktif çalışma süresinden ayrı düşün; örneğin 6 saat aktif çalışma hedefin varsa günün toplam takvim süresi biraz daha uzun olabilir. "
                    "Ama molaları plansız uzatmak yerine başlangıç ve bitişlerini belirli tut."
                )
            }
        ]
    },
        # -----------------------------------------------------
    # SÜRE YÖNETİMİ — 1/7
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "TYT Türkçede 50 dakika harcıyorum, matematikte de çok oyalanıyorum. Son bölümlere yetişemiyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Önce toplam süreden çok hangi bölümde ne kadar süre kaybettiğini ölçelim. "
                    "Türkçede süreli branş denemeleriyle 50 dakikanın hangi soru türlerinde uzadığını takip et. "
                    "Matematikte ilk turda uzun süre ilerleyemediğin soruları işaretleyip geç. "
                    "Tam TYT denemelerinde her derse başladığın ve bitirdiğin zamanı kaydet. "
                    "Hedefimiz bir anda çok hızlanmak değil, fene ve son bölümlere düzenli süre bırakacak bir sınav akışı kurmak."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # SÜRE YÖNETİMİ — 2/7
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Ders çalışırken bir soruya takılınca 15-20 dakika uğraşıyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Uzun süre tek soruda kalmak toplam çalışma verimini düşürebilir. "
                    "Bu daha çok hangi derste oluyor?"
                )
            },
            {
                "role": "user",
                "content": "En çok matematikte."
            },
            {
                "role": "assistant",
                "content": (
                    "Matematikte ilk denemede kendine yaklaşık 3-5 dakikalık bir sınır koy. "
                    "İlerleme yoksa soruyu işaretleyip devam et; çalışma bloğunun sonunda tekrar dön. "
                    "İkinci denemede de çözemiyorsan çözümü inceleyip neden takıldığını not et. "
                    "Amaç zor sorudan kaçmak değil, tek sorunun bütün çalışma bloğunu tüketmesini engellemek."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # SÜRE YÖNETİMİ — 3/7
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Akşam 3 saat çalışacağım diyorum ama masaya geçince ne yapacağıma karar vermekle yarım saat gidiyor."
            },
            {
                "role": "assistant",
                "content": (
                    "Sorun çalışma süresinin az olması değil, başlangıçta karar verme süresinin kaybolması. "
                    "Bir sonraki günün ilk görevini bir gece önce belirle. "
                    "Masaya oturduğunda ilk 60-90 dakikalık bloğun dersi, konusu ve materyali hazır olsun. "
                    "Kalan blokları da en fazla 2-3 görevle sınırla. "
                    "Böylece 3 saatin içinden her gün yeniden plan yapmak için yarım saat kaybetmezsin."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # SÜRE YÖNETİMİ — 4/7
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Programda her konuya 1 saat yazıyorum ama bazı konular 2 saat sürüyor ve bütün gün kayıyor."
            },
            {
                "role": "assistant",
                "content": (
                    "Her konunun aynı sürede biteceğini varsaymak programı kırılgan hale getirir. "
                    "Günde toplam kaç saat çalışıyorsun?"
                )
            },
            {
                "role": "user",
                "content": "5 saat."
            },
            {
                "role": "assistant",
                "content": (
                    "5 saatin tamamını sabit 1 saatlik konu kutularına bölmek yerine 3 ana blok kullan. "
                    "Örneğin 90 dakika, 90 dakika ve 90 dakika ana çalışma; kalan süreyi tekrar, soru ve geciken görevler için tampon bırak. "
                    "Bir konu uzarsa tüm günün bozulması yerine tampon süreden kullanırsın. "
                    "Bitmeyen konuyu da zorla aynı gün tamamlamak yerine sonraki plana taşıyabilirsin."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # SÜRE YÖNETİMİ — 5/7
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Denemede ilk 60 dakikada çok rahat davranıyorum, son yarım saatte panik olup yetiştiremiyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Burada sorun yalnızca son yarım saat değil; ilk bölümde zaman kontrolünün olmaması. "
                    "Denemeden önce dersler için yaklaşık kontrol noktaları belirle. "
                    "Örneğin belirli bir dakikada hangi bölüme geçmiş olman gerektiğini takip et. "
                    "Her 30-40 dakikada saate kısa bir bakış at ama sürekli saat kontrolü yapma. "
                    "Birkaç deneme boyunca gerçek bölüm sürelerini kaydedip kontrol noktalarını kendi hızına göre ayarla."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # SÜRE YÖNETİMİ — 6/7
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Hafta içi sadece 90 dakikam kalıyor. Bu sürede hiçbir şey yetişmiyor gibi hissediyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "90 dakika az görünebilir ama doğru kullanılırsa tek bir önemli hedef için yeterli olabilir. "
                    "Şu an en çok geliştirmek istediğin ders hangisi?"
                )
            },
            {
                "role": "user",
                "content": "AYT fizik."
            },
            {
                "role": "assistant",
                "content": (
                    "O zaman 90 dakikayı üç derse bölmek yerine fiziğe odaklan. "
                    "İlk 35-40 dakika konu veya eksik tamamlama, sonraki 40 dakika soru çözümü, son 10-15 dakika yanlış kontrolü yap. "
                    "Başka dersleri bu kısa akşama sıkıştırmak yerine hafta sonu veya diğer günlere dağıt. "
                    "Kısıtlı zamanda ana hedefi netleştirmek daha verimli olur."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # SÜRE YÖNETİMİ — 7/7
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Bir günlük programımda 4 saat aktif çalışma yazıyor. Aralarla birlikte toplam kaç saat ayırmalıyım?"
            },
            {
                "role": "assistant",
                "content": (
                    "4 saat aktif çalışma ile takvimde ayırman gereken toplam süre aynı olmayabilir. "
                    "Örneğin 60-90 dakikalık bloklar arasında toplam 30-45 dakika mola kullanıyorsan gün içinde yaklaşık 4,5-5 saatlik bir alan ayırman gerekir. "
                    "Burada önemli olan aktif çalışma süresi ile mola dahil toplam zamanı birbirine karıştırmamak. "
                    "Program yazarken ikisini ayrı takip et."
                )
            }
        ]
    },
        # -----------------------------------------------------
    # ERTELEME VE SÜRDÜRÜLEBİLİRLİK — 1/3
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Program yapıyorum ama bir gün aksayınca geri dönemiyorum. Ertesi gün de hiçbir şey yapmıyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Burada asıl sorun bir günün aksaması değil, aksayan günü bütün haftanın bozulması gibi yorumlaman. "
                    "Programı buna karşı dayanıklı hale getirebiliriz. Bir gün kaçırdığında görevleri ertesi güne yığma; "
                    "ertesi gün doğrudan normal plana dön. Önce günlük görev sayısını da azaltalım. "
                    "Şu an bir günde ortalama kaç ana görev yazıyorsun?"
                )
            },
            {
                "role": "user",
                "content": "Genelde 6-7 görev yazıyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "6-7 ana görev yerine 3 zorunlu görev belirle, diğerlerini ek görev olarak tut. "
                    "Bir gün aksadığında yalnızca ertesi günün 3 ana görevini uygula; eski görevleri üstüne ekleme. "
                    "İlk hedefin kusursuz hafta değil, aksadıktan sonra en geç ertesi gün geri dönebilmek olsun."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # ERTELEME VE SÜRDÜRÜLEBİLİRLİK — 2/3
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Derse başlayacağım zaman sürekli önce masayı düzenliyorum, kaynak seçiyorum, video arıyorum. Bir bakıyorum bir saat geçmiş."
            },
            {
                "role": "assistant",
                "content": (
                    "Burada erteleme çalışmamak şeklinde değil, hazırlık davranışlarının uzaması şeklinde ortaya çıkıyor. "
                    "Bir sonraki çalışma için kaynak, konu ve ilk görevi bir önceki akşam belirle. "
                    "Masaya geçtiğinde yeni kaynak arama veya plan değiştirme yapma; doğrudan önceden seçtiğin görevle başla. "
                    "İlk 30 dakikayı sadece işe başlama süresi olarak koru. Planlama ve kaynak seçimini çalışma saatinin dışına taşı."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # ERTELEME VE SÜRDÜRÜLEBİLİRLİK — 3/3
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Üç gün çok iyi çalışıyorum, dördüncü gün tamamen tükeniyorum. Sonra iki gün hiçbir şey yapamıyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Bu düzen, ilk üç günün yükünün sürdürülebilir olmamasından kaynaklanıyor olabilir. "
                    "İyi çalıştığın günlerde yaklaşık kaç saat çalışıyorsun?"
                )
            },
            {
                "role": "user",
                "content": "8-9 saat çalışıyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Üç gün 8-9 saat çalışıp ardından iki gün tamamen durmak yerine günlük yükü azaltmak daha sürdürülebilir olur. "
                    "İlk hafta 5-6 saatlik daha dengeli bir taban dene ve her gün en az bir hafif blok bırak. "
                    "Amaç tek günde maksimum süre yapmak değil, haftanın toplamında daha istikrarlı ilerlemek. "
                    "Bir haftanın sonunda kaç gün düzeni koruyabildiğine bakıp süreyi yeniden ayarlarız."
                )
            }
        ]
    },
        # -----------------------------------------------------
    # SABIRSIZ ÖĞRENCİ — 1/7
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Bana soru sorma, direkt bugün ne çalışacağımı söyle. Sayısalım, TYT 70 civarı ve 5 saatim var."
            },
            {
                "role": "assistant",
                "content": (
                    "Elindeki bilgiler bugün için başlangıç planı yapmaya yeterli. "
                    "İlk 2 saati AYT matematik veya en zayıf sayısal dersine, sonraki 90 dakikayı TYT matematik-fen çalışmasına, "
                    "60 dakikayı ikinci bir AYT dersine ve son 30 dakikayı yanlış analizine ayır. "
                    "Hangi dersinin daha zayıf olduğunu daha sonra söylersen sonraki günlerin dağılımını netleştiririz; bugün başlamak için bunu beklememize gerek yok."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # SABIRSIZ ÖĞRENCİ — 2/7
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Çok soru sorma. Hemen bir program çıkar."
            },
            {
                "role": "assistant",
                "content": (
                    "İlk programı hızlıca çıkarabilmem için sadece üç kritik bilgi yeterli: alanın, yaklaşık TYT seviyen ve günlük çalışma süren."
                )
            },
            {
                "role": "user",
                "content": "Sayısalım, TYT 64, günde 4 saat."
            },
            {
                "role": "assistant",
                "content": (
                    "Başlamak için yeterli. Günlük 4 saatin 90 dakikasını matematiğe, 60 dakikasını fen derslerine, "
                    "60 dakikasını AYT çalışmasına ve 30 dakikasını yanlış analizine ayır. "
                    "İlk üç gün bu düzeni uygula. Sonra hangi derste en fazla zorlandığını söylersen ayrıntıyı oradan geliştireceğiz."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # SABIRSIZ ÖĞRENCİ — 3/7
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Uzun açıklama istemiyorum. Bugün 3 saatim var, AYT matematik çalışmam gerekiyor. Ne yapayım?"
            },
            {
                "role": "assistant",
                "content": (
                    "Bugünü şöyle kullan: 75 dakika konu/eksik tamamlama, 15 dakika ara, "
                    "60 dakika aynı konudan soru çözümü, 15 dakika ara ve son 30 dakikada yanlışlarını incele. "
                    "Konuyu bitiremezsen süreyi aşma; kaldığın yeri yarına taşı."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # SABIRSIZ ÖĞRENCİ — 4/7
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Hemen söyle, TYT netimi nasıl artıracağım?"
            },
            {
                "role": "assistant",
                "content": (
                    "Hızlı başlayalım: önce son denemendeki ders netlerini yaz. Tek seferde sadece buna ihtiyacım var."
                )
            },
            {
                "role": "user",
                "content": "Türkçe 27, sosyal 13, matematik 16, fen 9."
            },
            {
                "role": "assistant",
                "content": (
                    "İlk önceliğin fen ve matematik olsun. Önümüzdeki hafta her gün bir matematik veya fen ana bloğu yap, "
                    "Türkçeyi kısa branş çalışmalarıyla koru ve en az bir TYT denemesi çöz. "
                    "Deneme sonrası özellikle matematik ve fen yanlışlarını konu, dikkat ve süre hatası olarak ayır. "
                    "Şimdilik başka bilgi istemiyorum; ilk hafta için bu yeterli."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # SABIRSIZ ÖĞRENCİ — 5/7
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Program yaparken bana 10 tane soru sorma. Mezunum, eşit ağırlığım, TYT 72, günde 6 saatim var. Başla."
            },
            {
                "role": "assistant",
                "content": (
                    "Bu bilgilerle başlayabiliriz. 6 saatin yaklaşık 2 saatini AYT matematiğe, "
                    "1,5 saatini edebiyat-sosyal çalışmalarına, 1,5 saatini TYT matematik/Türkçe korumaya ve 1 saatini yanlış analizi ile tekrara ayır. "
                    "İlk hafta bu iskeleti kullan. Sonra yalnızca zayıf derslerini netleştirip dağılımı güncelleriz."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # SABIRSIZ ÖĞRENCİ — 6/7
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Detaya girmeyelim, yarından itibaren başlayacağım. Bana ilk günü ver."
            },
            {
                "role": "assistant",
                "content": (
                    "İlk günü doğru kurmak için sadece alanını ve toplam çalışma süreni yaz."
                )
            },
            {
                "role": "user",
                "content": "Sayısalım, 5 saat."
            },
            {
                "role": "assistant",
                "content": (
                    "İlk gün: 2 saat matematik, 90 dakika fen, 60 dakika TYT koruma ve 30 dakika yanlış analizi. "
                    "Derslerin içindeki konu seçimini mevcut eksiklerinden yap. "
                    "İlk gün için daha fazla bilgi toplamaya gerek yok; uyguladıktan sonra sonucu üzerinden ikinci günü ayarlarız."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # SABIRSIZ ÖĞRENCİ — 7/7
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Ben planı hemen görmek istiyorum. Eksiklerimi sonra anlatırım. Şimdilik günde 4 saat çalışabiliyorum ve 12. sınıf sayısalım."
            },
            {
                "role": "assistant",
                "content": (
                    "İlk iskeleti hemen kuralım. Günlük 4 saatin 2 saatini AYT matematik-fen, "
                    "1 saatini okulda işlenen 12. sınıf konularına ve 1 saatini TYT korumaya ayır. "
                    "Eksiklerini sonra söylediğinde bu dağılımın içini kişiselleştiririz. "
                    "Şu an planı başlatmak için daha fazla ayrıntıya ihtiyacımız yok."
                )
            }
        ]
    },
        # -----------------------------------------------------
    # DENEME VE YANLIŞ ANALİZİ — 1/6
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Deneme çözüyorum ama yanlışlarıma sadece bakıp geçiyorum. Nasıl analiz etmeliyim?"
            },
            {
                "role": "assistant",
                "content": (
                    "Her yanlış için uzun not tutmana gerek yok. Önce yanlış ve boşları dört gruba ayır: "
                    "konu eksiği, dikkat/işlem hatası, süre sorunu ve yorumlama problemi. "
                    "Sonra aynı hata türünün tekrar ettiği soruları işaretle. "
                    "Bir sonraki çalışma planında en sık tekrar eden hata türüne öncelik ver. "
                    "Amaç tek tek bütün soruları arşivlemek değil, tekrar eden kayıp nedenini bulmak."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # DENEME VE YANLIŞ ANALİZİ — 2/6
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Son üç TYT denemem 74, 71 ve 73 geldi. Nerede sorun olduğunu anlayamıyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Toplam netler birbirine yakın. Sorunu bulmak için ders bazında karşılaştırmamız gerekir. "
                    "Son üç denemede matematik ve fen netlerin nasıl değişti?"
                )
            },
            {
                "role": "user",
                "content": "Matematik 22, 19, 18. Fen 10, 11, 13."
            },
            {
                "role": "assistant",
                "content": (
                    "Fen yükselirken matematik 22'den 18'e düşmüş; toplam netin sabit görünmesinin altında iki farklı hareket var. "
                    "Bu yüzden bütün programı değiştirmek yerine matematik yanlışlarını incele. "
                    "Son üç denemede matematikte hangi soruların konu eksiği, işlem/dikkat veya süre kaynaklı olduğunu ayır. "
                    "Fen çalışmasını tamamen azaltma; matematikteki düşüşün nedenini hedefli biçimde çöz."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # DENEME VE YANLIŞ ANALİZİ — 3/6
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Yanlış defteri tutuyorum ama defter çok büyüdü. Artık tekrar etmeye yetişemiyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Her yanlış soruyu deftere geçirmek sistemi gereğinden ağırlaştırmış olabilir. "
                    "Sadece tekrar etme ihtimalin yüksek olan yanlışları kaydet: aynı konuda ikinci kez yapılan hata, "
                    "önemli bir yöntem eksiği veya sık tekrarlanan dikkat hatası gibi. "
                    "Tek seferlik basit işlem hatalarını uzun uzun yazmak yerine kısa etiket kullan. "
                    "Yanlış defterinin amacı arşiv oluşturmak değil, tekrar eden hataları görünür hale getirmek."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # DENEME VE YANLIŞ ANALİZİ — 4/6
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Denemede fizik yanlışım çok ama konu çalışınca soruları yapabiliyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Bu durumda sorun yalnızca konu eksiği olmayabilir. Denemede fizik sorularında daha çok ne oluyor: "
                    "süre mi kalmıyor, soruyu yanlış mı okuyorsun, yoksa bildiğin yöntemi o anda hatırlayamıyor musun?"
                )
            },
            {
                "role": "user",
                "content": "Genelde sona bırakıyorum ve aceleyle okuyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "O zaman yeni konu çalışmasını artırmadan önce sınav akışına müdahale et. "
                    "Birkaç denemede fiziğe daha erken geçmeyi dene ve başladığın saati kaydet. "
                    "Yanlışlarını da konu eksiği diye değil, 'acele okuma/süre' etiketiyle işaretle. "
                    "Evde yapabildiğin soruları denemede kaçırıyorsan çalışma planının yanında sınav içi zaman yönetimini de düzeltmemiz gerekiyor."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # DENEME VE YANLIŞ ANALİZİ — 5/6
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Her denemeden sonra yanlış yaptığım bütün konuları tekrar baştan çalışmalı mıyım?"
            },
            {
                "role": "assistant",
                "content": (
                    "Hayır. Her yanlış, konuyu baştan öğrenmen gerektiği anlamına gelmez. "
                    "Önce yanlışın nedenini ayır. Konuyu gerçekten bilmiyorsan konu tekrarı yap; "
                    "işlem veya dikkat hatasıysa benzer birkaç soru çözmek yeterli olabilir; "
                    "süre kaynaklıysa deneme stratejisini çalış. "
                    "Yanlışın nedenine göre müdahale etmek, her konuyu baştan çalışmaktan daha verimlidir."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # DENEME VE YANLIŞ ANALİZİ — 6/6
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "AYT denemelerinde matematik netim bazen 24 bazen 17 geliyor. Çok dengesiz."
            },
            {
                "role": "assistant",
                "content": (
                    "7 netlik oynama önemli. Önce bunun konu dağılımından mı, süre veya dikkatten mi geldiğini ayıralım. "
                    "Düşük gelen denemelerde ortak bir durum fark ettin mi?"
                )
            },
            {
                "role": "user",
                "content": "Zor sorulara çok takılıyorum, son 8-10 soruya bazen bakamıyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "O zaman net dalgalanmasının önemli bir kısmı bilgi seviyesinden çok soru seçimi ve süre yönetiminden geliyor olabilir. "
                    "Bir sonraki denemelerde ilk turda uzun süre ilerlemeyen soruyu işaretleyip geç. "
                    "Kaç soruya hiç bakamadığını ve zor sorularda toplam ne kadar süre kaybettiğini kaydet. "
                    "Birkaç deneme boyunca bu iki veriyi izleyerek matematik netindeki dalgalanmanın azalıp azalmadığına bakalım."
                )
            }
        ]
    },
        # -----------------------------------------------------
    # HEDEF GERÇEKÇİLİĞİ — 1/2
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "TYT'de 52 net yapıyorum. Bir ay sonra kesin 90 nete çıkmam lazım. Bana bunu garanti edecek programı yaz."
            },
            {
                "role": "assistant",
                "content": (
                    "Bir ayda 52 netten 90 nete çıkacağını garanti etmek doğru olmaz. "
                    "Ama hedefi tamamen bırakmak yerine önce hangi derslerde hızlı ve gerçekçi kazanım alanı olduğunu bulabiliriz. "
                    "Son üç denemendeki ders bazlı netlerini ve yanlış türlerini karşılaştır. "
                    "İlk iki haftada en büyük iki kayıp alanına odaklanıp düzenli deneme yap. "
                    "Hedefimiz belirli bir sonucu garanti etmek değil, ölçülebilir biçimde hata sayısını azaltıp net eğilimini yükseltmek olsun."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # HEDEF GERÇEKÇİLİĞİ — 2/2
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Tıp istiyorum ama şu an TYT 63, AYT 28 civarı. Bana dürüstçe söyle, yetişir mi?"
            },
            {
                "role": "assistant",
                "content": (
                    "Mevcut TYT ve AYT seviyen ile hedefin arasında ciddi bir çalışma mesafesi var; bunu küçümsememek gerekir. "
                    "Ama yalnız bu iki netten 'kesin yetişir' veya 'kesin yetişmez' sonucu çıkarmak da doğru olmaz. "
                    "Kalan süreyi ve günlük gerçekçi çalışma süreni bilirsem hedefi daha somut bir çalışma planına çevirebiliriz."
                )
            },
            {
                "role": "user",
                "content": "Sınava 5 ay var ve günde 6 saat çalışabilirim."
            },
            {
                "role": "assistant",
                "content": (
                    "Beş ay ve günlük 6 saat, ciddi bir gelişim için kullanılabilecek bir süre; fakat tıp hedefi için sonuç garantisi veremeyiz. "
                    "İlk aşamada büyük sonuca değil, dört haftalık gelişim dönemine odaklanalım. "
                    "TYT'de temel kayıpları azaltırken AYT matematik ve fen çalışmalarını düzenli biçimde büyüt. "
                    "Her hafta deneme sonuçlarını kaydet ve dört hafta sonunda net eğilimine bak. "
                    "Hedefi koruyabiliriz ama planı gerçek performans verilerine göre düzenli olarak yeniden değerlendirmeliyiz."
                )
            }
        ]
    },
        # -----------------------------------------------------
    # OKUL / DERSHANE / BİREYSEL ÇALIŞMA DENGESİ — 1/9
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "12. sınıfım. Okul 16.00'da bitiyor, pazartesi çarşamba cuma da dershaneye gidiyorum. Kendi çalışmamı nereye koyacağımı bilemiyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Dershane olan günlerle olmayan günleri aynı planlamayalım. "
                    "Dershane günlerinde eve yaklaşık kaçta geliyorsun, diğer iki hafta içi günde kaç saat ayırabiliyorsun?"
                )
            },
            {
                "role": "user",
                "content": "Dershane günleri 20.00 gibi evdeyim. Salı ve perşembe 3 saat çalışabiliyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Pazartesi, çarşamba ve cuma günlerini ağır bireysel çalışma günleri yapmayalım. "
                    "Bu günlerde eve geldikten sonra 45-60 dakikalık dershane tekrarı veya yanlış kontrolü yeterli olabilir. "
                    "Salı ve perşembe 3 saatlik sürede ana bireysel çalışmalarını yap. "
                    "Hafta sonunu ise deneme, analiz ve daha uzun eksik kapatma blokları için kullan. "
                    "Böylece dershaneyi bireysel çalışmanın üstüne ek bir tam program gibi yüklememiş oluruz."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # OKUL / DERSHANE / BİREYSEL ÇALIŞMA DENGESİ — 2/9
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Okulda zaten matematik ve fizik görüyorum. Eve gelince aynı dersleri tekrar çalışmak zaman kaybı mı?"
            },
            {
                "role": "assistant",
                "content": (
                    "Aynı dersi tekrar görmek otomatik olarak zaman kaybı değildir; tekrarın biçimi önemli. "
                    "Okulda konuyu anladıysan eve gelince yeniden uzun konu anlatımı izlemek yerine kısa tekrar ve soru çözümü yapabilirsin. "
                    "Anlamadığın bir bölüm varsa yalnız o kısmı yeniden çalış. "
                    "Ama okulda işlendi diye matematik ve fiziği tamamen bireysel programdan çıkarmak da doğru olmaz."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # OKUL / DERSHANE / BİREYSEL ÇALIŞMA DENGESİ — 3/9
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Dershanede çok ödev veriliyor. Kendi programımı hiç uygulayamıyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Dershane ödevleri bütün bireysel çalışma zamanını tüketiyorsa önce yükü ayırmamız gerekir. "
                    "Hafta içi dershane ödevlerine yaklaşık kaç saat gidiyor?"
                )
            },
            {
                "role": "user",
                "content": "Neredeyse her gün 2-2,5 saat."
            },
            {
                "role": "assistant",
                "content": (
                    "Bu durumda dershane ödevlerini ayrı bir ek yük değil, toplam çalışma sürenin bir parçası sayalım. "
                    "Ödevlerde zaten yeterince çalıştığın dersleri aynı gün tekrar programa ekleme. "
                    "Her gün ayrıca en az 45-60 dakikayı kendi önceliğin olan zayıf derse ayırmaya çalış. "
                    "Hafta sonunda da dershane ödevlerinden bağımsız bir deneme ve kendi eksiklerine yönelik çalışma bloğu bırak. "
                    "Amaç iki ayrı tam program yürütmek değil, ikisini tek sisteme birleştirmek."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # OKUL / DERSHANE / BİREYSEL ÇALIŞMA DENGESİ — 4/9
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Okul sınavları başladı. YKS çalışmasını tamamen bırakıp yazılılara mı çalışayım?"
            },
            {
                "role": "assistant",
                "content": (
                    "Yazılı haftasında okul çalışmalarının ağırlığını artırmak mantıklı olabilir ama YKS'yi tamamen sıfırlamak zorunda değilsin. "
                    "Yazılı dönemi yaklaşık kaç gün sürecek?"
                )
            },
            {
                "role": "user",
                "content": "Yaklaşık 10 gün."
            },
            {
                "role": "assistant",
                "content": (
                    "Bu 10 günde okul sınavlarını ana öncelik yapıp YKS'yi koruma moduna alabiliriz. "
                    "Günde 30-60 dakikalık TYT problem, Türkçe veya kısa branş çalışmasıyla bağlantıyı koparma. "
                    "Okul sınavında çalıştığın matematik ve fen konuları YKS ile örtüşüyorsa bunları ayrıca iki kez çalışmana gerek yok. "
                    "Yazılılar bittikten sonra normal YKS düzenine geri dön."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # OKUL / DERSHANE / BİREYSEL ÇALIŞMA DENGESİ — 5/9
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Sabah 08.00-16.00 okuldayım, akşam da 18.00-20.00 dershanem var. Eve gelince 3 saat daha çalışmam gerekiyor gibi hissediyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Bu kadar dolu bir günün üstüne her akşam 3 saat daha zorunlu çalışma eklemek sürdürülebilir olmayabilir. "
                    "Dershane günlerinde 45-90 dakikalık kısa tekrar, ödev veya yanlış analizi yeterli olabilir. "
                    "Daha uzun bireysel çalışmaları dershane olmayan günlere ve hafta sonuna taşı. "
                    "Toplam yükü değerlendirirken okul ve dershanede yaptığın akademik çalışmayı da hesaba kat."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # OKUL / DERSHANE / BİREYSEL ÇALIŞMA DENGESİ — 6/9
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Dershanenin programı ile benim eksiklerim uyuşmuyor. Onlar başka konu işliyor, ben başka konuda çok gerideyim."
            },
            {
                "role": "assistant",
                "content": (
                    "Dershane sırasını tamamen takip etmek zorunda değilsin; kendi eksiklerin için ayrı bir bireysel hat oluşturabiliriz. "
                    "Hafta içinde kendine ait kaç saatlik çalışma süren kalıyor?"
                )
            },
            {
                "role": "user",
                "content": "Dershane dışında günde yaklaşık 2 saat."
            },
            {
                "role": "assistant",
                "content": (
                    "Bu 2 saatin tamamını dershanenin tekrarına vermeyelim. "
                    "Yaklaşık 60-75 dakikayı senin geride olduğun konuya, kalan süreyi dershanede işlenenlerin kısa tekrarı ve sorularına ayırabilirsin. "
                    "Dershanede işlenen konu zaten iyi bildiğin bir alansa o gün kendi eksiğine daha fazla zaman ver. "
                    "Böylece dershanenin temposunu takip ederken kişisel açığın da büyümez."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # OKUL / DERSHANE / BİREYSEL ÇALIŞMA DENGESİ — 7/9
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Hafta içi okul yüzünden çok az çalışıyorum. Hafta sonu bütün açığı kapatmaya çalışıyorum ve pazar akşamı bitiyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Hafta sonuna bütün haftanın yükünü taşımak iki günü gereğinden ağırlaştırıyor olabilir. "
                    "Hafta içi gerçekten kullanabileceğin en küçük düzenli süre ne kadar?"
                )
            },
            {
                "role": "user",
                "content": "Her akşam 1 saat kesin ayırabilirim."
            },
            {
                "role": "assistant",
                "content": (
                    "O bir saati küçümsemeyelim. Hafta içi her gün tek bir net görev yap: örneğin bir gün matematik soru çözümü, "
                    "bir gün fizik, bir gün TYT Türkçe gibi. "
                    "Böylece beş günde yaklaşık 5 saatlik yükü hafta sonundan almış olursun. "
                    "Cumartesi ve pazarı ise uzun ana çalışmalar, deneme ve analiz için kullan; bütün haftayı iki güne sıkıştırma."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # OKUL / DERSHANE / BİREYSEL ÇALIŞMA DENGESİ — 8/9
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Okulda boş derslerim oluyor. Eve gelince daha az çalışmak için bütün YKS çalışmamı okulda yapmaya çalışsam olur mu?"
            },
            {
                "role": "assistant",
                "content": (
                    "Okuldaki boş zamanları değerlendirmek iyi fikir ama her çalışma türü okul ortamına uygun olmayabilir. "
                    "Boş derslerde kısa tekrar, paragraf, problem, kelime veya yanlış notları gibi bölünebilir işleri yap. "
                    "Uzun konu öğrenme, tam deneme veya yoğun odak isteyen çalışmaları daha sakin zamana bırak. "
                    "Böylece okulda kazandığın süre eve geldiğinde yükünü azaltır ama çalışma kalitesini düşürmez."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # OKUL / DERSHANE / BİREYSEL ÇALIŞMA DENGESİ — 9/9
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Hem okul öğretmenimin verdiği ödevler hem dershane ödevleri hem de kendi soru bankalarım var. Hangisini önce yapacağımı şaşırıyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Üç ayrı listeyi aynı anda bitirmeye çalışmak yerine görevleri amaçlarına göre birleştirelim. "
                    "En çok zorlandığın ders hangisi?"
                )
            },
            {
                "role": "user",
                "content": "Matematik."
            },
            {
                "role": "assistant",
                "content": (
                    "Matematikte önce yakın tarihli okul veya dershane zorunlu ödevini tamamla; ardından aynı konudan ekstra kaynak çözmek gerçekten gerekiyorsa ekle. "
                    "Aynı beceriyi çalıştıran üç farklı kaynaktan bütün testleri aynı gün çözmek zorunda değilsin. "
                    "Zorunlu görevi yaptıktan sonra yanlışlarını kontrol et; hâlâ eksik varsa kendi soru bankandan hedefli birkaç test çöz. "
                    "Böylece kaynak sayısına göre değil, ihtiyaca göre ilerlersin."
                )
            }
        ]
    },
    # -----------------------------------------------------
    # SINAVA YAKIN DÖNEM / STRES / AİLE BASKISI — 1/5
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "YKS'ye 12 gün kaldı. Konularım hâlâ eksik. Bundan sonra her gün 10 saat çalışıp hepsini bitirmeli miyim?"
            },
            {
                "role": "assistant",
                "content": (
                    "Son 12 günde hedefi bütün eksikleri bitirmek olarak koymak yerine, kalan sürede en fazla katkı sağlayacak konuları seçmek daha gerçekçi olur. "
                    "Çalışma süresini bir anda 10 saate çıkarmak yerine sürdürebildiğin düzeni koru. "
                    "Eksikleri kısa sürede toparlanabilecek, soru pratiğiyle gelişebilecek ve şu aşamada çok zaman isteyenler diye ayır. "
                    "İlk iki gruba öncelik ver; deneme, yanlış analizi ve uyku düzenini de bırakma."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # SINAVA YAKIN DÖNEM / STRES / AİLE BASKISI — 2/5
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Sınava az kaldıkça denemelerde elim ayağım titriyor. Netlerim normalde yaptığımın altına düşüyor."
            },
            {
                "role": "assistant",
                "content": (
                    "Bu durumda yalnızca konu çalışmasını artırmak çözüm olmayabilir. "
                    "Kaygının denemenin hangi bölümünde arttığını fark ediyor musun?"
                )
            },
            {
                "role": "user",
                "content": "Özellikle matematiğe geçince çok geriliyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Önümüzdeki denemelerde matematiğe geçiş anını özellikle takip et. "
                    "İlk birkaç soruda hızlanmaya çalışma; kolay veya orta seviyede ilerleyebildiğin sorularla ritim kur. "
                    "Deneme sonrasında matematikteki yanlışları konu eksiği ve kaygı/süre kaynaklı hatalar diye ayır. "
                    "Kaygı çok yoğunlaşıyor, günlük yaşamını veya sınava girebilmeni ciddi biçimde etkiliyorsa bir psikolojik danışman ya da ruh sağlığı uzmanından destek almak da uygun olur."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # SINAVA YAKIN DÖNEM / STRES / AİLE BASKISI — 3/5
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Ailem son haftalarda sürekli netimi soruyor. Her denemeden sonra tartışıyoruz ve çalışmaya dönmekte zorlanıyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Deneme sonrası yaşanan tartışmalar çalışma düzenini bozuyorsa sonucu paylaşma biçimini değiştirmek işe yarayabilir. "
                    "Ailenle sonuçları ne sıklıkta konuşuyorsunuz?"
                )
            },
            {
                "role": "user",
                "content": "Neredeyse her denemeden hemen sonra."
            },
            {
                "role": "assistant",
                "content": (
                    "Sonuçları her denemeden hemen sonra tartışmak yerine haftada bir kez toplu değerlendirme önerebilirsin. "
                    "Örneğin deneme günü yalnızca kendi yanlış analizini yapıp, haftanın sonunda net trendini ve çalıştığın alanları birlikte paylaşabilirsin. "
                    "Senin tarafında da kötü bir denemeden sonra bütün günü bırakmak yerine kısa bir analiz ve tek küçük görevle yeniden çalışmaya dönmek hedef olsun."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # SINAVA YAKIN DÖNEM / STRES / AİLE BASKISI — 4/5
    # Tek turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Sınava 5 gün kaldı. Son günlerde deneme netlerim düştü. Artık yeni kaynak alıp sabaha kadar soru çözmek istiyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Son 5 günde yeni kaynak ve sabahlama eklemek yerine mevcut düzeni sadeleştirmek daha güvenli olur. "
                    "Net düşüşünün nedenini birkaç denemeyle incele; yorgunluk, süre veya belirli bir ders kaynaklı olabilir. "
                    "Daha önce yanlış yaptığın sorulara, kısa tekrarlarına ve kontrollü denemelere dön. "
                    "Uyku düzenini bozup yeni bir sistem kurmaya çalışma; amaç sınav gününe mümkün olduğunca dengeli gitmek."
                )
            }
        ]
    },

    # -----------------------------------------------------
    # SINAVA YAKIN DÖNEM / STRES / AİLE BASKISI — 5/5
    # Çok turlu
    # -----------------------------------------------------
    {
        "messages": [
            {
                "role": "user",
                "content": "Sınava bir hafta kaldı ama kendimi suçlu hissediyorum. Daha çok çalışmalıydım diye düşünüyorum ve masaya oturunca geçmişi düşünüyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Geçmişte ne kadar çalıştığını artık değiştiremeyiz; kalan bir haftayı nasıl kullanacağını değiştirebiliriz. "
                    "Şu an seni en çok zorlayan şey konu eksiği mi, deneme performansı mı, yoksa zihnini toparlamak mı?"
                )
            },
            {
                "role": "user",
                "content": "En çok zihnimi toparlayamıyorum. Sürekli geç kaldığımı düşünüyorum."
            },
            {
                "role": "assistant",
                "content": (
                    "Bu hafta için geçmiş çalışma süresini değerlendirmeyi bırakıp günlük çok küçük ve net hedefler kullanalım. "
                    "Her sabah yalnızca o günün 2-3 ana görevini belirle: kısa tekrar, seçilmiş soru çalışması ve gerekiyorsa deneme/analiz. "
                    "Gün içinde 'geç kaldım' düşüncesi geldiğinde yeni program yazmak yerine mevcut göreve geri dön. "
                    "Amaç son haftada açığı mucizevi biçimde kapatmak değil, sahip olduğun bilgiyi mümkün olduğunca düzenli kullanabilmek."
                )
            }
        ]
    },

    
]

def validate_plan():
    category_total = sum(CATEGORY_PLAN.values())
    conversation_total = sum(CONVERSATION_PLAN.values())
    answer_length_total = sum(ANSWER_LENGTH_PLAN.values())

    print("Gold Dataset v0.4 plan kontrolu")
    print()

    print(f"Kaynak: {SOURCE_FILE}")
    print(f"Hedef : {OUTPUT_FILE}")
    print()

    print(f"Hedef toplam ornek: {TARGET_TOTAL_EXAMPLES}")
    print(f"Kategori toplami  : {category_total}")
    print(f"Konusma toplami   : {conversation_total}")
    print(f"Cevap boyu toplami: {answer_length_total}")
    print()

    if category_total != TARGET_TOTAL_EXAMPLES:
        raise ValueError(
            f"Kategori toplami hatali: {category_total}"
        )

    if conversation_total != TARGET_TOTAL_EXAMPLES:
        raise ValueError(
            f"Konusma plani toplami hatali: {conversation_total}"
        )

    if answer_length_total != TARGET_TOTAL_EXAMPLES:
        raise ValueError(
            f"Cevap boyu plani toplami hatali: {answer_length_total}"
        )

    print("Kategori plani: OK")
    print("Konusma plani : OK")
    print("Cevap boyu    : OK")


if __name__ == "__main__":
    validate_plan()