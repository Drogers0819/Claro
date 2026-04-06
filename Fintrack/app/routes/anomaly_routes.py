from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.models.transaction import Transaction
from app.services.anomaly_service import detect_anomalies, get_anomaly_summary

anomaly_bp = Blueprint("anomalies", __name__, url_prefix="/api/anomalies")


@anomaly_bp.route("", methods=["GET"])
@login_required
def get_anomalies():
    transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.date.asc()).all()

    txn_list = []
    for t in transactions:
        txn_list.append({
            "amount": float(t.amount),
            "description": t.description,
            "merchant": t.merchant or t.description,
            "category": t.category_rel.name if t.category_rel else "Other",
            "type": t.type,
            "date": t.date
        })

    result = detect_anomalies(txn_list)
    result["summary"] = get_anomaly_summary(result)

    return jsonify(result), 200