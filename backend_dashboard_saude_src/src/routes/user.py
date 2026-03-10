from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import or_

from src.models.user import User, db
from src.models.tenant import Tenant, UserTenant

user_bp = Blueprint("user", __name__)


# =========================================================
# HELPERS
# =========================================================

def _jwt_ctx():
    claims = get_jwt() or {}
    return {
        "role": (claims.get("role") or "").strip().lower(),
        "tenant_slug": (claims.get("tenant") or "br").strip().lower(),
        "scope_type": (claims.get("tenant_scope_type") or "BR").strip().upper(),
        "scope_value": str(claims.get("tenant_scope_value") or "all").strip(),
    }


def _is_admin():
    return _jwt_ctx()["role"] == "admin"


def _is_global_admin():
    """
    Regra conservadora:
    - admin no tenant BR = admin global
    - admin em tenant municipal/UF = admin local
    """
    ctx = _jwt_ctx()
    return ctx["role"] == "admin" and ctx["tenant_slug"] == "br"


def _get_tenant_by_slug(slug: str):
    return (
        Tenant.query.filter(db.func.lower(Tenant.slug) == (slug or "").strip().lower())
        .filter(Tenant.is_active == True)
        .first()
    )


def _user_belongs_to_tenant(user_id: int, tenant_slug: str) -> bool:
    return (
        db.session.query(UserTenant)
        .join(Tenant, Tenant.id == UserTenant.tenant_id)
        .filter(
            UserTenant.user_id == user_id,
            db.func.lower(Tenant.slug) == (tenant_slug or "").strip().lower(),
        )
        .first()
        is not None
    )


def _scoped_users_query(search: str = ""):
    """
    Admin global:
      - vê todos os usuários
      - pode opcionalmente filtrar por tenant via ?tenant_slug=
    Admin local:
      - vê somente usuários vinculados ao tenant do JWT
    """
    ctx = _jwt_ctx()

    q = (
        db.session.query(User)
        .distinct()
        .outerjoin(UserTenant, UserTenant.user_id == User.id)
        .outerjoin(Tenant, Tenant.id == UserTenant.tenant_id)
    )

    if search:
        like = f"%{search}%"
        q = q.filter(
            or_(
                User.first_name.ilike(like),
                User.last_name.ilike(like),
                User.email.ilike(like),
            )
        )

    if _is_global_admin():
        tenant_filter = (request.args.get("tenant_slug") or "").strip().lower()
        if tenant_filter:
            q = q.filter(db.func.lower(Tenant.slug) == tenant_filter)
    else:
        q = q.filter(db.func.lower(Tenant.slug) == ctx["tenant_slug"])

    return q


def _serialize_user_admin(u: User):
    """
    Mantém compatibilidade com a UI e inclui tenants quando útil.
    """
    tenant_rows = (
        db.session.query(Tenant.slug, Tenant.name)
        .join(UserTenant, UserTenant.tenant_id == Tenant.id)
        .filter(UserTenant.user_id == u.id)
        .order_by(Tenant.slug.asc())
        .all()
    )

    payload = u.to_dict()
    payload["tenants"] = [{"slug": slug, "name": name} for slug, name in tenant_rows]
    return payload


def _can_manage_target_user(target_user_id: int) -> bool:
    """
    Admin global pode gerenciar qualquer usuário.
    Admin local só pode gerenciar usuário do próprio tenant.
    """
    if _is_global_admin():
        return True

    ctx = _jwt_ctx()
    return _user_belongs_to_tenant(target_user_id, ctx["tenant_slug"])


# =========================================================
# ROTAS LEGADAS / BÁSICAS
# =========================================================
# Mantidas com @jwt_required para reduzir exposição indevida.
# Se você não usa essas rotas no frontend atual, pode depois descontinuá-las.

@user_bp.route("/users", methods=["GET"])
@jwt_required()
def get_users():
    if not _is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    users = _scoped_users_query().order_by(User.created_at.desc()).all()
    return jsonify([_serialize_user_admin(user) for user in users]), 200


