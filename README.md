# crm-rfm-api

Müşteri segmentasyonu için RFM (Recency, Frequency, Monetary) analizi yapan ve sonuçları bir API üzerinden sunan proje.

## Kullanılan Teknolojiler

- PostgreSQL — veri tabanı
- FastAPI — API katmanı
- pandas / psycopg2 / SQLAlchemy — veri yükleme ve işleme

## Veritabanı Şeması

- `customers` — müşteri bilgileri
- `transactions` — satış işlemleri
- `segments` — hesaplanmış RFM skorları ve segment etiketleri
- `model_logs` — model çalıştırma kayıtları

## Kurulum

1. PostgreSQL'de `crm_db` veritabanını oluştur.
2. Proje kökünde aşağıdaki içerikle bir `.env` dosyası oluştur:
   ```
   DB_USER=postgres
   DB_PASSWORD=...
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=crm_db
   ```
3. Bağımlılıkları kur:
   ```
   pip install -r requirements.txt
   ```
4. "Online Retail II" veri setini Kaggle'dan indir, `data/online_retail_II.xlsx` olarak kaydet.
5. Veriyi yükle:
   ```
   python load_data.py
   ```
6. API'yi başlat:
   ```
   uvicorn main:app --reload
   ```

## Veri Kaynağı

Online Retail II Dataset — UCI Machine Learning Repository (Kaggle üzerinden indirildi)
