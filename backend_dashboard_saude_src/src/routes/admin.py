# # src/routes/admin.py
# from flask import Blueprint, jsonify, request
# from flask_jwt_extended import jwt_required, get_jwt
# from sqlalchemy import func

# from src.models.user import db, User
# from src.models.tenant import Tenant, UserTenant

# admin_bp = Blueprint("admin", __name__)


# # ----------------------------
# # Guard: somente admin
# # ----------------------------
# def _require_admin():
#     claims = get_jwt() or {}
#     role = (claims.get("role") or "").strip().lower()
#     if role != "admin":
#         return False
#     return True


# def _admin_or_403():
#     if not _require_admin():
#         return jsonify({"error": "ACESSO NEGADO: apenas administradores."}), 403
#     return None


# def _tenant_slugs_for_user(user_id: int):
#     rows = (
#         db.session.query(Tenant.slug)
#         .join(UserTenant, UserTenant.tenant_id == Tenant.id)
#         .filter(UserTenant.user_id == user_id)
#         .order_by(Tenant.slug.asc())
#         .all()
#     )
#     return [r[0] for r in rows]


# def _set_user_tenants(user_id: int, tenant_slugs):
#     """
#     Substitui os vínculos do usuário por tenant_slugs.
#     - Remove vínculos antigos
#     - Adiciona novos (somente tenants ativos)
#     """
#     slugs = []
#     if isinstance(tenant_slugs, list):
#         slugs = [str(s).strip().lower() for s in tenant_slugs if str(s).strip()]
#     slugs = list(dict.fromkeys(slugs))  # unique, preserva ordem

#     # (Guardrail) nunca deixar vazio
#     if len(slugs) == 0:
#         slugs = ["br"]

#     tenants = (
#         Tenant.query
#         .filter(func.lower(Tenant.slug).in_(slugs))
#         .filter(Tenant.is_active == True)
#         .all()
#     )
#     tenant_ids = {t.id for t in tenants}

#     # apaga existentes
#     db.session.query(UserTenant).filter(UserTenant.user_id == user_id).delete()

#     # recria vínculos (somente ativos)
#     for t in tenants:
#         db.session.add(UserTenant(user_id=user_id, tenant_id=t.id))


# # ----------------------------
# # GET /api/admin/tenants
# # ----------------------------
# @admin_bp.get("/admin/tenants")
# @jwt_required()
# def admin_list_tenants():
#     deny = _admin_or_403()
#     if deny:
#         return deny

#     rows = (
#         Tenant.query
#         .filter(Tenant.is_active == True)
#         .order_by(Tenant.slug.asc())
#         .all()
#     )
#     return jsonify([{"slug": t.slug, "name": t.name} for t in rows]), 200


# # ----------------------------
# # GET /api/admin/users
# # ----------------------------
# @admin_bp.get("/admin/users")
# @jwt_required()
# def admin_list_users():
#     deny = _admin_or_403()
#     if deny:
#         return deny

#     users = User.query.order_by(User.id.desc()).all()

#     out = []
#     for u in users:
#         out.append({
#             "id": u.id,
#             "first_name": u.first_name,
#             "last_name": u.last_name,
#             "email": u.email,
#             "role": u.role,
#             "is_active": bool(getattr(u, "is_active", True)),
#             "tenants": _tenant_slugs_for_user(u.id),
#         })

#     return jsonify(out), 200


# # ----------------------------
# # POST /api/admin/users
# # body: { first_name,last_name,email,password,role,is_active,tenant_slugs }
# # ----------------------------
# @admin_bp.post("/admin/users")
# @jwt_required()
# def admin_create_user():
#     deny = _admin_or_403()
#     if deny:
#         return deny

#     data = request.get_json(silent=True) or {}

#     first_name = str(data.get("first_name") or "").strip()
#     last_name = str(data.get("last_name") or "").strip()
#     email = str(data.get("email") or "").strip().lower()
#     password = str(data.get("password") or "")
#     role = str(data.get("role") or "guest").strip().lower()
#     is_active = bool(data.get("is_active", True))
#     tenant_slugs = data.get("tenant_slugs") or ["br"]

#     if not first_name or not last_name:
#         return jsonify({"error": "Nome e sobrenome são obrigatórios."}), 400
#     if not email or "@" not in email:
#         return jsonify({"error": "Email inválido."}), 400
#     if len(password) < 6:
#         return jsonify({"error": "Senha deve ter pelo menos 6 caracteres."}), 400
#     if role not in ("admin", "guest"):
#         return jsonify({"error": "role inválido (admin|guest)."}), 400

#     # email único
#     exists = User.query.filter(func.lower(User.email) == email).first()
#     if exists:
#         return jsonify({"error": "Email já cadastrado."}), 400

