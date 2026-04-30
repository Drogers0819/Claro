from datetime import date, timedelta
from app.services.budget_service import calculate_budget_status, suggest_budgets


class TestCalculateBudgetStatus:

    def test_on_track(self):
        budgets = [{
            "id": 1, "category_name": "Food", "category_icon": "🍕",
            "category_colour": "#E07A5F", "monthly_limit": 200,
            "is_active": True
        }]
        transactions = [{
            "amount": 20, "category": "Food", "type": "expense",
            "date": date.today()
        }]

        result = calculate_budget_status(budgets, transactions)
        assert result["budgets"][0]["status"] in ("on_track", "ahead_of_pace")
        assert result["budgets"][0]["spent"] == 20
        assert result["budgets"][0]["remaining"] == 180

    def test_exceeded(self):
        budgets = [{
            "id": 1, "category_name": "Food", "category_icon": "🍕",
            "category_colour": "#E07A5F", "monthly_limit": 100,
            "is_active": True
        }]
        transactions = [{
            "amount": 120, "category": "Food", "type": "expense",
            "date": date.today()
        }]

        result = calculate_budget_status(budgets, transactions)
        assert result["budgets"][0]["status"] == "exceeded"
        assert result["budgets"][0]["remaining"] == -20

    def test_warning(self):
        budgets = [{
            "id": 1, "category_name": "Food", "category_icon": "🍕",
            "category_colour": "#E07A5F", "monthly_limit": 100,
            "is_active": True
        }]
        transactions = [{
            "amount": 90, "category": "Food", "type": "expense",
            "date": date.today()
        }]

        result = calculate_budget_status(budgets, transactions)
        assert result["budgets"][0]["status"] == "warning"

    def test_multiple_budgets(self):
        budgets = [
            {"id": 1, "category_name": "Food", "category_icon": "🍕",
             "category_colour": "#E07A5F", "monthly_limit": 200, "is_active": True},
            {"id": 2, "category_name": "Transport", "category_icon": "🚌",
             "category_colour": "#3D85C6", "monthly_limit": 50, "is_active": True}
        ]
        transactions = [
            {"amount": 80, "category": "Food", "type": "expense", "date": date.today()},
            {"amount": 30, "category": "Transport", "type": "expense", "date": date.today()}
        ]

        result = calculate_budget_status(budgets, transactions)
        assert result["summary"]["budget_count"] == 2
        assert result["summary"]["total_budgeted"] == 250
        assert result["summary"]["total_spent"] == 110

    def test_empty_budgets(self):
        result = calculate_budget_status([], [])
        assert result["summary"]["budget_count"] == 0

    def test_ignores_income(self):
        budgets = [{
            "id": 1, "category_name": "Food", "category_icon": "🍕",
            "category_colour": "#E07A5F", "monthly_limit": 200,
            "is_active": True
        }]
        transactions = [
            {"amount": 50, "category": "Food", "type": "expense", "date": date.today()},
            {"amount": 1700, "category": "Income", "type": "income", "date": date.today()}
        ]

        result = calculate_budget_status(budgets, transactions)
        assert result["budgets"][0]["spent"] == 50

    def test_ignores_previous_month(self):
        budgets = [{
            "id": 1, "category_name": "Food", "category_icon": "🍕",
            "category_colour": "#E07A5F", "monthly_limit": 200,
            "is_active": True
        }]

        last_month = date.today().replace(day=1) - timedelta(days=1)
        transactions = [
            {"amount": 150, "category": "Food", "type": "expense", "date": last_month},
            {"amount": 50, "category": "Food", "type": "expense", "date": date.today()}
        ]

        result = calculate_budget_status(budgets, transactions)
        assert result["budgets"][0]["spent"] == 50

    def test_daily_remaining(self):
        # Pin to mid-month so daily_remaining is always > 0
        # (on the last day of the month, days_remaining is 0 and the value is 0).
        fixed_date = date(2026, 4, 15)
        budgets = [{
            "id": 1, "category_name": "Food", "category_icon": "🍕",
            "category_colour": "#E07A5F", "monthly_limit": 300,
            "is_active": True
        }]
        transactions = [{
            "amount": 100, "category": "Food", "type": "expense",
            "date": fixed_date
        }]

        result = calculate_budget_status(budgets, transactions, current_date=fixed_date)
        assert result["budgets"][0]["daily_remaining"] > 0

    def test_alerts_generated(self):
        budgets = [{
            "id": 1, "category_name": "Food", "category_icon": "🍕",
            "category_colour": "#E07A5F", "monthly_limit": 100,
            "is_active": True
        }]
        transactions = [{
            "amount": 110, "category": "Food", "type": "expense",
            "date": date.today()
        }]

        result = calculate_budget_status(budgets, transactions)
        assert len(result["alerts"]) >= 1
        assert result["alerts"][0]["severity"] == "high"

    def test_insight_generated(self):
        budgets = [{
            "id": 1, "category_name": "Food", "category_icon": "🍕",
            "category_colour": "#E07A5F", "monthly_limit": 200,
            "is_active": True
        }]
        transactions = [{
            "amount": 80, "category": "Food", "type": "expense",
            "date": date.today()
        }]

        result = calculate_budget_status(budgets, transactions)
        assert result["budgets"][0]["insight"] != ""

    def test_inactive_budget_ignored(self):
        budgets = [{
            "id": 1, "category_name": "Food", "category_icon": "🍕",
            "category_colour": "#E07A5F", "monthly_limit": 200,
            "is_active": False
        }]
        transactions = [{
            "amount": 80, "category": "Food", "type": "expense",
            "date": date.today()
        }]

        result = calculate_budget_status(budgets, transactions)
        assert result["summary"]["budget_count"] == 0


