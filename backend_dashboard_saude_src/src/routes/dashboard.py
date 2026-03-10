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


def _tenant_binds():
    return {
        "marica-rj": "marica",
        "macae-rj": "macae",
        "petropolis-rj": "petropolis",
    }


def _has_tenant_bind(tenant_slug: str) -> bool:
    return tenant_slug in _tenant_binds()


def _get_session_for_tenant(tenant_slug: str) -> Session:
    bind = _tenant_binds().get(tenant_slug)
    if bind:
        engine = db.get_engine(bind=bind)
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
    # TENANT PREFEITURA: DATALAKE DO TENANT VIA vw_dengue_kpis
    # ==========================================
    if scope_type == "MUN" and _has_tenant_bind(tenant_slug):
        try:
            sess = _get_session_for_tenant(tenant_slug)

            mun6 = _mun_code6(scope_value)
            if not mun6:
                return jsonify({"error": "Tenant MUN inválido (scope_value)"}), 400

            # datalake municipal atual é específico de dengue
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
                        "city_name": None,
                        "mode": "prefeitura"
                    }
                }), 200

            params = {"municipio": mun6}
            where_sql = """
                WHERE v.granularidade = 'mensal'
                  AND v.municipio = :municipio
            """

            total_sql = f"""
                SELECT COALESCE(SUM(v.casos), 0) AS total_cases
                FROM vw_dengue_kpis v
                {where_sql}
            """
            total_cases = int(sess.execute(text(total_sql), params).scalar() or 0)

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

            city_sql = f"""
                SELECT
                    m.name AS city,
                    m.uf AS uf,
                    SUM(v.casos) AS count
                FROM vw_dengue_kpis v
                JOIN municipalities m
                  ON LEFT(CAST(m.id AS CHAR), 6) = v.municipio
                {where_sql}
                GROUP BY m.name, m.uf
                ORDER BY count DESC
            """
            cases_by_city = sess.execute(text(city_sql), params).mappings().all()

            uf_sql = f"""
                SELECT
                    m.uf AS uf,
                    SUM(v.casos) AS count
                FROM vw_dengue_kpis v
                JOIN municipalities m
                  ON LEFT(CAST(m.id AS CHAR), 6) = v.municipio
                {where_sql}
                GROUP BY m.uf
                ORDER BY count DESC
            """
            cases_by_uf = sess.execute(text(uf_sql), params).mappings().all()

            city_name = cases_by_city[0]["city"] if cases_by_city else None

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
                    "city_name": city_name,
                    "mode": "prefeitura"
                }
            }), 200

        except Exception as e:
            print(f"❌ dashboard prefeitura ({tenant_slug}): {e}")
            return jsonify({"error": "Erro interno ao processar dashboard da prefeitura"}), 500

    # ==========================================
    # MODO PADRÃO: BRASIL / UF / MUN via health_cases
    # ==========================================
    base_total_q = db.session.query(func.count(HealthCase.id))

    if scope_type == "UF":
        base_total_q = base_total_q.filter(func.upper(HealthCase.sg_uf_not) == scope_value)

    if scope_type == "MUN":
        mun6 = _mun_code6(scope_value)
        if mun6:
            base_total_q = base_total_q.filter(func.substr(HealthCase.id_municip, 1, 6) == mun6)

    if disease_filter.lower() != "all":
        base_total_q = base_total_q.filter(func.lower(HealthCase.disease_name) == disease_filter.lower())

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

    if scope_type == "MUN":
        mun6 = _mun_code6(scope_value)
        if mun6:
            hosp_q = hosp_q.filter(func.substr(HealthCase.id_municip, 1, 6) == mun6)
            death_q = death_q.filter(func.substr(HealthCase.id_municip, 1, 6) == mun6)

    if disease_filter.lower() != "all":
        hosp_q = hosp_q.filter(func.lower(HealthCase.disease_name) == disease_filter.lower())
        death_q = death_q.filter(func.lower(HealthCase.disease_name) == disease_filter.lower())

    hosp_count = hosp_q.scalar() or 0
    hosp_rate = round((hosp_count / total_cases) * 100, 1) if total_cases else 0

    death_count = death_q.scalar() or 0
    death_rate = round((death_count / total_cases) * 100, 1) if total_cases else 0

    diseases_q = db.session.query(HealthCase.disease_name) \
        .filter(HealthCase.disease_name.isnot(None)) \
        .filter(func.trim(HealthCase.disease_name) != "")

    if scope_type == "UF":
        diseases_q = diseases_q.filter(func.upper(HealthCase.sg_uf_not) == scope_value)

    if scope_type == "MUN":
        mun6 = _mun_code6(scope_value)
        if mun6:
            diseases_q = diseases_q.filter(func.substr(HealthCase.id_municip, 1, 6) == mun6)

    diseases = [
        r[0] for r in diseases_q.distinct().order_by(HealthCase.disease_name.asc()).all()
    ]

    cases_by_disease_q = db.session.query(
        HealthCase.disease_name.label("disease"),
        func.count(HealthCase.id).label("count")
    )

    if scope_type == "UF":
        cases_by_disease_q = cases_by_disease_q.filter(func.upper(HealthCase.sg_uf_not) == scope_value)

    if scope_type == "MUN":
        mun6 = _mun_code6(scope_value)
        if mun6:
            cases_by_disease_q = cases_by_disease_q.filter(func.substr(HealthCase.id_municip, 1, 6) == mun6)

    if disease_filter.lower() != "all":
        cases_by_disease_q = cases_by_disease_q.filter(func.lower(HealthCase.disease_name) == disease_filter.lower())

    cases_by_disease = cases_by_disease_q.group_by(HealthCase.disease_name).all()

    cases_by_month_q = db.session.query(
        func.date_format(HealthCase.dt_notific, "%Y-%m").label("month"),
        func.count(HealthCase.id).label("count")
    ).filter(HealthCase.dt_notific.isnot(None))

    if scope_type == "UF":
        cases_by_month_q = cases_by_month_q.filter(func.upper(HealthCase.sg_uf_not) == scope_value)

    if scope_type == "MUN":
        mun6 = _mun_code6(scope_value)
        if mun6:
            cases_by_month_q = cases_by_month_q.filter(func.substr(HealthCase.id_municip, 1, 6) == mun6)

    if disease_filter.lower() != "all":
        cases_by_month_q = cases_by_month_q.filter(func.lower(HealthCase.disease_name) == disease_filter.lower())

    cases_by_month = cases_by_month_q.group_by("month").order_by("month").all()

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

    if scope_type == "UF":
        base_join = base_join.filter(func.upper(Municipality.uf) == scope_value)

    if scope_type == "MUN":
        mun6 = _mun_code6(scope_value)
        if mun6:
            base_join = base_join.filter(func.substr(HealthCase.id_municip, 1, 6) == mun6)

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
    )

    if scope_type == "UF":
        uf_disease_q = uf_disease_q.filter(func.upper(Municipality.uf) == scope_value)

    if scope_type == "MUN":
        mun6 = _mun_code6(scope_value)
        if mun6:
            uf_disease_q = uf_disease_q.filter(func.substr(HealthCase.id_municip, 1, 6) == mun6)

    if disease_filter.lower() != "all":
        uf_disease_q = uf_disease_q.filter(func.lower(HealthCase.disease_name) == disease_filter.lower())

    cases_by_uf_disease = (
        uf_disease_q
        .group_by(Municipality.uf, HealthCase.disease_name)
        .order_by(Municipality.uf.asc(), HealthCase.disease_name.asc())
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
        "cases_by_uf": [{"uf": u.uf_sigla, "count": int(u.count)} for u in cases_by_uf],
        "cases_by_uf_disease": [{"uf": u.uf, "disease": u.disease, "count": int(u.count)} for u in cases_by_uf_disease],
        "filters": {"disease": disease_filter},
        "scope": {
            "tenant_slug": tenant_slug,
            "scope_type": scope_type,
            "scope_value": scope_value,
            "city_name": None,
            "mode": "prefeitura" if scope_type == "MUN" else "brasil"
        }
    }), 200