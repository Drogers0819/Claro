from flask import Flask, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()


DEFAULT_CATEGORIES = [
    {"name": "Food", "icon": "🍕", "colour": "#E07A5F"},
    {"name": "Transport", "icon": "🚌", "colour": "#3D85C6"},
    {"name": "Bills", "icon": "🏠", "colour": "#81B29A"},
    {"name": "Entertainment", "icon": "🎬", "colour": "#F2CC8F"},
    {"name": "Shopping", "icon": "🛍️", "colour": "#BC6C8A"},
    {"name": "Health", "icon": "💊", "colour": "#6D9DC5"},
    {"name": "Education", "icon": "📚", "colour": "#B8B8D1"},
    {"name": "Subscriptions", "icon": "🔄", "colour": "#9B8EC0"},
    {"name": "Income", "icon": "💰", "colour": "#C5A35D"},
    {"name": "Other", "icon": "📌", "colour": "#888780"},
]


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
        from flask import request as req
        if req.path.startswith("/api/"):
            return jsonify({"error": "Authentication required"}), 401
        return redirect(url_for("pages.login"))

    with app.app_context():
        from app.models.user import User
        from app.models.category import Category
        from app.models.transaction import Transaction
        from app.models.goal import Goal
        from app.models.budget import Budget
        db.create_all()

        if Category.query.count() == 0:
            for cat_data in DEFAULT_CATEGORIES:
                category = Category(**cat_data)
                db.session.add(category)
            db.session.commit()

    from app.routes.auth_routes import auth_bp
    from app.routes.transaction_routes import transaction_bp
    from app.routes.dashboard_routes import dashboard_bp
    from app.routes.page_routes import page_bp
    from app.routes.category_routes import category_bp
    from app.routes.goal_routes import goal_bp
    from app.routes.upload_routes import upload_bp
    from app.routes.profile_routes import profile_bp
    from app.routes.analytics_routes import analytics_bp
    from app.routes.simulator_routes import simulator_bp
    from app.routes.recurring_routes import recurring_bp
    from app.routes.prediction_routes import prediction_bp
    from app.routes.budget_routes import budget_bp
    app.register_blueprint(budget_bp)
    app.register_blueprint(prediction_bp)
    app.register_blueprint(recurring_bp)
    app.register_blueprint(simulator_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(transaction_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(page_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(goal_bp)

    return app