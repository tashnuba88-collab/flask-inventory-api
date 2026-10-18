"""Helpers for fetching product details from the OpenFoodFacts API."""

import requests

BASE_URL = "https://world.openfoodfacts.org"

# OpenFoodFacts asks API users to identify their app with a User-Agent.
HEADERS = {"User-Agent": "flask-inventory-api/1.0 (student project)"}


def _simplify(product, fallback_barcode=None):
    """Keep only the fields our inventory cares about."""
    return {
        "barcode": product.get("code") or fallback_barcode,
        "product_name": product.get("product_name", ""),
        "brands": product.get("brands", ""),
        "ingredients_text": product.get("ingredients_text", ""),
    }


def lookup_by_barcode(barcode):
    """Return simplified product details for a barcode, or None if not found."""
    url = f"{BASE_URL}/api/v2/product/{barcode}.json"
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()
    data = response.json()

    # OpenFoodFacts sets status to 1 when the product exists.
    if data.get("status") != 1:
        return None
    return _simplify(data["product"], fallback_barcode=barcode)


def lookup_by_name(name):
    """Return simplified details for the top search match, or None."""
    url = f"{BASE_URL}/cgi/search.pl"
    params = {
        "search_terms": name,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 1,
    }
    response = requests.get(url, params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()
    products = response.json().get("products", [])

    if not products:
        return None
    return _simplify(products[0])


def lookup_product(barcode=None, name=None):
    """Look up a product by barcode if given, otherwise by name."""
    if barcode:
        return lookup_by_barcode(barcode)
    if name:
        return lookup_by_name(name)
    raise ValueError("Provide a barcode or a name")
