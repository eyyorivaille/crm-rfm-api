"""Haftalik RFM -> Segmentasyon -> Churn -> CLV pipeline'i.

Adimlar sirayla baglidir (>>): bir adim basarisiz olursa Airflow'un
varsayilan davranisi (trigger_rule=all_success) sonraki adimlari
calistirmaz - "bir adim basarisiz olursa pipeline durmali" gereksinimi
ekstra konfigurasyon gerektirmeden saglanir.

Her adim, basari/hata durumunu crm_logs_db.pipeline_runs tablosuna
(pipeline/run_logger.py uzerinden) kaydeder.
"""
import datetime

from airflow.decorators import dag, task
from airflow.operators.python import get_current_context

from pipeline.churn import run_churn_training
from pipeline.clv import run_clv_training
from pipeline.rfm import run_rfm_recalculation
from pipeline.run_logger import log_step_failure, log_step_start, log_step_success
from pipeline.segmentation import run_segmentation


def _run_step(step_name, func):
    dag_run_id = get_current_context()["dag_run"].run_id
    log_id = log_step_start(dag_run_id, step_name)
    try:
        result = func()
    except Exception as exc:
        log_step_failure(log_id, str(exc))
        raise

    customers_affected = (
        result.get("rows_written")
        or result.get("customers_scored")
        or (sum(result["cluster_sizes"]) if "cluster_sizes" in result else None)
    )
    log_step_success(log_id, customers_affected)
    return result


@dag(
    dag_id="weekly_rfm_churn_clv_pipeline",
    schedule="@weekly",
    start_date=datetime.datetime(2026, 1, 1),
    catchup=False,
    tags=["rfm", "segmentation", "churn", "clv"],
)
def weekly_pipeline():
    @task
    def rfm_step():
        return _run_step("rfm", run_rfm_recalculation)

    @task
    def segmentation_step():
        return _run_step("segmentation", run_segmentation)

    @task
    def churn_step():
        return _run_step("churn", run_churn_training)

    @task
    def clv_step():
        return _run_step("clv", run_clv_training)

    rfm_step() >> segmentation_step() >> churn_step() >> clv_step()


weekly_pipeline()
