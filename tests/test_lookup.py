"""Tests for the OpenFoodFacts helper functions. No real network calls."""

from unittest.mock import MagicMock, patch

import pytest
import requests

import openfoodfacts


def fake_response(json_data):
    """Build a stand-in for a requests response."""
    response = MagicMock()
    response.json.return_value = json_data
    response.raise_for_status.return_value = None
    return response


def test_barcode_found():
    data = {
        "status": 1,
        "product": {
            "code": "3017620422003",
            "product_name": "Nutella",
            "brands": "Ferrero",
            "ingredients_text": "Sugar, palm oil",
        },
    }
    with patch("openfoodfacts.requests.get", return_value=fake_response(data)) as mock_get:
        result = openfoodfacts.lookup_by_barcode("3017620422003")

    assert result == {
        "barcode": "3017620422003",
        "product_name": "Nutella",
        "brands": "Ferrero",
        "ingredients_text": "Sugar, palm oil",
    }
    assert "3017620422003" in mock_get.call_args[0][0]


def test_barcode_not_found():
    with patch("openfoodfacts.requests.get", return_value=fake_response({"status": 0})):
        assert openfoodfacts.lookup_by_barcode("000") is None


def test_barcode_falls_back_to_given_barcode():
    data = {"status": 1, "product": {"product_name": "X"}}
    with patch("openfoodfacts.requests.get", return_value=fake_response(data)):
        result = openfoodfacts.lookup_by_barcode("999")
    assert result["barcode"] == "999"


def test_missing_fields_become_empty_strings():
    data = {"status": 1, "product": {"code": "1"}}
    with patch("openfoodfacts.requests.get", return_value=fake_response(data)):
        result = openfoodfacts.lookup_by_barcode("1")
    assert result["product_name"] == ""
    assert result["brands"] == ""
    assert result["ingredients_text"] == ""


def test_name_search_returns_first_match():
    data = {
        "products": [
            {
                "code": "123",
                "product_name": "Nutella",
                "brands": "Ferrero",
                "ingredients_text": "Sugar",
            }
        ]
    }
    with patch("openfoodfacts.requests.get", return_value=fake_response(data)) as mock_get:
        result = openfoodfacts.lookup_by_name("nutella")

    assert result["product_name"] == "Nutella"
    assert mock_get.call_args.kwargs["params"]["search_terms"] == "nutella"


def test_name_search_no_results():
    with patch("openfoodfacts.requests.get", return_value=fake_response({"products": []})):
        assert openfoodfacts.lookup_by_name("zzzz") is None


def test_http_error_is_raised():
    response = fake_response({})
    response.raise_for_status.side_effect = requests.HTTPError("500")
    with patch("openfoodfacts.requests.get", return_value=response):
        with pytest.raises(requests.HTTPError):
            openfoodfacts.lookup_by_barcode("123")


def test_connection_error_is_raised():
    with patch("openfoodfacts.requests.get", side_effect=requests.ConnectionError):
        with pytest.raises(requests.ConnectionError):
            openfoodfacts.lookup_by_name("nutella")


def test_lookup_product_prefers_barcode():
    with patch("openfoodfacts.lookup_by_barcode", return_value={"a": 1}) as by_barcode, \
         patch("openfoodfacts.lookup_by_name") as by_name:
        result = openfoodfacts.lookup_product(barcode="1", name="x")

    assert result == {"a": 1}
    by_barcode.assert_called_once_with("1")
    by_name.assert_not_called()


def test_lookup_product_uses_name_when_no_barcode():
    with patch("openfoodfacts.lookup_by_name", return_value={"b": 2}) as by_name:
        result = openfoodfacts.lookup_product(name="milk")

    assert result == {"b": 2}
    by_name.assert_called_once_with("milk")


def test_lookup_product_requires_input():
    with pytest.raises(ValueError):
        openfoodfacts.lookup_product()
