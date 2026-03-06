# src/routes/admin_users.py

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_, func
from flask_cors import cross_origin

from src.models.user import db, User
from src.models.tenant import Tenant, UserTenant

admin_users_bp = Blueprint("admin_users", __name__)

# -------------------------------------------------
# Helper: parse bool seguro
# -------------------------------------------------
def _to_bool(v, default=None):
    """
    Converte vários tipos para bool, com fallback seguro.
    - True/False -> mantém
    - 1/0 -> bool
    - "true"/"false" -> converte
    - caso inválido -> default
    """
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    s = str(v).strip().lower()
    if s in ("1", "true", "yes", "y", "on"):
        return True
    if s in ("0", "false", "no", "n", "off"):
        return False
    return default


# -------------------------------------------------
# Helper: valida admin
# -------------------------------------------------
def _require_admin():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return None, (jsonify({"error": "Usuário não encontrado"}), 404)

    if (user.role or "").strip().lower() != "admin":
        return None, (jsonify({"error": "Acesso restrito a administradores"}), 403)

    return user, None


def _tenant_slugs_for_user(user_id: int):
    rows = (
        db.session.query(Tenant.slug)
        .join(UserTenant, UserTenant.tenant_id == Tenant.id)
        .filter(UserTenant.user_id == user_id)
        .order_by(Tenant.slug.asc())
        .all()
    )
    return [r[0] for r in rows]


def _set_user_tenants(user_id: int, tenant_slugs):
    """
    Substitui os vínculos do usuário por tenant_slugs (somente tenants ativos).

    Guardrails:
    - Nunca deixar vazio: se vier vazio -> tenta "br"
    - Se mesmo assim não houver tenant válido/ativo -> ERRO (não aplica mudanças)
    """
    slugs = []
    if isinstance(tenant_slugs, list):
        slugs = [str(s).strip().lower() for s in tenant_slugs if str(s).strip()]
    slugs = list(dict.fromkeys(slugs))  # unique

    if len(slugs) == 0:
        slugs = ["br"]

    tenants = (
        Tenant.query
        .filter(func.lower(Tenant.slug).in_(slugs))
        .filter(Tenant.is_active == True)
        .all()
    )

    if not tenants:
        raise ValueError("Nenhum tenant válido/ativo foi encontrado para vincular ao usuário.")

    # remove vínculos atuais
    db.session.query(UserTenant).filter(UserTenant.user_id == user_id).delete()

    # recria
    for t in tenants:
        db.session.add(UserTenant(user_id=user_id, tenant_id=t.id))


# -------------------------------------------------
# LISTAR TENANTS (para modal)
# GET /api/admin/tenants
# -------------------------------------------------
@admin_users_bp.route("/admin/tenants", methods=["GET"])
@jwt_required()
def list_tenants():
    _, err = _require_admin()
    if err:
        return err

    rows = (
        Tenant.query
        .filter(Tenant.is_active == True)
        .order_by(Tenant.slug.asc())
        .all()
    )

    return jsonify([{"slug": t.slug, "name": t.name} for t in rows]), 200


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

    out = []
    for u in users:
        d = u.to_dict()
        d["tenants"] = _tenant_slugs_for_user(u.id)
        out.append(d)

    return jsonify(out), 200


# -------------------------------------------------
# CRIAR USUÁRIO
# POST /api/admin/users
# body: { first_name,last_name,email,password,role,is_active,tenant_slugs }
# -------------------------------------------------
@admin_users_bp.route("/admin/users", methods=["POST"])
@jwt_required()
def create_user():
    _, err = _require_admin()
    if err:
        return err

    data = request.get_json(silent=True) or {}

    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()
    role = (data.get("role") or "guest").strip().lower()
    is_active = _to_bool(data.get("is_active"), True)
    tenant_slugs = data.get("tenant_slugs")

    if not first_name or not last_name or not email or not password:
        return jsonify({"error": "Campos obrigatórios: first_name, last_name, email, password"}), 400

    if role not in ["admin", "guest"]:
        return jsonify({"error": "Role inválido (admin ou guest)"}), 400

    if User.query.filter(func.lower(User.email) == email).first():
        return jsonify({"error": "Email já cadastrado"}), 400

    try:
        user = User(
            first_name=first_name[:50],
            last_name=last_name[:50],
            email=email,
            role=role,
            is_active=bool(is_active),
        )
        user.set_password(password)

        db.session.add(user)
        db.session.flush()

        _set_user_tenants(user.id, tenant_slugs)

        db.session.commit()

        d = user.to_dict()
        d["tenants"] = _tenant_slugs_for_user(user.id)
        return jsonify(d), 201

    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erro ao criar usuário: {str(e)}"}), 500


