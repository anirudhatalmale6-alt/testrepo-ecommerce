"""
Playwright UI tests for the Mini E-Commerce app.
Requires the app to be running at http://localhost:8000
Run with: pytest tests/test_ui_playwright.py
"""
import pytest
from playwright.sync_api import sync_playwright, Page, expect

BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="module")
def browser():
    pw = sync_playwright().start()
    br = pw.chromium.launch(headless=True)
    yield br
    br.close()
    pw.stop()


@pytest.fixture
def page(browser):
    pg = browser.new_page()
    yield pg
    pg.close()


def wait_toast(page: Page, text_fragment: str):
    toast = page.locator("#toast")
    expect(toast).to_contain_text(text_fragment, timeout=5000)


# -- Users -------------------------------------------------------------------

def test_page_loads(page: Page):
    page.goto(BASE_URL)
    expect(page).to_have_title("Mini E-Commerce")


def test_create_user(page: Page):
    page.goto(BASE_URL)
    page.fill("#user-name", "Alice")
    page.fill("#user-email", "alice-pw@example.com")
    page.click("#user-form button")
    wait_toast(page, "User created")
    expect(page.locator("#users-table")).to_contain_text("Alice")


def test_delete_user(page: Page):
    page.goto(BASE_URL)
    page.fill("#user-name", "ToDelete")
    page.fill("#user-email", "todelete-pw@example.com")
    page.click("#user-form button")
    wait_toast(page, "User created")

    del_buttons = page.locator("#users-table .btn-del")
    del_buttons.last.click()
    wait_toast(page, "User deleted")


# -- Products ----------------------------------------------------------------

def test_create_product(page: Page):
    page.goto(BASE_URL)
    page.click("#tab-products")
    page.wait_for_selector("#product-name", state="visible")

    page.fill("#product-name", "Widget")
    page.fill("#product-desc", "A nice widget")
    page.fill("#product-price", "9.99")
    page.fill("#product-stock", "100")
    page.click("#product-form button")
    wait_toast(page, "Product created")
    expect(page.locator("#products-table")).to_contain_text("Widget")


def test_delete_product(page: Page):
    page.goto(BASE_URL)
    page.click("#tab-products")
    page.wait_for_selector("#product-name", state="visible")

    page.fill("#product-name", "Temp Product")
    page.fill("#product-price", "1.00")
    page.fill("#product-stock", "10")
    page.click("#product-form button")
    wait_toast(page, "Product created")

    del_buttons = page.locator("#products-table .btn-del")
    del_buttons.last.click()
    wait_toast(page, "Product deleted")


# -- Orders ------------------------------------------------------------------

def test_create_order(page: Page):
    """Assumes user ID 1 and product ID 1 exist from previous tests."""
    page.goto(BASE_URL)
    page.click("#tab-orders")
    page.wait_for_selector("#order-user-id", state="visible")

    page.fill("#order-user-id", "1")
    page.fill("#order-product-id", "1")
    page.fill("#order-quantity", "2")
    page.click("#order-form button")
    wait_toast(page, "Order placed")
    expect(page.locator("#orders-table")).to_contain_text("P1 x2")


def test_delete_order(page: Page):
    page.goto(BASE_URL)
    page.click("#tab-orders")
    page.wait_for_selector("#order-user-id", state="visible")

    del_buttons = page.locator("#orders-table .btn-del")
    if del_buttons.count() > 0:
        del_buttons.last.click()
        wait_toast(page, "Order deleted")


# -- API-level tests (Playwright APIRequestContext) ---------------------------

def test_api_create_and_list_users(page: Page):
    ctx = page.context.request
    resp = ctx.post(f"{BASE_URL}/users/", data={"name": "ApiUser", "email": "apiuser-pw@test.com"})
    assert resp.status == 201
    body = resp.json()
    assert body["name"] == "ApiUser"

    resp = ctx.get(f"{BASE_URL}/users/")
    assert resp.status == 200
    users = resp.json()
    assert any(u["name"] == "ApiUser" for u in users)


def test_api_create_product(page: Page):
    ctx = page.context.request
    resp = ctx.post(f"{BASE_URL}/products/", data={
        "name": "API Widget", "price": 5.99, "stock": 50
    })
    assert resp.status == 201
    assert resp.json()["name"] == "API Widget"


def test_api_create_order(page: Page):
    ctx = page.context.request
    user = ctx.post(f"{BASE_URL}/users/", data={"name": "OrderUser", "email": "orderuser-pw@test.com"}).json()
    product = ctx.post(f"{BASE_URL}/products/", data={"name": "OrderItem", "price": 1.0, "stock": 10}).json()

    resp = ctx.post(f"{BASE_URL}/orders/", data={
        "user_id": user["id"],
        "items": [{"product_id": product["id"], "quantity": 2}]
    })
    assert resp.status == 201
    order = resp.json()
    assert order["user_id"] == user["id"]
    assert len(order["items"]) == 1
