from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import func, text, cast, String
from sqlalchemy.orm import Session
from datetime import datetime
import json

from src.models.user import db
from src.models.health_data import HealthCase, Municipality

analytics_bp = Blueprint("analytics", __name__)


def _tenant_scope():
    claims = get_jwt() or {}
    scope_type = (claims.get("tenant_scope_type") or "BR").strip().upper()
    scope_value = str(claims.get("tenant_scope_value") or "all").strip()
    tenant_slug = (claims.get("tenant") or "br").strip().lower()
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
    if not ds_row:
        return []
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


def _municipality_join_sql():
    return (
        "LEFT(CAST(m.id AS CHAR) COLLATE utf8mb4_unicode_ci, 6) = "
        "v.municipio COLLATE utf8mb4_unicode_ci"
    )


def _map_granularity(gran):
    g = (gran or "month").strip().lower()
    if g in ("week", "weekly", "semana", "semanal"):
        return "semanal", "week"
    return "mensal", "month"


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


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
    else:
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


def _municipality_scope_info(scope_value: str):
    mun6 = _mun_code6(scope_value)
    if not mun6:
        return None, None

    row = (
        db.session.query(Municipality.name, Municipality.uf)
        .filter(func.left(cast(Municipality.id, String), 6) == mun6)
        .first()
    )
    if not row:
        return None, None

    return row[0], row[1]


