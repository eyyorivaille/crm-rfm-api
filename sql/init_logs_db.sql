-- crm_db (is verisi) ile pipeline/orkestrasyon loglarini ayri tutmak icin
-- ayri bir veritabani. Airflow DAG run'larinin basari/hata gecmisi burada
-- tutulur - musteri/islem verisiyle aynı veritabaninda degil.

CREATE DATABASE crm_logs_db;

\c crm_logs_db

CREATE TABLE pipeline_runs (
    id                  SERIAL PRIMARY KEY,
    dag_run_id          VARCHAR(100) NOT NULL,
    step_name           VARCHAR(50) NOT NULL,
    started_at          TIMESTAMP NOT NULL,
    finished_at         TIMESTAMP,
    customers_affected  INTEGER,
    status              VARCHAR(20) NOT NULL,
    error_message       TEXT
);

CREATE INDEX idx_pipeline_runs_dag_run_id ON pipeline_runs(dag_run_id);
