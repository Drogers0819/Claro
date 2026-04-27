from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from app import db, limiter
from app.models.chat import ChatMessage
from app.models.goal import Goal
from app.services.companion_service import chat, check_rate_limit, increment_message_count
from app.services.planner_service import generate_financial_plan
from app.utils.auth import requires_subscription
from app.utils.validators import sanitize_string

companion_bp = Blueprint("companion", __name__)


@companion_bp.route("/companion")
@login_required
@requires_subscription
def companion_page():
    """Render the companion chat UI."""
    allowed, reason = check_rate_limit(current_user)
    messages_used = current_user.companion_messages_today or 0
    limit = current_user.daily_message_limit

    # Load recent chat history
    recent_messages = ChatMessage.query.filter_by(
        user_id=current_user.id
    ).order_by(ChatMessage.created_at.desc()).limit(20).all()
    recent_messages.reverse()

    return render_template("companion.html",
        allowed=allowed,
        reason=reason,
        messages_used=messages_used,
        daily_limit=limit,
        chat_history=recent_messages,
        tier=current_user.subscription_tier or "free"
    )


@companion_bp.route("/api/companion/edit", methods=["POST"])
@login_required
def edit_message():
    """Edit an existing user message and regenerate the AI response."""
    data = request.get_json(silent=True) or {}
    message_id = data.get("message_id")
    new_content = sanitize_string(data.get("new_content") or "", max_length=2000)

    if not message_id or not new_content:
        return jsonify({"error": "message_id and new_content required"}), 400

    # Verify ownership
    user_msg = ChatMessage.query.filter_by(
        id=message_id, user_id=current_user.id, role="user"
    ).first()
    if not user_msg:
        return jsonify({"error": "Message not found"}), 404

    # Rate limit check
    allowed, reason = check_rate_limit(current_user)
    if not allowed:
        return jsonify({"error": reason, "allowed": False}), 429

    # Delete the message and everything after it (re-generates from that point)
    ChatMessage.query.filter_by(user_id=current_user.id).filter(
        ChatMessage.id >= message_id
    ).delete()
    db.session.flush()

    # Load remaining history
    recent = ChatMessage.query.filter_by(
        user_id=current_user.id
    ).order_by(ChatMessage.created_at.desc()).limit(10).all()
    recent.reverse()
    conversation_history = [{"role": m.role, "content": m.content} for m in recent]

    # Build plan context
    plan = None
    if current_user.factfind_completed and current_user.monthly_income:
        user_profile = current_user.profile_dict()
        goals_data = [g.to_dict() for g in Goal.query.filter_by(
            user_id=current_user.id, status="active"
        ).order_by(Goal.priority_rank.asc()).all()]
        plan = generate_financial_plan(user_profile, goals_data)

    result = chat(
        user=current_user,
        message=new_content,
        plan=plan,
        conversation_history=conversation_history
    )

    new_user_msg = ChatMessage(user_id=current_user.id, role="user", content=new_content)
    db.session.add(new_user_msg)
    new_assistant_msg = ChatMessage(
        user_id=current_user.id, role="assistant",
        content=result["response"],
        model_used=result.get("model_used"),
        tokens_in=result.get("tokens_in", 0),
        tokens_out=result.get("tokens_out", 0)
    )
    db.session.add(new_assistant_msg)
    increment_message_count(current_user)
    db.session.commit()

    return jsonify({
        "response": result["response"],
        "user_message_id": new_user_msg.id,
        "allowed": True
    })


@companion_bp.route("/api/companion/clear", methods=["POST"])
@login_required
def clear_chat():
    """Delete all chat history for the current user."""
    ChatMessage.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({"success": True})


@companion_bp.route("/api/companion/chat", methods=["POST"])
@login_required
@limiter.limit("30 per day")
@requires_subscription
def companion_chat():
    """Handle a chat message to the companion."""
    # Rate limit check
    allowed, reason = check_rate_limit(current_user)
    if not allowed:
        return jsonify({"error": reason, "allowed": False}), 429

    data = request.get_json(silent=True) or {}
    raw_message = data.get("message")
    if not raw_message or not str(raw_message).strip():
        return jsonify({"error": "Message is required"}), 400

    message = sanitize_string(raw_message, max_length=2000)
    if not message:
        return jsonify({"error": "Message is required"}), 400

    # Build plan context
    plan = None
    if current_user.factfind_completed and current_user.monthly_income:
        user_profile = current_user.profile_dict()
        goals_data = [g.to_dict() for g in Goal.query.filter_by(
            user_id=current_user.id, status="active"
        ).order_by(Goal.priority_rank.asc()).all()]
        plan = generate_financial_plan(user_profile, goals_data)

    # Load conversation history
    recent = ChatMessage.query.filter_by(
        user_id=current_user.id
    ).order_by(ChatMessage.created_at.desc()).limit(10).all()
    recent.reverse()

    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in recent
    ]

    # Send to companion
    result = chat(
        user=current_user,
        message=message,
        plan=plan,
        conversation_history=conversation_history
    )

    # Save user message
    user_msg = ChatMessage(
        user_id=current_user.id,
        role="user",
        content=message
    )
    db.session.add(user_msg)

    # Save assistant response
    assistant_msg = ChatMessage(
        user_id=current_user.id,
        role="assistant",
        content=result["response"],
        model_used=result.get("model_used"),
        tokens_in=result.get("tokens_in", 0),
        tokens_out=result.get("tokens_out", 0)
    )
    db.session.add(assistant_msg)

    # Increment rate limit counter
    increment_message_count(current_user)
    db.session.commit()

    return jsonify({
        "response": result["response"],
        "model": result.get("model_used"),
        "user_message_id": user_msg.id,
        "messages_used": current_user.companion_messages_today,
        "daily_limit": current_user.daily_message_limit,
        "allowed": True
    })