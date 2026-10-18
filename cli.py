"""Menu-driven command line interface for the inventory API."""

import requests

BASE_URL = "http://127.0.0.1:5000"

MENU = """
Inventory Manager
1. List all items
2. View one item
3. Add an item
4. Update an item
5. Delete an item
6. Look up a product on OpenFoodFacts
7. Quit
"""

# Fields copied from an OpenFoodFacts result into an existing item.
MERGE_FIELDS = ("barcode", "brands", "ingredients_text")


def api_request(method, path, **kwargs):
    """Send a request to the API. Return the response, or None if unreachable."""
    try:
        return requests.request(method, f"{BASE_URL}{path}", timeout=40, **kwargs)
    except requests.RequestException:
        print("Could not reach the API. Is app.py running?")
        return None


def report_error(response):
    """Print the error message from a failed response."""
    try:
        message = response.json().get("error", response.text)
    except ValueError:
        message = response.text
    print(f"Error {response.status_code}: {message}")


def show_item(item):
    """Print one item on a few lines."""
    print(f"\nID: {item.get('id', '-')}")
    print(f"  Name: {item.get('product_name', '')}")
    print(f"  Brand: {item.get('brands', '')}")
    print(f"  Barcode: {item.get('barcode', '')}")
    print(f"  Ingredients: {item.get('ingredients_text', '')}")
    print(f"  Price: {item.get('price', '')}   Stock: {item.get('stock', '')}")


def read_number(prompt, cast):
    """Read a number. Return None if left blank or invalid."""
    raw = input(prompt).strip()
    if raw == "":
        return None
    try:
        return cast(raw)
    except ValueError:
        print("That is not a valid number, skipping it.")
        return None


def read_id():
    """Ask for an item id. Return None if it is not a whole number."""
    raw = input("Item ID: ").strip()
    if not raw.isdigit():
        print("The ID must be a whole number.")
        return None
    return int(raw)


def prompt_for_fields():
    """Ask for item fields. Blank answers are left out."""
    fields = {}
    questions = (
        ("product_name", "Product name: "),
        ("barcode", "Barcode: "),
        ("brands", "Brand: "),
        ("ingredients_text", "Ingredients: "),
    )
    for key, prompt in questions:
        value = input(prompt).strip()
        if value:
            fields[key] = value

    price = read_number("Price: ", float)
    if price is not None:
        fields["price"] = price
    stock = read_number("Stock: ", int)
    if stock is not None:
        fields["stock"] = stock
    return fields


def list_items():
    """Menu option 1: GET /inventory."""
    response = api_request("GET", "/inventory")
    if response is None:
        return
    if not response.ok:
        report_error(response)
        return

    items = response.json()
    if not items:
        print("Inventory is empty.")
    for item in items:
        show_item(item)


def view_item():
    """Menu option 2: GET /inventory/<id>."""
    item_id = read_id()
    if item_id is None:
        return
    response = api_request("GET", f"/inventory/{item_id}")
    if response is None:
        return
    if response.ok:
        show_item(response.json())
    else:
        report_error(response)


def add_item():
    """Menu option 3: POST /inventory."""
    print("Leave a field blank to skip it.")
    fields = prompt_for_fields()
    if "product_name" not in fields:
        print("A product name is required.")
        return

    response = api_request("POST", "/inventory", json=fields)
    if response is None:
        return
    if response.status_code == 201:
        print("Item added.")
        show_item(response.json())
    else:
        report_error(response)


def update_item():
    """Menu option 4: PATCH /inventory/<id>."""
    item_id = read_id()
    if item_id is None:
        return

    print("Leave a field blank to keep its current value.")
    fields = prompt_for_fields()
    if not fields:
        print("Nothing to update.")
        return

    response = api_request("PATCH", f"/inventory/{item_id}", json=fields)
    if response is None:
        return
    if response.ok:
        print("Item updated.")
        show_item(response.json())
    else:
        report_error(response)


def delete_item():
    """Menu option 5: DELETE /inventory/<id>."""
    item_id = read_id()
    if item_id is None:
        return

    confirm = input(f"Delete item {item_id}? (y/n): ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return

    response = api_request("DELETE", f"/inventory/{item_id}")
    if response is None:
        return
    if response.ok:
        print(response.json().get("message", "Item deleted."))
    else:
        report_error(response)


def add_lookup_result(product):
    """Add an OpenFoodFacts result to inventory with a price and stock."""
    data = dict(product)
    price = read_number("Price: ", float)
    if price is not None:
        data["price"] = price
    stock = read_number("Stock: ", int)
    if stock is not None:
        data["stock"] = stock

    response = api_request("POST", "/inventory", json=data)
    if response is None:
        return
    if response.status_code == 201:
        print("Item added.")
        show_item(response.json())
    else:
        report_error(response)


def merge_lookup_result(product):
    """Copy OpenFoodFacts details into an existing item."""
    item_id = read_id()
    if item_id is None:
        return

    data = {key: product[key] for key in MERGE_FIELDS if product.get(key)}
    if not data:
        print("The lookup result had no extra details to merge.")
        return

    response = api_request("PATCH", f"/inventory/{item_id}", json=data)
    if response is None:
        return
    if response.ok:
        print("Item updated with OpenFoodFacts details.")
        show_item(response.json())
    else:
        report_error(response)


def lookup_product_menu():
    """Menu option 6: GET /inventory/lookup, then optionally save the result."""
    choice = input("Search by (b)arcode or (n)ame? ").strip().lower()
    if choice == "b":
        params = {"barcode": input("Barcode: ").strip()}
    elif choice == "n":
        params = {"name": input("Product name: ").strip()}
    else:
        print("Please enter b or n.")
        return

    if not list(params.values())[0]:
        print("Nothing entered.")
        return

    response = api_request("GET", "/inventory/lookup", params=params)
    if response is None:
        return
    if not response.ok:
        report_error(response)
        return

    product = response.json()
    show_item(product)

    action = input(
        "\n(a)dd to inventory, (m)erge into an existing item, or (s)kip? "
    ).strip().lower()
    if action == "a":
        add_lookup_result(product)
    elif action == "m":
        merge_lookup_result(product)


def main():
    """Run the menu loop until the user quits."""
    actions = {
        "1": list_items,
        "2": view_item,
        "3": add_item,
        "4": update_item,
        "5": delete_item,
        "6": lookup_product_menu,
    }

    while True:
        print(MENU)
        choice = input("Choose an option (1-7): ").strip()
        if choice == "7":
            print("Goodbye.")
            break
        action = actions.get(choice)
        if action is None:
            print("Please choose a number from 1 to 7.")
        else:
            action()


if __name__ == "__main__":
    main()
