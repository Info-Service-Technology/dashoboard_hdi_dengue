from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import func, text
from sqlalchemy.orm import Session
import json

from src.models.user import db
from src.models.health_data import HealthCase, Municipality

dashboard_bp = Blueprint("dashboard", __name__)


# -----------------------------------------------------
# HELPERS DE TENANT
# -----------------------------------------------------

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


def _resolve_tenant_data_source(tenant_slug: str):
    sql = text("""
        SELECT
            t.slug AS tenant_slug,
            t.scope_type,
            t.scope_value,
            ds.bind_key,
            ds.datalake_db,
            ds.aggregate_view_name,
            ds.supported_diseases_json,
            ds.municipality_join_mode,
            ds.is_active
        FROM tenants t
        JOIN tenant_data_sources ds
          ON ds.tenant_id = t.id
        WHERE LOWER(t.slug) = :tenant_slug
          AND t.is_active = 1
          AND ds.is_active = 1
        LIMIT 1
    """)
    return db.session.execute(
        sql, {"tenant_slug": tenant_slug.lower()}
    ).mappings().first()


def _get_tenant_session(bind_key: str):
    if not bind_key:
        return db.session
    engine = db.get_engine(bind=bind_key)
    return Session(bind=engine)


def _get_supported_diseases(ds_row):
    raw = ds_row["supported_diseases_json"]
    if not raw:
        return []
    if isinstance(raw, str):
        return [x.lower() for x in json.loads(raw)]
    return [str(x).lower() for x in raw]


def _mun_code6(scope_value: str):
    v = str(scope_value or "").strip()
    if not v.isdigit():
        return None
    return v[:6] if len(v) >= 6 else None


def _display_disease_name(name: str):
    return str(name or "").strip().title()


def _municipality_join_sql():
    return (
        "LEFT(CAST(m.id AS CHAR) COLLATE utf8mb4_unicode_ci, 6) = "
        "v.municipio COLLATE utf8mb4_unicode_ci"
    )


