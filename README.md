# 📦 Smart Inventory Management Agent

An **AI agent** written in Python that solves **inventory management** problems from industrial engineering.

The user describes a problem and its numbers in plain sentences (in Turkish). The agent (Google Gemini) decides which calculation is needed, extracts the numbers from the text, and calls calculator functions written in Python. It then explains the result in Turkish. The project includes a web interface that runs in the browser.

> **Language note:** the app's interface and the agent's replies are in Turkish. This README is in English, and the screenshots below show the Turkish interface.

> **Key design decision:** the mathematical calculations are not left to the AI. Python functions do the math; the AI only decides *which calculation* to run and *which inputs* to use, and then interprets the result. This keeps the numbers consistent and verifiable.

## What does it do?

| Calculation | Description | Required inputs |
|---|---|---|
| **Economic order quantity (EOQ)** | The order quantity that minimizes the sum of annual ordering and holding costs | Annual demand, ordering cost per order, holding cost per unit per year |
| **Safety stock and reorder point** | The stock level at which a new order should be placed | Average daily demand, standard deviation of daily demand, lead time, service level |
| **Multi-product ABC analysis** | Classifies products as A/B/C by annual usage value to set priorities. For products with enough information, it also calculates EOQ and the reorder point | Annual demand and unit price for each product (other inputs are optional) |

The program contains no built-in or sample data. The user types the products and numbers in the chat. If information is missing, the agent does not guess; it asks the user.

## Screenshots

**Chat with the agent (opening screen):**

![Chat with the agent](ekran_goruntuleri/sohbet.png)

**The user describes the problem with its numbers:**

![Example question](ekran_goruntuleri/ornek_soru.png)

**The agent's answer:**

![Agent answer 1](ekran_goruntuleri/agent_cevap_1.png)

![Agent answer 2](ekran_goruntuleri/agent_cevap_2.png)

**Calculation results tab (metric boxes, table and chart):**

![Calculation results 1](ekran_goruntuleri/sonuclar_1.png)

![Calculation results 2](ekran_goruntuleri/sonuclar_2.png)

## How does the agent work?

1. The user writes the problem, e.g. *"My annual demand is 12000 units, ordering cost is 50 TL..."*
2. The agent sends the message, together with descriptions of its **tools** (the calculator functions), to Gemini.
3. Gemini picks the right tool and extracts the inputs from the sentence (*function calling*).
4. Python runs that function. The code does the calculation, not the AI.
5. The result is sent back to Gemini, which writes the interpretation in Turkish.
6. The results are shown in the "Hesap sonuçları" (Calculation results) tab of the interface as boxes, tables and charts.

## Installation

**Requirements:** Python 3.10 or later and a free Gemini API key.

1. Download the project (green **Code** button on GitHub, then **Download ZIP**) and extract it.
2. Open a terminal in the folder and install the required packages:
   ```
   python -m pip install -r requirements.txt
   ```
