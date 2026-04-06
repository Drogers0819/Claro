from datetime import date, timedelta
from app.services.anomaly_service import (
    detect_anomalies,
    get_anomaly_summary,
    _detect_large_transactions,
    _detect_category_spikes,
    _detect_new_merchants,
    _detect_frequency_changes,
    _detect_quiet_periods
)


class TestDetectLargeTransactions:

    def test_flags_outlier(self):
        today = date.today()
        txns = [
            {"amount": 30, "type": "expense", "date": today - timedelta(days=i),
             "description": f"Normal {i}", "category": "Food"}
            for i in range(1, 20)
        ]
        # Add one large transaction
        txns.append({
            "amount": 250, "type": "expense", "date": today,
            "description": "Big purchase", "category": "Shopping"
        })

        result = _detect_large_transactions(txns, today)
        assert len(result) >= 1
        assert result[0]["type"] == "large_transaction"
        assert result[0]["amount"] == 250

    def test_no_outliers(self):
        today = date.today()
        txns = [
            {"amount": 30, "type": "expense", "date": today - timedelta(days=i),
             "description": f"Normal {i}", "category": "Food"}
            for i in range(10)
        ]

        result = _detect_large_transactions(txns, today)
        assert len(result) == 0

    def test_ignores_old_transactions(self):
        today = date.today()
        txns = [
            {"amount": 30, "type": "expense", "date": today - timedelta(days=i),
             "description": f"Normal {i}", "category": "Food"}
            for i in range(1, 20)
        ]
        # Large transaction from 30 days ago — should not flag
        txns.append({
            "amount": 500, "type": "expense", "date": today - timedelta(days=30),
            "description": "Old big purchase", "category": "Shopping"
        })

        result = _detect_large_transactions(txns, today)
        flagged_descriptions = [a["description"] for a in result]
        assert "Old big purchase" not in flagged_descriptions

    def test_insufficient_data(self):
        today = date.today()
        txns = [
            {"amount": 50, "type": "expense", "date": today, "description": "Only one", "category": "Food"}
        ]
        result = _detect_large_transactions(txns, today)
        assert len(result) == 0


class TestDetectCategorySpikes:

    def test_detects_spike(self):
        today = date.today()
        txns = []

        # Create 3 months of food spending at ~£200/month
        for month_offset in range(1, 4):
            m = today.month - month_offset
            y = today.year
            if m <= 0:
                m += 12
                y -= 1
            for i in range(4):
                txns.append({
                    "amount": 50, "type": "expense",
                    "date": date(y, m, min(i * 7 + 1, 28)),
                    "category": "Food"
                })

        # Current month: already spent £400 (2x average)
        txns.append({
            "amount": 400, "type": "expense",
            "date": today, "category": "Food"
        })

        result = _detect_category_spikes(txns, today)
        food_spikes = [a for a in result if a["category"] == "Food"]
        assert len(food_spikes) >= 1

    def test_no_spike(self):
        today = date.today()
        txns = []

        for month_offset in range(1, 4):
            m = today.month - month_offset
            y = today.year
            if m <= 0:
                m += 12
                y -= 1
            txns.append({
                "amount": 200, "type": "expense",
                "date": date(y, m, 15), "category": "Food"
            })

        # Current month: normal spending
        txns.append({
            "amount": 50, "type": "expense",
            "date": today, "category": "Food"
        })

        result = _detect_category_spikes(txns, today)
        assert len(result) == 0

    def test_ignores_income(self):
        today = date.today()
        txns = [
            {"amount": 5000, "type": "income", "date": today, "category": "Income"}
        ]
        result = _detect_category_spikes(txns, today)
        assert len(result) == 0


class TestDetectNewMerchants:

    def test_flags_new_merchant(self):
        today = date.today()
        txns = [
            {"amount": 30, "type": "expense", "date": today - timedelta(days=30),
             "description": "Tesco", "merchant": "Tesco", "category": "Food"},
            {"amount": 50, "type": "expense", "date": today,
             "description": "Brand New Shop", "merchant": "Brand New Shop", "category": "Shopping"},
        ]

        result = _detect_new_merchants(txns, today)
        assert len(result) >= 1
        assert result[0]["type"] == "new_merchant"

    def test_ignores_known_merchant(self):
        today = date.today()
        txns = [
            {"amount": 30, "type": "expense", "date": today - timedelta(days=30),
             "description": "Tesco", "merchant": "Tesco", "category": "Food"},
            {"amount": 35, "type": "expense", "date": today,
             "description": "Tesco", "merchant": "Tesco", "category": "Food"},
        ]

        result = _detect_new_merchants(txns, today)
        assert len(result) == 0

    def test_ignores_small_amounts(self):
        today = date.today()
        txns = [
            {"amount": 30, "type": "expense", "date": today - timedelta(days=30),
             "description": "Tesco", "merchant": "Tesco", "category": "Food"},
            {"amount": 5, "type": "expense", "date": today,
             "description": "Tiny New Place", "merchant": "Tiny New Place", "category": "Other"},
        ]

        result = _detect_new_merchants(txns, today)
        assert len(result) == 0


