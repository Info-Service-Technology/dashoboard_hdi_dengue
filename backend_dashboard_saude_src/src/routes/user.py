from flask import Blueprint, jsonify, request
from src.models.user import User, db
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import or_

user_bp = Blueprint('user', __name__)

@user_bp.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@user_bp.route('/users', methods=['POST'])
def create_user():
    
    data = request.json
    user = User(username=data['username'], email=data['email'])
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201

@user_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())

@user_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.json
    user.username = data.get('username', user.username)
    user.email = data.get('email', user.email)
    db.session.commit()
    return jsonify(user.to_dict())

@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return '', 204

def _is_admin():
    # Ajuste conforme como você salva o role no JWT.
    # Opção A: você adiciona {"role": "..."} nas claims do JWT (recomendado).
    claims = get_jwt() or {}
    return (claims.get("role") or "").lower() == "admin"

@user_bp.route("/admin/users", methods=["GET"])
@jwt_required()
def admin_list_users():
    if not _is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    search = (request.args.get("search") or "").strip().lower()

    q = User.query
    if search:
        like = f"%{search}%"
        q = q.filter(
            or_(
                User.first_name.ilike(like),
                User.last_name.ilike(like),
                User.email.ilike(like),
            )
        )

    users = q.order_by(User.created_at.desc()).all()
    return jsonify([u.to_dict() for u in users]), 200


@user_bp.route("/admin/users/<int:user_id>", methods=["PATCH"])
@jwt_required()
def admin_update_user(user_id: int):
    if not _is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404

    data = request.get_json(silent=True) or {}

    # campos permitidos
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    email = data.get("email")
    role = data.get("role")
    password = data.get("password")  # opcional (se quiser suportar)

    # validações leves
    if first_name is not None:
        first_name = str(first_name).strip()
        if not first_name:
            return jsonify({"error": "first_name não pode ser vazio"}), 400
        user.first_name = first_name

    if last_name is not None:
        last_name = str(last_name).strip()
        if not last_name:
            return jsonify({"error": "last_name não pode ser vazio"}), 400
        user.last_name = last_name

    if email is not None:
        email = str(email).strip().lower()
        if not email or "@" not in email:
            return jsonify({"error": "email inválido"}), 400

        # checa duplicidade
        exists = User.query.filter(User.email == email, User.id != user.id).first()
        if exists:
            return jsonify({"error": "Email já está em uso"}), 409

        user.email = email

    if role is not None:
        role = str(role).strip().lower()
        if role not in ("admin", "guest"):
            return jsonify({"error": "role inválido (use admin|guest)"}), 400
        user.role = role

    if password is not None:
        password = str(password)
        if len(password) < 6:
            return jsonify({"error": "Senha deve ter pelo menos 6 caracteres"}), 400
        user.set_password(password)

    db.session.commit()
    return jsonify(user.to_dict()), 200


@user_bp.route("/admin/users/<int:user_id>/status", methods=["PATCH"])
@jwt_required()
def admin_toggle_user_status(user_id: int):
    if not _is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404

    data = request.get_json(silent=True) or {}
    if "is_active" not in data:
        return jsonify({"error": "Informe is_active"}), 400

    user.is_active = bool(data["is_active"])
    db.session.commit()
    return jsonify(user.to_dict()), 200


@user_bp.route("/admin/users/<int:user_id>", methods=["DELETE"])
@jwt_required()
def admin_delete_user(user_id: int):
    if not _is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({"ok": True}), 200