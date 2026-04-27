class TestThemeUpdate:

    def test_default_theme(self, auth_client):
        response = auth_client.get("/api/profile/factfind")
        data = response.get_json()
        assert data["profile"]["theme"] == "obsidian-vault"

    def test_theme_in_profile(self, auth_client):
        auth_client.post("/api/profile/factfind", json={
            "monthly_income": 1700,
            "rent_amount": 800,
            "bills_amount": 0
        })

        response = auth_client.get("/api/profile/factfind")
        data = response.get_json()
        assert data["profile"]["theme"] == "obsidian-vault"
        assert data["profile"]["factfind_completed"] is True
