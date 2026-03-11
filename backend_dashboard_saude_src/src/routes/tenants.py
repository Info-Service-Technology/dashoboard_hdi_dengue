from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from src.models.user import User
from src.models.tenant import Tenant

tenants_bp = Blueprint("tenants", __name__)


@tenants_bp.route("/tenants/me", methods=["GET"])
@jwt_required()
def get_my_tenant():
    try:
        user_id = get_jwt_identity()
        claims = get_jwt()

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "Usuário não encontrado"}), 404

        tenant_slug = claims.get("tenant")
        tenant_scope_type = claims.get("tenant_scope_type")
        tenant_scope_value = claims.get("tenant_scope_value")

        if not tenant_slug:
            return jsonify({"error": "Tenant não encontrado no token"}), 400

        tenant = Tenant.query.filter_by(slug=tenant_slug).first()
        if not tenant:
            return jsonify({"error": "Tenant informado no token não existe"}), 404

        return jsonify({
            "data": {
                "tenant_id": tenant.id,
                "slug": tenant.slug,
                "tenant_name": tenant.name,
                "scope_type": tenant.scope_type,
                "scope_value": tenant.scope_value,
                "is_active": tenant.is_active,
                "token_scope_type": tenant_scope_type,
                "token_scope_value": tenant_scope_value
            }
        }), 200

    except Exception as e:
        return jsonify({
            "error": "Erro ao obter tenant",
            "details": str(e)
        }), 500