from datetime import date, timedelta
from collections import defaultdict
import statistics
import re


def detect_recurring_transactions(transactions):
    if not transactions or len(transactions) < 2:
        return {
            "recurring": [],
            "total_monthly_cost": 0,
            "total_monthly_income": 0,
            "count": 0,
            "expense_count": 0,
            "income_count": 0,
            "message": "Not enough transaction history to detect patterns. Upload at least 2 months of data."
        }

    groups = _group_by_merchant(transactions)

    recurring = []

    for merchant, txns in groups.items():
        if len(txns) < 3:
            continue

        # Must span at least 2 different months to be recurring
        months_seen = set((t["date"].year, t["date"].month) for t in txns)
        if len(months_seen) < 2:
            continue

        txns.sort(key=lambda t: t["date"])

        intervals = []
        for i in range(1, len(txns)):
            days = (txns[i]["date"] - txns[i - 1]["date"]).days
            if days > 0:
                intervals.append(days)

        if not intervals:
            continue

        pattern = _analyse_intervals(intervals)

        if pattern["is_recurring"]:
            amounts = [float(t["amount"]) for t in txns]
            avg_amount = round(statistics.mean(amounts), 2)
            amount_variance = round(statistics.stdev(amounts), 2) if len(amounts) > 1 else 0

            monthly_cost = _calculate_monthly_cost(avg_amount, pattern["frequency"])

            recurring.append({
                "merchant": merchant,
                "frequency": pattern["frequency"],
                "frequency_label": pattern["frequency_label"],
                "avg_interval_days": pattern["avg_interval"],
                "confidence": pattern["confidence"],
                "occurrence_count": len(txns),
                "avg_amount": avg_amount,
                "amount_variance": amount_variance,
                "amount_consistent": amount_variance < (avg_amount * 0.1),
                "monthly_cost": monthly_cost,
                "last_date": txns[-1]["date"].isoformat(),
                "last_date_display": txns[-1]["date"].strftime("%#d %b %Y"),
                "next_expected": txns[-1]["date"] + timedelta(days=round(pattern["avg_interval"])),
                "next_expected_display": _predict_next_date(txns[-1]["date"], pattern["avg_interval"]),
                "category": txns[-1].get("category", "Other"),
                "category_id": txns[-1].get("category_id"),
                "transaction_type": txns[-1].get("type", "expense"),
                "sample_description": txns[-1].get("description", merchant)
            })

    recurring.sort(key=lambda r: r["monthly_cost"], reverse=True)

    total_monthly = round(sum(r["monthly_cost"] for r in recurring if r["transaction_type"] == "expense"), 2)
    total_monthly_income = round(sum(r["monthly_cost"] for r in recurring if r["transaction_type"] == "income"), 2)

    return {
        "recurring": recurring,
        "total_monthly_cost": total_monthly,
        "total_monthly_income": total_monthly_income,
        "count": len(recurring),
        "expense_count": sum(1 for r in recurring if r["transaction_type"] == "expense"),
        "income_count": sum(1 for r in recurring if r["transaction_type"] == "income")
    }


def _group_by_merchant(transactions):
    groups = defaultdict(list)

    for t in transactions:
        merchant = t.get("merchant", "") or t.get("description", "")
        normalised = _normalise_merchant(merchant)

        if normalised:
            groups[normalised].append(t)

    return groups


def _normalise_merchant(merchant):
    if not merchant:
        return ""

    name = merchant.lower().strip()

    name = re.sub(r'\s*-\s*\d+.*$', '', name)    # dash followed by numbers (must be BEFORE trailing numbers)
    name = re.sub(r'\s+\d{3,}$', '', name)        # trailing numbers (store codes)
    name = re.sub(r'\s+#\d+$', '', name)           # hash followed by numbers
    name = re.sub(r'\*.*$', '', name)               # asterisk and everything after
    name = re.sub(r'\s*-\s*$', '', name)            # trailing dash leftover
    name = re.sub(r'\s+', ' ', name).strip()        # collapse whitespace

    return name

