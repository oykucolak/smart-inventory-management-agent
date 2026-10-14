# portfoy.py
# Adım 5: Çok ürünlü stok analizi.
# Kullanıcının sohbette yazdığı ürün listesi için EOQ, emniyet stoku, yeniden sipariş noktası ve
# ABC sınıfını hesaplar. Hazır veri yoktur: ürünler ve rakamlar kullanıcıdan gelir.
# Hesaplar envanter.py'deki hesaplayıcılarla yapılır.

from envanter import eoq_hesapla, yeniden_siparis_noktasi

GUN_SAYISI = 365      # yıllık talebi güne çevirirken kullanılır
EN_FAZLA_URUN = 50    # çok uzun listeler istenirse reddedilir

# Hata mesajlarında kullanıcıya gösterilecek Türkçe adlar
ETIKET = {
    "yillik_talep": "yıllık talep",
    "birim_fiyat": "birim fiyat",
    "siparis_maliyeti": "sipariş maliyeti",
    "elde_tutma_orani": "elde tutma oranı",
    "birim_elde_tutma_maliyeti": "birim elde tutma maliyeti",
    "gunluk_talep_std": "günlük talep sapması",
    "tedarik_suresi_gun": "tedarik süresi",
    "hizmet_seviyesi": "hizmet seviyesi",
}


def _yok(u, anahtar):
    """Ürün sözlüğünde bu bilgi verilmemiş mi?"""
    return u.get(anahtar) is None or str(u.get(anahtar)).strip() == ""


def _sayi(u, anahtar, urun_adi):
    """Bilgiyi sayıya çevirir. '0,20' ya da '0.20' yazılmış olabilir."""
    try:
        return float(str(u[anahtar]).strip().replace(",", "."))
    except ValueError:
        raise ValueError(f"'{urun_adi}' ürünü için {ETIKET[anahtar]} bir sayı olmalı.")


def _oran(x):
    """Yüzde yazılmışsa (20 ya da 95) 0-1 arasına çevirir."""
    return x / 100 if x > 1 else x


