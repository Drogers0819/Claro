class TestCreateTransaction:

    def test_create_transaction_success(self, auth_client):
        response = auth_client.post("/api/transactions", json={
            "amount": 45.99,
            "description": "Tesco weekly shop",
            "category_id": 1,
            "type": "expense",
            "date": "2026-03-25",
            "merchant": "Tesco"
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["transaction"]["amount"] == 45.99
        assert data["transaction"]["description"] == "Tesco weekly shop"
        assert data["transaction"]["category"] == "Food"
        assert data["transaction"]["type"] == "expense"

    def test_create_transaction_without_auth(self, client):
        response = client.post("/api/transactions", json={
            "amount": 50,
            "description": "Test",
            "type": "expense",
            "date": "2026-03-25"
        })
        assert response.status_code == 401

    def test_create_transaction_missing_description(self, auth_client):
        response = auth_client.post("/api/transactions", json={
            "amount": 50,
            "type": "expense",
            "date": "2026-03-25"
        })
        assert response.status_code == 400

    def test_create_transaction_invalid_type(self, auth_client):
        response = auth_client.post("/api/transactions", json={
            "amount": 50,
            "description": "Test",
            "type": "transfer",
            "date": "2026-03-25"
        })
        assert response.status_code == 400

    def test_create_transaction_negative_amount(self, auth_client):
        response = auth_client.post("/api/transactions", json={
            "amount": -50,
            "description": "Test",
            "type": "expense",
            "date": "2026-03-25"
        })
        assert response.status_code == 400

    def test_create_transaction_invalid_date(self, auth_client):
        response = auth_client.post("/api/transactions", json={
            "amount": 50,
            "description": "Test",
            "type": "expense",
            "date": "not-a-date"
        })
        assert response.status_code == 400

    def test_create_transaction_default_category(self, auth_client):
        response = auth_client.post("/api/transactions", json={
            "amount": 50,
            "description": "Test transaction",
            "type": "expense",
            "date": "2026-03-25"
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["transaction"]["category"] == "Other"

    def test_create_transaction_invalid_category(self, auth_client):
        response = auth_client.post("/api/transactions", json={
            "amount": 50,
            "description": "Test",
            "category_id": 9999,
            "type": "expense",
            "date": "2026-03-25"
        })
        assert response.status_code == 400


class TestListTransactions:

    def test_list_transactions_empty(self, auth_client):
        response = auth_client.get("/api/transactions")
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 0
        assert data["transactions"] == []

    def test_list_transactions_with_data(self, auth_client):
        auth_client.post("/api/transactions", json={
            "amount": 100, "description": "First",
            "type": "expense", "date": "2026-03-20"
        })
        auth_client.post("/api/transactions", json={
            "amount": 200, "description": "Second",
            "type": "income", "date": "2026-03-25"
        })

        response = auth_client.get("/api/transactions")
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 2

    def test_list_transactions_without_auth(self, client):
        response = client.get("/api/transactions")
        assert response.status_code == 401


class TestGetTransaction:

    def test_get_transaction_success(self, auth_client):
        create_response = auth_client.post("/api/transactions", json={
            "amount": 75, "description": "Test item",
            "type": "expense", "date": "2026-03-25"
        })
        transaction_id = create_response.get_json()["transaction"]["id"]

        response = auth_client.get(f"/api/transactions/{transaction_id}")
        assert response.status_code == 200
        assert response.get_json()["transaction"]["description"] == "Test item"

    def test_get_transaction_not_found(self, auth_client):
        response = auth_client.get("/api/transactions/9999")
        assert response.status_code == 404


class TestDeleteTransaction:

    def test_delete_transaction_success(self, auth_client):
        create_response = auth_client.post("/api/transactions", json={
            "amount": 50, "description": "To delete",
            "type": "expense", "date": "2026-03-25"
        })
        transaction_id = create_response.get_json()["transaction"]["id"]

        delete_response = auth_client.delete(f"/api/transactions/{transaction_id}")
        assert delete_response.status_code == 200

        get_response = auth_client.get(f"/api/transactions/{transaction_id}")
        assert get_response.status_code == 404

    def test_delete_transaction_not_found(self, auth_client):
        response = auth_client.delete("/api/transactions/9999")
        assert response.status_code == 404


class TestDashboard:

    def test_dashboard_empty(self, auth_client):
        response = auth_client.get("/api/dashboard")
        assert response.status_code == 200
        data = response.get_json()
        assert data["summary"]["total_income"] == 0
        assert data["summary"]["total_expenses"] == 0
        assert data["summary"]["balance"] == 0
        assert data["summary"]["transaction_count"] == 0
        assert data["recent_transactions"] == []

    def test_dashboard_with_data(self, auth_client):
        auth_client.post("/api/transactions", json={
            "amount": 1700, "description": "Salary",
            "type": "income", "date": "2026-03-01"
        })
        auth_client.post("/api/transactions", json={
            "amount": 800, "description": "Rent",
            "type": "expense", "date": "2026-03-01"
        })
        auth_client.post("/api/transactions", json={
            "amount": 45.99, "description": "Groceries",
            "type": "expense", "date": "2026-03-15"
        })

        response = auth_client.get("/api/dashboard")
        assert response.status_code == 200
        data = response.get_json()
        assert data["summary"]["total_income"] == 1700
        assert data["summary"]["total_expenses"] == 845.99
        assert data["summary"]["balance"] == 854.01
        assert data["summary"]["transaction_count"] == 3
        assert len(data["recent_transactions"]) == 3

    def test_dashboard_without_auth(self, client):
        response = client.get("/api/dashboard")
        assert response.status_code == 401


class TestCategories:

    def test_list_categories(self, auth_client):
        response = auth_client.get("/api/categories")
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] >= 5
        names = [c["name"] for c in data["categories"]]
        assert "Food" in names
        assert "Other" in names

    def test_list_categories_without_auth(self, client):
        response = client.get("/api/categories")
        assert response.status_code == 401
