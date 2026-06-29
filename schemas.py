import datetime
import decimal

from pydantic import BaseModel, ConfigDict


class SegmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: str
    recency: int
    frequency: int
    monetary: decimal.Decimal
    rfm_score: str
    segment_label: str
    calculated_at: datetime.datetime


class SegmentSummaryOut(BaseModel):
    segment_label: str
    customer_count: int
    avg_monetary: decimal.Decimal


class RecalculateOut(BaseModel):
    rows_written: int
    run_at: datetime.datetime


class ModelInfoOut(BaseModel):
    model_name: str
    version: str
    stage: str | None
    run_id: str
    metrics: dict[str, float]
    params: dict[str, str]
