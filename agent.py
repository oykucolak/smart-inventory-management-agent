# agent.py
# Adım 4: Akıllı stok yönetimi AI ajanı
# Çalışması için aynı klasörde envanter.py de olmalı.
# Anahtar: terminalde GEMINI_API_KEY olarak tanımlı olmalı (koda yazılmaz).

import json
import os
import logging
import sys
import time

from google import genai

from envanter import eoq_hesapla, yeniden_siparis_noktasi
from portfoy import stok_listesi_analiz

# Teşhis: Gemini'ye giden her isteğin sonucunu (200 OK, 429, 503 gibi) ekrana yazar.
# Yavaşlık sorununu çözdük, o yüzden kapalı. Sorun çıkarsa True yapılabilir.
HIZ_TESHISI = False
if HIZ_TESHISI:
    logging.basicConfig(level=logging.WARNING, format="  [log] %(message)s")
    logging.getLogger("httpx").setLevel(logging.INFO)

# "flash-lite" Google'ın en hızlı modeli. Araç (fonksiyon) çağırma için bu yeterli.
# Önceki denemede gemini-3.8-flash cevap vermeden bekleyip durmuştu.
MODEL = "gemini-3.5-flash-lite"

# Ajana rolünü anlatan talimat.
TALIMAT = (
    "Sen bir endüstri mühendisliği stok yönetimi asistanısın. "
    "Kullanıcı Türkçe yazar. Sorusuna uygun aracı seç, sayıları sorudan çıkar ve aracı çağır. "
    "Soruda gerekli bir sayı eksikse tahmin etme, kullanıcıya hangi bilginin eksik olduğunu sor. "
    "Kullanıcı birden fazla ürünü kendi yazdığı rakamlarla verirse stok_listesi_analiz aracını kullan. "
    "Ürün adlarını ve rakamları yalnızca kullanıcının yazdıklarından al, hiçbir ürün ya da rakam uydurma. "
    "Hazır bir stok listesi ya da dosya yoktur; kullanıcı ürün vermediyse hangi bilgilere ihtiyaç olduğunu sor. "
    "Her ürün için yıllık talep ve birim fiyat zorunludur, eksikse sor. "
    "Sipariş maliyeti ve elde tutma maliyeti (oran ya da TL) varsa EOQ, günlük talep sapması, tedarik süresi ve "
    "hizmet seviyesi varsa yeniden sipariş noktası da hesaplanır. Sonuçta eksik bilgi listesi varsa kullanıcıya "
    "hangi bilgileri verirse daha fazla hesap yapılabileceğini söyle. "
    "Sonucu ABC sınıflarına göre yorumla (hangi ürüne öncelik verilmeli, hangisine daha az ilgi yeter). "
    "Sonucu Türkçe, kısa ve anlaşılır yorumla; sayıları birimiyle yaz."
)

# Ajanın kullanabileceği "araçlar". Yapay zeka bu açıklamalara bakıp hangisini seçeceğine karar verir.
ARACLAR = [
    {
        "type": "function",
        "name": "eoq_hesapla",
        "description": (
            "Ekonomik sipariş miktarını (EOQ) hesaplar: her seferde kaç adet sipariş verilirse "
            "yıllık sipariş + elde tutma maliyeti en düşük olur."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "yillik_talep": {"type": "number", "description": "Yıllık talep, adet"},
                "siparis_maliyeti": {"type": "number", "description": "Sipariş başına sabit maliyet, TL"},
                "birim_elde_tutma_maliyeti": {
                    "type": "number",
                    "description": "Bir birimi bir yıl elde tutma maliyeti, TL",
                },
            },
            "required": ["yillik_talep", "siparis_maliyeti", "birim_elde_tutma_maliyeti"],
        },
    },
    {
        "type": "function",
        "name": "yeniden_siparis_noktasi",
        "description": (
            "Yeniden sipariş noktasını ve emniyet stokunu hesaplar: stok kaç adede düşünce "
            "yeni sipariş verilmeli."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "gunluk_talep_ort": {"type": "number", "description": "Günlük ortalama talep, adet"},
                "gunluk_talep_std": {"type": "number", "description": "Günlük talebin standart sapması, adet"},
                "tedarik_suresi_gun": {"type": "number", "description": "Tedarik süresi, gün"},
                "hizmet_seviyesi": {
                    "type": "number",
                    "description": "Hizmet seviyesi, 0 ile 1 arası (%95 için 0.95)",
                },
            },
            "required": ["gunluk_talep_ort", "gunluk_talep_std", "tedarik_suresi_gun", "hizmet_seviyesi"],
        },
    },
    {
        "type": "function",
        "name": "stok_listesi_analiz",
        "description": (
            "Kullanıcının sohbette yazdığı birden fazla ürünü analiz eder: ürünleri yıllık kullanım değerine göre "
            "ABC sınıfına ayırır; bilgisi yeterliyse her ürün için ekonomik sipariş miktarı, emniyet stoku, "
            "yeniden sipariş noktası ve yıllık stok maliyetini de hesaplar."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "urunler": {
                    "type": "array",
                    "description": "Kullanıcının verdiği ürünler. Hiçbir ürün ya da rakam uydurulmaz.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "urun": {"type": "string", "description": "Ürün adı (kullanıcının yazdığı gibi)"},
                            "yillik_talep": {"type": "number", "description": "Yıllık talep, adet"},
                            "birim_fiyat": {"type": "number", "description": "Birim fiyat, TL"},
                            "siparis_maliyeti": {
                                "type": "number",
                                "description": "Sipariş başına sabit maliyet, TL (EOQ için)",
                            },
                            "elde_tutma_orani": {
                                "type": "number",
                                "description": "Yıllık elde tutma maliyetinin birim fiyata oranı, 0 ile 1 arası (%20 için 0.20)",
                            },
                            "birim_elde_tutma_maliyeti": {
                                "type": "number",
                                "description": "Bir birimi bir yıl elde tutma maliyeti, TL (oran yerine bu verilebilir)",
                            },
                            "gunluk_talep_std": {
                                "type": "number",
                                "description": "Günlük talebin standart sapması, adet (yeniden sipariş noktası için)",
                            },
                            "tedarik_suresi_gun": {
                                "type": "number",
                                "description": "Tedarik süresi, gün (yeniden sipariş noktası için)",
                            },
                            "hizmet_seviyesi": {
                                "type": "number",
                                "description": "Hizmet seviyesi, 0 ile 1 arası (%95 için 0.95)",
                            },
                        },
                        "required": ["urun", "yillik_talep", "birim_fiyat"],
                    },
                },
            },
            "required": ["urunler"],
        },
    },
]

