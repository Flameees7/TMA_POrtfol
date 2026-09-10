"""
Comprehensive End-to-End (E2E) Integration Test Suite for TMA Shop.
Verifies:
1. Database initialization and table schema
2. Google Sheets sync service with fallback seed & upsert
3. Product catalog API (GET /api/products, GET /api/products/{id})
4. Store requisites endpoint (GET /api/store/info)
5. Order checkout lifecycle:
   - Order creation (POST /api/orders)
   - Stock reservation status (reserved)
   - User order history (GET /api/orders/my)
   - Admin status update (PENDING -> ASSEMBLING -> IN_TRANSIT)
   - Customer receipt confirmation (PATCH /api/orders/{id}/received -> COMPLETED)
6. HMAC-SHA256 Telegram validation algorithm
7. Frontend static files serving
"""

import asyncio
import hashlib
import hmac
import json
import sys
import urllib.parse
import httpx
from sqlalchemy import select

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from backend.app.api.dependencies import verify_telegram_init_data
from backend.app.config import get_settings
from backend.app.database import AsyncSessionLocal, init_db
from backend.app.main import app
from backend.app.models.order import DeliveryType, Order, OrderStatus, PaymentMethod
from backend.app.models.product import Product
from backend.app.services.order_service import OrderService
from backend.app.services.sheets_sync import GoogleSheetsSyncService

settings = get_settings()


def generate_mock_telegram_init_data(user_id: int, first_name: str, username: str, bot_token: str) -> str:
    """Generates authentic Telegram WebApp initData string with valid HMAC-SHA256 signature."""
    user_data = {
        "id": user_id,
        "first_name": first_name,
        "username": username,
        "language_code": "ru"
    }
    user_json = json.dumps(user_data, separators=(',', ':'))
    auth_date = 1710000000

    params = {
        "auth_date": str(auth_date),
        "query_id": "AAHdF6IQAAAAAN0XohDZ2_K1",
        "user": user_json
    }

    # Sort keys
    sorted_items = sorted(params.items(), key=lambda x: x[0])
    data_check_string = "\n".join([f"{k}={v}" for k, v in sorted_items])

    # Calculate HMAC
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    data_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    params["hash"] = data_hash
    return urllib.parse.urlencode(params)


