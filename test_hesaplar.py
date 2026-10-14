# test_hesaplar.py
# Hesaplayıcıların doğru çalıştığını kontrol eden otomatik testler.
# Yapay zeka ve internet gerekmez. Çalıştırma:  python test_hesaplar.py

from envanter import eoq_hesapla, yeniden_siparis_noktasi
from portfoy import stok_listesi_analiz


def yaklasik(a, b, tolerans=0.05):
    return abs(a - b) <= tolerans


def test_eoq():
    s = eoq_hesapla(12000, 50, 2)
    assert yaklasik(s["eoq"], 774.6), s["eoq"]
    assert yaklasik(s["yillik_siparis_sayisi"], 15.49, 0.01)
    # EOQ noktasında yıllık sipariş maliyeti ile yıllık elde tutma maliyeti birbirine eşittir
    assert yaklasik(s["yillik_siparis_maliyeti"], s["yillik_elde_tutma_maliyeti"], 0.01)
    assert yaklasik(s["toplam_maliyet"], 1549.19, 0.01)


def test_yeniden_siparis_noktasi():
    s = yeniden_siparis_noktasi(33, 6, 5, 0.95)
    assert yaklasik(s["z"], 1.645, 0.001)
    assert yaklasik(s["emniyet_stoku"], 22.1)
    assert yaklasik(s["tedarik_suresi_talebi"], 165)
    assert yaklasik(s["yeniden_siparis_noktasi"], 187.1)


def test_abc_ve_tam_analiz():
    urunler = [
        {"urun": "Ürün A", "yillik_talep": 1200, "birim_fiyat": 1400, "siparis_maliyeti": 200,
         "elde_tutma_orani": 0.18, "gunluk_talep_std": 2, "tedarik_suresi_gun": 10, "hizmet_seviyesi": 0.98},
        {"urun": "Ürün B", "yillik_talep": 6000, "birim_fiyat": 120, "siparis_maliyeti": 150,
         "elde_tutma_orani": 0.20, "gunluk_talep_std": 6, "tedarik_suresi_gun": 5, "hizmet_seviyesi": 0.95},
        {"urun": "Ürün C", "yillik_talep": 3000, "birim_fiyat": 25},
    ]
    s = stok_listesi_analiz(urunler)
    siralama = [u["urun"] for u in s["urunler"]]
    assert siralama == ["Ürün A", "Ürün B", "Ürün C"], siralama  # değeri en yüksek ürün başta
    assert s["urunler"][0]["abc"] == "A" and s["urunler"][-1]["abc"] == "C"
    assert s["urunler"][0]["eoq"] == 44 and s["urunler"][0]["yeniden_siparis_noktasi"] == 46
    assert s["urunler"][1]["eoq"] == 274 and s["urunler"][1]["yeniden_siparis_noktasi"] == 104
    # Bilgisi eksik ürün için EOQ hesaplanmaz ve eksik listesinde bildirilir
    assert s["urunler"][2]["eoq"] is None
    assert "Ürün C" in s["eoq_icin_eksik_bilgisi_olan_urunler"]
    assert yaklasik(sum(u["deger_payi_yuzde"] for u in s["urunler"]), 100, 0.2)


def test_yuzde_ve_oran_ayni_sonucu_verir():
    temel = {"urun": "X", "yillik_talep": 4800, "birim_fiyat": 85, "siparis_maliyeti": 120}
    a = stok_listesi_analiz([{**temel, "elde_tutma_orani": 0.20, "gunluk_talep_std": 5,
                              "tedarik_suresi_gun": 7, "hizmet_seviyesi": 0.95}])
    b = stok_listesi_analiz([{**temel, "elde_tutma_orani": 20, "gunluk_talep_std": 5,
                              "tedarik_suresi_gun": 7, "hizmet_seviyesi": 95}])
    assert a["urunler"] == b["urunler"]


def hata_vermeli(fonksiyon, *args):
    try:
        fonksiyon(*args)
    except ValueError:
        return
    raise AssertionError("ValueError bekleniyordu ama hata çıkmadı")


def test_hatali_girisler():
    hata_vermeli(eoq_hesapla, 0, 50, 2)
    hata_vermeli(eoq_hesapla, 12000, -5, 2)
    hata_vermeli(yeniden_siparis_noktasi, 33, 6, 5, 1.0)   # hizmet seviyesi 0-1 arasında olmalı
    hata_vermeli(yeniden_siparis_noktasi, 33, 6, 0, 0.95)  # tedarik süresi 0 olamaz
    hata_vermeli(stok_listesi_analiz, [])
    hata_vermeli(stok_listesi_analiz, [{"urun": "X", "birim_fiyat": 5}])  # yıllık talep eksik
    hata_vermeli(stok_listesi_analiz, [{"urun": "X", "yillik_talep": "çok", "birim_fiyat": 5}])


if __name__ == "__main__":
    testler = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in testler:
        t()
        print("geçti:", t.__name__)
    print(f"\nTüm testler geçti ({len(testler)} test).")
