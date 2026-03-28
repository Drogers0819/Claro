import pytest
from app import create_app, db
from app.models.user import User
from config import TestingConfig


@pytest.fixture
def app():
    app = create_app(TestingConfig)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def registered_user(app):
    with app.app_context():
        user = User(email="test@test.com", name="Test User")
        user.set_password("testpassword123")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def auth_client(client, registered_user):
    client.post("/api/auth/login", json={
        "email": "test@test.com",
        "password": "testpassword123"
    })
    return client