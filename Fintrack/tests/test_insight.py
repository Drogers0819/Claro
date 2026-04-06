from datetime import date
from app.services.insight_service import (
    generate_page_insights,
    generate_daily_digest,
    generate_month_end_summary
)


class TestOverviewInsight:

    def test_with_money_left(self):
        data = {
            "money_left": 340,
            "days_remaining": 14,
            "predictions": {},
            "budget_status": {},
            "primary_goal": {"name": "House deposit", "progress_percent": 31},
            "anomalies": {"anomalies": []}
        }

        result = generate_page_insights("overview", data)
        assert "340" in result["whisper"]
        assert "14" in result["whisper"]
        assert result["page"] == "overview"

    def test_overspending(self):
        data = {
            "money_left": -50,
            "days_remaining": 10,
            "predictions": {},
            "budget_status": {"status": "overspending", "message": "Over budget"},
            "primary_goal": {},
            "anomalies": {"anomalies": []}
        }

        result = generate_page_insights("overview", data)
        assert result["priority"] == "overspending"

    def test_with_goal_progress(self):
        data = {
            "money_left": 500,
            "days_remaining": 20,
            "predictions": {},
            "budget_status": {},
            "primary_goal": {"name": "Holiday", "progress_percent": 65},
            "anomalies": {"anomalies": []}
        }

        result = generate_page_insights("overview", data)
        assert "Holiday" in result["whisper"]
        assert "65%" in result["whisper"]

    def test_with_anomaly(self):
        data = {
            "money_left": 300,
            "days_remaining": 15,
            "predictions": {},
            "budget_status": {},
            "primary_goal": {},
            "anomalies": {
                "anomalies": [
                    {"severity": "high", "message": "Unusual £500 at Amazon"}
                ]
            }
        }

        result = generate_page_insights("overview", data)
        assert "Amazon" in result["whisper"]

    def test_empty_data(self):
        data = {"user_name": "Sarah"}

        result = generate_page_insights("overview", data)
        assert "whisper" in result
        assert len(result["whisper"]) > 0

    def test_no_money_left(self):
        data = {}

        result = generate_page_insights("overview", data)
        assert "whisper" in result


class TestMyMoneyInsight:

    def test_with_spending(self):
        data = {
            "predictions": {
                "spending_so_far": {"total": 580, "transaction_count": 23},
                "comparison": {"status": "spending_high", "difference": 40},
                "predictions": {"by_category": []}
            },
            "trends": []
        }

        result = generate_page_insights("my_money", data)
        assert "580" in result["whisper"]
        assert "23" in result["whisper"]

    def test_below_average(self):
        data = {
            "predictions": {
                "spending_so_far": {"total": 400, "transaction_count": 15},
                "comparison": {"status": "spending_low", "difference": -60},
                "predictions": {"by_category": []}
            },
            "trends": []
        }

        result = generate_page_insights("my_money", data)
        assert "less" in result["whisper"].lower()

    def test_category_spike(self):
        data = {
            "predictions": {
                "spending_so_far": {"total": 500, "transaction_count": 20},
                "comparison": {"status": "on_track"},
                "predictions": {
                    "by_category": [
                        {"category": "Food", "status": "above_average", "pace_vs_average": 25}
                    ]
                }
            },
            "trends": []
        }

        result = generate_page_insights("my_money", data)
        assert "Food" in result["whisper"]

    def test_empty(self):
        data = {"predictions": {}, "trends": []}

        result = generate_page_insights("my_money", data)
        assert "Upload" in result["whisper"]


class TestMyGoalsInsight:

    def test_with_goals(self):
        data = {
            "goals": [
                {"name": "House deposit", "status": "active", "progress_percent": 31},
                {"name": "Holiday", "status": "active", "progress_percent": 50}
            ],
            "waterfall": {"conflicts": [], "unallocated": 0},
            "projections": []
        }

        result = generate_page_insights("my_goals", data)
        assert "2 active goals" in result["whisper"]
        assert "House deposit" in result["whisper"]

    def test_no_goals(self):
        data = {"goals": [], "waterfall": {}, "projections": []}

        result = generate_page_insights("my_goals", data)
        assert "haven't set" in result["whisper"]

    def test_with_conflicts(self):
        data = {
            "goals": [{"name": "Test", "status": "active", "progress_percent": 10}],
            "waterfall": {"conflicts": [{"type": "insufficient"}], "unallocated": 0},
            "projections": []
        }

        result = generate_page_insights("my_goals", data)
        assert result["priority"] == "attention"

    def test_with_projection(self):
        data = {
            "goals": [{"name": "Holiday", "status": "active", "progress_percent": 40}],
            "waterfall": {"conflicts": [], "unallocated": 0},
            "projections": [
                {"goal_name": "Holiday", "reachable": True,
                 "months_to_target": 6, "completion_date_human": "October 2026"}
            ]
        }

        result = generate_page_insights("my_goals", data)
        assert "October 2026" in result["whisper"]

    def test_unallocated_surplus(self):
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
                {"category_name": "Food", "status": "exceeded", "percent_used": 110, "remaining": -20}
            ],
            "recurring": {"count": 0, "total_monthly_cost": 0},
            "savings_opportunities": {"count": 0},
            "days_remaining": 10
        }

        result = generate_page_insights("my_budgets", data)
        assert "exceeded" in result["whisper"]
        assert result["priority"] == "high"

    def test_all_on_track(self):
        data = {
            "budget_statuses": [
                {"category_name": "Food", "status": "on_track", "percent_used": 40, "remaining": 120}
            ],
            "recurring": {"count": 3, "total_monthly_cost": 45},
            "savings_opportunities": {"count": 0},
            "days_remaining": 15
        }

        result = generate_page_insights("my_budgets", data)
        assert "on track" in result["whisper"]

    def test_no_budgets_with_recurring(self):
        data = {
            "budget_statuses": [],
            "recurring": {"count": 5, "total_monthly_cost": 120},
            "savings_opportunities": {"count": 0},
            "days_remaining": 10
        }

        result = generate_page_insights("my_budgets", data)
        assert "120" in result["whisper"]
        assert "5" in result["whisper"]

    def test_with_savings(self):
        data = {
            "budget_statuses": [
                {"category_name": "Food", "status": "on_track", "percent_used": 50, "remaining": 100}
            ],
            "recurring": {"count": 0, "total_monthly_cost": 0},
            "savings_opportunities": {"count": 2, "total_potential_annual_saving": 360},
            "days_remaining": 10
        }

        result = generate_page_insights("my_budgets", data)
        assert "saving" in result["whisper"].lower()


