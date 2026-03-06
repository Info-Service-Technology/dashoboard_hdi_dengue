from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from datetime import datetime, date

from src.models.user import db
from src.models.health_data import HealthCase, Municipality

analytics_bp = Blueprint("analytics", __name__)


# -----------------------------------------------------
# TENANT CONTEXT
# -----------------------------------------------------

def _tenant_scope():
    claims = get_jwt() or {}

    scope_type = (claims.get("tenant_scope_type") or "BR").strip().upper()
    scope_value = str(claims.get("tenant_scope_value") or "all").strip()
    tenant_slug = (claims.get("tenant") or "br").strip().lower()

    return scope_type, scope_value, tenant_slug


# -----------------------------------------------------
# SESSION POR TENANT
# -----------------------------------------------------

def _get_session_for_tenant(tenant_slug):
    if tenant_slug == "marica-rj":
        engine = db.get_engine(bind="marica")
        return Session(bind=engine)

    return db.session


# -----------------------------------------------------
# NORMALIZA IBGE 7 -> 6
# -----------------------------------------------------

def _mun_code6(scope_value):
    v = str(scope_value or "").strip()

    if len(v) == 7 and v.isdigit():
        return v[:6]

    return v if v.isdigit() else None


# -----------------------------------------------------
# GRANULARIDADE FRONT -> VIEW
# -----------------------------------------------------

def _map_granularity(gran):
    g = (gran or "month").strip().lower()

    if g in ("week", "weekly", "semana", "semanal"):
        return "semanal", "week"

    return "mensal", "month"


# -----------------------------------------------------
# PARSE DE DATA
# -----------------------------------------------------

def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


# -----------------------------------------------------
# MONTAGEM DE FILTRO DE PERÍODO PARA VIEW
# -----------------------------------------------------

def _build_period_filter(start_date, end_date, gran_db):
    clauses = []
    params = {}

    if gran_db == "mensal":
        if start_date:
            clauses.append("(v.ano > :start_year OR (v.ano = :start_year AND v.periodo >= :start_period))")
            params["start_year"] = start_date.year
            params["start_period"] = start_date.month

        if end_date:
            clauses.append("(v.ano < :end_year OR (v.ano = :end_year AND v.periodo <= :end_period))")
            params["end_year"] = end_date.year
            params["end_period"] = end_date.month

    else:  # semanal
        if start_date:
            iso = start_date.isocalendar()
            clauses.append("(v.ano > :start_year OR (v.ano = :start_year AND v.periodo >= :start_period))")
            params["start_year"] = iso.year
            params["start_period"] = iso.week

        if end_date:
            iso = end_date.isocalendar()
            clauses.append("(v.ano < :end_year OR (v.ano = :end_year AND v.periodo <= :end_period))")
            params["end_year"] = iso.year
            params["end_period"] = iso.week

    return clauses, params


# -----------------------------------------------------
# ENDPOINT PRINCIPAL ANALYTICS
# -----------------------------------------------------