async def run_e2e_tests():
    print("================================================================")
    print(">> STARTING COMPREHENSIVE TMA SHOP E2E TEST SUITE")
    print("================================================================")

    # 1. Test Database Initialization
    print("\n[1/7] Testing Database initialization...")
    await init_db()
    print("[OK] Database tables created successfully.")

    # 2. Test Google Sheets Sync & Seed
    print("\n[2/7] Testing Google Sheets sync service and data seeding...")
    async with AsyncSessionLocal() as db:
        sync_report = await GoogleSheetsSyncService.sync_database(db)
        print(f"[OK] Sync result: {sync_report['status']}, Total items: {sync_report['total']}")

        products_res = await db.execute(select(Product))
        products = products_res.scalars().all()
        assert len(products) > 0, "No products found in database after sync!"
        test_product = products[0]
        print(f"[OK] Verified product in DB: '{test_product.title}' (Price: {test_product.price} RUB, Photos: {len(test_product.photo_list)})")

    # 3. Test HMAC-SHA256 Telegram InitData Validation
    print("\n[3/7] Testing Telegram HMAC-SHA256 Signature Verification...")
    test_token = "9876543210:AAHjkl_test_bot_token_12345"
    init_data = generate_mock_telegram_init_data(
        user_id=777000123,
        first_name="Алексей",
        username="alex_shopper",
        bot_token=test_token
    )
    auth_res = verify_telegram_init_data(init_data, test_token)
    assert auth_res.user.id == 777000123, "Telegram User ID mismatch in auth verification"
    assert auth_res.user.username == "alex_shopper", "Username mismatch in auth verification"
    print(f"[OK] HMAC-SHA256 verification passed for user: {auth_res.user.full_name} (@{auth_res.user.username})")

    # 4. Test REST API Endpoints with ASGITransport
    print("\n[4/7] Testing REST API Endpoints...")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 4.1 Healthcheck
        res = await client.get("/api/health")
        assert res.status_code == 200 and res.json()["status"] == "healthy"
        print("[OK] GET /api/health passed.")

        # 4.2 Products List & Search
        res = await client.get("/api/products?in_stock_only=true")
        assert res.status_code == 200
        products_json = res.json()
        assert len(products_json) > 0, "No products returned from API"
        target_product_id = products_json[0]["id"]
        print(f"[OK] GET /api/products passed: received {len(products_json)} available products.")

        # 4.3 Single Product Details
        res = await client.get(f"/api/products/{target_product_id}")
        assert res.status_code == 200
        assert res.json()["id"] == target_product_id
        print(f"[OK] GET /api/products/{target_product_id} passed: '{res.json()['title']}'")

        # 4.4 Store Info & Requisites
        res = await client.get("/api/store/info")
        assert res.status_code == 200
        store_info = res.json()
        assert "sbp_phone" in store_info and "crypto_usdt_ton_wallet" in store_info
        print(f"[OK] GET /api/store/info passed: SBP Bank: {store_info['sbp_bank']}, Pickup: {store_info['pickup_address'][:25]}...")

        # 5. Test Full Order Lifecycle
        print("\n[5/7] Testing Full Order Lifecycle (Creation, Reserve, Tracking, Completion)...")

        # 5.1 Create Order
        order_payload = {
            "product_id": target_product_id,
            "delivery_type": "delivery",
            "delivery_provider": "СДЭК",
            "delivery_address": "г. Санкт-Петербург, Невский пр. 25, ПВЗ 401",
            "customer_name": "Алексей Смирнов",
            "customer_phone": "+7 (911) 123-45-67",
            "payment_method": "sbp"
        }
        res = await client.post("/api/orders", json=order_payload)
        assert res.status_code == 201, f"Failed to create order: {res.text}"
        order_data = res.json()
        order_id = order_data["id"]
        order_num = order_data["order_number"]
        assert order_data["status"] == "pending"
        print(f"[OK] POST /api/orders passed: Created order {order_num} for product ID {target_product_id}.")

        # 5.2 Verify Stock Reservation
        async with AsyncSessionLocal() as db:
            prod_db = await db.get(Product, target_product_id)
            assert prod_db.stock_status == "reserved", "Product was not transitioned to 'reserved' state!"
            print(f"[OK] Product stock status correctly updated to: '{prod_db.stock_status}'.")

        # 5.3 User Order History
        res = await client.get("/api/orders/my")
        assert res.status_code == 200
        my_orders = res.json()
        assert any(o["id"] == order_id for o in my_orders), "New order not found in user's order history!"
        print(f"[OK] GET /api/orders/my passed: {len(my_orders)} orders in user history.")

        # 5.4 Admin Status Transition: PENDING -> ASSEMBLING -> IN_TRANSIT
        async with AsyncSessionLocal() as db:
            order_assembling = await OrderService.update_order_status(db, order_id, OrderStatus.ASSEMBLING)
            assert order_assembling.status == OrderStatus.ASSEMBLING
            print(f"[OK] Order status transitioned: {OrderStatus.PENDING.label_ru} -> {OrderStatus.ASSEMBLING.label_ru}")

            order_in_transit = await OrderService.update_order_status(db, order_id, OrderStatus.IN_TRANSIT)
            assert order_in_transit.status == OrderStatus.IN_TRANSIT
            print(f"[OK] Order status transitioned: {OrderStatus.ASSEMBLING.label_ru} -> {OrderStatus.IN_TRANSIT.label_ru}")

        # 5.5 Customer Receipt Confirmation (PATCH /api/orders/{id}/received)
        res = await client.patch(f"/api/orders/{order_id}/received")
        assert res.status_code == 200, f"Customer receipt confirmation failed: {res.text}"
        updated_order = res.json()
        assert updated_order["status"] == "completed"
        print(f"[OK] PATCH /api/orders/{order_id}/received passed: Order {order_num} successfully marked as '{updated_order['status_label']}'.")

        # 6. Test Frontend Static Asset Delivery
        print("\n[6/7] Testing Frontend Static Files Delivery...")
        res = await client.get("/")
        assert res.status_code == 200
        assert "PREMIUM STORE" in res.text
        print(f"[OK] GET / (index.html) passed (Size: {len(res.text)} bytes).")

        res = await client.get("/static/css/styles.css")
        assert res.status_code == 200
        print(f"[OK] GET /static/css/styles.css passed (Size: {len(res.text)} bytes).")

        res = await client.get("/static/js/app.js")
        assert res.status_code == 200
        print(f"[OK] GET /static/js/app.js passed (Size: {len(res.text)} bytes).")

    # 7. Final Check
    print("\n[7/7] Verifying Bot Routers & Dispatcher...")
    from backend.app.bot.bot_instance import get_dispatcher
    dispatcher = get_dispatcher()
    assert len(dispatcher.sub_routers) == 2, "Dispatcher missing user or admin sub-routers"
    print("[OK] Telegram Bot Dispatcher loaded 2 sub-routers (User Commands & Admin Order Actions).")

    print("\n================================================================")
    print("SUCCESS: ALL E2E INTEGRATION TESTS PASSED WITH 100% SUCCESS!")
    print("================================================================")


if __name__ == "__main__":
    asyncio.run(run_e2e_tests())
