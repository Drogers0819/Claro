from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    email = data.get("email", "").strip()
    name = data.get("name", "").strip()
    password = data.get("password", "")

    if not email or not password or not name:
        return jsonify({"error": "Email, name, and password are required"}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    existing_user = User.query.filter_by(email=email).first()

    if existing_user:
        return jsonify({"error": "An account with this email already exists"}), 409

    user = User(email=email, name=name)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "message": "Account created successfully",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name
        }
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    login_user(user)

    return jsonify({
        "message": "Login successful",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name
        }
    }), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    if current_user.is_authenticated:
        logout_user()
        return jsonify({"message": "Logged out successfully"}), 200

    return jsonify({"message": "No active session"}), 200


@auth_bp.route("/me", methods=["GET"])
@login_required
def get_current_user():
    return jsonify({
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name
    }), 200