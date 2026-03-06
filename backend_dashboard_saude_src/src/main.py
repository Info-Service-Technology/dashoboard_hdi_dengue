import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from flasgger import Swagger

from src.models.user import db, User
from src.models.tenant import Tenant, UserTenant

from src.routes.user import user_bp
from src.routes.auth import auth_bp
from src.routes.health_data import health_data_bp
from src.routes.predictions import predictions_bp
from src.routes.maps import maps_bp
from src.routes.dashboard import dashboard_bp
from src.routes.account import account_bp
from src.routes.system import system_bp
from src.routes.uploads import uploads_bp
from src.routes.analytics import analytics_bp
from src.routes.data import data_bp
from src.routes.admin_users import admin_users_bp
from src.routes.kpis import kpis_bp
from src.routes.geo import geo_bp
from datetime import timedelta


def _env_truthy(name: str, default: str = "") -> bool:
    v = os.getenv(name, default).strip().lower()
    return v in ("1", "true", "yes", "on")


app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), "static"))

# -----------------------------
# Configs básicas
# -----------------------------
app.config["SECRET_KEY"] = "health-dashboard-secret-key-2025"
app.config["JWT_SECRET_KEY"] = "jwt-health-dashboard-secret-2025"
app.config["JWT_IDENTITY_CLAIM"] = "user_id"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=12)
# DB (o seu)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:123456@172.22.1.2:3306/dashboard_saude"
# app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:123456@172.22.1.2:3306/marica_datalake"
# binds: bases de dados "de dados" por prefeitura
app.config["SQLALCHEMY_BINDS"] = {
    "marica": "mysql+pymysql://root:123456@172.22.1.2:3306/marica_datalake",
}

# -----------------------------
# CORS (front React)
# -----------------------------
CORS(
    app,
    origins=["http://localhost:5173"],
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
)

# -----------------------------
# JWT
# -----------------------------
jwt = JWTManager(app)

# -----------------------------
# Swagger (DEV-only)
# -----------------------------
ENABLE_SWAGGER = _env_truthy("ENABLE_SWAGGER", "false")

swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec_1",
            "route": "/api/openapi.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api/docs/",
}

swagger_template = {
    "openapi": "3.0.2",
    "info": {
        "title": "Health Data Insights API",
        "description": "API do Dashboard HDI (multi-tenant: BR + Prefeituras).",
        "version": "1.0.0",
    },
    "components": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    },
    "security": [{"BearerAuth": []}],
}

# ✅ IMPORTANTE:
# - NÃO use Swagger(app) fora desse if.
# - Em debug de verdade, app.debug fica True em runtime.
# - Para garantir no DEV mesmo quando não refletir cedo, use ENABLE_SWAGGER=true.
if ENABLE_SWAGGER:
    Swagger(app, config=swagger_config, template=swagger_template)

# -----------------------------
# Blueprints
# -----------------------------
app.register_blueprint(user_bp, url_prefix="/api")
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(health_data_bp, url_prefix="/api/health")
app.register_blueprint(maps_bp, url_prefix="/api")
app.register_blueprint(dashboard_bp, url_prefix="/api")
app.register_blueprint(account_bp, url_prefix="/api")
app.register_blueprint(system_bp, url_prefix="/api")
app.register_blueprint(uploads_bp, url_prefix="/api")
app.register_blueprint(analytics_bp, url_prefix="/api")
app.register_blueprint(data_bp, url_prefix="/api")
app.register_blueprint(admin_users_bp, url_prefix="/api")
app.register_blueprint(predictions_bp, url_prefix="/api/predictions")
app.register_blueprint(kpis_bp, url_prefix="/api")
app.register_blueprint(geo_bp, url_prefix="/api")
# -----------------------------
# Init DB + seeds mínimos
# -----------------------------
db.init_app(app)
with app.app_context():
    db.create_all()

    # 1) garante tenant BR
    br = Tenant.query.filter_by(slug="br").first()
    if not br:
        br = Tenant(
            slug="br",
            name="Brasil (Default)",
            scope_type="BR",
            scope_value="all",
            is_active=True,
        )
        db.session.add(br)
        db.session.commit()
        print("Tenant 'br' criado.")

    # 2) garante admin
    user = User.query.filter_by(email="admin@example.com").first()
    if not user:
        user = User(first_name="Admin", last_name="User", email="admin@example.com", role="admin")
        user.set_password("admin")
        db.session.add(user)
        db.session.commit()
        print("Usuário admin padrão criado.")

    # 3) vincula admin ao tenant BR
    link = UserTenant.query.filter_by(user_id=user.id, tenant_id=br.id).first()
    if not link:
        db.session.add(UserTenant(user_id=user.id, tenant_id=br.id))
        db.session.commit()
        print("Admin vinculado ao tenant 'br'.")


# -----------------------------
# Healthcheck
# -----------------------------
@app.route("/api/test")
def test():
    return jsonify({"message": "API funcionando!", "status": "ok"})


# -----------------------------
# Frontend build (React)
# -----------------------------
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    target = os.path.join(static_folder_path, path)
    if path != "" and os.path.exists(target):
        return send_from_directory(static_folder_path, path)

    index_path = os.path.join(static_folder_path, "index.html")
    if os.path.exists(index_path):
        return send_from_directory(static_folder_path, "index.html")

    return "Frontend not built yet", 404


if __name__ == "__main__":
    # Dica prática:
    # - DEV: ENABLE_SWAGGER=true python main.py
    # - PROD: não setar ENABLE_SWAGGER
    print("🚀 Iniciando servidor Flask...")
    print("📊 Dashboard de Análise Preditiva em Saúde")
    print("🔗 API disponível em: http://localhost:5000")
    print("🧪 Teste a API em: http://localhost:5000/api/test")
    if _env_truthy("ENABLE_SWAGGER"):
        print("📘 Swagger: http://localhost:5000/api/docs/")
    app.run(host="0.0.0.0", port=5000, debug=True)