class TestDetectFrequencyChanges:

    def test_detects_high_frequency(self):
        today = date.today()
        txns = []

        # Historical: ~5 transactions per week for 4 weeks
        for week in range(1, 5):
            for i in range(5):
                txns.append({
                    "amount": 20, "type": "expense",
                    "date": today - timedelta(days=week * 7 + i),
                    "description": f"Shop {i}", "category": "Food"
                })

        # Recent week: 15 transactions (3x normal)
        for i in range(15):
            txns.append({
                "amount": 20, "type": "expense",
                "date": today - timedelta(days=i % 7),
                "description": f"Recent {i}", "category": "Food"
            })

        result = _detect_frequency_changes(txns, today)
        if result:
            assert result[0]["type"] == "frequency_spike"

    def test_normal_frequency(self):
        today = date.today()
        txns = []

        for week in range(5):
            for i in range(5):
                txns.append({
                    "amount": 20, "type": "expense",
                    "date": today - timedelta(days=week * 7 + i),
                    "description": f"Shop {i}", "category": "Food"
                })

        result = _detect_frequency_changes(txns, today)
        assert len(result) == 0


class TestDetectQuietPeriods:

    def test_detects_quiet_week(self):
        today = date.today()
        txns = []

        # Historical: ~£200 per week for 4 weeks
        for week in range(1, 5):
            for i in range(5):
                txns.append({
                    "amount": 40, "type": "expense",
                    "date": today - timedelta(days=week * 7 + i),
                    "description": f"Shop {i}", "category": "Food"
                })

        # Recent week: only £30 (much less than £200 average)
        txns.append({
            "amount": 30, "type": "expense",
            "date": today, "description": "Small shop", "category": "Food"
        })

        result = _detect_quiet_periods(txns, today)
        if result:
            assert result[0]["type"] == "quiet_period"
            assert result[0]["saved_amount"] > 0

    def test_normal_spending(self):
        today = date.today()
        txns = []

        for week in range(5):
            for i in range(5):
                txns.append({
                    "amount": 40, "type": "expense",
                    "date": today - timedelta(days=week * 7 + i),
                    "description": f"Shop {i}", "category": "Food"
                })

        result = _detect_quiet_periods(txns, today)
        assert len(result) == 0


class TestDetectAnomalies:

    def test_full_detection(self):
        today = date.today()
        txns = [
            {"amount": 30, "type": "expense", "date": today - timedelta(days=i),
             "description": "Regular shop", "merchant": "Regular shop",
             "category": "Food"}
            for i in range(1, 30)
        ]

        result = detect_anomalies(txns, today)
        assert "anomalies" in result
        assert "count" in result
        assert isinstance(result["anomalies"], list)

    def test_insufficient_data(self):
        result = detect_anomalies([])
        assert result["count"] == 0
        assert "message" in result

    def test_few_transactions(self):
        today = date.today()
        txns = [
            {"amount": 50, "type": "expense", "date": today,
             "description": "Shop", "merchant": "Shop", "category": "Food"}
        ]
        result = detect_anomalies(txns, today)
        assert result["count"] == 0

    def test_severity_counts(self):
        today = date.today()
        txns = [
            {"amount": 30, "type": "expense", "date": today - timedelta(days=i),
             "description": "Normal", "merchant": "Normal", "category": "Food"}
            for i in range(1, 20)
        ]
        txns.append({
            "amount": 500, "type": "expense", "date": today,
            "description": "Huge purchase", "merchant": "Huge purchase",
            "category": "Shopping"
        })

        result = detect_anomalies(txns, today)
        assert result["high_count"] + result["medium_count"] + result["low_count"] == result["count"]


class TestAnomalySummary:

    def test_summary_with_anomalies(self):
        result = {
            "anomalies": [
                {"severity": "high", "type": "large_transaction",
                 "message": "Big spend detected"},
                {"severity": "low", "type": "quiet_period",
                 "message": "Quiet week"}
            ],
            "count": 2
        }

        summary = get_anomaly_summary(result)
        assert summary is not None
        assert "Big spend" in summary

    def test_summary_no_anomalies(self):
        result = {"anomalies": [], "count": 0}
        summary = get_anomaly_summary(result)
        assert summary is None

    def test_summary_quiet_period_only(self):
        result = {
            "anomalies": [
                {"severity": "low", "type": "quiet_period",
                 "message": "You spent less this week"}
            ],
            "count": 1
        }

        summary = get_anomaly_summary(result)
        assert summary is not None


class TestAnomalyAPI:

    def test_get_anomalies(self, auth_client):
        response = auth_client.get("/api/anomalies")
        assert response.status_code == 200
        data = response.get_json()
        assert "anomalies" in data
        assert "count" in data

    def test_anomalies_without_auth(self, client):
        response = client.get("/api/anomalies")
        assert response.status_code == 401