# -------------------------------------------------
# EDITAR USUÁRIO (modal edit)
# PUT /api/admin/users/<id>
# body: { first_name,last_name,role,is_active,tenant_slugs }
# -------------------------------------------------
@admin_users_bp.route("/admin/users/<int:user_id>", methods=["PUT"])
@jwt_required()
def update_user(user_id):
    me, err = _require_admin()
    if err:
        return err

    data = request.get_json(silent=True) or {}

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404

    first_name = (data.get("first_name") or user.first_name or "").strip()
    last_name = (data.get("last_name") or user.last_name or "").strip()
    role = (data.get("role") or user.role or "guest").strip().lower()
    is_active = _to_bool(data.get("is_active"), getattr(user, "is_active", True))
    tenant_slugs = data.get("tenant_slugs")

    if not first_name or not last_name:
        return jsonify({"error": "Nome e sobrenome são obrigatórios"}), 400
    if role not in ["admin", "guest"]:
        return jsonify({"error": "Role inválido (admin ou guest)"}), 400

    # Guardrail: não permitir desativar você mesmo
    if int(user_id) == int(me.id) and _to_bool(data.get("is_active"), True) is False:
        return jsonify({"error": "Você não pode desativar seu próprio usuário."}), 400

    try:
        user.first_name = first_name[:50]
        user.last_name = last_name[:50]
        user.role = role
        user.is_active = bool(is_active)

        if tenant_slugs is not None:
            _set_user_tenants(user.id, tenant_slugs)

        db.session.commit()

        d = user.to_dict()
        d["tenants"] = _tenant_slugs_for_user(user.id)
        return jsonify(d), 200

    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erro ao atualizar usuário: {str(e)}"}), 500


# -------------------------------------------------
# COMPAT: toggle-active (adminUsersApi.js usa POST /toggle-active)
# POST /api/admin/users/<id>/toggle-active
# body: { is_active: true|false }
# -------------------------------------------------
@admin_users_bp.route("/admin/users/<int:user_id>/toggle-active", methods=["POST"])
@jwt_required()
def toggle_active(user_id):
    me, err = _require_admin()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    is_active = _to_bool(data.get("is_active"), None)
    if is_active is None:
        return jsonify({"error": "Campo 'is_active' é obrigatório (true/false)"}), 400

    # Guardrail: não permitir desativar você mesmo
    if int(user_id) == int(me.id) and is_active is False:
        return jsonify({"error": "Você não pode desativar seu próprio usuário."}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404

    try:
        user.is_active = bool(is_active)
        db.session.commit()
        return jsonify({"ok": True, "is_active": bool(user.is_active)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erro ao alterar status: {str(e)}"}), 500


# -------------------------------------------------
# Mantém PATCH /status (não quebra nada existente)
# PATCH /api/admin/users/<id>/status
# body: { is_active: true|false }
# -------------------------------------------------
@admin_users_bp.route("/admin/users/<int:user_id>/status", methods=["PATCH"])
@cross_origin(origins="http://localhost:5173", methods=["PATCH", "OPTIONS"])
@jwt_required()
def set_user_status(user_id):
    me, err = _require_admin()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    is_active = _to_bool(data.get("is_active"), None)
    if is_active is None:
        return jsonify({"error": "Campo 'is_active' é obrigatório (true/false)"}), 400

    # Guardrail: não permitir desativar você mesmo
    if int(user_id) == int(me.id) and is_active is False:
        return jsonify({"error": "Você não pode desativar seu próprio usuário."}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404

    try:
        user.is_active = bool(is_active)
        db.session.commit()
        return jsonify({"ok": True, "is_active": bool(user.is_active)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erro ao alterar status: {str(e)}"}), 500


# -------------------------------------------------
# RESET PASSWORD (adminUsersApi.js usa /reset-password)
# POST /api/admin/users/<id>/reset-password
# body: { password: "novaSenha" }
# -------------------------------------------------
@admin_users_bp.route("/admin/users/<int:user_id>/reset-password", methods=["POST"])
@jwt_required()
def reset_password(user_id):
    _, err = _require_admin()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    password = (data.get("password") or "").strip()

    if len(password) < 6:
        return jsonify({"error": "Senha deve ter pelo menos 6 caracteres."}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404

    try:
        user.set_password(password)
        db.session.commit()
        return jsonify({"ok": True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erro ao resetar senha: {str(e)}"}), 500


# -------------------------------------------------
# REMOVER USUÁRIO
# DELETE /api/admin/users/<id>
# -------------------------------------------------
@admin_users_bp.route("/admin/users/<int:user_id>", methods=["DELETE"])
@jwt_required()
def delete_user(user_id):
    me, err = _require_admin()
    if err:
        return err

    # Guardrail: não permitir deletar você mesmo
    if int(user_id) == int(me.id):
        return jsonify({"error": "Você não pode remover seu próprio usuário."}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404

    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"ok": True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erro ao remover usuário: {str(e)}"}), 500