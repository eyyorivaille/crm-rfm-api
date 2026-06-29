import asyncio

import pytest
from fastapi.testclient import TestClient

from db import engine
from logs_db import logs_engine
from main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    asyncio.run(engine.dispose())
    asyncio.run(logs_engine.dispose())


def test_get_customer_segment_found(client):
    response = client.get("/customers/12636/segment")
    assert response.status_code == 200
    body = response.json()
    assert body["customer_id"] == "12636"
    assert "segment_label" in body


def test_get_customer_segment_not_found(client):
    response = client.get("/customers/99999999/segment")
    assert response.status_code == 404


def test_segments_summary(client):
    response = client.get("/segments/summary")
    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    assert {"segment_label", "customer_count", "avg_monetary"} <= body[0].keys()


def test_rfm_recalculate(client):
    response = client.post("/rfm/recalculate")
    assert response.status_code == 200
    body = response.json()
    assert body["rows_written"] > 0


def test_model_info(client):
    response = client.get("/model/info")
    assert response.status_code == 200
    body = response.json()
    assert body["model_name"] == "rfm-customer-segments"
    assert body["stage"] == "Production"
    assert "silhouette" in body["metrics"]


def test_pipeline_status(client):
    response = client.get("/pipeline/status")
    assert response.status_code == 200
    body = response.json()
    assert "dag_run_id" in body
    assert len(body["steps"]) > 0
    assert {"step_name", "started_at", "status"} <= body["steps"][0].keys()
