# src/routes/kpis.py
import os
import mysql.connector
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
kpis_bp = Blueprint("kpis", __name__)

MYSQL_HOST = os.getenv("MYSQL_HOST", "172.22.1.2")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DB = os.getenv("MYSQL_DB", "marica_datalake")   # <-- IMPORTANTE
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "123456")

def get_db_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )

@kpis_bp.route("/kpis/dengue", methods=["GET"])
@jwt_required()
def dengue_kpis():
    municipio = (request.args.get("municipio") or "").strip()
    granularidade = (request.args.get("granularidade") or "mensal").strip().lower()
    ano = (request.args.get("ano") or "").strip()
    limit = (request.args.get("limit") or "5000").strip()

    if not municipio:
        return jsonify({"error": "municipio is required"}), 400

    if granularidade not in ("mensal", "semanal", "all"):
        return jsonify({"error": "granularidade must be mensal|semanal|all"}), 400

    try:
        limit_i = max(1, min(int(limit), 20000))
    except Exception:
        return jsonify({"error": "limit must be an integer"}), 400

    params = {"municipio": municipio}
    where = ["municipio = %(municipio)s"]

    if ano:
        try:
            params["ano"] = int(ano)
            where.append("ano = %(ano)s")
        except Exception:
            return jsonify({"error": "ano must be an integer"}), 400

    if granularidade != "all":
        params["granularidade"] = granularidade
        where.append("granularidade = %(granularidade)s")
    scope_type, scope_value = _tenant_scope()

    if scope_type == "MUN":
        if municipio != scope_value:
            return jsonify({"error": "ACESSO NEGADO: você não pode acessar escopo de outra cidade."}), 403
    sql = f"""
        SELECT granularidade, municipio, ano, periodo, casos, max_dt_notific, updated_at
        FROM vw_dengue_kpis
        WHERE {" AND ".join(where)}
        ORDER BY granularidade, ano, periodo
        LIMIT {limit_i}
    """

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify({
        "municipio": municipio,
        "granularidade": granularidade,
        "ano": int(ano) if ano else None,
        "count": len(rows),
        "data": rows
    }), 200

def _tenant_scope():
    claims = get_jwt() or {}
    scope_type = (claims.get("tenant_scope_type") or "BR").strip().upper()
    scope_value = (claims.get("tenant_scope_value") or "all").strip()
    if scope_type == "BR":
        scope_value = "all"
    elif scope_type == "UF":
        scope_value = scope_value.upper()
    return scope_type, scope_value