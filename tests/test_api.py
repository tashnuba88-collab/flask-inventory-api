"""Tests for the Flask inventory API routes."""

import copy
from unittest.mock import patch

import pytest
import requests

import app as app_module


@pytest.fixture(autouse=True)
def reset_data():
    """Restore the mock inventory after every test so tests don't affect each other."""
    original = copy.deepcopy(app_module.inventory)
    original_next_id = app_module.next_id
    yield
    app_module.inventory[:] = original
    app_module.next_id = original_next_id


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


# GET /inventory

def test_get_all_items(client):
    response = client.get("/inventory")
    assert response.status_code == 200
    assert len(response.get_json()) == 2


# GET /inventory/<id>

def test_get_one_item(client):
    response = client.get("/inventory/1")
    assert response.status_code == 200
    assert response.get_json()["product_name"] == "Organic Almond Milk"


def test_get_missing_item_returns_404(client):
    response = client.get("/inventory/999")
    assert response.status_code == 404
    assert "error" in response.get_json()


# POST /inventory

def test_add_item(client):
    response = client.post(
        "/inventory", json={"product_name": "Oat Milk", "price": 4.5, "stock": 10}
    )
    assert response.status_code == 201
    assert response.get_json()["id"] == 3
    assert len(client.get("/inventory").get_json()) == 3


def test_add_item_requires_product_name(client):
    response = client.post("/inventory", json={"price": 1.0})
    assert response.status_code == 400


def test_add_item_ignores_client_supplied_id(client):
    response = client.post("/inventory", json={"product_name": "Rice", "id": 99})
    assert response.get_json()["id"] == 3


def test_ids_are_not_reused_after_delete(client):
    client.post("/inventory", json={"product_name": "First"})
    client.delete("/inventory/3")
    response = client.post("/inventory", json={"product_name": "Second"})
    assert response.get_json()["id"] == 4


# PATCH /inventory/<id>

def test_update_item_changes_only_given_fields(client):
    response = client.patch("/inventory/1", json={"stock": 5})
    data = response.get_json()
    assert response.status_code == 200
    assert data["stock"] == 5
    assert data["product_name"] == "Organic Almond Milk"


def test_update_missing_item_returns_404(client):
    response = client.patch("/inventory/999", json={"stock": 5})
    assert response.status_code == 404


def test_update_with_empty_body_returns_400(client):
    response = client.patch("/inventory/1", json={})
    assert response.status_code == 400


# DELETE /inventory/<id>

def test_delete_item(client):
    response = client.delete("/inventory/1")
    assert response.status_code == 200
    assert client.get("/inventory/1").status_code == 404


def test_delete_missing_item_returns_404(client):
    response = client.delete("/inventory/999")
    assert response.status_code == 404


# GET /inventory/lookup (OpenFoodFacts is mocked, so no internet is needed)

def test_lookup_by_barcode(client):
    fake = {"barcode": "123", "product_name": "Fake", "brands": "B", "ingredients_text": "x"}
    with patch("app.lookup_product", return_value=fake) as mock_lookup:
        response = client.get("/inventory/lookup?barcode=123")
    assert response.status_code == 200
    assert response.get_json()["product_name"] == "Fake"
    mock_lookup.assert_called_once_with(barcode="123", name=None)


def test_lookup_without_parameters_returns_400(client):
    response = client.get("/inventory/lookup")
    assert response.status_code == 400


def test_lookup_not_found_returns_404(client):
    with patch("app.lookup_product", return_value=None):
        response = client.get("/inventory/lookup?name=nothing")
    assert response.status_code == 404


def test_lookup_network_failure_returns_502(client):
    with patch("app.lookup_product", side_effect=requests.ConnectionError):
        response = client.get("/inventory/lookup?barcode=123")
    assert response.status_code == 502
