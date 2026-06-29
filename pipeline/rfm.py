"""RFM yeniden hesaplama - main.py'daki /rfm/recalculate endpoint'iyle ayni
SQL'i (sql/rfm_scoring.sql) kullanir, ama Airflow'un cagirabilecegi senkron
bir fonksiyon olarak.
"""
import json
from pathlib import Path

from pipeline.db_utils import get_engine

RFM_SQL = (Path(__file__).resolve().parent.parent / "sql" / "rfm_scoring.sql").read_text()


def run_rfm_recalculation():
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.exec_driver_sql(RFM_SQL)
        inserted_rows = result.fetchall()
        rows_written = len(inserted_rows)
        run_at = inserted_rows[0][0] if inserted_rows else None

        distribution_result = conn.exec_driver_sql(
            "SELECT segment_label, count(*) AS customer_count "
            "FROM segments WHERE calculated_at = %(run_at)s GROUP BY segment_label",
            {"run_at": run_at},
        )
        segment_distribution = {row[0]: row[1] for row in distribution_result}

        conn.exec_driver_sql(
            "INSERT INTO model_logs (model_name, run_at, parameters, metrics, notes) "
            "VALUES (%(model_name)s, %(run_at)s, %(parameters)s::jsonb, %(metrics)s::jsonb, %(notes)s)",
            {
                "model_name": "rfm_ntile5",
                "run_at": run_at,
                "parameters": json.dumps({"ntile_buckets": 5}),
                "metrics": json.dumps({
                    "customers_affected": rows_written,
                    "segment_distribution": segment_distribution,
                }),
                "notes": "Airflow haftalik pipeline calistirmasi",
            },
        )

    print(f"RFM yeniden hesaplandi: {rows_written} musteri, run_at={run_at}")
    return {"run_at": run_at, "rows_written": rows_written, "segment_distribution": segment_distribution}


if __name__ == "__main__":
    run_rfm_recalculation()
