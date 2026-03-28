from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()


def create_app(config_class=None):
    if config_class is None:
        from config import DevelopmentConfig
        config_class = DevelopmentConfig

    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({"error": "Authentication required"}), 401

    with app.app_context():
        from app.models.user import User
        from app.models.transaction import Transaction
        db.create_all()

    from app.routes.auth_routes import auth_bp
    from app.routes.transaction_routes import transaction_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(transaction_bp)

    return app