class TestSuggestBudgets:

    def test_suggests_from_history(self):
        last_month = date.today().replace(day=1) - timedelta(days=1)
        two_months_ago = last_month.replace(day=1) - timedelta(days=1)

        transactions = [
            {"amount": 200, "category": "Food", "type": "expense", "date": last_month},
            {"amount": 180, "category": "Food", "type": "expense", "date": two_months_ago},
            {"amount": 50, "category": "Transport", "type": "expense", "date": last_month},
            {"amount": 60, "category": "Transport", "type": "expense", "date": two_months_ago}
        ]

        result = suggest_budgets(transactions)
        assert len(result["suggestions"]) >= 1
        food = next((s for s in result["suggestions"] if s["category"] == "Food"), None)
        assert food is not None
        assert food["suggested_limit"] > food["average_monthly"]

    def test_excludes_current_month(self):
        transactions = [
            {"amount": 200, "category": "Food", "type": "expense", "date": date.today()}
        ]

        result = suggest_budgets(transactions)
        assert len(result["suggestions"]) == 0

    def test_excludes_income(self):
        last_month = date.today().replace(day=1) - timedelta(days=1)
        transactions = [
            {"amount": 1700, "category": "Income", "type": "income", "date": last_month}
        ]

        result = suggest_budgets(transactions)
        assert len(result["suggestions"]) == 0

    def test_empty_transactions(self):
        result = suggest_budgets([])
        assert len(result["suggestions"]) == 0


class TestBudgetAPI:

    def test_create_budget(self, auth_client):
        response = auth_client.post("/api/budgets", json={
            "category_id": 1,
            "monthly_limit": 200
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["budget"]["monthly_limit"] == 200

    def test_create_budget_duplicate(self, auth_client):
        auth_client.post("/api/budgets", json={
            "category_id": 1, "monthly_limit": 200
        })
        response = auth_client.post("/api/budgets", json={
            "category_id": 1, "monthly_limit": 300
        })
        assert response.status_code == 409

    def test_create_budget_invalid_limit(self, auth_client):
        response = auth_client.post("/api/budgets", json={
            "category_id": 1, "monthly_limit": -50
        })
        assert response.status_code == 400

    def test_list_budgets(self, auth_client):
        auth_client.post("/api/budgets", json={
            "category_id": 1, "monthly_limit": 200
        })

        response = auth_client.get("/api/budgets")
        assert response.status_code == 200
        assert response.get_json()["count"] == 1

    def test_update_budget(self, auth_client):
        create = auth_client.post("/api/budgets", json={
            "category_id": 1, "monthly_limit": 200
        })
        budget_id = create.get_json()["budget"]["id"]

        response = auth_client.put(f"/api/budgets/{budget_id}", json={
            "monthly_limit": 250
        })
        assert response.status_code == 200
        assert response.get_json()["budget"]["monthly_limit"] == 250

    def test_delete_budget(self, auth_client):
        create = auth_client.post("/api/budgets", json={
            "category_id": 1, "monthly_limit": 200
        })
        budget_id = create.get_json()["budget"]["id"]

        response = auth_client.delete(f"/api/budgets/{budget_id}")
        assert response.status_code == 200

    def test_budget_status(self, auth_client):
        auth_client.post("/api/budgets", json={
            "category_id": 1, "monthly_limit": 200
        })

        response = auth_client.get("/api/budgets/status")
        assert response.status_code == 200
        data = response.get_json()
        assert "budgets" in data
        assert "summary" in data
        assert "alerts" in data

    def test_budget_suggestions(self, auth_client):
        response = auth_client.get("/api/budgets/suggestions")
        assert response.status_code == 200
        assert "suggestions" in response.get_json()

    def test_budget_without_auth(self, client):
        response = client.get("/api/budgets")
        assert response.status_code == 401

    def test_budget_status_empty(self, auth_client):
        response = auth_client.get("/api/budgets/status")
        assert response.status_code == 200
        assert response.get_json()["summary"]["budget_count"] == 0