class TestSettingsInsight:

    def test_with_data(self):
        data = {
            "total_transactions": 45,
            "active_goals": 3,
            "member_since": "March 2026"
        }

        result = generate_page_insights("settings", data)
        assert "45" in result["whisper"]

    def test_empty(self):
        data = {}
        result = generate_page_insights("settings", data)
        assert "whisper" in result


class TestFallbackInsight:

    def test_unknown_page(self):
        result = generate_page_insights("nonexistent_page", {})
        assert result["page"] == "unknown"
        assert len(result["whisper"]) > 0


class TestDailyDigest:

    def test_with_full_data(self):
        data = {
            "money_left": 340,
            "days_remaining": 14,
            "budget_statuses": [
                {"category_name": "Food", "status": "warning",
                 "insight": "85% used", "percent_used": 85}
            ],
            "goals": [
                {"name": "House deposit", "status": "active", "progress_percent": 31}
            ],
            "anomalies": {"anomalies": []}
        }

        result = generate_daily_digest(data)
        assert result["section_count"] >= 1
        assert "generated_at" in result

    def test_with_anomaly(self):
        data = {
            "money_left": 300,
            "days_remaining": 10,
            "budget_statuses": [],
            "goals": [],
            "anomalies": {
                "anomalies": [
                    {"severity": "high", "type": "large_transaction",
                     "message": "Big Amazon purchase"}
                ]
            }
        }

        result = generate_daily_digest(data)
        assert result["has_alerts"] is True

    def test_empty_data(self):
        data = {
            "budget_statuses": [],
            "goals": [],
            "anomalies": {"anomalies": []}
        }

        result = generate_daily_digest(data)
        assert result["section_count"] == 0

    def test_quiet_period(self):
        data = {
            "budget_statuses": [],
            "goals": [],
            "anomalies": {
                "anomalies": [
                    {"severity": "low", "type": "quiet_period",
                     "message": "Low spend week"}
                ]
            }
        }

        result = generate_daily_digest(data)
        positive = [s for s in result["sections"] if s["priority"] == "positive"]
        assert len(positive) >= 1


class TestMonthEndSummary:

    def test_above_average(self):
        data = {
            "predictions": {
                "spending_so_far": {"total": 1200},
                "comparison": {"historical_average": 1000, "difference": 200}
            },
            "goals": [{"name": "Test", "status": "active", "progress_percent": 50}],
            "budget_statuses": [{"status": "on_track"}],
            "recurring": {"total_monthly_cost": 150}
        }

        result = generate_month_end_summary(data)
        assert "more" in result["spending_verdict"]
        assert result["total_spent"] == 1200

    def test_below_average(self):
        data = {
            "predictions": {
                "spending_so_far": {"total": 800},
                "comparison": {"historical_average": 1000, "difference": -200}
            },
            "goals": [],
            "budget_statuses": [],
            "recurring": {"total_monthly_cost": 0}
        }

        result = generate_month_end_summary(data)
        assert "less" in result["spending_verdict"]
        assert "Well done" in result["spending_verdict"]

    def test_budgets_exceeded(self):
        data = {
            "predictions": {
                "spending_so_far": {"total": 500},
                "comparison": {}
            },
            "goals": [],
            "budget_statuses": [
                {"status": "exceeded"},
                {"status": "on_track"}
            ],
            "recurring": {}
        }

        result = generate_month_end_summary(data)
        assert result["budgets_exceeded"] == 1
        assert result["budgets_on_track"] == 1

    def test_empty_data(self):
        data = {
            "predictions": {"spending_so_far": {}, "comparison": {}},
            "goals": [],
            "budget_statuses": [],
            "recurring": {}
        }

        result = generate_month_end_summary(data)
        assert "spending_verdict" in result


class TestInsightAPI:

    def test_page_insight(self, auth_client):
        response = auth_client.get("/api/insights/page/overview")
        assert response.status_code == 200
        data = response.get_json()
        assert "whisper" in data
        assert "page" in data

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
        data = response.get_json()
        assert data["page"] == "unknown"

    def test_insights_without_auth(self, client):
        response = client.get("/api/insights/page/overview")
        assert response.status_code == 401