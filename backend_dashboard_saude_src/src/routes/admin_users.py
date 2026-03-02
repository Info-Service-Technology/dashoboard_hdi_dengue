# src/routes/admin_users.py

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_
from flask_cors import cross_origin
from src.models.user import db, User

admin_users_bp = Blueprint("admin_users", __name__)


# -------------------------------------------------
# Helper: valida admin
# -------------------------------------------------
def _require_admin():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return None, (jsonify({"error": "Usuário não encontrado"}), 404)

    if user.role != "admin":
        return None, (jsonify({"error": "Acesso restrito a administradores"}), 403)

    return user, None


# -------------------------------------------------
# LISTAR USUÁRIOS
# GET /api/admin/users
# -------------------------------------------------
@admin_users_bp.route("/admin/users", methods=["GET"])
@jwt_required()
def list_users():
    _, err = _require_admin()
    if err:
        return err

    search = (request.args.get("search") or "").strip()

    query = User.query

    if search:
        s = f"%{search}%"
        query = query.filter(
            or_(
                User.first_name.ilike(s),
                User.last_name.ilike(s),
                User.email.ilike(s),
            )
        )

    users = query.order_by(User.id.desc()).all()

    return jsonify([u.to_dict() for u in users]), 200


# -------------------------------------------------
# CRIAR USUÁRIO
# POST /api/admin/users
# -------------------------------------------------
@admin_users_bp.route("/admin/users", methods=["POST"])
@jwt_required()
def create_user():
    _, err = _require_admin()
    if err:
        return err

    data = request.get_json() or {}

    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()
    role = (data.get("role") or "guest").strip()

    if not first_name or not last_name or not email or not password:
        return jsonify({"error": "Campos obrigatórios: first_name, last_name, email, password"}), 400

    if role not in ["admin", "guest"]:
        return jsonify({"error": "Role inválido (admin ou guest)"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email já cadastrado"}), 400

    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        role=role,
        is_active=True
    )

    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return jsonify(user.to_dict()), 201


# -------------------------------------------------
# ATIVAR / DESATIVAR
# PATCH /api/admin/users/<id>/status
# -------------------------------------------------
@admin_users_bp.route("/admin/users/<int:user_id>/status", methods=["PATCH"])
@cross_origin(origins='http://localhost:5173', methods=['PATCH', 'OPTIONS'])
@jwt_required()
def set_user_status(user_id):
    _, err = _require_admin()
    if err:
        return err

    data = request.get_json() or {}
    is_active = data.get("is_active")

    if is_active is None:
        return jsonify({"error": "Campo 'is_active' é obrigatório (true/false)"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404

    user.is_active = bool(is_active)
    db.session.commit()

    return jsonify({"ok": True}), 200


# -------------------------------------------------
# REMOVER USUÁRIO
# DELETE /api/admin/users/<id>
# -------------------------------------------------
@admin_users_bp.route("/admin/users/<int:user_id>", methods=["DELETE"])
@jwt_required()
def delete_user(user_id):
    _, err = _require_admin()
    if err:
        return err

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404

    db.session.delete(user)
    db.session.commit()

    return jsonify({"ok": True}), 200