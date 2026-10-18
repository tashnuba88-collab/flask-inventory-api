# Flask Inventory API

A small inventory management system for an e-commerce admin portal. It has a Flask REST API with CRUD routes, a lookup route that pulls product details from the OpenFoodFacts API, a menu-driven command line interface, and a pytest suite.

Inventory is stored in a Python list in memory, so it resets every time the server restarts.

## Project structure

- `app.py`: Flask routes and the mock inventory list
- `openfoodfacts.py`: functions that query the OpenFoodFacts API
- `cli.py`: menu-driven command line interface that talks to the API
- `tests/test_api.py`: tests for the API routes
- `tests/test_lookup.py`: tests for the OpenFoodFacts functions
- `tests/test_cli.py`: tests for the CLI
- `pytest.ini`: tells pytest where to find the source files
- `requirements.txt`: Python dependencies

## Installation and setup

You need Python 3.

```
git clone https://github.com/tashnuba88-collab/flask-inventory-api.git
cd flask-inventory-api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the API

```
python app.py
```

The server runs at `http://127.0.0.1:5000` in debug mode. Leave this terminal open while you use the CLI.

## API endpoints

Each item has an `id`, `barcode`, `product_name`, `brands`, `ingredients_text`, `price`, and `stock`.

- `GET /inventory` returns all items.
- `GET /inventory/<id>` returns one item, or 404 if the id does not exist.
- `POST /inventory` adds an item from a JSON body. `product_name` is required. Returns the new item with status 201. The server assigns the id.
- `PATCH /inventory/<id>` updates only the fields in the JSON body. Returns the updated item, or 404 if the id does not exist.
- `DELETE /inventory/<id>` removes an item. Returns a confirmation message, or 404 if the id does not exist.
- `GET /inventory/lookup?barcode=<code>` or `GET /inventory/lookup?name=<text>` searches OpenFoodFacts and returns the product's barcode, name, brand, and ingredients. It returns 400 if neither parameter is given, 404 if no product is found, and 502 if OpenFoodFacts cannot be reached.

Errors come back as JSON in the form `{"error": "message"}`.

Example requests:

```
curl http://127.0.0.1:5000/inventory

curl -X POST http://127.0.0.1:5000/inventory \
  -H "Content-Type: application/json" \
  -d '{"product_name": "Oat Milk", "price": 4.5, "stock": 10}'

curl -X PATCH http://127.0.0.1:5000/inventory/1 \
  -H "Content-Type: application/json" \
  -d '{"stock": 5}'

curl -X DELETE http://127.0.0.1:5000/inventory/1

curl "http://127.0.0.1:5000/inventory/lookup?barcode=3017620422003"
```

## Using the CLI

With the API running, open a second terminal, activate the virtual environment, and run:

```
python cli.py
```

The menu looks like this:

```
1. List all items
2. View one item
3. Add an item
4. Update an item
5. Delete an item
6. Look up a product on OpenFoodFacts
7. Quit
```

Examples:

- Option 1 prints every item in the inventory.
- Option 3 asks for each field. Press Return to skip a field. Only the product name is required.
- Option 4 asks for an item id, then for the fields to change. Blank fields are left as they are.
- Option 6 asks whether to search by barcode or name. After showing the result, it offers to add the product to inventory or merge its barcode, brand, and ingredients into an existing item.

Lookups need an internet connection. Name searches on OpenFoodFacts can be slow, and barcode lookups are faster. Try the barcode `3017620422003` for a quick test.

## Running the tests

```
python -m pytest -v
```

The tests do not need the server running or an internet connection. OpenFoodFacts requests and keyboard input are mocked with `unittest.mock`. They cover all five API routes, the lookup route and its error cases, the OpenFoodFacts functions, and every CLI menu option.