from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from src.models.user import db
from src.models.health_data import HealthCase, Municipality

dashboard_bp = Blueprint("dashboard", __name__)


def _tenant_scope():
    claims = get_jwt() or {}
    scope_type = (claims.get("tenant_scope_type") or "BR").strip().upper()
    scope_value = str(claims.get("tenant_scope_value") or "all").strip()
    tenant_slug = (claims.get("tenant") or "br").strip().lower()

    if scope_type == "BR":
        scope_value = "all"
    elif scope_type == "UF":
        scope_value = scope_value.upper()
    elif scope_type == "MUN":
        scope_value = scope_value.strip()

    return scope_type, scope_value, tenant_slug


def _get_session_for_tenant(tenant_slug: str) -> Session:
    if tenant_slug == "marica-rj":
        engine = db.get_engine(bind="marica")
        return Session(bind=engine)
    return db.session


def _mun_code6(scope_value: str):
    v = str(scope_value or "").strip()
    if not v.isdigit():
        return None
    if len(v) == 6:
        return v
    if len(v) == 7:
        return v[:6]
    return None


@dashboard_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def dashboard():
    disease_filter = (request.args.get("disease") or "all").strip()

    scope_type, scope_value, tenant_slug = _tenant_scope()

    # ==========================================
    # TENANT PREFEITURA: MARICÁ via vw_dengue_kpis
    # ==========================================
    if tenant_slug == "marica-rj":
        try:
            sess = _get_session_for_tenant(tenant_slug)

            mun6 = _mun_code6(scope_value) if scope_type == "MUN" else None
            if scope_type == "MUN" and not mun6:
                return jsonify({"error": "Tenant MUN inválido (scope_value)"}), 400

            # A view do tenant Maricá é específica de dengue.
            if disease_filter.lower() not in ("all", "dengue"):
                return jsonify({
                    "total_cases": 0,
                    "hospitalization_rate": 0,
                    "hospitalization_count": 0,
                    "death_rate": 0,
                    "death_count": 0,
                    "cases_by_disease": [],
                    "cases_by_month": [],
                    "cases_by_uf": [],
                    "cases_by_uf_disease": [],
                    "cases_by_city": [],
                    "diseases": ["Dengue"],
                    "filters": {"disease": disease_filter},
                    "scope": {
                        "tenant_slug": tenant_slug,
                        "scope_type": scope_type,
                        "scope_value": scope_value,
                        "mode": "prefeitura"
                    }
                }), 200

            params = {}
            where_clauses = ["v.granularidade = 'mensal'"]

            if scope_type == "MUN":
                where_clauses.append("v.municipio = :municipio")
                params["municipio"] = mun6

            where_sql = "WHERE " + " AND ".join(where_clauses)

            # total de casos - SEMPRE usando granularidade mensal
            total_sql = f"""
                SELECT COALESCE(SUM(v.casos), 0) AS total_cases
                FROM vw_dengue_kpis v
                {where_sql}
            """
            total_cases = int(sess.execute(text(total_sql), params).scalar() or 0)

            # evolução mensal
            month_sql = f"""
                SELECT
                    CONCAT(v.ano, '-', LPAD(v.periodo, 2, '0')) AS month,
                    SUM(v.casos) AS count
                FROM vw_dengue_kpis v
                {where_sql}
                GROUP BY v.ano, v.periodo
                ORDER BY v.ano, v.periodo
            """
            cases_by_month = sess.execute(text(month_sql), params).mappings().all()

            # município / UF do tenant - também usando granularidade mensal
            city_sql = f"""
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
            """
            cases_by_city = sess.execute(text(city_sql), params).mappings().all()

            # compatibilidade com frontend atual
            uf_sql = f"""
                SELECT
                    m.uf AS uf,
                    SUM(v.casos) AS count
                FROM vw_dengue_kpis v
                JOIN municipalities m
                  ON m.id = CONCAT(v.municipio, '0')
                {where_sql}
                GROUP BY m.uf
                ORDER BY count DESC
            """
            cases_by_uf = sess.execute(text(uf_sql), params).mappings().all()

            return jsonify({
                "total_cases": total_cases,
                "hospitalization_rate": 0,
                "hospitalization_count": 0,
                "death_rate": 0,
                "death_count": 0,
                "diseases": ["Dengue"],
                "cases_by_disease": [{"disease": "Dengue", "count": total_cases}],
                "cases_by_month": [
                    {"month": r["month"], "count": int(r["count"] or 0)}
                    for r in cases_by_month
                ],
                "cases_by_uf": [
                    {"uf": r["uf"], "count": int(r["count"] or 0)}
                    for r in cases_by_uf
                ],
                "cases_by_uf_disease": [
                    {"uf": r["uf"], "disease": "Dengue", "count": int(r["count"] or 0)}
                    for r in cases_by_uf
                ],
                "cases_by_city": [
                    {"city": r["city"], "uf": r["uf"], "count": int(r["count"] or 0)}
                    for r in cases_by_city
                ],
                "filters": {"disease": disease_filter},
                "scope": {
                    "tenant_slug": tenant_slug,
                    "scope_type": scope_type,
                    "scope_value": scope_value,
                    "mode": "prefeitura"
                }
            }), 200

        except Exception as e:
            print(f"❌ dashboard prefeitura: {e}")
            return jsonify({"error": "Erro interno ao processar dashboard da prefeitura"}), 500

    # ==========================================
    # MODO PADRÃO: BRASIL / UF via health_cases
    # ==========================================
    total_cases = db.session.query(func.count(HealthCase.id)).scalar() or 0

    if total_cases == 0:
        return jsonify({
            "total_cases": 0,
            "hospitalization_rate": 0,
            "hospitalization_count": 0,
            "death_rate": 0,
            "death_count": 0,
            "cases_by_disease": [],
            "cases_by_month": [],
            "cases_by_uf": [],
            "cases_by_uf_disease": [],
            "diseases": [],
            "scope": {
                "tenant_slug": tenant_slug,
                "scope_type": scope_type,
                "scope_value": scope_value,
                "mode": "brasil"
            }
        }), 200

    hosp_count = db.session.query(func.count(HealthCase.id)).filter(HealthCase.hospitaliz == 1).scalar() or 0
    hosp_rate = round((hosp_count / total_cases) * 100, 1) if total_cases else 0

    death_count = db.session.query(func.count(HealthCase.id)).filter(HealthCase.evolucao == 2).scalar() or 0
    death_rate = round((death_count / total_cases) * 100, 1) if total_cases else 0

    diseases = [
        r[0] for r in db.session.query(HealthCase.disease_name)
        .filter(HealthCase.disease_name.isnot(None))
        .filter(func.trim(HealthCase.disease_name) != "")
        .distinct()
        .order_by(HealthCase.disease_name.asc())
        .all()
    ]

    cases_by_disease = db.session.query(
        HealthCase.disease_name.label("disease"),
        func.count(HealthCase.id).label("count")
    ).group_by(HealthCase.disease_name).all()

    cases_by_month = db.session.query(
        func.date_format(HealthCase.dt_notific, "%Y-%m").label("month"),
        func.count(HealthCase.id).label("count")
    ).filter(HealthCase.dt_notific.isnot(None)).group_by("month").order_by("month").all()

    base_join = (
        db.session.query(
            Municipality.uf.label("uf_sigla"),
            func.count(HealthCase.id).label("count")
        )
        .join(
            Municipality,
            func.substr(Municipality.id, 1, 6) == func.substr(HealthCase.id_municip, 1, 6)
        )
    )

    if disease_filter.lower() != "all":
        base_join = base_join.filter(func.lower(HealthCase.disease_name) == disease_filter.lower())

    cases_by_uf = (
        base_join
        .group_by(Municipality.uf)
        .order_by(func.count(HealthCase.id).desc())
        .limit(10)
        .all()
    )

    uf_disease_q = (
        db.session.query(
            Municipality.uf.label("uf"),
            HealthCase.disease_name.label("disease"),
            func.count(HealthCase.id).label("count")
        )
        .join(
            Municipality,
            func.substr(Municipality.id, 1, 6) == func.substr(HealthCase.id_municip, 1, 6)
        )
        .filter(HealthCase.disease_name.isnot(None))
        .group_by(Municipality.uf, HealthCase.disease_name)
        .order_by(Municipality.uf.asc(), HealthCase.disease_name.asc())
    )

    if disease_filter.lower() != "all":
        uf_disease_q = uf_disease_q.filter(func.lower(HealthCase.disease_name) == disease_filter.lower())

    cases_by_uf_disease = uf_disease_q.all()

    return jsonify({
        "total_cases": total_cases,
        "hospitalization_rate": hosp_rate,
        "hospitalization_count": hosp_count,
        "death_rate": death_rate,
        "death_count": death_count,
        "diseases": diseases,
        "cases_by_disease": [{"disease": d.disease, "count": int(d.count)} for d in cases_by_disease],
        "cases_by_month": [{"month": m.month, "count": int(m.count)} for m in cases_by_month],
        "cases_by_uf": [{"uf": u.uf_sigla, "count": int(u.count)} for u in cases_by_uf],
        "cases_by_uf_disease": [{"uf": u.uf, "disease": u.disease, "count": int(u.count)} for u in cases_by_uf_disease],
        "filters": {"disease": disease_filter},
        "scope": {
            "tenant_slug": tenant_slug,
            "scope_type": scope_type,
            "scope_value": scope_value,
            "mode": "brasil"
        }
    }), 200