def stok_listesi_analiz(urunler):
    """
    urunler: kullanıcının verdiği ürünlerin listesi. Her ürün bir sözlüktür:
      zorunlu : urun, yillik_talep, birim_fiyat
      EOQ için (ikisi birden gerekir):
                siparis_maliyeti  +  (elde_tutma_orani  veya  birim_elde_tutma_maliyeti)
      yeniden sipariş noktası için (üçü birden gerekir):
                gunluk_talep_std, tedarik_suresi_gun, hizmet_seviyesi
    Eksik bilgisi olan ürün için ilgili hesap yapılmaz ve sonuçta "eksik bilgi" olarak bildirilir.
    """
    if not isinstance(urunler, list) or not urunler:
        raise ValueError("En az bir ürün gerekli.")
    if len(urunler) > EN_FAZLA_URUN:
        raise ValueError(f"En fazla {EN_FAZLA_URUN} ürün analiz edilebilir.")

    sonuc_urunleri = []
    eoq_eksik, rop_eksik = [], []

    for sira, u in enumerate(urunler, start=1):
        if not isinstance(u, dict):
            raise ValueError(f"{sira}. ürün geçersiz.")
        ad = str(u.get("urun") or f"Ürün {sira}")

        for gerekli in ("yillik_talep", "birim_fiyat"):
            if _yok(u, gerekli):
                raise ValueError(f"'{ad}' ürünü için {ETIKET[gerekli]} eksik.")
        talep = _sayi(u, "yillik_talep", ad)
        fiyat = _sayi(u, "birim_fiyat", ad)
        if talep <= 0 or fiyat <= 0:
            raise ValueError(f"'{ad}' ürününde yıllık talep ve birim fiyat 0'dan büyük olmalı.")

        kayit = {
            "urun": ad,
            "yillik_talep": round(talep),
            "birim_fiyat": fiyat,
            "yillik_kullanim_degeri": round(talep * fiyat, 2),
            "eoq": None,
            "yillik_siparis_sayisi": None,
            "yillik_stok_maliyeti": None,
            "emniyet_stoku": None,
            "yeniden_siparis_noktasi": None,
        }

        # --- EOQ: sipariş maliyeti ve elde tutma maliyeti (oran ya da TL) varsa ---
        elde_tutma_var = not _yok(u, "elde_tutma_orani") or not _yok(u, "birim_elde_tutma_maliyeti")
        if not _yok(u, "siparis_maliyeti") and elde_tutma_var:
            siparis = _sayi(u, "siparis_maliyeti", ad)
            if not _yok(u, "birim_elde_tutma_maliyeti"):
                elde_tutma = _sayi(u, "birim_elde_tutma_maliyeti", ad)
            else:
                elde_tutma = fiyat * _oran(_sayi(u, "elde_tutma_orani", ad))
            try:
                e = eoq_hesapla(talep, siparis, elde_tutma)
            except ValueError as hata:
                raise ValueError(f"'{ad}' ürünü: {hata}")
            kayit["eoq"] = round(e["eoq"])
            kayit["yillik_siparis_sayisi"] = round(e["yillik_siparis_sayisi"], 1)
            kayit["yillik_stok_maliyeti"] = round(e["toplam_maliyet"], 2)
        else:
            eoq_eksik.append(ad)

        # --- Yeniden sipariş noktası: sapma, tedarik süresi ve hizmet seviyesi varsa ---
        if not any(_yok(u, k) for k in ("gunluk_talep_std", "tedarik_suresi_gun", "hizmet_seviyesi")):
            try:
                r = yeniden_siparis_noktasi(
                    talep / GUN_SAYISI,
                    _sayi(u, "gunluk_talep_std", ad),
                    _sayi(u, "tedarik_suresi_gun", ad),
                    _oran(_sayi(u, "hizmet_seviyesi", ad)),
                )
            except ValueError as hata:
                raise ValueError(f"'{ad}' ürünü: {hata}")
            kayit["emniyet_stoku"] = round(r["emniyet_stoku"])
            kayit["yeniden_siparis_noktasi"] = round(r["yeniden_siparis_noktasi"])
        else:
            rop_eksik.append(ad)

        sonuc_urunleri.append(kayit)

    # ABC sınıflandırması: değeri en yüksek ürünlerden başla.
    # Kümülatif payın %80'ine kadar A, %95'ine kadar B, kalanı C.
    sonuc_urunleri.sort(key=lambda k: k["yillik_kullanim_degeri"], reverse=True)
    toplam_deger = sum(k["yillik_kullanim_degeri"] for k in sonuc_urunleri)
    onceki_toplam = 0
    for k in sonuc_urunleri:
        pay_once = onceki_toplam / toplam_deger
        k["abc"] = "A" if pay_once < 0.80 else ("B" if pay_once < 0.95 else "C")
        k["deger_payi_yuzde"] = round(100 * k["yillik_kullanim_degeri"] / toplam_deger, 1)
        onceki_toplam += k["yillik_kullanim_degeri"]

    maliyetler = [k["yillik_stok_maliyeti"] for k in sonuc_urunleri if k["yillik_stok_maliyeti"] is not None]
    return {
        "urunler": sonuc_urunleri,
        "toplam_yillik_kullanim_degeri": round(toplam_deger, 2),
        # Hiç EOQ hesaplanamadıysa None; bazı ürünlerde hesaplandıysa sadece onların toplamı
        "toplam_yillik_stok_maliyeti": round(sum(maliyetler), 2) if maliyetler else None,
        "eoq_icin_eksik_bilgisi_olan_urunler": eoq_eksik,
        "yeniden_siparis_noktasi_icin_eksik_bilgisi_olan_urunler": rop_eksik,
    }


# Deneme: python portfoy.py
# DİKKAT: Aşağıdaki liste yalnızca bu dosyanın kendi testi içindir. Ajan ve web sitesi bu listeyi KULLANMAZ.
if __name__ == "__main__":
    deneme = [
        {"urun": "Ürün 1", "yillik_talep": 4800, "birim_fiyat": 85, "siparis_maliyeti": 120,
         "elde_tutma_orani": 0.20, "gunluk_talep_std": 5, "tedarik_suresi_gun": 7, "hizmet_seviyesi": 0.95},
        {"urun": "Ürün 2", "yillik_talep": 600, "birim_fiyat": 950},
        {"urun": "Ürün 3", "yillik_talep": 3000, "birim_fiyat": 18, "siparis_maliyeti": 90,
         "birim_elde_tutma_maliyeti": 4.5},
    ]
    sonuc = stok_listesi_analiz(deneme)
    print(f"{'Ürün':<10}{'ABC':<5}{'Değer%':<8}{'EOQ':<7}{'Emn.stok':<10}{'ROP':<7}{'Stok maliyeti'}")
    for k in sonuc["urunler"]:
        def g(x):
            return "-" if x is None else x
        print(f"{k['urun']:<10}{k['abc']:<5}{k['deger_payi_yuzde']:<8}{g(k['eoq']):<7}"
              f"{g(k['emniyet_stoku']):<10}{g(k['yeniden_siparis_noktasi']):<7}{g(k['yillik_stok_maliyeti'])}")
    print("EOQ için eksik bilgi :", sonuc["eoq_icin_eksik_bilgisi_olan_urunler"])
    print("ROP için eksik bilgi :", sonuc["yeniden_siparis_noktasi_icin_eksik_bilgisi_olan_urunler"])
