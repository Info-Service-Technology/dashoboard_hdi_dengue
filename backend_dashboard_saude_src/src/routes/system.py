from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import db, User
from src.models.system_settings import SystemSettings

system_bp = Blueprint("system_bp", __name__)

def _require_admin(user_id: int):
    user = User.query.get(user_id)
    if not user:
        return None, (jsonify({"error": "Usuário não encontrado"}), 404)
    if user.role != "admin":
        return None, (jsonify({"error": "Acesso negado (admin)"}), 403)
    return user, None

@system_bp.get("/system/settings")
@jwt_required()
def get_settings():
    user_id = get_jwt_identity()
    _, err = _require_admin(user_id)
    if err:
        return err

    settings = SystemSettings.query.get(1)
    if not settings:
        settings = SystemSettings(id=1)
        db.session.add(settings)
        db.session.commit()

    return jsonify(settings.to_dict()), 200

@system_bp.put("/system/settings")
@jwt_required()
def update_settings():
    user_id = get_jwt_identity()
    _, err = _require_admin(user_id)
    if err:
        return err

    payload = request.get_json(silent=True) or {}

    settings = SystemSettings.query.get(1)
    if not settings:
        settings = SystemSettings(id=1)
        db.session.add(settings)

    # Campos permitidos
    if "app_name" in payload:
        settings.app_name = str(payload["app_name"])[:120]
    if "default_language" in payload:
        settings.default_language = str(payload["default_language"])[:10]
    if "timezone" in payload:
        settings.timezone = str(payload["timezone"])[:64]

    if "enable_notifications" in payload:
        settings.enable_notifications = bool(payload["enable_notifications"])
    if "enable_audit_log" in payload:
        settings.enable_audit_log = bool(payload["enable_audit_log"])

    if "data_refresh_minutes" in payload:
        settings.data_refresh_minutes = int(payload["data_refresh_minutes"])
    if "maps_default_zoom" in payload:
        settings.maps_default_zoom = int(payload["maps_default_zoom"])

    if "theme_default" in payload:
        theme = str(payload["theme_default"]).lower()
        if theme not in ("light", "dark", "system"):
            return jsonify({"error": "theme_default inválido (light|dark|system)"}), 400
        settings.theme_default = theme

    settings.updated_by_user_id = user_id
    db.session.commit()

    return jsonify({"success": True}), 200