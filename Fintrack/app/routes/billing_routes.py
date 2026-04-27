import logging
from datetime import datetime, timedelta

import stripe
from flask import Blueprint, abort, current_app, flash, redirect, request, url_for
from flask_login import current_user, login_required

from app import csrf, db, limiter
from app.models.user import User
from app.services.stripe_service import (
    init_stripe,
    price_id_for_plan,
    tier_for_price_id,
    webhook_secret,
)


billing_bp = Blueprint("billing", __name__)

logger = logging.getLogger(__name__)


@billing_bp.route("/checkout/<plan>")
@login_required
@limiter.limit("10 per minute")
def checkout(plan):
    price_id = price_id_for_plan(plan)
    if not price_id:
        flash("That plan isn't available.", "error")
        return redirect(url_for("pages.trial_gate"))

    if not init_stripe():
        flash("Payments are temporarily unavailable. Please try again shortly.", "error")
        return redirect(url_for("pages.trial_gate"))

    session_kwargs = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "subscription_data": {"trial_period_days": 14},
        "success_url": url_for("pages.overview", _external=True) + "?checkout=success",
        "cancel_url": url_for("pages.trial_gate", _external=True),
        "metadata": {"user_id": str(current_user.id)},
        "allow_promotion_codes": True,
    }

    if current_user.stripe_customer_id:
        session_kwargs["customer"] = current_user.stripe_customer_id
    else:
        session_kwargs["customer_email"] = current_user.email

    try:
        session = stripe.checkout.Session.create(**session_kwargs)
    except stripe.error.StripeError:
        logger.exception("Stripe checkout session failed for user %s", current_user.id)
        flash("We couldn't start checkout. Please try again.", "error")
        return redirect(url_for("pages.trial_gate"))

    return redirect(session.url, code=303)


@billing_bp.route("/billing")
@login_required
def billing_portal():
    if not current_user.stripe_customer_id:
        flash("You don't have a subscription yet.", "info")
        return redirect(url_for("pages.trial_gate"))

    if not init_stripe():
        flash("The billing portal is temporarily unavailable.", "error")
        return redirect(url_for("pages.settings"))

    try:
        session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=url_for("pages.settings", _external=True),
        )
    except stripe.error.StripeError:
        logger.exception("Stripe billing portal failed for user %s", current_user.id)
        flash("We couldn't open the billing portal. Please try again.", "error")
        return redirect(url_for("pages.settings"))

    return redirect(session.url, code=303)


@csrf.exempt
@limiter.exempt
@billing_bp.route("/stripe/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")

    secret = webhook_secret()
    if not secret or not init_stripe():
        logger.warning("Stripe webhook invoked without configured secret/key")
        abort(400)

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, secret)
    except ValueError:
        abort(400)
    except stripe.error.SignatureVerificationError:
        abort(400)

    try:
        _handle_event(event)
    except Exception:
        logger.exception("Error handling Stripe event %s", event.get("id"))

    return ("", 200)


def _handle_event(event):
    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {}) or {}

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(data)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data)
    elif event_type == "invoice.paid":
        _handle_invoice_paid(data)
    elif event_type == "invoice.payment_failed":
        _handle_invoice_failed(data)


def _user_from_session(session):
    metadata = session.get("metadata") or {}
    user_id = metadata.get("user_id")
    if user_id:
        try:
            user = db.session.get(User, int(user_id))
            if user:
                return user
        except (TypeError, ValueError):
            pass

    customer_id = session.get("customer")
    if customer_id:
        return User.query.filter_by(stripe_customer_id=customer_id).first()
    return None


def _user_from_customer(customer_id):
    if not customer_id:
        return None
    return User.query.filter_by(stripe_customer_id=customer_id).first()


def _first_price_id(subscription_obj):
    items = (subscription_obj.get("items") or {}).get("data") or []
    if not items:
        return None
    price = items[0].get("price") or {}
    return price.get("id")


def _handle_checkout_completed(session):
    user = _user_from_session(session)
    if not user:
        logger.warning("checkout.session.completed without matching user: %s", session.get("id"))
        return

    customer_id = session.get("customer")
    subscription_id = session.get("subscription")

    if customer_id:
        user.stripe_customer_id = customer_id
    if subscription_id:
        user.stripe_subscription_id = subscription_id

        try:
            sub = stripe.Subscription.retrieve(subscription_id)
            price_id = _first_price_id(sub)
            if price_id:
                user.subscription_tier = tier_for_price_id(price_id)
        except stripe.error.StripeError:
            logger.exception("Could not retrieve subscription %s", subscription_id)

    user.subscription_status = "trialing"
    user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
    db.session.commit()


def _handle_subscription_updated(subscription):
    customer_id = subscription.get("customer")
    user = _user_from_customer(customer_id)
    if not user:
        return

    price_id = _first_price_id(subscription)
    if price_id:
        user.subscription_tier = tier_for_price_id(price_id)

    status = subscription.get("status")
    if status:
        user.subscription_status = status

    sub_id = subscription.get("id")
    if sub_id:
        user.stripe_subscription_id = sub_id

    db.session.commit()


def _handle_subscription_deleted(subscription):
    customer_id = subscription.get("customer")
    user = _user_from_customer(customer_id)
    if not user:
        return

    user.subscription_tier = "free"
    user.subscription_status = "canceled"
    user.stripe_subscription_id = None
    db.session.commit()


def _handle_invoice_paid(invoice):
    customer_id = invoice.get("customer")
    user = _user_from_customer(customer_id)
    if not user:
        return

    user.subscription_status = "active"
    db.session.commit()


def _handle_invoice_failed(invoice):
    customer_id = invoice.get("customer")
    user = _user_from_customer(customer_id)
    if not user:
        return

    user.subscription_status = "past_due"
    db.session.commit()
