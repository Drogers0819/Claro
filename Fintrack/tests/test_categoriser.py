from app.services.categoriser_service import (
    categorise_by_rules,
    TransactionCategoriser,
    categorise_transactions,
    build_categoriser_for_user
)


class TestRuleBasedCategorisation:

    def test_tesco(self):
        assert categorise_by_rules("TESCO STORES 4521") == "Food"

    def test_uber(self):
        assert categorise_by_rules("UBER *TRIP BHX") == "Transport"

    def test_netflix(self):
        assert categorise_by_rules("NETFLIX.COM") == "Entertainment"

    def test_amazon(self):
        assert categorise_by_rules("AMAZON.CO.UK MARKETPLACE") == "Shopping"

    def test_council_tax(self):
        assert categorise_by_rules("COUNCIL TAX DD") == "Bills"

    def test_salary(self):
        assert categorise_by_rules("SALARY ACME LTD") == "Income"

    def test_boots(self):
        assert categorise_by_rules("BOOTS 1234") == "Health"

    def test_spotify(self):
        assert categorise_by_rules("SPOTIFY P12345") == "Entertainment"

    def test_deliveroo(self):
        assert categorise_by_rules("DELIVEROO ORDER 789") == "Food"

    def test_unknown_merchant(self):
        assert categorise_by_rules("OBSCURE SHOP XYZ") is None

    def test_empty_description(self):
        assert categorise_by_rules("") is None

    def test_none_description(self):
        assert categorise_by_rules(None) is None

    def test_case_insensitive(self):
        assert categorise_by_rules("tesco") == "Food"
        assert categorise_by_rules("TESCO") == "Food"
        assert categorise_by_rules("Tesco") == "Food"


class TestMLCategoriser:

    def _get_training_data(self):
        return [
            {"description": "Tesco weekly shop", "category": "Food"},
            {"description": "Sainsburys groceries", "category": "Food"},
            {"description": "Aldi shopping", "category": "Food"},
            {"description": "Deliveroo order", "category": "Food"},
            {"description": "Just Eat takeaway", "category": "Food"},
            {"description": "Uber trip to work", "category": "Transport"},
            {"description": "TFL bus journey", "category": "Transport"},
            {"description": "Trainline ticket", "category": "Transport"},
            {"description": "Northern Rail", "category": "Transport"},
            {"description": "Shell petrol station", "category": "Transport"},
            {"description": "Netflix subscription", "category": "Entertainment"},
            {"description": "Spotify premium", "category": "Entertainment"},
            {"description": "Cinema tickets", "category": "Entertainment"},
        ]

    def test_train_with_sufficient_data(self):
        categoriser = TransactionCategoriser()
        result = categoriser.train(self._get_training_data())
        assert result is True
        assert categoriser.is_trained is True

    def test_train_with_insufficient_data(self):
        categoriser = TransactionCategoriser()
        result = categoriser.train([
            {"description": "Test", "category": "Food"},
            {"description": "Test2", "category": "Transport"},
        ])
        assert result is False
        assert categoriser.is_trained is False

    def test_predict_food(self):
        categoriser = TransactionCategoriser()
        categoriser.train(self._get_training_data())

        category, confidence = categoriser.predict("Asda grocery shop")
        assert category == "Food"
        assert confidence > 0.3

    def test_predict_transport(self):
        categoriser = TransactionCategoriser()
        categoriser.train(self._get_training_data())

        category, confidence = categoriser.predict("Uber ride home")
        assert category == "Transport"
        assert confidence > 0.3

    def test_predict_untrained(self):
        categoriser = TransactionCategoriser()
        category, confidence = categoriser.predict("Something")
        assert category is None
        assert confidence == 0.0

    def test_predict_with_fallback_rules_first(self):
        categoriser = TransactionCategoriser()
        categoriser.train(self._get_training_data())

        category, confidence, source = categoriser.predict_with_fallback("TESCO STORES")
        assert category == "Food"
        assert confidence == 1.0
        assert source == "rule"

    def test_predict_with_fallback_ml(self):
        categoriser = TransactionCategoriser()
        categoriser.train(self._get_training_data())

        category, confidence, source = categoriser.predict_with_fallback("weekly grocery run")
        assert source in ("ml", "fallback")

    def test_predict_with_fallback_unknown(self):
        categoriser = TransactionCategoriser()
        category, confidence, source = categoriser.predict_with_fallback("ZZZZZ UNKNOWN 999")
        assert category == "Other"
        assert source == "fallback"


class TestCategoriseTransactions:

    def test_categorise_batch(self):
        transactions = [
            {"description": "TESCO STORES 4521", "amount": 52.40},
            {"description": "UBER TRIP BHX", "amount": 12.80},
            {"description": "RANDOM SHOP XYZ", "amount": 25.00},
        ]

        results = categorise_transactions(transactions)

        assert results[0]["suggested_category"] == "Food"
        assert results[0]["category_source"] == "rule"
        assert results[1]["suggested_category"] == "Transport"
        assert results[1]["category_source"] == "rule"
        assert results[2]["suggested_category"] == "Other"
        assert results[2]["category_source"] == "fallback"

    def test_categorise_with_trained_ml(self):
        training_data = [
            {"description": "Tesco shop", "category": "Food"},
            {"description": "Sainsburys groceries", "category": "Food"},
            {"description": "Aldi shop", "category": "Food"},
            {"description": "Asda weekly", "category": "Food"},
            {"description": "Morrisons shop", "category": "Food"},
            {"description": "Uber ride", "category": "Transport"},
            {"description": "TFL bus", "category": "Transport"},
            {"description": "Train ticket", "category": "Transport"},
            {"description": "Bus pass", "category": "Transport"},
            {"description": "Taxi home", "category": "Transport"},
        ]

        categoriser = build_categoriser_for_user(training_data)

        transactions = [
            {"description": "Local grocery store run", "amount": 35.00},
        ]

        results = categorise_transactions(transactions, categoriser)
        assert len(results) == 1
        assert results[0]["category_confidence"] >= 0


class TestRecategorise:

    def test_recategorise_transaction(self, auth_client):
        create = auth_client.post("/api/transactions", json={
            "amount": 52.40,
            "description": "Tesco",
            "type": "expense",
            "date": "2026-04-01"
        })
        tid = create.get_json()["transaction"]["id"]

        response = auth_client.put(f"/api/transactions/{tid}/categorise", json={
            "category_id": 1
        })
        assert response.status_code == 200
        assert response.get_json()["transaction"]["category"] == "Food"

    def test_recategorise_invalid_category(self, auth_client):
        create = auth_client.post("/api/transactions", json={
            "amount": 50,
            "description": "Test",
            "type": "expense",
            "date": "2026-04-01"
        })
        tid = create.get_json()["transaction"]["id"]

        response = auth_client.put(f"/api/transactions/{tid}/categorise", json={
            "category_id": 9999
        })
        assert response.status_code == 400

    def test_recategorise_not_found(self, auth_client):
        response = auth_client.put("/api/transactions/9999/categorise", json={
            "category_id": 1
        })
        assert response.status_code == 404

    def test_recategorise_without_auth(self, client):
        response = client.put("/api/transactions/1/categorise", json={
            "category_id": 1
        })
        assert response.status_code == 401