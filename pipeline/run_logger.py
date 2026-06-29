"""crm_logs_db.pipeline_runs tablosuna yazan kucuk yardimci - DAG task'lari
basina/sonuna bunu cagirir, boylece her adimin basari/hata durumu, suresi
ve etkiledigi musteri sayisi merkezi olarak gorulebilir.
"""
import datetime

from sqlalchemy import text

from pipeline.db_utils import get_logs_engine


def log_step_start(dag_run_id: str, step_name: str) -> int:
    engine = get_logs_engine()
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO pipeline_runs (dag_run_id, step_name, started_at, status) "
                "VALUES (:dag_run_id, :step_name, :started_at, 'running') RETURNING id"
            ),
            {
                "dag_run_id": dag_run_id,
                "step_name": step_name,
                "started_at": datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
            },
        )
        return result.scalar_one()


def log_step_success(log_id: int, customers_affected: int | None = None) -> None:
    engine = get_logs_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE pipeline_runs SET finished_at = :finished_at, "
                "customers_affected = :customers_affected, status = 'success' "
                "WHERE id = :id"
            ),
            {
                "finished_at": datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
                "customers_affected": customers_affected,
                "id": log_id,
            },
        )


def log_step_failure(log_id: int, error_message: str) -> None:
    engine = get_logs_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE pipeline_runs SET finished_at = :finished_at, "
                "status = 'failed', error_message = :error_message "
                "WHERE id = :id"
            ),
            {
                "finished_at": datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
                "error_message": error_message[:2000],
                "id": log_id,
            },
        )
