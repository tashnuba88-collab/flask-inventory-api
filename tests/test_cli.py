"""Tests for the menu-driven CLI. The API and keyboard input are mocked."""

from unittest.mock import MagicMock, patch

import pytest
import requests

import cli


def make_response(status=200, json_data=None):
    """Build a stand-in for a requests response."""
    response = MagicMock()
    response.status_code = status
    response.ok = status < 400
    response.json.return_value = json_data if json_data is not None else {}
    return response


@pytest.fixture
def feed(monkeypatch):
    """Return a function that queues up typed answers for input()."""

    def _feed(*answers):
        answer_iter = iter(answers)
        monkeypatch.setattr("builtins.input", lambda prompt="": next(answer_iter))

    return _feed


PRODUCT = {
    "barcode": "123",
    "product_name": "Nutella",
    "brands": "Ferrero",
    "ingredients_text": "Sugar",
}


# Helpers

def test_api_request_handles_unreachable_api(capsys):
    with patch("cli.requests.request", side_effect=requests.ConnectionError):
        result = cli.api_request("GET", "/inventory")
    assert result is None
    assert "Could not reach the API" in capsys.readouterr().out


def test_read_id_rejects_non_numbers(feed, capsys):
    feed("abc")
    assert cli.read_id() is None
    assert "whole number" in capsys.readouterr().out


def test_read_id_accepts_numbers(feed):
    feed("5")
    assert cli.read_id() == 5


# Options 1 to 5

def test_list_items_shows_items(capsys):
    items = [{"id": 1, "product_name": "Organic Almond Milk"}]
    with patch("cli.api_request", return_value=make_response(200, items)):
        cli.list_items()
    assert "Organic Almond Milk" in capsys.readouterr().out


def test_list_items_empty(capsys):
    with patch("cli.api_request", return_value=make_response(200, [])):
        cli.list_items()
    assert "Inventory is empty." in capsys.readouterr().out


def test_view_item_not_found(feed, capsys):
    feed("999")
    response = make_response(404, {"error": "Item not found"})
    with patch("cli.api_request", return_value=response):
        cli.view_item()
    assert "Error 404: Item not found" in capsys.readouterr().out


def test_add_item_requires_a_name(feed, capsys):
    feed("", "", "", "", "", "")
    with patch("cli.api_request") as mock_api:
        cli.add_item()
    mock_api.assert_not_called()
    assert "product name is required" in capsys.readouterr().out


def test_add_item_sends_post(feed):
    feed("Oat Milk", "", "", "", "4.5", "10")
    created = make_response(201, {"id": 3, "product_name": "Oat Milk"})
    with patch("cli.api_request", return_value=created) as mock_api:
        cli.add_item()
    mock_api.assert_called_once_with(
        "POST", "/inventory", json={"product_name": "Oat Milk", "price": 4.5, "stock": 10}
    )


def test_update_item_sends_only_filled_fields(feed):
    feed("1", "", "", "", "", "", "5")
    updated = make_response(200, {"id": 1, "stock": 5})
    with patch("cli.api_request", return_value=updated) as mock_api:
        cli.update_item()
    mock_api.assert_called_once_with("PATCH", "/inventory/1", json={"stock": 5})


def test_delete_item_cancelled(feed, capsys):
    feed("1", "n")
    with patch("cli.api_request") as mock_api:
        cli.delete_item()
    mock_api.assert_not_called()
    assert "Cancelled." in capsys.readouterr().out


def test_delete_item_confirmed(feed):
    feed("1", "y")
    deleted = make_response(200, {"message": "Item 1 deleted"})
    with patch("cli.api_request", return_value=deleted) as mock_api:
        cli.delete_item()
    mock_api.assert_called_once_with("DELETE", "/inventory/1")


# Option 6: OpenFoodFacts lookup

def test_lookup_by_barcode_then_skip(feed):
    feed("b", "123", "s")
    with patch("cli.api_request", return_value=make_response(200, PRODUCT)) as mock_api:
        cli.lookup_product_menu()
    mock_api.assert_called_once_with(
        "GET", "/inventory/lookup", params={"barcode": "123"}
    )


def test_lookup_then_add_to_inventory(feed):
    feed("b", "123", "a", "", "")
    responses = [make_response(200, PRODUCT), make_response(201, {"id": 3, **PRODUCT})]
    with patch("cli.api_request", side_effect=responses) as mock_api:
        cli.lookup_product_menu()

    post_call = mock_api.call_args_list[1]
    assert post_call.args == ("POST", "/inventory")
    assert post_call.kwargs == {"json": PRODUCT}


def test_lookup_then_merge_into_existing_item(feed):
    feed("n", "nutella", "m", "2")
    responses = [make_response(200, PRODUCT), make_response(200, {"id": 2})]
    with patch("cli.api_request", side_effect=responses) as mock_api:
        cli.lookup_product_menu()

    patch_call = mock_api.call_args_list[1]
    assert patch_call.args == ("PATCH", "/inventory/2")
    # product_name is not merged, only the extra details.
    assert patch_call.kwargs == {
        "json": {"barcode": "123", "brands": "Ferrero", "ingredients_text": "Sugar"}
    }


def test_lookup_not_found(feed, capsys):
    feed("b", "000")
    response = make_response(404, {"error": "Product not found on OpenFoodFacts"})
    with patch("cli.api_request", return_value=response) as mock_api:
        cli.lookup_product_menu()
    assert mock_api.call_count == 1
    assert "Error 404" in capsys.readouterr().out


# Menu loop

def test_main_quits(feed, capsys):
    feed("7")
    cli.main()
    assert "Goodbye." in capsys.readouterr().out


def test_main_rejects_invalid_choice(feed, capsys):
    feed("9", "7")
    cli.main()
    assert "Please choose a number from 1 to 7." in capsys.readouterr().out


def test_main_runs_chosen_option(feed):
    feed("1", "7")
    with patch("cli.list_items") as mock_list:
        cli.main()
    mock_list.assert_called_once()