@user_bp.route("/users", methods=["POST"])
@jwt_required()
def create_user():
    if not _is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    data = request.get_json(silent=True) or {}

    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "123456").strip()
    role = (data.get("role") or "guest").strip().lower()

    if not first_name or not last_name or not email:
        return jsonify({"error": "first_name, last_name e email são obrigatórios"}), 400

    if "@" not in email:
        return jsonify({"error": "email inválido"}), 400

    if role not in ("admin", "guest"):
        return jsonify({"error": "role inválido (use admin|guest)"}), 400

    exists = User.query.filter(db.func.lower(User.email) == email).first()
    if exists:
        return jsonify({"error": "Email já cadastrado"}), 409

    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        role=role,
        is_active=True,
    )
    user.set_password(password)

    db.session.add(user)
    db.session.flush()

    ctx = _jwt_ctx()

    # Admin global pode informar tenant_slug; admin local cria sempre no tenant atual
    tenant_slug = (
        (data.get("tenant_slug") or "").strip().lower()
        if _is_global_admin()
        else ctx["tenant_slug"]
    ) or ctx["tenant_slug"]

    tenant = _get_tenant_by_slug(tenant_slug)
    if not tenant:
        db.session.rollback()
        return jsonify({"error": "Tenant inválido ou inativo"}), 400

    db.session.add(UserTenant(user_id=user.id, tenant_id=tenant.id))
    db.session.commit()

    return jsonify(_serialize_user_admin(user)), 201


@user_bp.route("/users/<int:user_id>", methods=["GET"])
@jwt_required()
def get_user(user_id):
    if not _is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    if not _can_manage_target_user(user_id):
        return jsonify({"error": "Acesso negado ao usuário fora do tenant"}), 403

    user = User.query.get_or_404(user_id)
    return jsonify(_serialize_user_admin(user)), 200


@user_bp.route("/users/<int:user_id>", methods=["PUT"])
@jwt_required()
def update_user(user_id):
    if not _is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    if not _can_manage_target_user(user_id):
        return jsonify({"error": "Acesso negado ao usuário fora do tenant"}), 403

    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}

    first_name = data.get("first_name")
    last_name = data.get("last_name")
    email = data.get("email")

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

        exists = User.query.filter(User.email == email, User.id != user.id).first()
        if exists:
            return jsonify({"error": "Email já está em uso"}), 409

        user.email = email

    db.session.commit()
    return jsonify(_serialize_user_admin(user)), 200


@user_bp.route("/users/<int:user_id>", methods=["DELETE"])
@jwt_required()
def delete_user(user_id):
    if not _is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    if not _can_manage_target_user(user_id):
        return jsonify({"error": "Acesso negado ao usuário fora do tenant"}), 403

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return "", 204


# =========================================================
# ROTAS ADMIN USADAS PELA UI
# =========================================================

@user_bp.route("/admin/users", methods=["GET"])
@jwt_required()
def admin_list_users():
    if not _is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    search = (request.args.get("search") or "").strip().lower()

    users = _scoped_users_query(search=search).order_by(User.created_at.desc()).all()
    return jsonify([_serialize_user_admin(u) for u in users]), 200


@user_bp.route("/admin/users/<int:user_id>", methods=["PATCH"])
@jwt_required()
def admin_update_user(user_id: int):
    if not _is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    if not _can_manage_target_user(user_id):
        return jsonify({"error": "Acesso negado ao usuário fora do tenant"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404

    data = request.get_json(silent=True) or {}

    first_name = data.get("first_name")
    last_name = data.get("last_name")
    email = data.get("email")
    role = data.get("role")
    password = data.get("password")

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

        exists = User.query.filter(User.email == email, User.id != user.id).first()
        if exists:
            return jsonify({"error": "Email já está em uso"}), 409

        user.email = email

    # Admin local pode continuar ajustando role dentro do próprio tenant.
    # Se quiser endurecer depois, podemos restringir isso ao admin global.
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
    return jsonify(_serialize_user_admin(user)), 200


@user_bp.route("/admin/users/<int:user_id>/status", methods=["PATCH"])
@jwt_required()
def admin_toggle_user_status(user_id: int):
    if not _is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    if not _can_manage_target_user(user_id):
        return jsonify({"error": "Acesso negado ao usuário fora do tenant"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404

    data = request.get_json(silent=True) or {}
    if "is_active" not in data:
        return jsonify({"error": "Informe is_active"}), 400

    user.is_active = bool(data["is_active"])
    db.session.commit()
    return jsonify(_serialize_user_admin(user)), 200


@user_bp.route("/admin/users/<int:user_id>", methods=["DELETE"])
@jwt_required()
def admin_delete_user(user_id: int):
    if not _is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    if not _can_manage_target_user(user_id):
        return jsonify({"error": "Acesso negado ao usuário fora do tenant"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({"ok": True}), 200