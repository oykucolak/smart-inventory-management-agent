# app.py
# Adım 6: Tarayıcıda açılan arayüz (Streamlit).
# Çalıştırma:  python -m streamlit run app.py
# Aynı klasörde agent.py, envanter.py ve portfoy.py olmalı. Hazır veri yoktur: rakamları kullanıcı sohbette yazar.

import os

import altair as alt
import pandas as pd
import streamlit as st
from google import genai

from agent import MODEL, ajan_calistir

st.set_page_config(page_title="Akıllı Stok Yönetimi Ajanı", page_icon="📦", layout="wide")

# Ajanın kullandığı hesapların sayfada görünen Türkçe adları (kod adları sayfada gösterilmez)
HESAP_ADLARI = {
    "eoq_hesapla": "Ekonomik sipariş miktarı (EOQ) hesabı",
    "yeniden_siparis_noktasi": "Yeniden sipariş noktası ve emniyet stoku hesabı",
    "stok_listesi_analiz": "Çok ürünlü stok listesi analizi (ABC)",
}
GIRDI_ADLARI = {
    "yillik_talep": "Yıllık talep",
    "siparis_maliyeti": "Sipariş maliyeti",
    "birim_elde_tutma_maliyeti": "Birim elde tutma maliyeti",
    "gunluk_talep_ort": "Günlük ortalama talep",
    "gunluk_talep_std": "Günlük talebin sapması",
    "tedarik_suresi_gun": "Tedarik süresi (gün)",
    "hizmet_seviyesi": "Hizmet seviyesi",
}

# Sayfa ilk açıldığında bunlar boştur; hesaplar yapıldıkça dolar.
if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = []
if "hesaplar" not in st.session_state:
    st.session_state.hesaplar = []


def girdi_satirlari(parametreler):
    """Ajanın hesaba verdiği girdileri 'Ad: değer' satırları olarak döndürür."""
    satirlar = []
    for ad, deger in parametreler.items():
        if ad not in GIRDI_ADLARI:
            continue
        if ad == "hizmet_seviyesi":
            deger = f"%{float(deger) * 100:g}"
        satirlar.append(f"{GIRDI_ADLARI[ad]}: {deger}")
    return satirlar


def arac_goster(araclar):
    """Sohbet balonunun altında: ajanın hangi hesabı hangi girdilerle yaptığını düz Türkçe gösterir."""
    for a in araclar:
        st.markdown("**" + HESAP_ADLARI.get(a["ad"], "Hesap") + "**")
        satirlar = girdi_satirlari(a["parametreler"])
        if a["ad"] == "stok_listesi_analiz":
            satirlar = ["Veri: sohbette girilen ürün listesi"]
        if satirlar:
            st.markdown("\n".join("- " + s for s in satirlar))


def hesap_kutusu(araclar):
    with st.expander("Ajan hangi hesabı yaptı?"):
        arac_goster(araclar)
    st.caption("Sonuçların tamamı «Hesap sonuçları» sekmesinde.")


# ---------- Hesap sonuçlarını sekmede gösteren parçalar ----------
def eoq_goster(s):
    k1, k2, k3 = st.columns(3)
    k1.metric("Ekonomik sipariş miktarı", f"{s['eoq']:,.0f} adet")
    k2.metric("Yıllık sipariş sayısı", f"{s['yillik_siparis_sayisi']:,.1f}")
    k3.metric("Toplam yıllık maliyet", f"{s['toplam_maliyet']:,.0f} TL")
    st.caption(
        f"Yıllık sipariş maliyeti {s['yillik_siparis_maliyeti']:,.0f} TL + yıllık elde tutma maliyeti "
        f"{s['yillik_elde_tutma_maliyeti']:,.0f} TL. En iyi sipariş miktarında bu iki maliyet birbirine eşit olur."
    )


def rop_goster(s):
    k1, k2, k3 = st.columns(3)
    k1.metric("Yeniden sipariş noktası", f"{s['yeniden_siparis_noktasi']:,.0f} adet")
    k2.metric("Emniyet stoku", f"{s['emniyet_stoku']:,.0f} adet")
    k3.metric("Tedarik süresince beklenen talep", f"{s['tedarik_suresi_talebi']:,.0f} adet")
    st.caption(
        "Stok yeniden sipariş noktasına düşünce yeni sipariş verilir. "
        "Yeniden sipariş noktası = tedarik süresince beklenen talep + emniyet stoku."
    )


