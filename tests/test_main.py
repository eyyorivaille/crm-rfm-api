import asyncio

import pytest
from fastapi.testclient import TestClient

from db import engine
from main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    asyncio.run(engine.dispose())


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
