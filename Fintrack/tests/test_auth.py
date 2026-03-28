class TestRegister:

    def test_register_success(self, client):
        response = client.post("/api/auth/register", json={
            "email": "new@test.com",
            "name": "New User",
            "password": "newpassword123"
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["user"]["email"] == "new@test.com"
        assert data["user"]["name"] == "New User"
        assert "password" not in str(data)

    def test_register_duplicate_email(self, client, registered_user):
        response = client.post("/api/auth/register", json={
            "email": "test@test.com",
            "name": "Duplicate",
            "password": "password123"
        })
        assert response.status_code == 409

    def test_register_missing_fields(self, client):
        response = client.post("/api/auth/register", json={
            "email": "test@test.com"
        })
        assert response.status_code == 400

    def test_register_short_password(self, client):
        response = client.post("/api/auth/register", json={
            "email": "new@test.com",
            "name": "Test",
            "password": "short"
        })
        assert response.status_code == 400


class TestLogin:

    def test_login_success(self, client, registered_user):
        response = client.post("/api/auth/login", json={
            "email": "test@test.com",
            "password": "testpassword123"
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data["user"]["email"] == "test@test.com"

    def test_login_wrong_password(self, client, registered_user):
        response = client.post("/api/auth/login", json={
            "email": "test@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401

    def test_login_nonexistent_email(self, client):
        response = client.post("/api/auth/login", json={
            "email": "nobody@test.com",
            "password": "password123"
        })
        assert response.status_code == 401


class TestProtectedRoutes:

    def test_me_when_logged_in(self, auth_client):
        response = auth_client.get("/api/auth/me")
        assert response.status_code == 200
        data = response.get_json()
        assert data["email"] == "test@test.com"

    def test_me_when_logged_out(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 401