import datetime
import json
import os
from pathlib import Path

import mlflow
from fastapi import Depends, FastAPI, HTTPException
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from logs_db import get_logs_db
from models import Segment
from schemas import ModelInfoOut, PipelineStatusOut, PipelineStepOut, RecalculateOut, SegmentOut, SegmentSummaryOut

app = FastAPI()

RFM_SQL = (Path(__file__).parent / "sql" / "rfm_scoring.sql").read_text()

MLFLOW_MODEL_NAME = "rfm-customer-segments"
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))
mlflow_client = MlflowClient()


@app.get("/")
def read_root():
    return {"Mesaj": "FastAPI başarıyla kuruldu!"}


@app.get("/customers/{customer_id}/segment", response_model=SegmentOut)
async def get_customer_segment(customer_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Segment)
        .where(Segment.customer_id == customer_id)
        .order_by(Segment.calculated_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    segment = result.scalar_one_or_none()
    if segment is None:
        raise HTTPException(status_code=404, detail="Customer not found or has no segment")
    return segment


@app.get("/segments/summary", response_model=list[SegmentSummaryOut])
async def get_segments_summary(db: AsyncSession = Depends(get_db)):
    sql = text("""
        WITH latest AS (
            SELECT DISTINCT ON (customer_id) *
            FROM segments
            ORDER BY customer_id, calculated_at DESC
        )
        SELECT segment_label, count(*) AS customer_count, avg(monetary) AS avg_monetary
        FROM latest
        GROUP BY segment_label
        ORDER BY customer_count DESC
    """)
    result = await db.execute(sql)
    return [SegmentSummaryOut(**row._mapping) for row in result]


@app.post("/rfm/recalculate", response_model=RecalculateOut)
async def recalculate_rfm(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text(RFM_SQL))
    inserted_rows = result.fetchall()
    rows_written = len(inserted_rows)
    run_at = inserted_rows[0].calculated_at if inserted_rows else datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

    distribution_result = await db.execute(
        text(
            "SELECT segment_label, count(*) AS customer_count "
            "FROM segments WHERE calculated_at = :run_at GROUP BY segment_label"
        ),
        {"run_at": run_at},
    )
    segment_distribution = {row.segment_label: row.customer_count for row in distribution_result}

    await db.execute(
        text(
            "INSERT INTO model_logs (model_name, run_at, parameters, metrics, notes) "
            "VALUES (:model_name, :run_at, CAST(:parameters AS jsonb), CAST(:metrics AS jsonb), :notes)"
        ),
        {
            "model_name": "rfm_ntile5",
            "run_at": run_at,
            "parameters": json.dumps({"ntile_buckets": 5}),
            "metrics": json.dumps({
                "customers_affected": rows_written,
                "segment_distribution": segment_distribution,
            }),
            "notes": "Manual recalculation via /rfm/recalculate endpoint",
        },
    )
    await db.commit()
    return RecalculateOut(rows_written=rows_written, run_at=run_at)


@app.get("/pipeline/status", response_model=PipelineStatusOut)
async def get_pipeline_status(logs_db: AsyncSession = Depends(get_logs_db)):
    sql = text("""
        WITH latest_run AS (
            SELECT dag_run_id FROM pipeline_runs ORDER BY started_at DESC LIMIT 1
        )
        SELECT dag_run_id, step_name, started_at, finished_at, customers_affected, status, error_message
        FROM pipeline_runs
        WHERE dag_run_id = (SELECT dag_run_id FROM latest_run)
        ORDER BY started_at ASC
    """)
    result = await logs_db.execute(sql)
    rows = result.fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="No pipeline runs logged yet")

    return PipelineStatusOut(
        dag_run_id=rows[0].dag_run_id,
        steps=[PipelineStepOut(**row._mapping) for row in rows],
    )


@app.get("/model/info", response_model=ModelInfoOut)
def get_model_info():
    try:
        mv = mlflow_client.get_model_version_by_alias(MLFLOW_MODEL_NAME, "production")
    except MlflowException:
        raise HTTPException(status_code=404, detail="No model registered with the 'production' alias")

    run = mlflow_client.get_run(mv.run_id)
    return ModelInfoOut(
        model_name=MLFLOW_MODEL_NAME,
        version=mv.version,
        stage=mv.tags.get("stage"),
        run_id=mv.run_id,
        metrics=run.data.metrics,
        params=run.data.params,
    )
