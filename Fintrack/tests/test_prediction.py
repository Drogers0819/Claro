from datetime import date, timedelta
from app.services.prediction_service import (
    predict_monthly_spending,
    calculate_budget_status,
    _linear_projection,
    _historical_prediction,
    _blend_predictions
)


class TestLinearProjection:

    def test_mid_month(self):
        result = _linear_projection(500, 15, 30)
        assert result["predicted_total"] == 1000
        assert result["daily_rate"] == 33.33
        assert result["confidence"] == 0.5

    def test_end_of_month(self):
        result = _linear_projection(900, 28, 30)
        assert result["predicted_total"] > 900
        assert result["confidence"] > 0.9

    def test_start_of_month(self):
        result = _linear_projection(50, 2, 30)
        assert result["predicted_total"] == 750
        assert result["confidence"] < 0.1

    def test_zero_days(self):
        result = _linear_projection(0, 0, 30)
        assert result["predicted_total"] == 0


class TestHistoricalPrediction:

    def test_with_data(self):
        months = {
            "2026-01": [{"amount": 800, "category": "Food"}],
            "2026-02": [{"amount": 900, "category": "Food"}],
            "2026-03": [{"amount": 850, "category": "Food"}]
        }
        result = _historical_prediction(months)
        assert result["predicted_total"] == 850
        assert result["months_used"] == 3
        assert result["confidence"] > 0

    def test_empty(self):
        result = _historical_prediction({})
        assert result["predicted_total"] == 0
        assert result["months_used"] == 0

    def test_single_month(self):
        months = {"2026-01": [{"amount": 500, "category": "Food"}]}
        result = _historical_prediction(months)
        assert result["predicted_total"] == 500
        assert result["months_used"] == 1


class TestBlendPredictions:

    def test_early_month_favours_historical(self):
        linear = {"predicted_total": 2000, "confidence": 0.1}
        historical = {"predicted_total": 1000, "confidence": 0.7}

        result = _blend_predictions(linear, historical, 2, 30, 3)
        assert result["method"] == "historical_only"

    def test_late_month_favours_linear(self):
        linear = {"predicted_total": 1200, "confidence": 0.9}
        historical = {"predicted_total": 1000, "confidence": 0.7}

        result = _blend_predictions(linear, historical, 25, 30, 3)
        assert result["predicted_total"] > 1100

    def test_no_historical(self):
        linear = {"predicted_total": 1000, "confidence": 0.5}
        historical = {"predicted_total": 0, "confidence": 0}

        result = _blend_predictions(linear, historical, 15, 30, 0)
        assert result["method"] == "linear_only"

    def test_mid_month_blends(self):
        linear = {"predicted_total": 1200, "confidence": 0.5}
        historical = {"predicted_total": 1000, "confidence": 0.7}

        result = _blend_predictions(linear, historical, 15, 30, 3)
        assert result["method"] == "blended"
        assert 1000 < result["predicted_total"] < 1200