def liste_goster(s):
    urunler = s["urunler"]
    a_sayisi = sum(1 for u in urunler if u["abc"] == "A")

    maliyet = s["toplam_yillik_stok_maliyeti"]
    k1, k2, k3 = st.columns(3)
    k1.metric("Toplam yıllık kullanım değeri", f"{s['toplam_yillik_kullanim_degeri']:,.0f} TL")
    k2.metric("Toplam yıllık stok maliyeti", "-" if maliyet is None else f"{maliyet:,.0f} TL")
    k3.metric("A sınıfı ürün sayısı", f"{a_sayisi} / {len(urunler)}")

    # Bilgisi eksik olduğu için bazı hesapların yapılamadığı ürünleri belirt
    eoq_eksik = s.get("eoq_icin_eksik_bilgisi_olan_urunler") or []
    rop_eksik = s.get("yeniden_siparis_noktasi_icin_eksik_bilgisi_olan_urunler") or []
    if eoq_eksik:
        st.caption(
            "Sipariş maliyeti ve elde tutma maliyeti verilmediği için EOQ hesaplanamayan ürünler: "
            + ", ".join(eoq_eksik)
        )
    if rop_eksik:
        st.caption(
            "Günlük talep sapması, tedarik süresi ve hizmet seviyesi verilmediği için yeniden sipariş noktası "
            "hesaplanamayan ürünler: " + ", ".join(rop_eksik)
        )

    sutunlar = {
        "urun": "Ürün",
        "abc": "ABC",
        "deger_payi_yuzde": "Değer payı (%)",
        "yillik_talep": "Yıllık talep",
        "eoq": "EOQ (adet)",
        "yillik_siparis_sayisi": "Sipariş/yıl",
        "emniyet_stoku": "Emniyet stoku",
        "yeniden_siparis_noktasi": "Sipariş noktası",
        "yillik_kullanim_degeri": "Kullanım değeri (TL)",
        "yillik_stok_maliyeti": "Stok maliyeti (TL)",
    }
    # Hiçbir üründe hesaplanamayan sütunlar (tamamen boş) tabloda gösterilmez
    tablo = pd.DataFrame(urunler)[list(sutunlar)].rename(columns=sutunlar).dropna(axis=1, how="all")
    # Bazı ürünlerde hesaplanamayan değerler boş kalmasın, "-" yazılsın
    for sutun in tablo.columns:
        if tablo[sutun].isna().any():
            tablo[sutun] = tablo[sutun].map(lambda x: "-" if pd.isna(x) else f"{x:g}")
    st.dataframe(tablo, hide_index=True)

    # Çubuklar değere göre büyükten küçüğe sıralı, eksen sıfırdan başlar.
    grafik_verisi = pd.DataFrame(
        {
            "urun": [u["urun"] for u in urunler],
            "deger": [u["yillik_kullanim_degeri"] for u in urunler],
            "abc": [u["abc"] for u in urunler],
            "pay": [u["deger_payi_yuzde"] for u in urunler],
        }
    )
    grafik = (
        alt.Chart(grafik_verisi)
        .mark_bar()
        .encode(
            x=alt.X("urun:N", sort="-y", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("deger:Q", title="Yıllık kullanım değeri (TL)"),
            color=alt.Color("abc:N", title="ABC sınıfı"),
            tooltip=[
                alt.Tooltip("urun:N", title="Ürün"),
                alt.Tooltip("abc:N", title="ABC"),
                alt.Tooltip("deger:Q", title="Değer (TL)"),
                alt.Tooltip("pay:Q", title="Pay (%)"),
            ],
        )
    )
    st.altair_chart(grafik)

    st.caption(
        "ABC analizi: ürünler yıllık kullanım değerine (talep × birim fiyat) göre büyükten küçüğe sıralanır. "
        "Toplam değerin ilk %80'ini oluşturanlar A (sıkı takip), sonraki %15'i B (orta takip), "
        "kalan %5'i C (basit takip) sınıfıdır. Böylece zaman ve para en değerli ürünlere harcanır."
    )


def hesap_goster(a, baslik=True):
    if baslik:
        st.subheader(HESAP_ADLARI.get(a["ad"], "Hesap"))
    if a["ad"] == "stok_listesi_analiz":
        st.caption(f"Veri: sohbette girilen {len(a['sonuc']['urunler'])} ürün.")
        liste_goster(a["sonuc"])
        return
    girdiler = girdi_satirlari(a["parametreler"])
    if girdiler:
        st.caption("Girdiler: " + " · ".join(girdiler))
    if a["ad"] == "eoq_hesapla":
        eoq_goster(a["sonuc"])
    elif a["ad"] == "yeniden_siparis_noktasi":
        rop_goster(a["sonuc"])


# ---------- Sayfa başlığı ----------
st.title("📦 Akıllı Stok Yönetimi Ajanı")
st.caption(
    "Endüstri mühendisliği stok yönetimi: ekonomik sipariş miktarı (EOQ), emniyet stoku, "
    "yeniden sipariş noktası ve ABC analizi. Hesaplar Python'da yapılır, yapay zeka hangi hesabın yapılacağına karar verir ve sonucu yorumlar."
)

# ---------- Yan panel: API anahtarı ----------
with st.sidebar:
    st.header("Ayarlar")
    anahtar = os.environ.get("GEMINI_API_KEY", "")
    if anahtar:
        st.success("API anahtarı terminalden alındı.")
    else:
        anahtar = st.text_input("Gemini API anahtarı", type="password", help="Anahtar sadece bu oturumda kullanılır, hiçbir yere kaydedilmez.")
    model_adi = MODEL.replace("-", " ").title()  # gemini-3.5-flash-lite -> Gemini 3.5 Flash Lite
    st.write(f"Yapay zeka modeli: {model_adi}")
    st.info("Ajanla sohbet etmek için API anahtarı gerekir.")

# İlk sekme sayfa açılınca görünen sekmedir: sohbet.
sekme_sohbet, sekme_sonuc = st.tabs(["💬 Ajan ile sohbet", "📊 Hesap sonuçları"])

# ---------- Sekme 1: ajan ile sohbet ----------
with sekme_sohbet:
    st.subheader("Ajana sor")
    st.caption("Problemini rakamlarıyla birlikte kendi cümlelerinle yaz. Ajan uygun hesabı seçer, eksik bilgi olursa sorar.")
    with st.expander("Hangi hesaplar yapılabilir, hangi bilgiler gerekir?"):
        st.markdown(
            "- **Ekonomik sipariş miktarı (EOQ):** yıllık talep, sipariş başına maliyet, birim elde tutma maliyeti\n"
            "- **Yeniden sipariş noktası ve emniyet stoku:** günlük ortalama talep, günlük talebin sapması, "
            "tedarik süresi, hizmet seviyesi\n"
            "- **Çok ürünlü ABC analizi:** her ürün için yıllık talep ve birim fiyat. Sipariş maliyeti, elde tutma "
            "maliyeti, günlük talep sapması, tedarik süresi ve hizmet seviyesi de eklenirse EOQ ve yeniden sipariş "
            "noktası da hesaplanır"
        )

    # Mesajlar sabit yükseklikli, kaydırılabilir bir kutuda akar.
    # Soru kutusu bu kutudan SONRA tanımlanır, bu yüzden hep kutunun altında durur.
    mesaj_kutusu = st.container(height=520)
    soru = st.chat_input("Sorunu yaz...")

    with mesaj_kutusu:
        # Önceki mesajlar
        for m in st.session_state.mesajlar:
            with st.chat_message(m["rol"]):
                st.markdown(m["metin"])
                if m.get("araclar"):
                    hesap_kutusu(m["araclar"])

        # Yeni soru: soru ve cevap da aynı kutunun içinde, en sonda görünür
        if soru:
            with st.chat_message("user"):
                st.markdown(soru)
            st.session_state.mesajlar.append({"rol": "user", "metin": soru})

            with st.chat_message("assistant"):
                if not anahtar:
                    cevap, araclar = "Önce yan panele Gemini API anahtarını gir.", []
                    st.warning(cevap)
                else:
                    araclar = []
                    with st.spinner("Ajan çalışıyor, 30-60 saniye sürebilir..."):
                        try:
                            cevap = ajan_calistir(genai.Client(api_key=anahtar), soru, araclar)
                        except Exception as hata:
                            cevap = f"Hata oluştu: {hata}"
                    cevap = cevap.replace("$", "\\$")  # Streamlit $ işaretini formül sanmasın
                    st.markdown(cevap)
                    if araclar:
                        hesap_kutusu(araclar)

            # Hatasız biten hesaplar "Hesap sonuçları" sekmesine eklenir
            st.session_state.hesaplar.extend(a for a in araclar if "hata" not in a["sonuc"])
            st.session_state.mesajlar.append({"rol": "assistant", "metin": cevap, "araclar": araclar})

# ---------- Sekme 2: hesap sonuçları (sohbet kodundan sonra çalışır, o yüzden en yeni hesabı görür) ----------
with sekme_sonuc:
    hesaplar = st.session_state.hesaplar
    if not hesaplar:
        st.info(
            "Henüz bir hesap yapılmadı. «Ajan ile sohbet» sekmesinde ajana bir soru sor, "
            "hesabın sonucu burada görünür."
        )
    else:
        hesap_goster(hesaplar[-1])
        if len(hesaplar) > 1:
            st.divider()
            st.subheader("Önceki hesaplar")
            for a in reversed(hesaplar[:-1]):
                girdi = " · ".join(girdi_satirlari(a["parametreler"]))
                etiket = HESAP_ADLARI.get(a["ad"], "Hesap") + (f" ({girdi})" if girdi else "")
                with st.expander(etiket):
                    hesap_goster(a, baslik=False)