@analytics_bp.route("/analytics", methods=["GET"])
@jwt_required()
def analytics():
    disease = (request.args.get("disease") or "all").strip().lower()
    gran = (request.args.get("gran") or "month").strip().lower()
    start = _parse_date(request.args.get("start"))
    end = _parse_date(request.args.get("end"))
    requested_uf = (request.args.get("uf") or "all").strip().upper()

    scope_type, scope_value, tenant_slug = _tenant_scope()
    ds = _resolve_tenant_data_source(tenant_slug)

    # =====================================================
    # MODO TENANT MUNICIPAL COM DATA SOURCE ESPECÍFICO
    # =====================================================
    if scope_type == "MUN" and ds:
        try:
            sess = _get_tenant_session(ds["bind_key"])
            view_name = ds["aggregate_view_name"]
            supported_diseases = _get_supported_diseases(ds)
            mun6 = _mun_code6(scope_value)
            city_name, city_uf = _municipality_scope_info(scope_value)

            if not mun6:
                return jsonify({"error": "Tenant MUN inválido (scope_value)"}), 400

            if disease != "all" and disease not in supported_diseases:
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
                    "scope": {
                        "tenant_slug": tenant_slug,
                        "scope_type": scope_type,
                        "scope_value": scope_value,
                        "city_name": city_name
                    },
                    "filters": {
                        "disease": disease,
                        "uf": "all",
                        "start": request.args.get("start"),
                        "end": request.args.get("end"),
                        "gran": gran
                    }
                }), 200

            gran_db, gran_front = _map_granularity(gran)
            where_clauses = [
                "v.granularidade = :gran_db",
                "v.municipio = :mun"
            ]
            params = {
                "gran_db": gran_db,
                "mun": mun6,
            }

            if disease != "all":
                where_clauses.append("LOWER(v.disease_name) = :disease_name")
                params["disease_name"] = disease

            period_clauses, period_params = _build_period_filter(start, end, gran_db)
            where_clauses.extend(period_clauses)
            params.update(period_params)

            where_sql = "WHERE " + " AND ".join(where_clauses)
            join_sql = _municipality_join_sql()
            label_expr = "CONCAT(v.ano, '-', LPAD(v.periodo, 2, '0'))"

            sql_series = f"""
                SELECT
                    {label_expr} AS period,
                    SUM(v.casos) AS count
                FROM {view_name} v
                {where_sql}
                GROUP BY v.ano, v.periodo
                ORDER BY v.ano, v.periodo
            """
            rows = sess.execute(text(sql_series), params).mappings().all()

            sql_kpi = f"""
                SELECT
                    COALESCE(SUM(v.casos), 0) AS total_cases
                FROM {view_name} v
                {where_sql}
            """
            kpi = sess.execute(text(sql_kpi), params).mappings().first()

            total_cases = int((kpi["total_cases"] if kpi else 0) or 0)
            municipality_count = 1 if total_cases > 0 else 0
            uf_count = 0

            sql_comp = f"""
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
                LIMIT 10
            """
            comp_rows = sess.execute(text(sql_comp), params).mappings().all()

            comparatives = [
                {
                    "city": r["city"],
                    "uf": r["uf"],
                    "count": int(r["count"] or 0)
                }
                for r in comp_rows
            ]

            if not comparatives and total_cases > 0 and city_name:
                comparatives = [{
                    "city": city_name,
                    "uf": city_uf,
                    "count": total_cases
                }]

            cases_by_period = [
                {
                    "period": r["period"],
                    "month": r["period"],
                    "count": int(r["count"] or 0)
                }
                for r in rows
            ]

            return jsonify({
                "cases_in_period": total_cases,
                "uf_count": uf_count,
                "municipality_count": municipality_count,
                "delta_vs_previous": 0,
                "delta_label": "0",
                "cases_by_period": cases_by_period,
                "cases_by_month": cases_by_period,
                "comparatives": comparatives,
                "mode": "prefeitura",
                "granularity": gran_front,
                "scope": {
                    "tenant_slug": tenant_slug,
                    "scope_type": scope_type,
                    "scope_value": scope_value,
                    "city_name": city_name
                },
                "filters": {
                    "disease": disease,
                    "uf": "all",
                    "start": request.args.get("start"),
                    "end": request.args.get("end"),
                    "gran": gran_front
                }
            }), 200

        except Exception as e:
            print(f"❌ analytics tenant ({tenant_slug}): {e}")
            return jsonify({"error": "Erro interno ao processar analytics do tenant"}), 500

    # =====================================================
    # FALLBACK GENÉRICO: BR / UF / MUN
    # =====================================================

    city_name, city_uf = (None, None)
    if scope_type == "MUN":
        city_name, city_uf = _municipality_scope_info(scope_value)

    q_series = (
        db.session.query(
            func.date_format(HealthCase.dt_notific, "%Y-%m").label("month"),
            func.count(HealthCase.id).label("count")
        )
        .join(
            Municipality,
            func.left(cast(Municipality.id, String), 6) == func.substr(HealthCase.id_municip, 1, 6)
        )
        .filter(HealthCase.dt_notific.isnot(None))
    )

    if disease != "all":
        q_series = q_series.filter(func.lower(HealthCase.disease_name) == disease)

    if scope_type == "UF":
        q_series = q_series.filter(func.upper(Municipality.uf) == scope_value)
    elif scope_type == "MUN":
        mun6 = _mun_code6(scope_value)
        if mun6:
            q_series = q_series.filter(func.substr(HealthCase.id_municip, 1, 6) == mun6)
    elif scope_type == "BR" and requested_uf != "ALL":
        q_series = q_series.filter(func.upper(Municipality.uf) == requested_uf)

    if start:
        q_series = q_series.filter(HealthCase.dt_notific >= start)
    if end:
        q_series = q_series.filter(HealthCase.dt_notific <= end)

    rows = q_series.group_by("month").order_by("month").all()

    q_total = (
        db.session.query(func.count(HealthCase.id))
        .join(
            Municipality,
            func.left(cast(Municipality.id, String), 6) == func.substr(HealthCase.id_municip, 1, 6)
        )
        .filter(HealthCase.dt_notific.isnot(None))
    )

    if disease != "all":
        q_total = q_total.filter(func.lower(HealthCase.disease_name) == disease)

    if scope_type == "UF":
        q_total = q_total.filter(func.upper(Municipality.uf) == scope_value)
    elif scope_type == "MUN":
        mun6 = _mun_code6(scope_value)
        if mun6:
            q_total = q_total.filter(func.substr(HealthCase.id_municip, 1, 6) == mun6)
    elif scope_type == "BR" and requested_uf != "ALL":
        q_total = q_total.filter(func.upper(Municipality.uf) == requested_uf)

    if start:
        q_total = q_total.filter(HealthCase.dt_notific >= start)
    if end:
        q_total = q_total.filter(HealthCase.dt_notific <= end)

    total_cases = int(q_total.scalar() or 0)

    q_uf_count = (
        db.session.query(func.count(func.distinct(Municipality.uf)))
        .join(
            HealthCase,
            func.left(cast(Municipality.id, String), 6) == func.substr(HealthCase.id_municip, 1, 6)
        )
        .filter(HealthCase.dt_notific.isnot(None))
    )

    q_municipality_count = (
        db.session.query(func.count(func.distinct(func.left(cast(Municipality.id, String), 6))))
        .join(
            HealthCase,
            func.left(cast(Municipality.id, String), 6) == func.substr(HealthCase.id_municip, 1, 6)
        )
        .filter(HealthCase.dt_notific.isnot(None))
    )

    if disease != "all":
        q_uf_count = q_uf_count.filter(func.lower(HealthCase.disease_name) == disease)
        q_municipality_count = q_municipality_count.filter(func.lower(HealthCase.disease_name) == disease)

    if scope_type == "UF":
        q_uf_count = q_uf_count.filter(func.upper(Municipality.uf) == scope_value)
        q_municipality_count = q_municipality_count.filter(func.upper(Municipality.uf) == scope_value)
    elif scope_type == "MUN":
        mun6 = _mun_code6(scope_value)
        if mun6:
            q_uf_count = q_uf_count.filter(func.left(cast(Municipality.id, String), 6) == mun6)
            q_municipality_count = q_municipality_count.filter(func.left(cast(Municipality.id, String), 6) == mun6)
    elif scope_type == "BR" and requested_uf != "ALL":
        q_uf_count = q_uf_count.filter(func.upper(Municipality.uf) == requested_uf)
        q_municipality_count = q_municipality_count.filter(func.upper(Municipality.uf) == requested_uf)

    if start:
        q_uf_count = q_uf_count.filter(HealthCase.dt_notific >= start)
        q_municipality_count = q_municipality_count.filter(HealthCase.dt_notific >= start)
    if end:
        q_uf_count = q_uf_count.filter(HealthCase.dt_notific <= end)
        q_municipality_count = q_municipality_count.filter(HealthCase.dt_notific <= end)

    uf_count = int(q_uf_count.scalar() or 0)
    municipality_count = int(q_municipality_count.scalar() or 0)

    q_comp = (
        db.session.query(
            Municipality.name.label("city"),
            Municipality.uf.label("uf"),
            func.count(HealthCase.id).label("count")
        )
        .join(
            HealthCase,
            func.left(cast(Municipality.id, String), 6) == func.substr(HealthCase.id_municip, 1, 6)
        )
        .filter(HealthCase.dt_notific.isnot(None))
    )

    if disease != "all":
        q_comp = q_comp.filter(func.lower(HealthCase.disease_name) == disease)

    if scope_type == "UF":
        q_comp = q_comp.filter(func.upper(Municipality.uf) == scope_value)
    elif scope_type == "MUN":
        mun6 = _mun_code6(scope_value)
        if mun6:
            q_comp = q_comp.filter(func.left(cast(Municipality.id, String), 6) == mun6)
    elif scope_type == "BR" and requested_uf != "ALL":
        q_comp = q_comp.filter(func.upper(Municipality.uf) == requested_uf)

    if start:
        q_comp = q_comp.filter(HealthCase.dt_notific >= start)
    if end:
        q_comp = q_comp.filter(HealthCase.dt_notific <= end)

    comp_rows = (
        q_comp
        .group_by(Municipality.name, Municipality.uf)
        .order_by(func.count(HealthCase.id).desc())
        .limit(10)
        .all()
    )

    comparatives = [
        {
            "city": r.city,
            "uf": r.uf,
            "count": int(r.count or 0)
        }
        for r in comp_rows
    ]

    if scope_type == "MUN" and not comparatives and total_cases > 0 and city_name:
        comparatives = [{
            "city": city_name,
            "uf": city_uf,
            "count": total_cases
        }]

    return jsonify({
        "cases_in_period": total_cases,
        "uf_count": uf_count,
        "municipality_count": municipality_count,
        "delta_vs_previous": 0,
        "delta_label": "0",
        "cases_by_period": [{"period": r.month, "month": r.month, "count": int(r.count)} for r in rows],
        "cases_by_month": [{"month": r.month, "count": int(r.count)} for r in rows],
        "comparatives": comparatives,
        "mode": "prefeitura" if scope_type == "MUN" else ("brasil" if scope_type == "BR" else "uf"),
        "granularity": "month",
        "scope": {
            "tenant_slug": tenant_slug,
            "scope_type": scope_type,
            "scope_value": scope_value,
            "city_name": city_name if scope_type == "MUN" else None
        },
        "filters": {
            "disease": disease,
            "uf": (
                "all" if scope_type == "MUN"
                else requested_uf.lower() if scope_type == "BR"
                else scope_value.lower()
            ),
            "start": request.args.get("start"),
            "end": request.args.get("end"),
            "gran": gran
        }
    }), 200