#     try:
#         user = User(
#             first_name=first_name[:50],
#             last_name=last_name[:50],
#             email=email,
#             role=role,
#         )
#         # is_active pode existir no model
#         if hasattr(user, "is_active"):
#             user.is_active = is_active

#         user.set_password(password)

#         db.session.add(user)
#         db.session.flush()  # pega user.id sem commit ainda

#         _set_user_tenants(user.id, tenant_slugs)

#         db.session.commit()

#         return jsonify({
#             "success": True,
#             "user": {
#                 "id": user.id,
#                 "first_name": user.first_name,
#                 "last_name": user.last_name,
#                 "email": user.email,
#                 "role": user.role,
#                 "is_active": bool(getattr(user, "is_active", True)),
#                 "tenants": _tenant_slugs_for_user(user.id),
#             }
#         }), 201

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({"error": f"Erro ao criar usuário: {str(e)}"}), 500


# # ----------------------------
# # PUT /api/admin/users/<id>
# # body: { first_name,last_name,role,is_active,tenant_slugs }
# # (não troca email aqui, conforme sua UI)
# # ----------------------------
# @admin_bp.put("/admin/users/<int:user_id>")
# @jwt_required()
# def admin_update_user(user_id: int):
#     deny = _admin_or_403()
#     if deny:
#         return deny

#     data = request.get_json(silent=True) or {}

#     user = User.query.get(user_id)
#     if not user:
#         return jsonify({"error": "Usuário não encontrado."}), 404

#     first_name = str(data.get("first_name") or user.first_name or "").strip()
#     last_name = str(data.get("last_name") or user.last_name or "").strip()
#     role = str(data.get("role") or user.role or "guest").strip().lower()
#     is_active = bool(data.get("is_active", getattr(user, "is_active", True)))
#     tenant_slugs = data.get("tenant_slugs")

#     if not first_name or not last_name:
#         return jsonify({"error": "Nome e sobrenome são obrigatórios."}), 400
#     if role not in ("admin", "guest"):
#         return jsonify({"error": "role inválido (admin|guest)."}), 400

#     try:
#         user.first_name = first_name[:50]
#         user.last_name = last_name[:50]
#         user.role = role

#         if hasattr(user, "is_active"):
#             user.is_active = is_active

#         if tenant_slugs is not None:
#             _set_user_tenants(user.id, tenant_slugs)

#         db.session.commit()

#         return jsonify({
#             "success": True,
#             "user": {
#                 "id": user.id,
#                 "first_name": user.first_name,
#                 "last_name": user.last_name,
#                 "email": user.email,
#                 "role": user.role,
#                 "is_active": bool(getattr(user, "is_active", True)),
#                 "tenants": _tenant_slugs_for_user(user.id),
#             }
#         }), 200

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({"error": f"Erro ao atualizar usuário: {str(e)}"}), 500


# # ----------------------------
# # POST /api/admin/users/<id>/toggle-active
# # body: { is_active: true|false }
# # ----------------------------
# @admin_bp.post("/admin/users/<int:user_id>/toggle-active")
# @jwt_required()
# def admin_toggle_user_active(user_id: int):
#     deny = _admin_or_403()
#     if deny:
#         return deny

#     user = User.query.get(user_id)
#     if not user:
#         return jsonify({"error": "Usuário não encontrado."}), 404

#     if not hasattr(user, "is_active"):
#         return jsonify({"error": "Model User não possui is_active."}), 400

#     data = request.get_json(silent=True) or {}
#     is_active = bool(data.get("is_active", True))

#     try:
#         user.is_active = is_active
#         db.session.commit()
#         return jsonify({"success": True, "is_active": bool(user.is_active)}), 200
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({"error": f"Erro ao alterar status: {str(e)}"}), 500


# # ----------------------------
# # POST /api/admin/users/<id>/reset-password
# # body: { password: "..." }
# # ----------------------------
# @admin_bp.post("/admin/users/<int:user_id>/reset-password")
# @jwt_required()
# def admin_reset_user_password(user_id: int):
#     deny = _admin_or_403()
#     if deny:
#         return deny

#     user = User.query.get(user_id)
#     if not user:
#         return jsonify({"error": "Usuário não encontrado."}), 404

#     data = request.get_json(silent=True) or {}
#     password = str(data.get("password") or "")

#     if len(password) < 6:
#         return jsonify({"error": "Senha deve ter pelo menos 6 caracteres."}), 400

#     try:
#         user.set_password(password)
#         db.session.commit()
#         return jsonify({"success": True}), 200
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({"error": f"Erro ao resetar senha: {str(e)}"}), 500