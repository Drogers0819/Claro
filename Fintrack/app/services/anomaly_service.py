from datetime import date, timedelta
from collections import defaultdict
import statistics


def detect_anomalies(transactions, current_date=None):
    """
    Scans transaction history and identifies unusual patterns:
    - Unusually large individual transactions
    - Category spending spikes
    - New merchants not seen before
    - Unusual frequency (spending more often than normal)
    - Quiet periods (spending less than normal)
    """
    if current_date is None:
        current_date = date.today()

    if not transactions or len(transactions) < 5:
        return {
            "anomalies": [],
            "count": 0,
            "message": "Not enough data to detect anomalies. Keep tracking to unlock this feature."
        }

    anomalies = []

    # Run each detection method
    anomalies.extend(_detect_large_transactions(transactions, current_date))
    anomalies.extend(_detect_category_spikes(transactions, current_date))
    anomalies.extend(_detect_new_merchants(transactions, current_date))
    anomalies.extend(_detect_frequency_changes(transactions, current_date))
    anomalies.extend(_detect_quiet_periods(transactions, current_date))

    # Sort by severity then recency
    severity_order = {"high": 0, "medium": 1, "low": 2}
    anomalies.sort(key=lambda a: (severity_order.get(a["severity"], 3), a.get("date", ""), ))

    return {
        "anomalies": anomalies,
        "count": len(anomalies),
        "high_count": sum(1 for a in anomalies if a["severity"] == "high"),
        "medium_count": sum(1 for a in anomalies if a["severity"] == "medium"),
        "low_count": sum(1 for a in anomalies if a["severity"] == "low")
    }


def _detect_large_transactions(transactions, current_date):
    """
    Flags individual transactions that are significantly larger
    than the user's average transaction size.
    """
    anomalies = []

    expenses = [t for t in transactions if t.get("type") == "expense"]
    if len(expenses) < 5:
        return anomalies

    amounts = [float(t["amount"]) for t in expenses]
    avg = statistics.mean(amounts)
    std = statistics.stdev(amounts) if len(amounts) > 1 else 0

    if std == 0:
        return anomalies

    # Check recent transactions (last 7 days)
    recent_cutoff = current_date - timedelta(days=7)

    for t in expenses:
        txn_date = t["date"] if isinstance(t["date"], date) else date.fromisoformat(str(t["date"]))

        if txn_date < recent_cutoff:
            continue

        amount = float(t["amount"])
        z_score = (amount - avg) / std if std > 0 else 0

        if z_score > 2.0:
            multiplier = round(amount / avg, 1)
            anomalies.append({
                "type": "large_transaction",
                "severity": "high" if z_score > 3 else "medium",
                "date": txn_date.isoformat(),
                "description": t.get("description", ""),
                "category": t.get("category", "Other"),
                "amount": round(amount, 2),
                "average_amount": round(avg, 2),
                "multiplier": multiplier,
                "message": f"£{amount:.2f} at {t.get('description', 'unknown')}: that's {multiplier}x your average transaction of £{avg:.2f}."
            })

    return anomalies


def _detect_category_spikes(transactions, current_date):
    """
    Identifies categories where current month spending is
    significantly above the historical monthly average.
    """
    anomalies = []

    current_month = current_date.month
    current_year = current_date.year

    # Split into current and historical
    current_by_cat = defaultdict(float)
    historical_by_cat = defaultdict(lambda: defaultdict(float))

    for t in transactions:
        if t.get("type") != "expense":
            continue

        txn_date = t["date"] if isinstance(t["date"], date) else date.fromisoformat(str(t["date"]))
        amount = float(t["amount"])
        category = t.get("category", "Other")

        if txn_date.month == current_month and txn_date.year == current_year:
            current_by_cat[category] += amount
        else:
            key = f"{txn_date.year}-{txn_date.month:02d}"
            historical_by_cat[category][key] += amount

    # Aggregate historical into monthly averages per category
    cat_monthly_totals = {}
    for category, months in historical_by_cat.items():
        cat_monthly_totals[category] = list(months.values())

    # Compare current to historical
    day_of_month = current_date.day
    import calendar
    days_in_month = calendar.monthrange(current_year, current_month)[1]
    month_progress = day_of_month / days_in_month

    for category, current_total in current_by_cat.items():
        hist_totals = cat_monthly_totals.get(category, [])

        if len(hist_totals) < 2:
            continue

        hist_avg = statistics.mean(hist_totals)

        if hist_avg <= 0:
            continue

        # Project current month total
        projected = current_total / month_progress if month_progress > 0.1 else current_total

        # How far above average is the projected total?
        deviation = (projected - hist_avg) / hist_avg * 100

        if deviation > 50:
            anomalies.append({
                "type": "category_spike",
                "severity": "high" if deviation > 100 else "medium",
                "category": category,
                "current_spent": round(current_total, 2),
                "projected_total": round(projected, 2),
                "historical_average": round(hist_avg, 2),
                "deviation_percent": round(deviation, 1),
                "date": current_date.isoformat(),
                "message": f"Your {category} spending is on track to hit £{projected:.2f} this month, {deviation:.0f}% above your average of £{hist_avg:.2f}."
            })

    return anomalies


