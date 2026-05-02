import os

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)


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
    import os
    if config_class is None:
        if os.environ.get("FLASK_ENV") == "production":
            from config import ProductionConfig
            config_class = ProductionConfig
        else:
            from config import DevelopmentConfig
            config_class = DevelopmentConfig

    app = Flask(__name__)
    app.config.from_object(config_class)

    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # SQLite doesn't enforce foreign keys by default. Without this, ON DELETE
    # CASCADE / passive_deletes are silently ignored in local dev and tests,
    # so a deletion appears to succeed but related rows linger. Postgres
    # enforces FKs unconditionally, so this hook is a no-op there.
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    @event.listens_for(Engine, "connect")
    def _sqlite_fk_pragma(dbapi_connection, connection_record):
        try:
            import sqlite3
            if isinstance(dbapi_connection, sqlite3.Connection):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys = ON")
                cursor.close()
        except Exception:
            pass

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if not app.debug:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

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
        from app.models.life_checkin import LifeCheckIn
        from app.models.checkin import CheckIn, CheckInEntry

        db.create_all()

        # ── Idempotent column migrations ──
        # On a fresh DB, db.create_all() picks these columns up from the
        # models, so the migration is a no-op. On an existing PostgreSQL
        # DB that pre-dates a column, this adds it without manual SQL.
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        try:
            existing_columns = [col["name"] for col in inspector.get_columns("users")]
        except Exception:
            existing_columns = []

        migrations = [
            ("employment_type", "ALTER TABLE users ADD COLUMN employment_type VARCHAR(30) DEFAULT 'full_time'"),
        ]

        for col_name, sql in migrations:
            if col_name not in existing_columns:
                try:
                    db.session.execute(text(sql))
                    db.session.commit()
                    print(f"Migration: added column {col_name}")
                except Exception as e:
                    db.session.rollback()
                    print(f"Migration skipped {col_name}: {e}")

        # ── Foreign-key cascade migration (Postgres only) ──
        # Production needs ON DELETE CASCADE on every FK referencing
        # users.id (and on checkin_entries.checkin_id) so account deletion
        # works without orphaning data — required for UK GDPR Article 17.
        #
        # SQLite local dev relies on SQLAlchemy ORM-level cascade
        # (cascade="all, delete-orphan", passive_deletes=True on the
        # relationships). Both code paths produce the same end state for
        # account deletion; they just route through different layers.
        #
        # Idempotent: each FK is only dropped/recreated if the live
        # constraint's delete_rule is not already CASCADE, so redeploys
        # are no-ops once the cascade has been applied.
        if db.engine.dialect.name == "postgresql":
            cascade_targets = [
                # (table, fk_column, referenced_table, delete_rule)
                ("transactions", "user_id", "users", "CASCADE"),
                ("goals", "user_id", "users", "CASCADE"),
                ("budgets", "user_id", "users", "CASCADE"),
                ("chat_messages", "user_id", "users", "CASCADE"),
                ("life_checkins", "user_id", "users", "CASCADE"),
                ("checkins", "user_id", "users", "CASCADE"),
                ("checkin_entries", "checkin_id", "checkins", "CASCADE"),
                ("checkin_entries", "goal_id", "goals", "SET NULL"),
            ]

            for table, column, ref_table, desired_rule in cascade_targets:
                try:
                    row = db.session.execute(text("""
                        SELECT tc.constraint_name, rc.delete_rule
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                          ON tc.constraint_name = kcu.constraint_name
                         AND tc.table_schema = kcu.table_schema
                        JOIN information_schema.referential_constraints rc
                          ON tc.constraint_name = rc.constraint_name
                         AND tc.table_schema = rc.constraint_schema
                        WHERE tc.constraint_type = 'FOREIGN KEY'
                          AND tc.table_name = :table
                          AND kcu.column_name = :column
                        LIMIT 1
                    """), {"table": table, "column": column}).fetchone()

                    if row is None:
                        # Table or FK doesn't exist yet — db.create_all() will
                        # build it from the model, which already declares the
                        # cascade. Nothing to migrate.
                        continue

                    constraint_name, current_rule = row
                    if (current_rule or "").upper() == desired_rule.upper():
                        continue

                    db.session.execute(text(
                        f'ALTER TABLE {table} DROP CONSTRAINT "{constraint_name}"'
                    ))
                    db.session.execute(text(
                        f'ALTER TABLE {table} ADD CONSTRAINT "{constraint_name}" '
                        f'FOREIGN KEY ({column}) REFERENCES {ref_table}(id) '
                        f'ON DELETE {desired_rule}'
                    ))
                    db.session.commit()
                    print(f"Migration: {table}.{column} FK now ON DELETE {desired_rule}")
                except Exception as e:
                    db.session.rollback()
                    print(f"Migration skipped {table}.{column} FK: {e}")

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
    from app.routes.billing_routes import billing_bp
    app.register_blueprint(narrative_bp)
    app.register_blueprint(companion_bp)
    app.register_blueprint(billing_bp)

    from app.services.stripe_service import init_stripe
    init_stripe()

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

    # Pages that opt into the slim icon-sidebar / bottom-tab-bar shell
    _SLIM_SHELL_ENDPOINTS = {
        "pages.overview",
        "pages.my_goals",
        "pages.add_goal",
        "pages.edit_goal",
        "pages.goal_detail",
        "companion.companion_page",
        "pages.plan",
        "pages.scenario_page",
        "pages.checkin",
        "pages.settings",
    }

    @app.context_processor
    def _inject_slim_shell_flag():
        from flask import request
        return {"use_slim_shell": request.endpoint in _SLIM_SHELL_ENDPOINTS}

    @app.context_processor
    def _inject_companion_access():
        """Templates use `can_access_companion` to decide whether to render
        the Companion nav link. The companion page itself is gated by
        @requires_subscription; this just keeps the nav consistent with
        what the user can actually reach."""
        from flask_login import current_user
        from app.utils.auth import is_subscription_active
        try:
            allowed = bool(
                current_user
                and current_user.is_authenticated
                and is_subscription_active(current_user)
            )
        except Exception:
            allowed = False
        return {"can_access_companion": allowed}

    # Debug-only smoke-test routes. Each one is meant to be hit a couple
    # times by the developer on a fresh deploy and then removed in a
    # follow-up commit; they bypass real-user logic on purpose.
    if app.debug:
        from app.services.analytics_service import track_event, flush as ph_flush

        @app.route("/dev/posthog-test")
        def _posthog_test():
            track_event("dev-test-user", "dev_test_event", {"source": "manual_smoke_test"})
            ph_flush()
            return "fired", 200

        @app.route("/dev/companion-smoke-test")
        def _companion_smoke_test():
            from time import perf_counter
            from app.services.companion_service import smoke_test_chat
            start = perf_counter()
            try:
                result = smoke_test_chat()
                latency_ms = int((perf_counter() - start) * 1000)
                cache_read = result.get("cache_read_input_tokens", 0)
                cache_create = result.get("cache_creation_input_tokens", 0)
                from flask import jsonify
                return jsonify({
                    "success": result.get("error") is None,
                    "response_text": result.get("text", ""),
                    "model_used": result.get("model", ""),
                    "cache_read_input_tokens": cache_read,
                    "cache_creation_input_tokens": cache_create,
                    "cache_hit": cache_read > 0,
                    "input_tokens": result.get("input_tokens", 0),
                    "output_tokens": result.get("output_tokens", 0),
                    "latency_ms": latency_ms,
                    "error": result.get("error"),
                })
            except Exception as exc:  # noqa: BLE001
                from flask import jsonify
                return jsonify({"success": False, "error": str(exc)}), 500

    return app