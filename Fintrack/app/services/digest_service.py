"""
Weekly digest data builder.

Takes a User object and all pre-computed insight data, returns a structured
dict ready to be rendered into an email. No sending logic here — that lives
in email_service.py.
"""

from datetime import date
import calendar


def build_weekly_digest(user, txn_list, whisper_data):
    """
    Builds the weekly digest payload for a single user.

    Returns None if the user has no meaningful data to report.
    Only call this for users who have opted in to email (no opt-out
    mechanism exists yet — assumed opted-in on registration).
    """
    total_txns = whisper_data.get("total_transactions", 0)
    if total_txns == 0:
        return None

    today = date.today()
    month_name = today.strftime("%B")

    # ── Goal status ──────────────────────────────────────────────
    goals = whisper_data.get("goals", [])
    active_goals = [g for g in goals if g.get("status") == "active"]
    primary_goal = active_goals[0] if active_goals else None

    goal_line = None
    if primary_goal and primary_goal.get("target_amount"):
        progress = primary_goal.get("progress_percent", 0) or 0
        name = primary_goal.get("name", "your goal")
        current = primary_goal.get("current_amount", 0) or 0
        target = primary_goal.get("target_amount", 0)
        goal_line = {
            "name": name,
            "progress": progress,
            "current": float(current),
            "target": float(target),
        }

    # ── Spending status ──────────────────────────────────────────
    predictions = whisper_data.get("predictions", {})
    comparison = predictions.get("comparison", {})
    spending_status = comparison.get("status", "")
    spending_diff = abs(comparison.get("difference", 0))

    spending_line = None
    if spending_status == "spending_high" and spending_diff > 0:
        spending_line = {
            "direction": "above",
            "amount": round(spending_diff, 2),
            "label": f"£{spending_diff:.2f} above your usual pace for {month_name}",
        }
    elif spending_status == "spending_low" and spending_diff > 0:
        spending_line = {
            "direction": "below",
            "amount": round(spending_diff, 2),
            "label": f"£{spending_diff:.2f} below your usual pace, a lighter week",
        }

    # ── Whisper insight ──────────────────────────────────────────
    whisper = whisper_data.get("whisper")  # pre-computed by insight engine

    # ── Recurring summary ────────────────────────────────────────
    recurring = whisper_data.get("recurring", {})
    recurring_count = recurring.get("expense_count", 0)
    recurring_total = recurring.get("total_monthly_cost", 0)

    # ── Subject line — personalised to something that changed ────
    if spending_line and spending_line["direction"] == "above":
        subject = f"You're spending a little fast this week, {user.name.split()[0]}"
    elif goal_line and goal_line["progress"] >= 90:
        subject = f"Almost there: {goal_line['name']} is {goal_line['progress']}% funded"
    elif goal_line and goal_line["progress"] >= 50:
        subject = f"Over halfway to {goal_line['name']}. Your Claro update."
    elif spending_line and spending_line["direction"] == "below":
        subject = f"Good week, {user.name.split()[0]}. You're under pace."
    else:
        subject = f"Your Claro update, {today.strftime('%d %b')}"

    return {
        "user_name": user.name.split()[0],
        "user_email": user.email,
        "subject": subject,
        "goal_line": goal_line,
        "spending_line": spending_line,
        "whisper": whisper,
        "recurring_count": recurring_count,
        "recurring_total": recurring_total,
        "month_name": month_name,
        "generated_on": today.strftime("%A %-d %B"),
    }


