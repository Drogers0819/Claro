from datetime import date
from app.services.insight_service import (
    generate_page_insights,
    generate_daily_digest,
    generate_month_end_summary
)


class TestOverviewInsight:

    def test_money_left_healthy(self):
        data = {
            "money_left": 340,
            "days_remaining": 14,
            "budget_statuses": [],
            "primary_goal": {"name": "House deposit", "progress_percent": 31}
        }
        result = generate_page_insights("overview", data)
        assert "340" in result["whisper"]
        assert "24" in result["whisper"]
        assert "House deposit" in result["whisper"]

    def test_money_left_overspent(self):
        data = {
            "money_left": -45,
            "days_remaining": 8,
            "budget_statuses": [],
            "primary_goal": {}
        }
        result = generate_page_insights("overview", data)
        assert "45" in result["whisper"]
        assert "more than planned" in result["whisper"]

    def test_budget_exceeded_shown(self):
        data = {
            "money_left": 200,
            "days_remaining": 10,
            "budget_statuses": [
                {"category_name": "Food", "status": "exceeded", "remaining": -20}
            ],
            "primary_goal": {}
        }
        result = generate_page_insights("overview", data)
        assert "Food" in result["whisper"]
        assert "over" in result["whisper"]

    def test_budget_warning_shown(self):
        data = {
            "money_left": 200,
            "days_remaining": 10,
            "budget_statuses": [
                {"category_name": "Transport", "status": "warning", "remaining": 15}
            ],
            "primary_goal": {}
        }
        result = generate_page_insights("overview", data)
        assert "Transport" in result["whisper"]
        assert "15" in result["whisper"]

    def test_goal_shown_when_no_budget_problems(self):
        data = {
            "money_left": 500,
            "days_remaining": 20,
            "budget_statuses": [
                {"category_name": "Food", "status": "on_track", "remaining": 100}
            ],
            "primary_goal": {"name": "Holiday", "progress_percent": 65}
        }
        result = generate_page_insights("overview", data)
        assert "Holiday" in result["whisper"]
        assert "65%" in result["whisper"]

    def test_no_profile(self):
        data = {"user_name": "Sarah"}
        result = generate_page_insights("overview", data)
        assert "Sarah" in result["whisper"]
        assert "get started" in result["whisper"]

    def test_empty_data(self):
        result = generate_page_insights("overview", {})
        assert "whisper" in result
        assert len(result["whisper"]) > 0


class TestMyMoneyInsight:

    def test_spending_with_comparison_high(self):
        data = {
            "predictions": {
                "spending_so_far": {"total": 580, "transaction_count": 23},
                "comparison": {"status": "spending_high", "difference": 40}
            }
        }
        result = generate_page_insights("my_money", data)
        assert "580" in result["whisper"]
        assert "23" in result["whisper"]
        assert "40" in result["whisper"]

    def test_spending_below_average(self):
        data = {
            "predictions": {
                "spending_so_far": {"total": 400, "transaction_count": 15},
                "comparison": {"status": "spending_low", "difference": -60}
            }
        }
        result = generate_page_insights("my_money", data)
        assert "less than usual" in result["whisper"]

    def test_no_data(self):
        data = {"predictions": {}}
        result = generate_page_insights("my_money", data)
        assert "Upload" in result["whisper"]


class TestMyGoalsInsight:

    def test_with_progress(self):
        data = {
            "goals": [
                {"name": "House deposit", "status": "active", "progress_percent": 31}
            ],
            "waterfall": {"conflicts": [], "unallocated": 0},
            "projections": [
                {"goal_name": "House deposit", "reachable": True,
                 "months_to_target": 36, "completion_date_human": "March 2029"}
            ]
        }
        result = generate_page_insights("my_goals", data)
        assert "31%" in result["whisper"]
        assert "March 2029" in result["whisper"]

    def test_no_goals(self):
        data = {"goals": [], "waterfall": {}, "projections": []}
        result = generate_page_insights("my_goals", data)
        assert "haven't set" in result["whisper"]

    def test_conflict(self):
        data = {
            "goals": [{"name": "Test", "status": "active", "progress_percent": 10}],
            "waterfall": {"conflicts": [{"type": "insufficient"}], "unallocated": 0},
            "projections": []
        }
        result = generate_page_insights("my_goals", data)
        assert "more than you have" in result["whisper"]

    def test_unallocated(self):
        data = {
            "goals": [{"name": "Test", "status": "active", "progress_percent": 10}],
            "waterfall": {"conflicts": [], "unallocated": 150},
            "projections": []
        }
        result = generate_page_insights("my_goals", data)
        assert "150" in result["whisper"]