def _detect_new_merchants(transactions, current_date):
    """
    Flags merchants that appear for the first time in recent
    transactions. New recurring charges could be accidental
    subscriptions.
    """
    anomalies = []

    recent_cutoff = current_date - timedelta(days=14)
    historical_cutoff = current_date - timedelta(days=90)

    historical_merchants = set()
    recent_new = []

    for t in transactions:
        if t.get("type") != "expense":
            continue

        txn_date = t["date"] if isinstance(t["date"], date) else date.fromisoformat(str(t["date"]))
        merchant = (t.get("merchant") or t.get("description", "")).lower().strip()

        if not merchant:
            continue

        if txn_date < recent_cutoff:
            historical_merchants.add(merchant)
        elif txn_date >= recent_cutoff and merchant not in historical_merchants:
            recent_new.append(t)

    # Only flag new merchants with significant amounts
    for t in recent_new:
        amount = float(t["amount"])
        if amount >= 15:
            txn_date = t["date"] if isinstance(t["date"], date) else date.fromisoformat(str(t["date"]))
            anomalies.append({
                "type": "new_merchant",
                "severity": "low",
                "date": txn_date.isoformat(),
                "description": t.get("description", ""),
                "merchant": t.get("merchant", t.get("description", "")),
                "amount": round(amount, 2),
                "category": t.get("category", "Other"),
                "message": f"First time spending at {t.get('description', 'this merchant')}: £{amount:.2f}. New subscription?"
            })

    return anomalies


def _detect_frequency_changes(transactions, current_date):
    """
    Detects when the user is making transactions more frequently
    than their historical average.
    """
    anomalies = []

    expenses = [t for t in transactions if t.get("type") == "expense"]
    if len(expenses) < 14:
        return anomalies

    # Count transactions per week for historical and recent
    current_week_start = current_date - timedelta(days=7)
    historical_weeks = defaultdict(int)

    recent_count = 0

    for t in expenses:
        txn_date = t["date"] if isinstance(t["date"], date) else date.fromisoformat(str(t["date"]))

        if txn_date >= current_week_start:
            recent_count += 1
        else:
            week_number = (current_date - txn_date).days // 7
            if week_number > 0:
                historical_weeks[week_number] += 1

    if not historical_weeks:
        return anomalies

    weekly_counts = list(historical_weeks.values())
    avg_weekly = statistics.mean(weekly_counts)

    if avg_weekly <= 0:
        return anomalies

    if recent_count > avg_weekly * 1.5 and recent_count > avg_weekly + 3:
        anomalies.append({
            "type": "frequency_spike",
            "severity": "low",
            "recent_count": recent_count,
            "average_weekly": round(avg_weekly, 1),
            "date": current_date.isoformat(),
            "message": f"You've made {recent_count} transactions this week, vs your usual {avg_weekly:.0f}. More frequent than normal."
        })

    return anomalies


def _detect_quiet_periods(transactions, current_date):
    """
    Detects when the user has been spending significantly less
    than normal — potential savings opportunity.
    """
    anomalies = []

    expenses = [t for t in transactions if t.get("type") == "expense"]
    if len(expenses) < 14:
        return anomalies

    # Compare last 7 days spending to weekly average
    week_cutoff = current_date - timedelta(days=7)
    recent_total = 0
    historical_weeks = defaultdict(float)

    for t in expenses:
        txn_date = t["date"] if isinstance(t["date"], date) else date.fromisoformat(str(t["date"]))
        amount = float(t["amount"])

        if txn_date >= week_cutoff:
            recent_total += amount
        else:
            week_number = (current_date - txn_date).days // 7
            if week_number > 0:
                historical_weeks[week_number] += amount

    if not historical_weeks:
        return anomalies

    weekly_totals = list(historical_weeks.values())
    avg_weekly = statistics.mean(weekly_totals)

    if avg_weekly <= 0:
        return anomalies

    savings_amount = avg_weekly - recent_total

    if recent_total < avg_weekly * 0.5 and savings_amount > 20:
        anomalies.append({
            "type": "quiet_period",
            "severity": "low",
            "recent_total": round(recent_total, 2),
            "average_weekly": round(avg_weekly, 2),
            "saved_amount": round(savings_amount, 2),
            "date": current_date.isoformat(),
            "message": f"You've spent £{recent_total:.2f} this week, £{savings_amount:.2f} less than your usual £{avg_weekly:.2f}. Nice restraint."
        })

    return anomalies


def get_anomaly_summary(anomalies_result):
    """
    Generates a brief summary for the dashboard whisper.
    """
    if anomalies_result["count"] == 0:
        return None

    parts = []

    high = [a for a in anomalies_result["anomalies"] if a["severity"] == "high"]
    if high:
        parts.append(high[0]["message"])

    medium = [a for a in anomalies_result["anomalies"] if a["severity"] == "medium"]
    if medium and not high:
        parts.append(medium[0]["message"])

    quiet = [a for a in anomalies_result["anomalies"] if a["type"] == "quiet_period"]
    if quiet:
        parts.append(quiet[0]["message"])

    return " ".join(parts[:2]) if parts else None