3. Sign in to [Google AI Studio](https://aistudio.google.com) with your Google account and create an **API key**.
4. Define the key in the terminal (the key is never written into the code). **Windows PowerShell:**
   ```
   $env:GEMINI_API_KEY="YOUR_KEY_HERE"
   ```
   **Mac / Linux:**
   ```
   export GEMINI_API_KEY="YOUR_KEY_HERE"
   ```
   This setting is valid only for that terminal window. You can also open the app without defining the key and enter it in the sidebar of the page instead.

## Running

**Browser interface (recommended):**
```
python -m streamlit run app.py
```
The page opens at `http://localhost:8501`.

**Chat in the terminal:**
```
python agent.py
```

**Tests** (no internet or API key needed):
```
python test_hesaplar.py
```

## Example problem

Write the following to the agent (the app works in Turkish):

> Bir otomotiv yedek parça deposunun stok yöneticisiyim, 4 ürünüm var. Fren balatası: yıllık talep 6000 adet, birim fiyat 120 TL, sipariş maliyeti 150 TL, elde tutma oranı %20, günlük talep sapması 6, tedarik süresi 5 gün, hizmet seviyesi %95. Yağ filtresi: yıllık talep 9000 adet, birim fiyat 35 TL, sipariş maliyeti 100 TL, elde tutma oranı %22, günlük talep sapması 8, tedarik süresi 4 gün, hizmet seviyesi %95. Akü: yıllık talep 1200 adet, birim fiyat 1400 TL, sipariş maliyeti 200 TL, elde tutma oranı %18, günlük talep sapması 2, tedarik süresi 10 gün, hizmet seviyesi %98. Silecek lastiği: yıllık talep 3000 adet, birim fiyat 25 TL, sipariş maliyeti 80 TL, elde tutma oranı %25, günlük talep sapması 4, tedarik süresi 3 gün, hizmet seviyesi %90. Hangi ürünlere öncelik vermeliyim, her ürün için kaç adet sipariş vermeliyim ve stok kaça düşünce sipariş vermeliyim?

In English, the same problem reads: *I am the inventory manager of an automotive spare-parts warehouse with 4 products. Brake pads: annual demand 6000 units, unit price 120 TL, ordering cost 150 TL, holding cost rate 20%, daily demand standard deviation 6, lead time 5 days, service level 95%. Oil filter: annual demand 9000 units, unit price 35 TL, ordering cost 100 TL, holding cost rate 22%, daily demand standard deviation 8, lead time 4 days, service level 95%. Battery: annual demand 1200 units, unit price 1400 TL, ordering cost 200 TL, holding cost rate 18%, daily demand standard deviation 2, lead time 10 days, service level 98%. Wiper blade: annual demand 3000 units, unit price 25 TL, ordering cost 80 TL, holding cost rate 25%, daily demand standard deviation 4, lead time 3 days, service level 90%. Which products should I prioritize, how many units should I order for each product, and at what stock level should I place an order?*

Expected result (the data is hypothetical):

| Product | ABC | Value share | EOQ (units) | Safety stock | Reorder point | Annual inventory cost |
|---|---|---|---|---|---|---|
| Battery (Akü) | A | 60.2% | 44 | 13 | 46 | 10,998 TL |
| Brake pads (Fren balatası) | A | 25.8% | 274 | 22 | 104 | 6,573 TL |
| Oil filter (Yağ filtresi) | B | 11.3% | 483 | 26 | 125 | 3,723 TL |
| Wiper blade (Silecek lastiği) | C | 2.7% | 277 | 9 | 34 | 1,732 TL |

Total annual usage value is 2,790,000 TL and total annual inventory cost is 23,026 TL.

## Formulas used

- **EOQ** = √(2 · D · S / H)  
  D: annual demand, S: ordering cost per order, H: annual holding cost per unit (unit price × holding cost rate)
- **Safety stock** = z · σ · √L  
  z: standard normal value for the service level, σ: standard deviation of daily demand, L: lead time (days)
- **Reorder point** = d · L + safety stock  
  d: average daily demand (annual demand / 365)
- **ABC analysis:** products are sorted by annual usage value (demand × unit price). Those making up the first 80% of the cumulative share are class A, the next 15% are class B, and the rest are class C.

## Assumptions and limitations

- Demand is assumed constant over the year, daily demand follows a normal distribution, and lead time is constant.
- The EOQ calculation has no quantity discounts and no shortage (stockout) cost.
- A year is taken as 365 days.
- Because the agent is based on a language model, it may misread a sentence. The **"Ajan hangi hesabı yaptı?"** (Which calculation did the agent run?) box under each answer shows the inputs the agent used, so you can check them.
- Response times may be long on the free API tier.
- The model used is set on the `MODEL` line in `agent.py`. If Google retires the model, change it there.

## Project structure

```
├── app.py              Browser interface (Streamlit)
├── agent.py            The agent: talks to Gemini, selects and calls the tools
├── envanter.py         Calculators: EOQ, safety stock, reorder point
├── portfoy.py          Multi-product analysis and ABC classification
├── test_hesaplar.py    Automated tests of the calculators
├── test_gemini.py      Gemini connection test (needs an API key)
├── requirements.txt    Required Python packages
└── ekran_goruntuleri/  Screenshots shown in this README
```

## Security note

The API key is never written into the code or uploaded to GitHub. It is read only from the `GEMINI_API_KEY` environment variable on your computer (or entered in the sidebar of the interface). The `.gitignore` file prevents secret files from being uploaded by accident.

## Technologies

Python · Google Gemini (Interactions API, function calling) · Streamlit · pandas · Altair

---

Prepared by: **Öykü Çolak** · Course: **Integrated Systems Design**