class TestPredictMonthlySpending:

    def test_with_current_month_data(self):
        today = date.today()
        txns = [
            {"amount": 50, "type": "expense", "date": today, "category": "Food", "description": "Tesco"},
            {"amount": 30, "type": "expense", "date": today - timedelta(days=1), "category": "Transport", "description": "Uber"},
        ]

        result = predict_monthly_spending(txns, today)
        assert result["spending_so_far"]["total"] == 80
        assert result["predictions"]["blended"]["predicted_total"] > 0

    def test_with_historical_data(self):
        today = date.today()
        txns = []

        # Last month data
        last_month = today.replace(day=1) - timedelta(days=1)
        for i in range(10):
            txns.append({
                "amount": 50,
                "type": "expense",
                "date": last_month - timedelta(days=i),
                "category": "Food",
                "description": "Shop"
            })

        # Current month data
        txns.append({
            "amount": 100,
            "type": "expense",
            "date": today,
            "category": "Food",
            "description": "Big shop"
        })

        result = predict_monthly_spending(txns, today)
        assert result["historical_months_available"] >= 1
        assert result["spending_so_far"]["total"] == 100

    def test_empty_transactions(self):
        result = predict_monthly_spending([], date.today())
        assert result["spending_so_far"]["total"] == 0

    def test_income_excluded(self):
        today = date.today()
        txns = [
            {"amount": 1700, "type": "income", "date": today, "category": "Income", "description": "Salary"},
            {"amount": 50, "type": "expense", "date": today, "category": "Food", "description": "Tesco"},
        ]

        result = predict_monthly_spending(txns, today)
        assert result["spending_so_far"]["total"] == 50

    def test_category_predictions(self):
        today = date.today()
        txns = [
            {"amount": 80, "type": "expense", "date": today, "category": "Food", "description": "Shop"},
            {"amount": 20, "type": "expense", "date": today, "category": "Transport", "description": "Uber"},
        ]

        result = predict_monthly_spending(txns, today)
        cats = result["predictions"]["by_category"]
        assert len(cats) == 2

    def test_insight_generated(self):
        today = date.today()
        txns = [
            {"amount": 100, "type": "expense", "date": today, "category": "Food", "description": "Shop"}
        ]

        result = predict_monthly_spending(txns, today)
        assert result["insight"]["summary"] != ""
        assert result["insight"]["predicted_total"] > 0


class TestBudgetStatus:

    def test_healthy_status(self):
        predictions = {
            "predictions": {
                "blended": {"predicted_total": 200}
            }
        }
        user_profile = {"monthly_income": 1700, "fixed_commitments": 800}
        goals = [{"id": 1, "name": "Savings", "monthly_allocation": 400}]

        result = calculate_budget_status(predictions, user_profile, goals)
        assert result["status"] == "healthy"
        assert result["surplus_after_goals"] > 0

    def test_tight_status(self):
        predictions = {
            "predictions": {
                "blended": {"predicted_total": 500}
            }
        }
        user_profile = {"monthly_income": 1700, "fixed_commitments": 800}
        goals = [{"id": 1, "name": "Savings", "monthly_allocation": 500}]

        result = calculate_budget_status(predictions, user_profile, goals)
        assert result["status"] == "tight"

    def test_overspending_status(self):
        predictions = {
            "predictions": {
                "blended": {"predicted_total": 1200}
            }
        }
        user_profile = {"monthly_income": 1700, "fixed_commitments": 800}
        goals = [{"id": 1, "name": "Savings", "monthly_allocation": 400}]

        result = calculate_budget_status(predictions, user_profile, goals)
        assert result["status"] == "overspending"

    def test_no_goals(self):
        predictions = {
            "predictions": {
                "blended": {"predicted_total": 500}
            }
        }
        user_profile = {"monthly_income": 1700, "fixed_commitments": 800}

        result = calculate_budget_status(predictions, user_profile, [])
        assert result["status"] == "healthy"


class TestPredictionAPI:

    def test_monthly_prediction(self, auth_client):
        response = auth_client.get("/api/predictions/monthly")
        assert response.status_code == 200
        data = response.get_json()
        assert "current_month" in data
        assert "predictions" in data
        assert "spending_so_far" in data

    def test_budget_status_with_factfind(self, auth_client):
        auth_client.post("/api/profile/factfind", json={
            "monthly_income": 1700,
            "rent_amount": 800,
            "bills_amount": 0
        })

        response = auth_client.get("/api/predictions/budget-status")
        assert response.status_code == 200
        data = response.get_json()
        assert "budget_status" in data
        assert "predictions" in data

    def test_budget_status_without_factfind(self, auth_client):
        response = auth_client.get("/api/predictions/budget-status")
        assert response.status_code == 400

    def test_prediction_without_auth(self, client):
        response = client.get("/api/predictions/monthly")
        assert response.status_code == 401

    def test_budget_status_without_auth(self, client):
        response = client.get("/api/predictions/budget-status")
        assert response.status_code == 401