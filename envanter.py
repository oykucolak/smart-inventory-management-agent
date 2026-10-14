# envanter.py
# Adım 1: EOQ (Ekonomik Sipariş Miktarı) hesaplayıcısı
# Henüz yapay zeka yok. Önce hesaplamanın doğru çalıştığından emin oluyoruz.

import math
from statistics import NormalDist


def eoq_hesapla(yillik_talep, siparis_maliyeti, birim_elde_tutma_maliyeti):
    """
    yillik_talep              : bir yılda kaç adet satılıyor (D)
    siparis_maliyeti          : her sipariş verdiğinde ödediğin sabit para, TL (S)
    birim_elde_tutma_maliyeti : bir ürünü bir yıl depoda tutmanın maliyeti, TL (H)
    """
    if yillik_talep <= 0 or siparis_maliyeti <= 0 or birim_elde_tutma_maliyeti <= 0:
        raise ValueError("Tüm değerler 0'dan büyük olmalı.")

    # EOQ formülü: karekök(2 * D * S / H)
    q = math.sqrt(2 * yillik_talep * siparis_maliyeti / birim_elde_tutma_maliyeti)

    siparis_sayisi = yillik_talep / q
    siparis_maliyeti_toplam = siparis_sayisi * siparis_maliyeti
    elde_tutma_toplam = (q / 2) * birim_elde_tutma_maliyeti

    return {
        "eoq": q,
        "yillik_siparis_sayisi": siparis_sayisi,
        "yillik_siparis_maliyeti": siparis_maliyeti_toplam,
        "yillik_elde_tutma_maliyeti": elde_tutma_toplam,
        "toplam_maliyet": siparis_maliyeti_toplam + elde_tutma_toplam,
    }


def yeniden_siparis_noktasi(gunluk_talep_ort, gunluk_talep_std, tedarik_suresi_gun, hizmet_seviyesi):
    """
    Adım 2: Stok kaça düşünce yeni sipariş verilmeli? (ROP) + emniyet stoku.

    gunluk_talep_ort   : günde ortalama kaç adet satılıyor
    gunluk_talep_std   : günlük satışın standart sapması (günden güne ne kadar dalgalanıyor)
    tedarik_suresi_gun : sipariş verdikten kaç gün sonra mal geliyor
    hizmet_seviyesi    : 0 ile 1 arası. Örnek: 0.95 = "talebin %95'ini stoktan karşılamak istiyorum"
    """
    if gunluk_talep_ort <= 0 or gunluk_talep_std < 0 or tedarik_suresi_gun <= 0:
        raise ValueError("Talep ve tedarik süresi 0'dan büyük, standart sapma negatif olmamalı.")
    if not (0 < hizmet_seviyesi < 1):
        raise ValueError("Hizmet seviyesi 0 ile 1 arasında olmalı (örnek: 0.95).")

    # z değeri: hizmet seviyesine karşılık gelen normal dağılım katsayısı.
    # %95 için yaklaşık 1.645 çıkar. Python'un hazır modülü hesaplıyor, kurulum gerekmez.
    z = NormalDist().inv_cdf(hizmet_seviyesi)

    # Emniyet stoku = z * günlük std * karekök(tedarik süresi)
    emniyet_stoku = z * gunluk_talep_std * math.sqrt(tedarik_suresi_gun)

    # Tedarik süresi boyunca beklenen satış
    tedarik_suresi_talebi = gunluk_talep_ort * tedarik_suresi_gun

    return {
        "z": z,
        "emniyet_stoku": emniyet_stoku,
        "tedarik_suresi_talebi": tedarik_suresi_talebi,
        "yeniden_siparis_noktasi": tedarik_suresi_talebi + emniyet_stoku,
    }


# Bu kısım sadece dosyayı doğrudan çalıştırınca devreye girer (test için).
if __name__ == "__main__":
    print("--- EOQ ---")
    sonuc = eoq_hesapla(yillik_talep=12000, siparis_maliyeti=50, birim_elde_tutma_maliyeti=2)

    print("Ekonomik sipariş miktarı :", round(sonuc["eoq"], 1), "adet")
    print("Yıllık sipariş sayısı    :", round(sonuc["yillik_siparis_sayisi"], 1))
    print("Yıllık sipariş maliyeti  :", round(sonuc["yillik_siparis_maliyeti"], 2), "TL")
    print("Yıllık elde tutma maliyeti:", round(sonuc["yillik_elde_tutma_maliyeti"], 2), "TL")
    print("Toplam maliyet           :", round(sonuc["toplam_maliyet"], 2), "TL")

    print()
    print("--- Yeniden sipariş noktası ---")
    rop = yeniden_siparis_noktasi(
        gunluk_talep_ort=33, gunluk_talep_std=6, tedarik_suresi_gun=5, hizmet_seviyesi=0.95
    )
    print("z değeri                 :", round(rop["z"], 3))
    print("Tedarik süresi talebi    :", round(rop["tedarik_suresi_talebi"], 1), "adet")
    print("Emniyet stoku            :", round(rop["emniyet_stoku"], 1), "adet")
    print("Yeniden sipariş noktası  :", round(rop["yeniden_siparis_noktasi"], 1), "adet")
