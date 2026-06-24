# crm-rfm-api

Müşteri segmentasyonu için RFM (Recency, Frequency, Monetary) analizi yapan ve sonuçları bir API üzerinden sunan proje. RFM skorları SQL (window function + `NTILE`) ile hesaplanır, sonuçlar PostgreSQL'e yazılır ve async FastAPI endpoint'leri üzerinden sunulur.

## Kullanılan Teknolojiler

- PostgreSQL — veri tabanı
- FastAPI + SQLAlchemy (async) + asyncpg — API katmanı
- pandas / psycopg2 — başlangıç veri yükleme scripti
- Docker Compose — API + veritabanını tek komutla ayağa kaldırma
- pytest — endpoint testleri

## Veritabanı Şeması

- `customers` — müşteri bilgileri
- `transactions` — satış işlemleri
- `segments` — hesaplanmış RFM skorları ve segment etiketleri (her recalculate çalıştırması geçmişe yeni satırlar ekler)
- `model_logs` — her RFM hesaplama çalıştırmasının kaydı (zaman, parametreler, segment dağılımı)

Şema tanımı: [`sql/schema.sql`](sql/schema.sql). RFM hesaplama sorgusu: [`sql/rfm_scoring.sql`](sql/rfm_scoring.sql).

## Kurulum — Docker Compose (önerilen, başka bir bilgisayarda çalıştırmak için)

1. [Docker Desktop](https://www.docker.com/products/docker-desktop/) kurulu ve açık olmalı (sistem tepsisinde "Engine running" görünmeli).
2. Repoyu klonla:
   ```
   git clone https://github.com/eyyorivaille/crm-rfm-api.git
   cd crm-rfm-api
   ```
3. `.env.example`'ı kopyalayıp kendi `.env`'ini oluştur (şifreyi istediğin gibi değiştirebilirsin, bu sadece kendi local Docker container'ının şifresi):
   ```
   cp .env.example .env
   ```
4. Tek komutla API + PostgreSQL'i ayağa kaldır:
   ```
   docker compose up -d --build
   ```
   - PostgreSQL container'ı ilk açılışta `sql/schema.sql`'i otomatik çalıştırır, tablolar hazır gelir.
   - API: http://localhost:8000 (Swagger: http://localhost:8000/docs)
5. Bu noktada veritabanı **boş** (sadece tablolar var). Gerçek Online Retail II verisini yüklemek için:
   - "Online Retail II" veri setini Kaggle'dan indir, proje kökündeki `data/online_retail_II.xlsx` olarak kaydet (bu klasör `docker-compose.yml` ile `api` container'ına otomatik mount edilir).
   - Container içinde yükleme scriptini çalıştır:
     ```
     docker compose exec api python load_data.py
     ```
   - RFM skorlarını hesapla:
     ```
     curl -X POST http://localhost:8000/rfm/recalculate
     ```
6. Durdurmak için: `docker compose down` (veritabanı verisi `pgdata` volume'unda kalıcı kalır, silmek istersen `-v` ekle).

## Kurulum — Local (Docker'sız)

1. PostgreSQL'de `crm_db` veritabanını oluştur, `sql/schema.sql`'i çalıştır.
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
6. RFM skorlarını hesapla (ilk kez): `sql/rfm_scoring.sql`'i pgAdmin'de çalıştır, ya da API ayaktayken `POST /rfm/recalculate` çağır.
7. API'yi başlat:
   ```
   uvicorn main:app --reload
   ```

## API Endpoint'leri

### `GET /customers/{customer_id}/segment`

Müşterinin en güncel RFM segmentini döndürür.

```
GET /customers/12636/segment
```
```json
{
  "customer_id": "12636",
  "recency": 738,
  "frequency": 1,
  "monetary": "141.00",
  "rfm_score": "111",
  "segment_label": "Hibernating",
  "calculated_at": "2026-06-24T16:21:30.159257"
}
```
Müşteri yoksa veya hiç segmenti hesaplanmamışsa `404` döner.

### `GET /segments/summary`

Segment başına müşteri sayısı ve ortalama harcamayı döndürür (her müşterinin en güncel kaydı baz alınır).

```
GET /segments/summary
```
```json
[
  {"segment_label": "Hibernating", "customer_count": 1534, "avg_monetary": "361.65"},
  {"segment_label": "Champion", "customer_count": 1292, "avg_monetary": "9373.90"}
]
```

### `POST /rfm/recalculate`

RFM hesaplamasını yeniden tetikler, `segments` tablosuna yeni bir geçmiş kaydı yazar ve `model_logs` tablosuna çalıştırma özetini (zaman, segment dağılımı, etkilenen müşteri sayısı) kaydeder.

```
POST /rfm/recalculate
```
```json
{
  "rows_written": 5878,
  "run_at": "2026-06-24T16:42:58.128484"
}
```

## Testler

```
pytest tests/ -v
```

## Veri Kaynağı

Online Retail II Dataset — UCI Machine Learning Repository (Kaggle üzerinden indirildi)
