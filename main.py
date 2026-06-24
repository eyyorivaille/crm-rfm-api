import datetime
import json
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models import Segment
from schemas import RecalculateOut, SegmentOut, SegmentSummaryOut

app = FastAPI()

RFM_SQL = (Path(__file__).parent / "sql" / "rfm_scoring.sql").read_text()


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
    rows_written = result.rowcount
    run_at = datetime.datetime.utcnow()

    await db.execute(
        text(
            "INSERT INTO model_logs (model_name, run_at, parameters, metrics, notes) "
            "VALUES (:model_name, :run_at, CAST(:parameters AS jsonb), CAST(:metrics AS jsonb), :notes)"
        ),
        {
            "model_name": "rfm_ntile5",
            "run_at": run_at,
            "parameters": json.dumps({"ntile_buckets": 5}),
            "metrics": json.dumps({"rows_written": rows_written}),
            "notes": "Manual recalculation via /rfm/recalculate endpoint",
        },
    )
    await db.commit()
    return RecalculateOut(rows_written=rows_written, run_at=run_at)
