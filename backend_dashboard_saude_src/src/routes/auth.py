# src/routes/auth.py
from datetime import timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from flask_cors import cross_origin
from src.models.user import User, db
from src.models.tenant import Tenant, UserTenant


auth_bp = Blueprint("auth", __name__)


def _get_tenant_or_403(user_id: int, tenant_slug: str):
    """
    Resolve tenant por slug e valida vínculo user<->tenant.
    Retorna (tenant, None) se OK, ou (None, (payload, status)) se erro.
    """
    slug = (tenant_slug or "br").strip().lower() or "br"

    tenant = (
        Tenant.query.filter(db.func.lower(Tenant.slug) == slug)
        .filter(Tenant.is_active == True)
        .first()
    )
    if not tenant:
        return None, ({"error": "Tenant inválido ou inativo"}, 403)

    link = (
        db.session.query(UserTenant)
        .filter(UserTenant.user_id == user_id, UserTenant.tenant_id == tenant.id)
        .first()
    )
    if not link:
        return None, (
            {"error": "ACESSO NEGADO: você não pode acessar escopo de outra cidade."},
            403,
        )

    return tenant, None


def _issue_token(user: User, tenant: Tenant):
    """
    Emite JWT com claims de tenant.
    """
    additional_claims = {
        "role": user.role,
        "tenant": tenant.slug,
        "tenant_scope_type": tenant.scope_type,      # BR|UF|MUN
        "tenant_scope_value": tenant.scope_value,    # all | RJ | 330270
    }

    return create_access_token(
        identity=user.id,
        additional_claims=additional_claims,
        expires_delta=timedelta(days=7),
    )


def _ensure_default_tenant_br_for_user(user_id: int):
    """
    Garante vínculo no tenant 'br' se existir e se ainda não estiver vinculado.
    """
    tenant_br = Tenant.query.filter(db.func.lower(Tenant.slug) == "br", Tenant.is_active == True).first()
    if not tenant_br:
        return

    exists = (
        db.session.query(UserTenant)
        .filter(UserTenant.user_id == user_id, UserTenant.tenant_id == tenant_br.id)
        .first()
    )
    if not exists:
        db.session.add(UserTenant(user_id=user_id, tenant_id=tenant_br.id))


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Registrar novo usuário.
    - Cria usuário
    - Vincula automaticamente ao tenant default 'br' (se existir)
    - Retorna token já no tenant 'br'
    """
    try:
        data = request.get_json(silent=True) or {}

        required_fields = ["first_name", "last_name", "email", "password"]
        for field in required_fields:
            if not (data.get(field) or "").strip():
                return jsonify({"error": f"Campo {field} é obrigatório"}), 400

        email = data["email"].strip().lower()

        if User.query.filter(db.func.lower(User.email) == email).first():
            return jsonify({"error": "Email já cadastrado"}), 400

        user = User(
            first_name=data["first_name"].strip(),
            last_name=data["last_name"].strip(),
            email=email,
            role=(data.get("role") or "guest"),
        )
        user.set_password(data["password"])

        db.session.add(user)
        db.session.commit()

        # vínculo default BR
        _ensure_default_tenant_br_for_user(user.id)
        db.session.commit()

        # emite token BR
        tenant_br = Tenant.query.filter(db.func.lower(Tenant.slug) == "br", Tenant.is_active == True).first()
        if not tenant_br:
            # fallback seguro se não existir tenant br
            return jsonify({
                "message": "Usuário registrado com sucesso, mas tenant 'br' não está configurado.",
                "user": user.to_dict(),
            }), 201

        access_token = _issue_token(user, tenant_br)

        return jsonify({
            "message": "Usuário registrado com sucesso",
            "access_token": access_token,
            "user": user.to_dict(),
            "tenant": {
                "slug": tenant_br.slug,
                "name": tenant_br.name,
                "scope_type": tenant_br.scope_type,
                "scope_value": tenant_br.scope_value,
            },
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Login do usuário + seleção de tenant:
    body: { email, password, tenant_slug }
    """
    try:
        data = request.get_json(silent=True) or {}

        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        tenant_slug = (data.get("tenant_slug") or "br").strip().lower()

        if not email or not password:
            return jsonify({"error": "Email e senha são obrigatórios"}), 400

        user = User.query.filter(db.func.lower(User.email) == email).first()
        if not user or not user.check_password(password):
            return jsonify({"error": "Email ou senha inválidos"}), 401

        if not getattr(user, "is_active", True):
            return jsonify({"error": "Usuário inativo"}), 401

        tenant, err = _get_tenant_or_403(user.id, tenant_slug)
        if err:
            payload, status = err
            return jsonify(payload), status

        access_token = _issue_token(user, tenant)

        return jsonify({
            "message": "Login realizado com sucesso",
            "access_token": access_token,
            "user": user.to_dict(),
            "tenant": {
                "slug": tenant.slug,
                "name": tenant.name,
                "scope_type": tenant.scope_type,
                "scope_value": tenant.scope_value,
            },
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    """Obter perfil do usuário logado (básico)."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({"error": "Usuário não encontrado"}), 404

        return jsonify({"user": user.to_dict()}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    """Atualizar perfil do usuário (first/last/email)."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({"error": "Usuário não encontrado"}), 404

        data = request.get_json(silent=True) or {}

        if "first_name" in data:
            user.first_name = str(data["first_name"])[:50]
        if "last_name" in data:
            user.last_name = str(data["last_name"])[:50]
        if "email" in data:
            new_email = str(data["email"]).strip().lower()
            existing_user = User.query.filter(db.func.lower(User.email) == new_email).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({"error": "Email já está em uso"}), 400
            user.email = new_email

        db.session.commit()

        return jsonify({
            "message": "Perfil atualizado com sucesso",
            "user": user.to_dict(),
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    """Alterar senha do usuário."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({"error": "Usuário não encontrado"}), 404

        data = request.get_json(silent=True) or {}

        current_password = data.get("current_password") or ""
        new_password = data.get("new_password") or ""

        if not current_password or not new_password:
            return jsonify({"error": "Senha atual e nova senha são obrigatórias"}), 400

        if not user.check_password(current_password):
            return jsonify({"error": "Senha atual incorreta"}), 400

        user.set_password(new_password)
        db.session.commit()

        return jsonify({"message": "Senha alterada com sucesso"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/tenants", methods=["GET"])
def list_user_tenants():
    """
    Retorna tenants disponíveis para o email informado.
    GET /api/auth/tenants?email=...
    (Sem JWT para permitir dropdown antes do login)
    """
    email = (request.args.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Informe email"}), 400

    user = User.query.filter(db.func.lower(User.email) == email).first()
    if not user:
        return jsonify([]), 200

    rows = (
        db.session.query(Tenant)
        .join(UserTenant, UserTenant.tenant_id == Tenant.id)
        .filter(UserTenant.user_id == user.id, Tenant.is_active == True)
        .order_by(Tenant.slug.asc())
        .all()
    )

    # ✅ retorno mínimo pro dropdown
    return jsonify([{"slug": t.slug, "name": t.name} for t in rows]), 200