def _analyse_intervals(intervals):
    if not intervals:
        return {"is_recurring": False}

    avg = statistics.mean(intervals)
    std = statistics.stdev(intervals) if len(intervals) > 1 else 0

    cv = std / avg if avg > 0 else float('inf')

    frequency, frequency_label = _classify_frequency(avg)

    consistency_score = max(0, 1 - cv)
    sample_score = min(1, len(intervals) / 6)
    confidence = round(consistency_score * 0.7 + sample_score * 0.3, 2)

    is_recurring = (
        confidence >= 0.4 and
        frequency is not None and
        cv < 0.5
    )

    return {
        "is_recurring": is_recurring,
        "frequency": frequency,
        "frequency_label": frequency_label,
        "avg_interval": round(avg, 1),
        "interval_std": round(std, 1),
        "coefficient_of_variation": round(cv, 3),
        "confidence": confidence
    }


def _classify_frequency(avg_days):
    if 5 <= avg_days <= 10:
        return "weekly", "Weekly"
    elif 11 <= avg_days <= 18:
        return "fortnightly", "Every 2 weeks"
    elif 25 <= avg_days <= 35:
        return "monthly", "Monthly"
    elif 55 <= avg_days <= 70:
        return "bimonthly", "Every 2 months"
    elif 80 <= avg_days <= 100:
        return "quarterly", "Quarterly"
    elif 170 <= avg_days <= 200:
        return "biannual", "Every 6 months"
    elif 340 <= avg_days <= 400:
        return "annual", "Annual"
    else:
        return None, "Irregular"


def _calculate_monthly_cost(avg_amount, frequency):
    multipliers = {
        "weekly": 4.33,
        "fortnightly": 2.17,
        "monthly": 1.0,
        "bimonthly": 0.5,
        "quarterly": 0.33,
        "biannual": 0.167,
        "annual": 0.083,
    }

    multiplier = multipliers.get(frequency, 1.0)
    return round(avg_amount * multiplier, 2)


def _predict_next_date(last_date, avg_interval_days):
    next_date = last_date + timedelta(days=round(avg_interval_days))
    return next_date.strftime("%#d %b %Y")


_EXCLUDED_SAVING_CATEGORIES = {"Bills", "Income", "Rent"}


def identify_potential_savings(recurring_transactions):
    savings_opportunities = []

    for r in recurring_transactions:
        if r["transaction_type"] != "expense":
            continue

        # Skip non-discretionary categories — rent, energy, broadband are not savings opportunities
        if r.get("category", "") in _EXCLUDED_SAVING_CATEGORIES:
            continue

        last = date.fromisoformat(r["last_date"])
        days_since = (date.today() - last).days

        if days_since > 45 and r["frequency"] == "monthly":
            savings_opportunities.append({
                "merchant": r["merchant"],
                "monthly_cost": r["monthly_cost"],
                "last_seen": r["last_date"],
                "days_since_last": days_since,
                "type": "potentially_unused",
                "message": f"You haven't used {r['merchant']} in {days_since} days but it may still be charging you £{r['monthly_cost']:.2f}/month.",
                "annual_saving": round(r["monthly_cost"] * 12, 2)
            })

        if r["frequency"] == "weekly" and r["monthly_cost"] > 50:
            savings_opportunities.append({
                "merchant": r["merchant"],
                "monthly_cost": r["monthly_cost"],
                "type": "high_frequency",
                "message": f"Your weekly {r['merchant']} habit costs £{r['monthly_cost']:.2f}/month (£{r['monthly_cost'] * 12:.2f}/year).",
                "annual_saving": round(r["monthly_cost"] * 12, 2)
            })

        if r["frequency"] == "monthly" and r["avg_amount"] > 30:
            savings_opportunities.append({
                "merchant": r["merchant"],
                "monthly_cost": r["monthly_cost"],
                "type": "expensive_subscription",
                "message": f"{r['merchant']} costs £{r['monthly_cost']:.2f}/month. Worth reviewing if you're getting full value.",
                "annual_saving": round(r["monthly_cost"] * 12, 2)
            })

    savings_opportunities.sort(key=lambda s: s["annual_saving"], reverse=True)

    total_potential = round(sum(s["annual_saving"] for s in savings_opportunities), 2)

    return {
        "opportunities": savings_opportunities,
        "count": len(savings_opportunities),
        "total_potential_annual_saving": total_potential
    }