def render_digest_html(digest):
    """
    Renders the digest dict into an inline-styled HTML email string.
    All CSS is inline — required for Gmail and Outlook compatibility.
    """
    if not digest:
        return None

    first_name = digest["user_name"]
    subject = digest["subject"]
    goal = digest.get("goal_line")
    spending = digest.get("spending_line")
    whisper = digest.get("whisper")
    recurring_count = digest.get("recurring_count", 0)
    recurring_total = digest.get("recurring_total", 0)
    generated_on = digest.get("generated_on", "")

    # Goal block
    goal_block = ""
    if goal:
        bar_width = min(int(goal["progress"]), 100)
        goal_block = f"""
        <tr>
          <td style="padding: 20px 0 0;">
            <p style="margin:0 0 6px; font-size:11px; text-transform:uppercase; letter-spacing:0.08em; color:#888;">Goal</p>
            <p style="margin:0 0 8px; font-size:15px; font-weight:600; color:#f5f0e8;">{goal['name']}</p>
            <p style="margin:0 0 10px; font-size:13px; color:#aaa;">
              £{goal['current']:,.2f} saved of £{goal['target']:,.2f} &nbsp;·&nbsp; {goal['progress']}%
            </p>
            <div style="background:#2a2a2a; border-radius:4px; height:6px; width:100%;">
              <div style="background:#c5a35d; border-radius:4px; height:6px; width:{bar_width}%;"></div>
            </div>
          </td>
        </tr>"""

    # Spending block
    spending_block = ""
    if spending:
        colour = "#e07a5f" if spending["direction"] == "above" else "#81b29a"
        spending_block = f"""
        <tr>
          <td style="padding: 20px 0 0;">
            <p style="margin:0 0 6px; font-size:11px; text-transform:uppercase; letter-spacing:0.08em; color:#888;">Spending pace</p>
            <p style="margin:0; font-size:14px; color:{colour};">{spending['label']}</p>
          </td>
        </tr>"""

    # Whisper block
    whisper_block = ""
    if whisper:
        whisper_block = f"""
        <tr>
          <td style="padding: 20px 0 0; border-top: 1px solid #2a2a2a; margin-top:20px;">
            <p style="margin:0 0 6px; font-size:11px; text-transform:uppercase; letter-spacing:0.08em; color:#888;">This week</p>
            <p style="margin:0; font-size:14px; color:#ccc; line-height:1.6;">{whisper}</p>
          </td>
        </tr>"""

    # Recurring block
    recurring_block = ""
    if recurring_count > 0:
        recurring_block = f"""
        <tr>
          <td style="padding: 16px 0 0;">
            <p style="margin:0; font-size:13px; color:#888;">
              {recurring_count} recurring payment{"s" if recurring_count != 1 else ""} · £{recurring_total:.2f}/month tracked automatically.
            </p>
          </td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0; padding:0; background:#0d0d0d; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0d0d0d; padding: 40px 20px;">
    <tr>
      <td align="center">
        <table width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;">

          <!-- Header -->
          <tr>
            <td style="padding-bottom: 32px;">
              <p style="margin:0 0 24px; font-size:13px; color:#666;">{generated_on}</p>
              <p style="margin:0 0 4px; font-size:11px; text-transform:uppercase; letter-spacing:0.12em; color:#c5a35d;">Claro</p>
              <p style="margin:0; font-size:22px; font-weight:600; color:#f5f0e8; line-height:1.3;">{subject}</p>
            </td>
          </tr>

          <!-- Main card -->
          <tr>
            <td style="background:#161616; border-radius:12px; padding: 24px; border: 1px solid #222;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <p style="margin:0; font-size:15px; color:#ddd; line-height:1.6;">
                      Hi {first_name}, here's where things stand.
                    </p>
                  </td>
                </tr>
                {goal_block}
                {spending_block}
                {whisper_block}
                {recurring_block}
              </table>
            </td>
          </tr>

          <!-- CTA -->
          <tr>
            <td style="padding: 24px 0 0; text-align:center;">
              <a href="https://getclaro.co.uk/overview"
                 style="display:inline-block; background:#c5a35d; color:#0d0d0d; font-size:13px; font-weight:600;
                        padding: 12px 28px; border-radius:8px; text-decoration:none; letter-spacing:0.02em;">
                Open Claro
              </a>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 28px 0 0; text-align:center;">
              <p style="margin:0 0 6px; font-size:11px; color:#555;">
                Sent by Daniel at Claro · <a href="https://getclaro.co.uk/unsubscribe" style="color:#555;">Unsubscribe</a>
              </p>
              <p style="margin:0; font-size:11px; color:#444;">Encrypted in transit · never sold · never shared</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    return html
