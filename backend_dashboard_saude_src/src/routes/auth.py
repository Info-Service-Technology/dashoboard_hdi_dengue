# src/routes/auth.py
from datetime import timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from src.models.user import User, db
from src.models.tenant import Tenant, UserTenant

auth_bp = Blueprint("auth", __name__)


def _get_tenant_by_slug(slug: str):
    slug = (slug or "br").strip().lower() or "br"
    return (
        Tenant.query.filter(db.func.lower(Tenant.slug) == slug)
        .filter(Tenant.is_active == True)
        .first()
    )


def _get_tenant_or_error(user_id: int, tenant_slug: str):
    """
    Resolve tenant por slug e valida vínculo user<->tenant.
    Retorna (tenant, None) se OK, ou (None, (payload, status)) se erro.
    """
    slug = (tenant_slug or "br").strip().lower() or "br"

    tenant = _get_tenant_by_slug(slug)
    if not tenant:
        return None, ({"error": "Tenant inválido ou inativo"}, 400)

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


def _issue_token(user: User, tenant: Tenant) -> str:
    """
    Emite JWT com claims de tenant.
    """
    additional_claims = {
        "role": user.role,
        "tenant": tenant.slug,
        "tenant_scope_type": tenant.scope_type,   # BR|UF|MUN
        "tenant_scope_value": tenant.scope_value, # all | RJ | 3302700
    }

    return create_access_token(
        identity=user.id,
        additional_claims=additional_claims,
        expires_delta=timedelta(days=7),
    )


def _ensure_tenant_link(user_id: int, tenant: Tenant) -> None:
    """
    Garante vínculo user<->tenant sem duplicar registro.
    Não dá commit aqui.
    """
    exists = (
        db.session.query(UserTenant)
        .filter(UserTenant.user_id == user_id, UserTenant.tenant_id == tenant.id)
        .first()
    )
    if not exists:
        db.session.add(UserTenant(user_id=user_id, tenant_id=tenant.id))


def _ensure_default_tenant_br_for_user(user_id: int) -> None:
    """
    Garante vínculo no tenant 'br' se existir e se ainda não estiver vinculado.
    (Não dá commit aqui; deixa quem chama decidir.)
    """
    tenant_br = _get_tenant_by_slug("br")
    if not tenant_br:
        return

    _ensure_tenant_link(user_id, tenant_br)


def _sanitize_role(role: str) -> str:
    """
    Evita que alguém se registre como admin via payload.
    Ajuste conforme seus papéis reais.
    """
    role = (role or "guest").strip().lower()

    # REGRA SEGURA:
    # cadastro público não deve conseguir criar admin livremente
    # se quiser manter seu comportamento antigo, troque para {"guest", "admin"}
    allowed = {"guest"}
    return role if role in allowed else "guest"


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Registrar novo usuário.

    Comportamento:
    - Cria usuário
    - Se vier tenant_slug no payload, vincula nesse tenant
    - Se não vier tenant_slug, cai no tenant 'br'
    - Também mantém vínculo em 'br' se ele existir (opcional e seguro para fallback)
    - Retorna token já no tenant escolhido
    """
    try:
        data = request.get_json(silent=True) or {}

        required_fields = ["first_name", "last_name", "email", "password"]
        for field in required_fields:
            if not (data.get(field) or "").strip():
                return jsonify({"error": f"Campo {field} é obrigatório"}), 400

        email = data["email"].strip().lower()
        tenant_slug = (data.get("tenant_slug") or "br").strip().lower() or "br"

        if User.query.filter(db.func.lower(User.email) == email).first():
            return jsonify({"error": "Email já cadastrado"}), 400

        tenant = _get_tenant_by_slug(tenant_slug)
        if not tenant:
            return jsonify({"error": "Tenant inválido ou inativo"}), 400

        user = User(
            first_name=data["first_name"].strip(),
            last_name=data["last_name"].strip(),
            email=email,
            role=_sanitize_role(data.get("role")),
        )
        user.set_password(data["password"])

        db.session.add(user)
        db.session.flush()

        # vínculo no tenant solicitado
        _ensure_tenant_link(user.id, tenant)

        # mantém vínculo BR se existir, sem quebrar compatibilidade
        if tenant.slug != "br":
            _ensure_default_tenant_br_for_user(user.id)

        db.session.commit()

        access_token = _issue_token(user, tenant)

        return jsonify(
            {
                "message": "Usuário registrado com sucesso",
                "access_token": access_token,
                "user": user.to_dict(),
                "tenant": {
                    "slug": tenant.slug,
                    "name": tenant.name,
                    "scope_type": tenant.scope_type,
                    "scope_value": tenant.scope_value,
                },
            }
        ), 201

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

        tenant, err = _get_tenant_or_error(user.id, tenant_slug)
        if err:
            payload, status = err
            return jsonify(payload), status

        access_token = _issue_token(user, tenant)

        return jsonify(
            {
                "message": "Login realizado com sucesso",
                "access_token": access_token,
                "user": user.to_dict(),
                "tenant": {
                    "slug": tenant.slug,
                    "name": tenant.name,
                    "scope_type": tenant.scope_type,
                    "scope_value": tenant.scope_value,
                },
            }
        ), 200

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

        return jsonify(
            {
                "message": "Perfil atualizado com sucesso",
                "user": user.to_dict(),
            }
        ), 200

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

    return jsonify(
        [{"slug": t.slug, "name": t.name} for t in rows]
    ), 200