from flask import jsonify
from flask_jwt_extended import get_jwt
from functools import wraps

def get_tenant_claim():
    """
    Retorna (tenant_slug, scope_type, scope_value) do JWT.
    """
    claims = get_jwt() or {}
    return (
        claims.get("tenant"),
        claims.get("tenant_scope_type"),
        claims.get("tenant_scope_value"),
    )

def tenant_required(fn):
    """
    Garante que existe tenant no token (login escolheu tenant).
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        tenant_slug, scope_type, scope_value = get_tenant_claim()
        if not tenant_slug or not scope_type or scope_value is None:
            return jsonify({"error": "Tenant não informado no token. Faça login novamente."}), 401
        return fn(*args, **kwargs)
    return wrapper

def enforce_tenant_on_params(request_args: dict, allowed_keys=("municipio", "uf")):
    """
    Se o tenant NÃO for Brasil, impede que o usuário force municipio/uf de outro escopo via query.
    Regra:
      - BR: não força
      - UF: se request vier com uf diferente => 403
      - MUN: se request vier com municipio diferente => 403
    """
    tenant_slug, scope_type, scope_value = get_tenant_claim()

    if scope_type == "BR":
        return None  # ok

    # UF scope
    if scope_type == "UF":
        req_uf = (request_args.get("uf") or "").strip()
        if req_uf and req_uf.lower() != "all" and req_uf.upper() != str(scope_value).upper():
            return ({"error": "ACESSO NEGADO: você não pode acessar escopo de outra UF."}, 403)

    # MUN scope
    if scope_type == "MUN":
        req_mun = (request_args.get("municipio") or "").strip()
        if req_mun and req_mun != str(scope_value):
            return ({"error": "ACESSO NEGADO: você não pode acessar escopo de outra cidade."}, 403)

    return None  # ok