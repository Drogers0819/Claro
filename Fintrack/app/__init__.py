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
    {"name": "Rent", "icon": "🏠", "colour": "#7BA68C"},
    {"name": "Transfer", "icon": "🔄", "colour": "#6B7280"},
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

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        from flask import render_template
        return render_template("500.html"), 500

    with app.app_context():
        from app.models.user import User
        from app.models.category import Category
        from app.models.transaction import Transaction
        from app.models.goal import Goal
        from app.models.budget import Budget
        from app.models.chat import ChatMessage
        from app.models.checkin import CheckIn, CheckInEntry
        
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
    from app.routes.anomaly_routes import anomaly_bp
    from app.routes.insight_routes import insight_bp
    from app.routes.narrative_routes import narrative_bp
    from app.routes.companion_routes import companion_bp
    app.register_blueprint(narrative_bp)
    app.register_blueprint(companion_bp)

    # Scheduler — only in main process (not Flask reloader worker)
    import os
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        try:
            from app.scheduler import init_scheduler
            init_scheduler(app)
        except ImportError:
            import logging
            logging.getLogger(__name__).warning(
                "APScheduler not installed — weekly digest scheduler disabled. "
                "Run: pip install APScheduler==3.10.4 resend==2.10.0"
            )
    app.register_blueprint(insight_bp)
    app.register_blueprint(anomaly_bp)
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