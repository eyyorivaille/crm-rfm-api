-- Airflow'un kendi orkestrasyon metadata'si (DAG/task state gecmisi) icin
-- ayri bir veritabani. crm_db (is verisi) ve crm_logs_db (bizim
-- pipeline_runs tablomuz) ile karistirilmamali - bu, Airflow'un kendi
-- ic mekanizmasinin ihtiyac duydugu, bizim sorgulamadigimiz bir DB.

CREATE DATABASE airflow_meta;
