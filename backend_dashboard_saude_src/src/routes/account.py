from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from src.models.user import db, User
from src.models.user_profile import UserProfile

account_bp = Blueprint("account_bp", __name__)

@account_bp.get("/account/me")
@jwt_required()
def get_me():
    user_id = get_jwt_identity()
    claims = get_jwt() or {}

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404

    profile = UserProfile.query.get(user_id)
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.session.add(profile)
        db.session.commit()

    tenant = {
        "slug": claims.get("tenant", "br"),
        "scope_type": claims.get("tenant_scope_type", "BR"),
        "scope_value": claims.get("tenant_scope_value", "all"),
    }

    return jsonify({
        "user": user.to_dict() if hasattr(user, "to_dict") else {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "role": user.role,
            "is_active": getattr(user, "is_active", True),
        },
        "profile": profile.to_dict(),
        "tenant": tenant,
    }), 200


@account_bp.put("/account/me")
@jwt_required()
def update_me():
    user_id = get_jwt_identity()
    payload = request.get_json(silent=True) or {}

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404

    profile = UserProfile.query.get(user_id)
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.session.add(profile)

    # Campos permitidos
    if "first_name" in payload:
        user.first_name = str(payload["first_name"])[:50]
    if "last_name" in payload:
        user.last_name = str(payload["last_name"])[:50]

    if "phone" in payload:
        profile.phone = str(payload["phone"])[:30] if payload["phone"] else None
    if "location" in payload:
        profile.location = str(payload["location"])[:120] if payload["location"] else None
    if "about" in payload:
        profile.about = str(payload["about"]) if payload["about"] else None

    if "avatar_url" in payload:
        profile.avatar_url = str(payload["avatar_url"])[:255] if payload["avatar_url"] else None
    if "theme" in payload:
        theme = str(payload["theme"]).lower()
        if theme not in ("light", "dark", "system"):
            return jsonify({"error": "theme inválido (light|dark|system)"}), 400
        profile.theme = theme

    db.session.commit()
    return jsonify({"success": True}), 200