@analytics_bp.route("/analytics", methods=["GET"])
@jwt_required()
def analytics():
    disease = (request.args.get("disease") or "all").strip().lower()
    gran = (request.args.get("gran") or "month").strip().lower()
    start = _parse_date(request.args.get("start"))
    end = _parse_date(request.args.get("end"))

    scope_type, scope_value, tenant_slug = _tenant_scope()

    # =================================================
    # TENANT PREFEITURA (MARICÁ)
    # =================================================
    if tenant_slug == "marica-rj":
        try:
            sess = _get_session_for_tenant(tenant_slug)

            # view do tenant Maricá é específica de dengue
            if disease not in ("all", "dengue"):
                return jsonify({
                    "cases_in_period": 0,
                    "uf_count": 0,
                    "municipality_count": 0,
                    "delta_vs_previous": 0,
                    "delta_label": "Sem dados na janela",
                    "cases_by_period": [],
                    "cases_by_month": [],
                    "comparatives": [],
                    "mode": "prefeitura",
                    "granularity": gran,
                    "filters": {
                        "disease": disease,
                        "start": request.args.get("start"),
                        "end": request.args.get("end"),
                        "gran": gran
                    }
                }), 200

            mun6 = _mun_code6(scope_value)
            if scope_type == "MUN" and not mun6:
                return jsonify({"error": "Tenant MUN inválido (scope_value)"}), 400

            gran_db, gran_front = _map_granularity(gran)

            where_clauses = ["v.granularidade = :gran_db"]
            params = {"gran_db": gran_db}

            if scope_type == "MUN":
                where_clauses.append("v.municipio = :mun")
                params["mun"] = mun6

            period_clauses, period_params = _build_period_filter(start, end, gran_db)
            where_clauses.extend(period_clauses)
            params.update(period_params)

            where_sql = "WHERE " + " AND ".join(where_clauses)

            # Série temporal
            label_expr = "CONCAT(v.ano, '-', LPAD(v.periodo, 2, '0'))"

            sql_series = f"""
                SELECT
                    {label_expr} AS period,
                    SUM(v.casos) AS count
                FROM vw_dengue_kpis v
                {where_sql}
                GROUP BY v.ano, v.periodo
                ORDER BY v.ano, v.periodo
            """

            rows = sess.execute(text(sql_series), params).mappings().all()

            # KPIs
            sql_kpi = f"""
                SELECT
                    COALESCE(SUM(v.casos), 0) AS total_cases,
                    COUNT(DISTINCT v.municipio) AS municipality_count
                FROM vw_dengue_kpis v
                {where_sql}
            """

            kpi = sess.execute(text(sql_kpi), params).mappings().first()

            total_cases = int((kpi["total_cases"] if kpi else 0) or 0)
            municipality_count = int((kpi["municipality_count"] if kpi else 0) or 0)
            uf_count = 1 if municipality_count > 0 else 0

            # Comparativo simples por município
            sql_comp = f"""
                SELECT
                    m.name AS city,
                    m.uf AS uf,
                    SUM(v.casos) AS count
                FROM vw_dengue_kpis v
                JOIN municipalities m
                  ON m.id = CONCAT(v.municipio, '0')
                {where_sql}
                GROUP BY m.name, m.uf
                ORDER BY count DESC
                LIMIT 10
            """

            comp_rows = sess.execute(text(sql_comp), params).mappings().all()

            # Delta ainda não calculado contra período anterior
            delta_vs_previous = 0
            delta_label = "Sem dados na janela" if total_cases == 0 else "0"

            cases_by_period = [
                {
                    "period": r["period"],
                    "month": r["period"],   # compatibilidade com frontend antigo
                    "count": int(r["count"] or 0)
                }
                for r in rows
            ]

            return jsonify({
                "cases_in_period": total_cases,
                "uf_count": uf_count,
                "municipality_count": municipality_count,
                "delta_vs_previous": delta_vs_previous,
                "delta_label": delta_label,
                "cases_by_period": cases_by_period,
                "cases_by_month": cases_by_period,  # compatibilidade
                "comparatives": [
                    {
                        "city": r["city"],
                        "uf": r["uf"],
                        "count": int(r["count"] or 0)
                    }
                    for r in comp_rows
                ],
                "mode": "prefeitura",
                "granularity": gran_front,
                "scope": {
                    "tenant_slug": tenant_slug,
                    "scope_type": scope_type,
                    "scope_value": scope_value
                },
                "filters": {
                    "disease": disease,
                    "start": request.args.get("start"),
                    "end": request.args.get("end"),
                    "gran": gran_front
                }
            }), 200

        except Exception as e:
            print(f"❌ analytics prefeitura: {e}")
            return jsonify({"error": "Erro interno ao processar analytics da prefeitura"}), 500

    # =================================================
    # MODO BRASIL (BASE GERAL)
    # =================================================

    q = db.session.query(
        func.date_format(HealthCase.dt_notific, "%Y-%m").label("month"),
        func.count(HealthCase.id).label("count")
    )

    if disease != "all":
        q = q.filter(func.lower(HealthCase.disease_name) == disease)

    if start:
        q = q.filter(HealthCase.dt_notific >= start)

    if end:
        q = q.filter(HealthCase.dt_notific <= end)

    rows = (
        q.filter(HealthCase.dt_notific.isnot(None))
        .group_by("month")
        .order_by("month")
        .all()
    )

    total_cases_q = db.session.query(func.count(HealthCase.id))

    if disease != "all":
        total_cases_q = total_cases_q.filter(func.lower(HealthCase.disease_name) == disease)

    if start:
        total_cases_q = total_cases_q.filter(HealthCase.dt_notific >= start)

    if end:
        total_cases_q = total_cases_q.filter(HealthCase.dt_notific <= end)

    total_cases = int(total_cases_q.scalar() or 0)

    return jsonify({
        "cases_in_period": total_cases,
        "uf_count": 0,
        "municipality_count": 0,
        "delta_vs_previous": 0,
        "delta_label": "0",
        "cases_by_period": [
            {
                "period": r.month,
                "month": r.month,
                "count": int(r.count)
            }
            for r in rows
        ],
        "cases_by_month": [
            {
                "month": r.month,
                "count": int(r.count)
            }
            for r in rows
        ],
        "comparatives": [],
        "mode": "brasil",
        "granularity": "month",
        "filters": {
            "disease": disease,
            "start": request.args.get("start"),
            "end": request.args.get("end"),
            "gran": gran
        }
    }), 200