# test_gemini.py
# Adım 3: Gemini'ye bağlanabiliyor muyuz? Sadece küçük bir bağlantı testi.
# API anahtarı bu dosyaya YAZILMAZ. Python onu bilgisayarın "ortam değişkeni"nden okur
# (GEMINI_API_KEY adıyla). Böylece anahtar kodda durmaz, GitHub'a yanlışlıkla gitmez.

import os
import sys

from google import genai

from agent import MODEL  # ajanla aynı model

if not os.environ.get("GEMINI_API_KEY"):
    print("HATA: GEMINI_API_KEY bulunamadı. Önce terminalde anahtarı tanımlamalısın.")
    sys.exit(1)

client = genai.Client()  # anahtarı ortam değişkeninden kendisi alır

try:
    cevap = client.interactions.create(
        model=MODEL,
        input="Bir envanter yönetimi ajanısın. Tek cümleyle Türkçe merhaba de.",
    )
    print("Gemini cevabı:", cevap.output_text)
except Exception as hata:
    print("Bağlantı hatası:")
    print(hata)
