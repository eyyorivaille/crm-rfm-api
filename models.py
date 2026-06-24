import datetime
import decimal

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(primary_key=True)
    country: Mapped[str | None]
    first_seen: Mapped[datetime.date | None]
    created_at: Mapped[datetime.datetime | None]


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[str]
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"))
    stock_code: Mapped[str]
    description: Mapped[str | None]
    quantity: Mapped[int]
    invoice_date: Mapped[datetime.datetime]
    unit_price: Mapped[decimal.Decimal]


class Segment(Base):
    __tablename__ = "segments"

    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"), primary_key=True)
    recency: Mapped[int]
    frequency: Mapped[int]
    monetary: Mapped[decimal.Decimal]
    rfm_score: Mapped[str]
    segment_label: Mapped[str]
    calculated_at: Mapped[datetime.datetime] = mapped_column(primary_key=True)


class ModelLog(Base):
    __tablename__ = "model_logs"

    log_id: Mapped[int] = mapped_column(primary_key=True)
    model_name: Mapped[str]
    run_at: Mapped[datetime.datetime]
    parameters: Mapped[dict | None] = mapped_column(JSONB)
    metrics: Mapped[dict | None] = mapped_column(JSONB)
    notes: Mapped[str | None]
