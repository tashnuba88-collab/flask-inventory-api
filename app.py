"""Flask REST API for a simple inventory management system."""

import requests
from flask import Flask, jsonify, request

from openfoodfacts import lookup_product

app = Flask(__name__)

# Simulated database: a list of dictionaries, each with a unique id.
inventory = [
    {
        "id": 1,
        "barcode": "1111111111111",
        "product_name": "Organic Almond Milk",
        "brands": "Silk",
        "ingredients_text": "Filtered water, almonds, cane sugar",
        "price": 3.99,
        "stock": 24,
    },
    {
        "id": 2,
        "barcode": "2222222222222",
        "product_name": "Whole Wheat Bread",
        "brands": "Daily Loaf",
        "ingredients_text": "Whole wheat flour, water, yeast, salt",
        "price": 2.49,
        "stock": 40,
    },
]

# Next id to hand out. Tracked separately so ids are never reused after a delete.
next_id = 3

# Fields a client is allowed to set on an item.
ALLOWED_FIELDS = {
    "barcode",
    "product_name",
    "brands",
    "ingredients_text",
    "price",
    "stock",
}


def find_item(item_id):
    """Return the item with this id, or None."""
    for item in inventory:
        if item["id"] == item_id:
            return item
    return None


def error(message, status):
    """Build a consistent JSON error response."""
    return jsonify({"error": message}), status


@app.route("/inventory", methods=["GET"])
def get_inventory():
    """Return every item."""
    return jsonify(inventory), 200


@app.route("/inventory/lookup", methods=["GET"])
def lookup():
    """Look up product details on OpenFoodFacts by barcode or name."""
    barcode = request.args.get("barcode")
    name = request.args.get("name")

    if not barcode and not name:
        return error("Provide a barcode or name query parameter", 400)

    try:
        product = lookup_product(barcode=barcode, name=name)
    except requests.RequestException:
        return error("Could not reach OpenFoodFacts", 502)

    if product is None:
        return error("Product not found on OpenFoodFacts", 404)
    return jsonify(product), 200


@app.route("/inventory/<int:item_id>", methods=["GET"])
def get_item(item_id):
    """Return a single item."""
    item = find_item(item_id)
    if item is None:
        return error("Item not found", 404)
    return jsonify(item), 200


@app.route("/inventory", methods=["POST"])
def add_item():
    """Create a new item from the JSON body."""
    global next_id

    data = request.get_json(silent=True)
    if not data or not data.get("product_name"):
        return error("product_name is required", 400)

    # Keep only known fields so clients can't inject an id or extras.
    item = {key: value for key, value in data.items() if key in ALLOWED_FIELDS}
    item["id"] = next_id
    next_id += 1

    inventory.append(item)
    return jsonify(item), 201


@app.route("/inventory/<int:item_id>", methods=["PATCH"])
def update_item(item_id):
    """Update only the fields supplied in the JSON body."""
    item = find_item(item_id)
    if item is None:
        return error("Item not found", 404)

    data = request.get_json(silent=True)
    if not data:
        return error("Request body must be JSON", 400)

    for key, value in data.items():
        if key in ALLOWED_FIELDS:
            item[key] = value

    return jsonify(item), 200


@app.route("/inventory/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    """Remove an item."""
    item = find_item(item_id)
    if item is None:
        return error("Item not found", 404)

    inventory.remove(item)
    return jsonify({"message": f"Item {item_id} deleted"}), 200


if __name__ == "__main__":
    # Debug mode reloads on changes and shows tracebacks.
    app.run(debug=True)