@dashboard_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def dashboard():
    disease_filter = (request.args.get("disease") or "all").strip().lower()
    scope_type, scope_value, tenant_slug = _tenant_scope()
    ds = _resolve_tenant_data_source(tenant_slug)

    # ==========================================
    # MODO TENANT MUNICIPAL
    # ==========================================
    if scope_type == "MUN" and ds:
        try:
            sess = _get_tenant_session(ds["bind_key"])
            view_name = ds["aggregate_view_name"]
            supported_diseases = _get_supported_diseases(ds)
            display_diseases = [_display_disease_name(d) for d in supported_diseases]
            mun6 = _mun_code6(scope_value)

            if not mun6:
                return jsonify({"error": "Tenant MUN inválido (scope_value)"}), 400

            if disease_filter != "all" and disease_filter not in supported_diseases:
                return jsonify({
                    "total_cases": 0,
                    "hospitalization_rate": 0,
                    "hospitalization_count": 0,
                    "death_rate": 0,
                    "death_count": 0,
                    "diseases": display_diseases,
                    "cases_by_disease": [],
                    "cases_by_month": [],
                    "cases_by_uf": [],
                    "cases_by_uf_disease": [],
                    "cases_by_city": [],
                    "filters": {"disease": disease_filter},
                    "scope": {
                        "tenant_slug": tenant_slug,
                        "scope_type": scope_type,
                        "scope_value": scope_value,
                        "city_name": None,
                        "mode": "prefeitura"
                    }
                }), 200

            where_clauses = [
                "v.granularidade = 'mensal'",
                "v.municipio = :municipio",
            ]
            params = {"municipio": mun6}

            if disease_filter != "all":
                where_clauses.append("LOWER(v.disease_name) = :disease_name")
                params["disease_name"] = disease_filter

            where_sql = "WHERE " + " AND ".join(where_clauses)
            join_sql = _municipality_join_sql()

            total_sql = f"""
                SELECT COALESCE(SUM(v.casos), 0) AS total_cases
                FROM {view_name} v
                {where_sql}
            """
            total_cases = int(sess.execute(text(total_sql), params).scalar() or 0)

            month_sql = f"""
                SELECT
                    CONCAT(v.ano, '-', LPAD(v.periodo, 2, '0')) AS month,
                    SUM(v.casos) AS count
                FROM {view_name} v
                {where_sql}
                GROUP BY v.ano, v.periodo
                ORDER BY v.ano, v.periodo
            """
            cases_by_month = sess.execute(text(month_sql), params).mappings().all()

            disease_sql = f"""
                SELECT
                    v.disease_name AS disease,
                    SUM(v.casos) AS count
                FROM {view_name} v
                WHERE v.granularidade = 'mensal'
                  AND v.municipio = :municipio
                GROUP BY v.disease_name
                ORDER BY count DESC
            """
            cases_by_disease = sess.execute(
                text(disease_sql), {"municipio": mun6}
            ).mappings().all()

            city_sql = f"""
                SELECT
                    m.name AS city,
                    m.uf AS uf,
                    SUM(v.casos) AS count
                FROM {view_name} v
                JOIN municipalities m
                  ON {join_sql}
                {where_sql}
                GROUP BY m.name, m.uf
                ORDER BY count DESC
            """
            cases_by_city = sess.execute(text(city_sql), params).mappings().all()

            uf_sql = f"""
                SELECT
                    m.uf AS uf,
                    SUM(v.casos) AS count
                FROM {view_name} v
                JOIN municipalities m
                  ON {join_sql}
                {where_sql}
                GROUP BY m.uf
                ORDER BY count DESC
            """
            cases_by_uf = sess.execute(text(uf_sql), params).mappings().all()

            uf_disease_sql = f"""
                SELECT
                    m.uf AS uf,
                    v.disease_name AS disease,
                    SUM(v.casos) AS count
                FROM {view_name} v
                JOIN municipalities m
                  ON {join_sql}
                WHERE v.granularidade = 'mensal'
                  AND v.municipio = :municipio
                GROUP BY m.uf, v.disease_name
                ORDER BY m.uf, count DESC
            """
            cases_by_uf_disease = sess.execute(
                text(uf_disease_sql), {"municipio": mun6}
            ).mappings().all()

            city_name = cases_by_city[0]["city"] if cases_by_city else None

            return jsonify({
                "total_cases": total_cases,
                "hospitalization_rate": 0,
                "hospitalization_count": 0,
                "death_rate": 0,
                "death_count": 0,
                "diseases": display_diseases,
                "cases_by_disease": [
                    {
                        "disease": _display_disease_name(r["disease"]),
                        "count": int(r["count"] or 0)
                    }
                    for r in cases_by_disease
                ],
                "cases_by_month": [
                    {"month": r["month"], "count": int(r["count"] or 0)}
                    for r in cases_by_month
                ],
                "cases_by_uf": [
                    {"uf": r["uf"], "count": int(r["count"] or 0)}
                    for r in cases_by_uf
                ],
                "cases_by_uf_disease": [
                    {
                        "uf": r["uf"],
                        "disease": _display_disease_name(r["disease"]),
                        "count": int(r["count"] or 0)
                    }
                    for r in cases_by_uf_disease
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
                    "city_name": city_name,
                    "mode": "prefeitura"
                }
            }), 200

        except Exception as e:
            print(f"❌ Erro Dashboard Tenant ({tenant_slug}): {e}")
            return jsonify({"error": "Erro ao processar dados do tenant"}), 500

    # ==========================================
    # MODO PADRÃO: BRASIL / UF / MUN
    # ==========================================
    base_total_q = db.session.query(func.count(HealthCase.id))

    if scope_type == "UF":
        base_total_q = base_total_q.filter(func.upper(HealthCase.sg_uf_not) == scope_value)
    elif scope_type == "MUN":
        mun6 = _mun_code6(scope_value)
        if mun6:
            base_total_q = base_total_q.filter(func.substr(HealthCase.id_municip, 1, 6) == mun6)

    if disease_filter != "all":
        base_total_q = base_total_q.filter(func.lower(HealthCase.disease_name) == disease_filter)

    total_cases = base_total_q.scalar() or 0

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
            "cases_by_city": [],
            "diseases": [],
            "scope": {
                "tenant_slug": tenant_slug,
                "scope_type": scope_type,
                "scope_value": scope_value,
                "city_name": None,
                "mode": "prefeitura" if scope_type == "MUN" else "brasil"
            }
        }), 200

    hosp_q = db.session.query(func.count(HealthCase.id)).filter(HealthCase.hospitaliz == 1)
    death_q = db.session.query(func.count(HealthCase.id)).filter(HealthCase.evolucao == 2)

    if scope_type == "UF":
        hosp_q = hosp_q.filter(func.upper(HealthCase.sg_uf_not) == scope_value)
        death_q = death_q.filter(func.upper(HealthCase.sg_uf_not) == scope_value)
    elif scope_type == "MUN":
        mun6 = _mun_code6(scope_value)
        if mun6:
            hosp_q = hosp_q.filter(func.substr(HealthCase.id_municip, 1, 6) == mun6)
            death_q = death_q.filter(func.substr(HealthCase.id_municip, 1, 6) == mun6)

    if disease_filter != "all":
        hosp_q = hosp_q.filter(func.lower(HealthCase.disease_name) == disease_filter)
        death_q = death_q.filter(func.lower(HealthCase.disease_name) == disease_filter)

    hosp_count = hosp_q.scalar() or 0
    death_count = death_q.scalar() or 0
    hosp_rate = round((hosp_count / total_cases) * 100, 1) if total_cases else 0
    death_rate = round((death_count / total_cases) * 100, 1) if total_cases else 0

    diseases_q = (
        db.session.query(HealthCase.disease_name)
        .filter(HealthCase.disease_name.isnot(None))
        .filter(func.trim(HealthCase.disease_name) != "")
    )

    if scope_type == "UF":
        diseases_q = diseases_q.filter(func.upper(HealthCase.sg_uf_not) == scope_value)
    elif scope_type == "MUN":
        mun6 = _mun_code6(scope_value)
        if mun6:
            diseases_q = diseases_q.filter(func.substr(HealthCase.id_municip, 1, 6) == mun6)

    diseases = [r[0] for r in diseases_q.distinct().order_by(HealthCase.disease_name.asc()).all()]

    cases_by_disease_q = db.session.query(
        HealthCase.disease_name.label("disease"),
        func.count(HealthCase.id).label("count")
    )

    if scope_type == "UF":
        cases_by_disease_q = cases_by_disease_q.filter(func.upper(HealthCase.sg_uf_not) == scope_value)
    elif scope_type == "MUN":
        mun6 = _mun_code6(scope_value)
        if mun6:
            cases_by_disease_q = cases_by_disease_q.filter(func.substr(HealthCase.id_municip, 1, 6) == mun6)

    if disease_filter != "all":
        cases_by_disease_q = cases_by_disease_q.filter(func.lower(HealthCase.disease_name) == disease_filter)

    cases_by_disease = cases_by_disease_q.group_by(HealthCase.disease_name).all()

    cases_by_month_q = db.session.query(
        func.date_format(HealthCase.dt_notific, "%Y-%m").label("month"),
        func.count(HealthCase.id).label("count")
    ).filter(HealthCase.dt_notific.isnot(None))

    if scope_type == "UF":
        cases_by_month_q = cases_by_month_q.filter(func.upper(HealthCase.sg_uf_not) == scope_value)
    elif scope_type == "MUN":
        mun6 = _mun_code6(scope_value)
        if mun6:
            cases_by_month_q = cases_by_month_q.filter(func.substr(HealthCase.id_municip, 1, 6) == mun6)

    if disease_filter != "all":
        cases_by_month_q = cases_by_month_q.filter(func.lower(HealthCase.disease_name) == disease_filter)

    cases_by_month = cases_by_month_q.group_by("month").order_by("month").all()

    cases_by_uf_q = (
        db.session.query(
            Municipality.uf.label("uf"),
            func.count(HealthCase.id).label("count")
        )
        .join(Municipality, func.substr(Municipality.id, 1, 6) == func.substr(HealthCase.id_municip, 1, 6))
    )

    if scope_type == "UF":
        cases_by_uf_q = cases_by_uf_q.filter(func.upper(Municipality.uf) == scope_value)
    elif scope_type == "MUN":
        mun6 = _mun_code6(scope_value)
        if mun6:
            cases_by_uf_q = cases_by_uf_q.filter(func.substr(HealthCase.id_municip, 1, 6) == mun6)

    if disease_filter != "all":
        cases_by_uf_q = cases_by_uf_q.filter(func.lower(HealthCase.disease_name) == disease_filter)

    cases_by_uf = cases_by_uf_q.group_by(Municipality.uf).order_by(func.count(HealthCase.id).desc()).all()

    uf_disease_q = (
        db.session.query(
            Municipality.uf.label("uf"),
            HealthCase.disease_name.label("disease"),
            func.count(HealthCase.id).label("count")
        )
        .join(Municipality, func.substr(Municipality.id, 1, 6) == func.substr(HealthCase.id_municip, 1, 6))
        .filter(HealthCase.disease_name.isnot(None))
    )

    if scope_type == "UF":
        uf_disease_q = uf_disease_q.filter(func.upper(Municipality.uf) == scope_value)
    elif scope_type == "MUN":
        mun6 = _mun_code6(scope_value)
        if mun6:
            uf_disease_q = uf_disease_q.filter(func.substr(HealthCase.id_municip, 1, 6) == mun6)

    if disease_filter != "all":
        uf_disease_q = uf_disease_q.filter(func.lower(HealthCase.disease_name) == disease_filter)

    cases_by_uf_disease = (
        uf_disease_q
        .group_by(Municipality.uf, HealthCase.disease_name)
        .order_by(Municipality.uf.asc(), HealthCase.disease_name.asc())
        .all()
    )

    cases_by_city_q = (
        db.session.query(
            Municipality.name.label("city"),
            Municipality.uf.label("uf"),
            func.count(HealthCase.id).label("count")
        )
        .join(Municipality, func.substr(Municipality.id, 1, 6) == func.substr(HealthCase.id_municip, 1, 6))
    )

    if scope_type == "UF":
        cases_by_city_q = cases_by_city_q.filter(func.upper(Municipality.uf) == scope_value)
    elif scope_type == "MUN":
        mun6 = _mun_code6(scope_value)
        if mun6:
            cases_by_city_q = cases_by_city_q.filter(func.substr(HealthCase.id_municip, 1, 6) == mun6)

    if disease_filter != "all":
        cases_by_city_q = cases_by_city_q.filter(func.lower(HealthCase.disease_name) == disease_filter)

    cases_by_city = (
        cases_by_city_q
        .group_by(Municipality.name, Municipality.uf)
        .order_by(func.count(HealthCase.id).desc())
        .all()
    )

    return jsonify({
        "total_cases": total_cases,
        "hospitalization_rate": hosp_rate,
        "hospitalization_count": hosp_count,
        "death_rate": death_rate,
        "death_count": death_count,
        "diseases": diseases,
        "cases_by_disease": [{"disease": d.disease, "count": int(d.count)} for d in cases_by_disease],
        "cases_by_month": [{"month": m.month, "count": int(m.count)} for m in cases_by_month],
        "cases_by_uf": [{"uf": u.uf, "count": int(u.count)} for u in cases_by_uf],
        "cases_by_uf_disease": [{"uf": u.uf, "disease": u.disease, "count": int(u.count)} for u in cases_by_uf_disease],
        "cases_by_city": [{"city": c.city, "uf": c.uf, "count": int(c.count)} for c in cases_by_city],
        "filters": {"disease": disease_filter},
        "scope": {
            "tenant_slug": tenant_slug,
            "scope_type": scope_type,
            "scope_value": scope_value,
            "city_name": None,
            "mode": "prefeitura" if scope_type == "MUN" else "brasil"
        }
    }), 200