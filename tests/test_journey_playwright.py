"""
Playwright JOURNEY TEST — Full E2E User Flow
User page → Add user → Products page → Add product → Orders page → Place order

This single test covers the complete user journey across all 3 pages.
Run with: pytest tests/test_journey_playwright.py -v -s
"""
import os
import time
import pytest
from playwright.sync_api import Page, expect

BASE_URL = os.getenv("SFCC_SITE_URL", "http://localhost:8000")


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright
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


class TestFullJourney:
    """End-to-end: Users → Products → Orders (UI + API)"""

    def test_complete_journey_ui(self, page: Page):
        """Full UI journey through all tabs with form submissions."""
        print("\n=== Full UI Journey ===")

        # Step 1: Load homepage
        page.goto(BASE_URL)
        expect(page).to_have_title("Mini E-Commerce")
        print("  Step 1: Homepage loaded")

        # Step 2: Create a user
        page.fill("#user-name", "Journey User")
        page.fill("#user-email", f"journey_{int(time.time())}@test.com")
        page.click("#user-form button")
        toast = page.locator("#toast")
        expect(toast).to_contain_text("User created", timeout=5000)
        expect(page.locator("#users-table")).to_contain_text("Journey User")
        print("  Step 2: User created")

        # Step 3: Navigate to Products tab
        page.click("#tab-products")
        page.wait_for_selector("#product-name", state="visible")
        print("  Step 3: Products tab loaded")

        # Step 4: Create a product
        page.fill("#product-name", "Journey Widget")
        page.fill("#product-desc", "Created during journey test")
        page.fill("#product-price", "29.99")
        page.fill("#product-stock", "50")
        page.click("#product-form button")
        expect(toast).to_contain_text("Product created", timeout=5000)
        expect(page.locator("#products-table")).to_contain_text("Journey Widget")
        print("  Step 4: Product created")

        # Step 5: Navigate to Orders tab
        page.click("#tab-orders")
        page.wait_for_selector("#order-user-id", state="visible")
        print("  Step 5: Orders tab loaded")

        # Step 6: Place an order
        page.fill("#order-user-id", "1")
        page.fill("#order-product-id", "1")
        page.fill("#order-quantity", "3")
        page.click("#order-form button")
        expect(toast).to_contain_text("Order placed", timeout=5000)
        print("  Step 6: Order placed")

        # Step 7: Verify order appears in table
        expect(page.locator("#orders-table")).to_contain_text("P1 x3")
        print("  Step 7: Order verified in table")

        print("  UI Journey COMPLETE!")

    def test_complete_journey_api(self, page: Page):
        """Full API journey: create user → product → order → verify → cleanup."""
        ctx = page.context.request
        print("\n=== Full API Journey ===")

        # Step 1: Create user
        user_resp = ctx.post(f"{BASE_URL}/users/", data={
            "name": "API Journey User",
            "email": f"api_journey_{int(time.time())}@test.com",
        })
        assert user_resp.status == 201
        user = user_resp.json()
        user_id = user["id"]
        print(f"  Step 1: Created user ID {user_id}")

        # Step 2: Create product
        product_resp = ctx.post(f"{BASE_URL}/products/", data={
            "name": "API Journey Product",
            "price": 19.99,
            "stock": 100,
        })
        assert product_resp.status == 201
        product = product_resp.json()
        product_id = product["id"]
        print(f"  Step 2: Created product ID {product_id}")

        # Step 3: Verify user and product exist
        assert ctx.get(f"{BASE_URL}/users/{user_id}").status == 200
        assert ctx.get(f"{BASE_URL}/products/{product_id}").status == 200
        print("  Step 3: Verified user and product exist")

        # Step 4: Place order
        order_resp = ctx.post(f"{BASE_URL}/orders/", data={
            "user_id": user_id,
            "items": [{"product_id": product_id, "quantity": 5}],
        })
        assert order_resp.status == 201
        order = order_resp.json()
        order_id = order["id"]
        assert order["user_id"] == user_id
        assert len(order["items"]) == 1
        assert order["items"][0]["quantity"] == 5
        print(f"  Step 4: Placed order ID {order_id}")

        # Step 5: Verify stock decreased
        updated_product = ctx.get(f"{BASE_URL}/products/{product_id}").json()
        assert updated_product["stock"] == 95
        print("  Step 5: Stock decreased from 100 to 95")

        # Step 6: List all orders
        orders = ctx.get(f"{BASE_URL}/orders/").json()
        assert any(o["id"] == order_id for o in orders)
        print(f"  Step 6: Order {order_id} found in orders list")

        # Step 7: Cleanup — delete order (restores stock)
        assert ctx.delete(f"{BASE_URL}/orders/{order_id}").status == 204
        restored = ctx.get(f"{BASE_URL}/products/{product_id}").json()
        assert restored["stock"] == 100
        print("  Step 7: Order deleted, stock restored to 100")

        # Step 8: Cleanup — delete product and user
        assert ctx.delete(f"{BASE_URL}/products/{product_id}").status == 204
        assert ctx.delete(f"{BASE_URL}/users/{user_id}").status == 204
        print("  Step 8: Cleanup complete")

        print("  API Journey COMPLETE!")

    def test_journey_performance(self, page: Page):
        """Measure total page navigation time across all tabs."""
        print("\n=== Journey Performance ===")

        start = time.time()

        # Navigate through all pages
        page.goto(BASE_URL)
        page.click("#tab-products")
        page.wait_for_selector("#product-name", state="visible")
        page.click("#tab-orders")
        page.wait_for_selector("#order-user-id", state="visible")
        page.click("#tab-users")
        page.wait_for_selector("#user-name", state="visible")

        total_ms = (time.time() - start) * 1000
        print(f"  Total navigation time: {total_ms:.0f}ms")
        assert total_ms < 10000, f"Journey took {total_ms:.0f}ms (threshold: 10000ms)"
        print("  Performance OK!")
