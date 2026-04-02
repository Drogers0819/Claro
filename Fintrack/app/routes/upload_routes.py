from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.transaction import Transaction
from app.models.category import Category
from app.services.csv_parser import extract_transactions_from_csv, CSVParseError
from app.services.categoriser_service import categorise_transactions, build_categoriser_for_user

upload_bp = Blueprint("upload", __name__, url_prefix="/api/upload")


@upload_bp.route("/csv", methods=["POST"])
@login_required
def upload_csv():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.lower().endswith(".csv"):
        return jsonify({"error": "File must be a CSV"}), 400

    file_content = file.read()

    if len(file_content) == 0:
        return jsonify({"error": "File is empty"}), 400

    if len(file_content) > 5 * 1024 * 1024:
        return jsonify({"error": "File too large. Maximum size is 5MB"}), 400

    try:
        result = extract_transactions_from_csv(file_content)
    except CSVParseError as e:
        return jsonify({"error": str(e)}), 400

    if not result["transactions"]:
        return jsonify({
            "error": "No valid transactions found in file",
            "errors": result["errors"]
        }), 400

    # Build categoriser from user's existing categorised transactions
    existing = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.category_id != _get_other_category_id()
    ).all()

    training_data = []
    for t in existing:
        if t.category_rel:
            training_data.append({
                "description": t.description,
                "category": t.category_rel.name
            })

    categoriser = build_categoriser_for_user(training_data) if training_data else None

    # Categorise the parsed transactions
    categorised = categorise_transactions(result["transactions"], categoriser)

    # Build category name-to-id lookup
    categories = Category.query.all()
    category_lookup = {c.name: c.id for c in categories}
    other_id = category_lookup.get("Other", 1)

    created_count = 0
    skipped_count = 0
    auto_categorised_count = 0

    for t in categorised:
        existing_t = Transaction.query.filter_by(
            user_id=current_user.id,
            amount=t["amount"],
            description=t["description"],
            date=t["date"],
            type=t["type"]
        ).first()

        if existing_t:
            skipped_count += 1
            continue

        # Look up category ID from the suggested category name
        suggested = t.get("suggested_category", "Other")
        category_id = category_lookup.get(suggested, other_id)

        if suggested != "Other":
            auto_categorised_count += 1

        transaction = Transaction(
            user_id=current_user.id,
            amount=t["amount"],
            description=t["description"],
            category_id=category_id,
            type=t["type"],
            date=t["date"],
            merchant=t.get("merchant")
        )

        db.session.add(transaction)
        created_count += 1

    db.session.commit()

    return jsonify({
        "message": f"Import complete. {created_count} transactions created, {skipped_count} duplicates skipped.",
        "bank_detected": result["bank_detected"],
        "created": created_count,
        "skipped": skipped_count,
        "auto_categorised": auto_categorised_count,
        "errors": result["errors"],
        "error_count": result["error_count"]
    }), 201


def _get_other_category_id():
    other = Category.query.filter_by(name="Other").first()
    return other.id if other else 1