# Yapay zekanın söylediği isim -> gerçek Python fonksiyonu.
# Sadece bu listedeki fonksiyonlar çalıştırılabilir.
FONKSIYONLAR = {
    "eoq_hesapla": eoq_hesapla,
    "yeniden_siparis_noktasi": yeniden_siparis_noktasi,
    "stok_listesi_analiz": stok_listesi_analiz,
}


def ajan_calistir(client, soru, kayit=None):
    """Soruyu yapay zekaya gönderir, istediği araçları çalıştırır, son cevabı döndürür.
    kayit: boş bir liste verilirse ajanın çağırdığı araçlar içine yazılır (web arayüzü bunu gösterir)."""
    print("  [Gemini'ye soruluyor, 10-30 saniye sürebilir...]")
    baslangic = time.time()
    etkilesim = client.interactions.create(model=MODEL, input=TALIMAT + "\n\nSoru: " + soru, tools=ARACLAR)
    print(f"  [Gemini cevap verdi: {time.time() - baslangic:.1f} saniye]")

    # En fazla 5 tur: yapay zeka araç ister -> biz çalıştırırız -> sonucu geri veririz
    for _ in range(5):
        cagrilar = [adim for adim in etkilesim.steps if adim.type == "function_call"]
        if not cagrilar:
            break  # araç istemiyor, cevabı hazır demektir

        sonuclar = []
        for cagri in cagrilar:
            print(f"  [ajan aracı çağırdı: {cagri.name} {dict(cagri.arguments)}]")
            fonksiyon = FONKSIYONLAR.get(cagri.name)
            if fonksiyon is None:
                sonuc = {"hata": "Bilinmeyen araç: " + cagri.name}
            else:
                try:
                    sonuc = fonksiyon(**cagri.arguments)
                except Exception as hata:
                    sonuc = {"hata": str(hata)}
            if kayit is not None:
                # Web arayüzü için: hangi hesap, hangi girdilerle yapıldı, sonuç ne çıktı
                kayit.append({"ad": cagri.name, "parametreler": dict(cagri.arguments), "sonuc": sonuc})
            sonuclar.append(
                {
                    "type": "function_result",
                    "name": cagri.name,
                    "call_id": cagri.id,
                    "result": [{"type": "text", "text": json.dumps(sonuc, ensure_ascii=False)}],
                }
            )

        print("  [sonuç Gemini'ye geri gönderiliyor...]")
        baslangic = time.time()
        etkilesim = client.interactions.create(
            model=MODEL,
            input=sonuclar,
            previous_interaction_id=etkilesim.id,
            tools=ARACLAR,
        )
        print(f"  [Gemini ikinci cevabı verdi: {time.time() - baslangic:.1f} saniye]")

    return etkilesim.output_text


if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        print("HATA: GEMINI_API_KEY tanımlı değil. Önce terminalde anahtarı tanımla.")
        sys.exit(1)

    client = genai.Client()
    print("Stok Yönetimi Ajanı hazır. Çıkmak için q yaz.")

    while True:
        soru = input("\nSen: ").strip()
        if soru.lower() in ("q", "çık", "cik"):
            break
        if not soru:
            continue
        try:
            print("Ajan:", ajan_calistir(client, soru))
        except Exception as hata:
            print("Hata:", hata)