class TestMyBudgetsInsight:

    def test_exceeded(self):
        data = {
            "budget_statuses": [
                {"category_name": "Food", "status": "exceeded", "remaining": -20, "percent_used": 110},
                {"category_name": "Transport", "status": "on_track", "remaining": 30, "percent_used": 40}
            ],
            "recurring": {"count": 0, "total_monthly_cost": 0},
            "days_remaining": 10
        }
        result = generate_page_insights("my_budgets", data)
        assert "Food" in result["whisper"]
        assert "over" in result["whisper"]
        assert "1 other" in result["whisper"] or "other" in result["whisper"]

    def test_warning(self):
        data = {
            "budget_statuses": [
                {"category_name": "Food", "status": "warning", "remaining": 15,
                 "daily_remaining": 1.50, "percent_used": 88}
            ],
            "recurring": {"count": 0, "total_monthly_cost": 0},
            "days_remaining": 10
        }
        result = generate_page_insights("my_budgets", data)
        assert "15" in result["whisper"]
        assert "1.50" in result["whisper"]

    def test_all_on_track(self):
        data = {
            "budget_statuses": [
                {"category_name": "Food", "status": "on_track", "remaining": 65,
                 "daily_remaining": 5.42, "percent_used": 68},
                {"category_name": "Transport", "status": "on_track", "remaining": 30,
                 "daily_remaining": 2.50, "percent_used": 40}
            ],
            "recurring": {"count": 0, "total_monthly_cost": 0},
            "days_remaining": 12
        }
        result = generate_page_insights("my_budgets", data)
        assert "on track" in result["whisper"]

    def test_no_budgets_with_recurring(self):
        data = {
            "budget_statuses": [],
            "recurring": {"count": 5, "total_monthly_cost": 120},
            "days_remaining": 10
        }
        result = generate_page_insights("my_budgets", data)
        assert "5" in result["whisper"]
        assert "120" in result["whisper"]

    def test_no_budgets_no_recurring(self):
        data = {
            "budget_statuses": [],
            "recurring": {"count": 0, "total_monthly_cost": 0},
            "days_remaining": 10
        }
        result = generate_page_insights("my_budgets", data)
        assert "Set" in result["whisper"]


class TestSettingsInsight:

    def test_with_data(self):
        data = {"total_transactions": 45, "active_goals": 3}
        result = generate_page_insights("settings", data)
        assert "45" in result["whisper"]
        assert "3" in result["whisper"]

    def test_empty(self):
        data = {}
        result = generate_page_insights("settings", data)
        assert "theme" in result["whisper"].lower()


class TestFallback:

    def test_unknown_page(self):
        result = generate_page_insights("nonexistent", {})
        assert result["page"] == "unknown"


class TestDailyDigest:

    def test_with_data(self):
        data = {
            "money_left": 340,
            "days_remaining": 14,
            "budget_statuses": [
                {"category_name": "Food", "status": "warning", "remaining": 15}
            ],
            "goals": [
                {"name": "House deposit", "status": "active", "progress_percent": 31}
            ]
        }
        result = generate_daily_digest(data)
        assert result["section_count"] >= 2

    def test_budget_exceeded_flagged(self):
        data = {
            "budget_statuses": [
                {"category_name": "Food", "status": "exceeded", "remaining": -20}
            ],
            "goals": []
        }
        result = generate_daily_digest(data)
        assert result["has_alerts"] is True

    def test_empty(self):
        data = {"budget_statuses": [], "goals": []}
        result = generate_daily_digest(data)
        assert result["section_count"] == 0


class TestMonthEndSummary:

    def test_above_average(self):
        data = {
            "predictions": {
                "spending_so_far": {"total": 1200},
                "comparison": {"historical_average": 1000, "difference": 200}
            },
            "goals": [], "budget_statuses": [], "recurring": {}
        }
        result = generate_month_end_summary(data)
        assert "more" in result["spending_verdict"]

    def test_below_average(self):
        data = {
            "predictions": {
                "spending_so_far": {"total": 800},
                "comparison": {"historical_average": 1000, "difference": -200}
            },
            "goals": [], "budget_statuses": [], "recurring": {}
        }
        result = generate_month_end_summary(data)
        assert "less" in result["spending_verdict"]

    def test_empty(self):
        data = {
            "predictions": {"spending_so_far": {}, "comparison": {}},
            "goals": [], "budget_statuses": [], "recurring": {}
        }
        result = generate_month_end_summary(data)
        assert "spending_verdict" in result


class TestInsightAPI:

    def test_page_insight(self, auth_client):
        response = auth_client.get("/api/insights/page/overview")
        assert response.status_code == 200
        data = response.get_json()
        assert "whisper" in data

    def test_daily_digest(self, auth_client):
        response = auth_client.get("/api/insights/digest")
        assert response.status_code == 200
        data = response.get_json()
        assert "sections" in data

    def test_month_summary(self, auth_client):
        response = auth_client.get("/api/insights/month-summary")
        assert response.status_code == 200
        data = response.get_json()
        assert "spending_verdict" in data

    def test_unknown_page(self, auth_client):
        response = auth_client.get("/api/insights/page/nonexistent")
        assert response.status_code == 200
        assert response.get_json()["page"] == "unknown"

    def test_without_auth(self, client):
        response = client.get("/api/insights/page/overview")
        assert response.status_code == 401