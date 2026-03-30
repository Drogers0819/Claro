from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import db, bcrypt
from app.models.user import User
from app.models.transaction import Transaction
from sqlalchemy import func
from datetime import date, datetime
from app.models.category import Category


page_bp = Blueprint("pages", __name__)


@page_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("pages.dashboard"))
    return redirect(url_for("pages.login"))


@page_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("pages.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required", "error")
            return redirect(url_for("pages.register"))

        if len(password) < 8:
            flash("Password must be at least 8 characters", "error")
            return redirect(url_for("pages.register"))

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists", "error")
            return redirect(url_for("pages.register"))

        user = User(email=email, name=name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash("Account created successfully", "success")
        return redirect(url_for("pages.dashboard"))

    return render_template("register.html")


@page_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("pages.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password", "error")
            return redirect(url_for("pages.login"))

        login_user(user)
        return redirect(url_for("pages.dashboard"))

    return render_template("login.html")


@page_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out", "success")
    return redirect(url_for("pages.login"))


@page_bp.route("/dashboard")
@login_required
def dashboard():
    income = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter_by(user_id=current_user.id, type="income").scalar()

    expenses = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter_by(user_id=current_user.id, type="expense").scalar()

    balance = float(income) - float(expenses)
    transaction_count = Transaction.query.filter_by(user_id=current_user.id).count()

    recent = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.date.desc()).limit(5).all()

    hour = datetime.now().hour
    if hour < 12:
        greeting = "morning"
    elif hour < 18:
        greeting = "afternoon"
    else:
        greeting = "evening"

    return render_template("dashboard.html",
        summary={
            "total_income": float(income),
            "total_expenses": float(expenses),
            "balance": balance,
            "transaction_count": transaction_count
        },
        recent_transactions=[t.to_dict() for t in recent],
        greeting=greeting
    )


@page_bp.route("/transactions")
@login_required
def transactions():
    all_transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.date.desc()).all()

    return render_template("transactions.html",
        transactions=[t.to_dict() for t in all_transactions]
    )


@page_bp.route("/add-transaction", methods=["GET", "POST"])
@login_required
def add_transaction():
    if request.method == "POST":
        try:
            amount = round(float(request.form.get("amount", 0)), 2)
        except (ValueError, TypeError):
            flash("Invalid amount", "error")
            return redirect(url_for("pages.add_transaction"))

        if amount <= 0:
            flash("Amount must be greater than zero", "error")
            return redirect(url_for("pages.add_transaction"))

        description = request.form.get("description", "").strip()
        if not description:
            flash("Description is required", "error")
            return redirect(url_for("pages.add_transaction"))

        transaction_type = request.form.get("type", "expense")
        category_id = request.form.get("category_id", type=int)
        merchant = request.form.get("merchant", "").strip() or None

        if not category_id:
            other = Category.query.filter_by(name="Other").first()
            category_id = other.id if other else 1

        try:
            transaction_date = date.fromisoformat(request.form.get("date", ""))
        except (ValueError, TypeError):
            flash("Invalid date", "error")
            return redirect(url_for("pages.add_transaction"))

        transaction = Transaction(
            user_id=current_user.id,
            amount=amount,
            description=description,
            category_id=category_id,
            type=transaction_type,
            date=transaction_date,
            merchant=merchant
        )

        db.session.add(transaction)
        db.session.commit()

        flash("Transaction recorded successfully", "success")
        return redirect(url_for("pages.transactions"))

    categories = Category.query.order_by(Category.name).all()
    return render_template("add_transaction.html", categories=categories)

@page_bp.route("/delete-transaction/<int:transaction_id>", methods=["POST"])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.filter_by(
        id=transaction_id,
        user_id=current_user.id
    ).first()

    if not transaction:
        flash("Transaction not found", "error")
        return redirect(url_for("pages.transactions"))

    db.session.delete(transaction)
    db.session.commit()

    flash("Transaction deleted", "success")
    return redirect(url_for("pages.transactions"))