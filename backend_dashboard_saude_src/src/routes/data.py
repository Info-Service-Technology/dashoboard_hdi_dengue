from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import func, desc, asc, text
from sqlalchemy.orm import Session
import json

from src.models.user import db
from src.models.health_data import HealthCase, Municipality

data_bp = Blueprint("data", __name__)


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


def _parse_dates():
    end = request.args.get("end")
    start = request.args.get("start")

    end_dt = datetime.fromisoformat(end) if end else datetime.utcnow()
    start_dt = datetime.fromisoformat(start) if start else (end_dt - timedelta(days=90))

    if start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt

    return start_dt.date(), end_dt.date()


def _base_query():
    disease = (request.args.get("disease") or "all").strip()
    uf = (request.args.get("uf") or "all").strip()
    start_d, end_d = _parse_dates()

    q = (
        db.session.query(HealthCase, Municipality)
        .join(
            Municipality,
            func.substr(Municipality.id, 1, 6) == func.substr(HealthCase.id_municip, 1, 6),
        )
        .filter(HealthCase.dt_notific.isnot(None))
        .filter(HealthCase.dt_notific >= start_d)
        .filter(HealthCase.dt_notific <= end_d)
    )

    if disease.lower() != "all":
        q = q.filter(func.lower(HealthCase.disease_name) == func.lower(disease))

    if uf.lower() != "all":
        q = q.filter(func.upper(Municipality.uf) == uf.upper())

    return q, disease, uf, start_d, end_d


@data_bp.route("/data", methods=["GET"])
@data_bp.route("/data/cases", methods=["GET"])
@jwt_required()
def list_cases():
    scope_type, scope_value, tenant_slug = _tenant_scope()
    ds = _resolve_tenant_data_source(tenant_slug)

    if scope_type == "MUN" and ds:
        try:
            sess = _get_tenant_session(ds["bind_key"])
            view_name = ds["aggregate_view_name"]
            supported_diseases = _get_supported_diseases(ds)

            disease = (request.args.get("disease") or "all").strip().lower()
            start_d, end_d = _parse_dates()
            search = (request.args.get("search") or request.args.get("q") or "").strip().lower()

            page = int(request.args.get("page") or 1)
            page_size = int(request.args.get("page_size") or 25)
            page = max(page, 1)
            page_size = min(max(page_size, 1), 200)

            sort = (request.args.get("sort") or "dt_notific").strip().lower()
            direction = (request.args.get("dir") or "desc").strip().lower()
            order_dir = "DESC" if direction == "desc" else "ASC"

            mun6 = _mun_code6(scope_value)
            if not mun6:
                return jsonify({"error": "Tenant MUN inválido (scope_value)"}), 400

            if disease != "all" and disease not in supported_diseases:
                return jsonify({
                    "items": [],
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                    "filters": {
                        "disease": disease,
                        "uf": "all",
                        "start": start_d.isoformat(),
                        "end": end_d.isoformat(),
                        "search": search,
                        "sort": sort,
                        "dir": direction,
                    },
                    "scope": {
                        "tenant_slug": tenant_slug,
                        "scope_type": scope_type,
                        "scope_value": scope_value,
                        "mode": "prefeitura"
                    }
                }), 200

            join_sql = _municipality_join_sql()
            where_clauses = [
                "v.granularidade = 'mensal'",
                "STR_TO_DATE(CONCAT(v.ano, '-', LPAD(v.periodo, 2, '0'), '-01'), '%Y-%m-%d') >= :start_d",
                "STR_TO_DATE(CONCAT(v.ano, '-', LPAD(v.periodo, 2, '0'), '-01'), '%Y-%m-%d') <= :end_d",
                "v.municipio = :municipio",
            ]
            params = {
                "start_d": start_d.isoformat(),
                "end_d": end_d.isoformat(),
                "municipio": mun6,
            }

            if disease != "all":
                where_clauses.append("LOWER(v.disease_name) = :disease_name")
                params["disease_name"] = disease

            if search:
                where_clauses.append(
                    "(LOWER(m.name) LIKE :search OR LOWER(m.uf) LIKE :search OR LOWER(v.disease_name) LIKE :search)"
                )
                params["search"] = f"%{search}%"

            where_sql = "WHERE " + " AND ".join(where_clauses)

            sort_map = {
                "dt_notific": "dt_notific_ref",
                "disease_name": "disease_name",
                "uf": "uf",
                "municipality": "municipality",
                "count": "count",
            }
            sort_col = sort_map.get(sort, "dt_notific_ref")

            total_sql = f"""
                SELECT COUNT(*) AS total
                FROM (
                    SELECT
                        STR_TO_DATE(CONCAT(v.ano, '-', LPAD(v.periodo, 2, '0'), '-01'), '%Y-%m-%d') AS dt_notific_ref,
                        v.disease_name AS disease_name,
                        m.uf AS uf,
                        m.name AS municipality,
                        m.id AS ibge,
                        v.casos AS count
                    FROM {view_name} v
                    JOIN municipalities m
                      ON {join_sql}
                    {where_sql}
                ) x
            """
            total = int(sess.execute(text(total_sql), params).scalar() or 0)

            data_sql = f"""
                SELECT
                    STR_TO_DATE(CONCAT(v.ano, '-', LPAD(v.periodo, 2, '0'), '-01'), '%Y-%m-%d') AS dt_notific_ref,
                    v.disease_name AS disease_name,
                    m.uf AS uf,
                    m.name AS municipality,
                    m.id AS ibge,
                    v.casos AS count,
                    CONCAT('Agregado mensal do tenant prefeitura - ', v.ano, '-', LPAD(v.periodo, 2, '0')) AS note
                FROM {view_name} v
                JOIN municipalities m
                  ON {join_sql}
                {where_sql}
                ORDER BY {sort_col} {order_dir}
                LIMIT :limit OFFSET :offset
            """
            params_page = dict(params)
            params_page["limit"] = page_size
            params_page["offset"] = (page - 1) * page_size

            rows = sess.execute(text(data_sql), params_page).mappings().all()

            items = []
            for r in rows:
                items.append({
                    "id": f"{r['ibge']}-{r['disease_name']}-{r['dt_notific_ref']}",
                    "dt_notific": r["dt_notific_ref"].isoformat() if r["dt_notific_ref"] else None,
                    "disease_name": r["disease_name"],
                    "disease": r["disease_name"],
                    "uf": r["uf"],
                    "municipality": r["municipality"],
                    "city": r["municipality"],
                    "ibge": r["ibge"],
                    "count": int(r["count"] or 0),
                    "cases": int(r["count"] or 0),
                    "note": r["note"],
                })

            return jsonify({
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "filters": {
                    "disease": disease,
                    "uf": "all",
                    "start": start_d.isoformat(),
                    "end": end_d.isoformat(),
                    "search": search,
                    "sort": sort,
                    "dir": direction,
                },
                "scope": {
                    "tenant_slug": tenant_slug,
                    "scope_type": scope_type,
                    "scope_value": scope_value,
                    "mode": "prefeitura"
                }
            }), 200

        except Exception as e:
            print(f"❌ data tenant ({tenant_slug}): {e}")
            return jsonify({"error": "Erro interno ao processar dados do tenant"}), 500

    q, disease, uf, start_d, end_d = _base_query()

    search = (request.args.get("search") or request.args.get("q") or "").strip()
    if search:
        s = f"%{search.lower()}%"
        q = q.filter(
            func.lower(Municipality.name).like(s) |
            func.lower(HealthCase.disease_name).like(s)
        )

    if scope_type == "UF":
        q = q.filter(func.upper(Municipality.uf) == scope_value)
    elif scope_type == "MUN":
        mun6 = _mun_code6(scope_value)
        if mun6:
            q = q.filter(func.substr(HealthCase.id_municip, 1, 6) == mun6)

    sort = (request.args.get("sort") or "dt_notific").strip()
    direction = (request.args.get("dir") or "desc").strip().lower()
    order_fn = desc if direction == "desc" else asc

    sort_map = {
        "dt_notific": HealthCase.dt_notific,
        "disease_name": HealthCase.disease_name,
        "uf": Municipality.uf,
        "municipality": Municipality.name,
    }
    sort_col = sort_map.get(sort, HealthCase.dt_notific)
    q = q.order_by(order_fn(sort_col))

    page = int(request.args.get("page") or 1)
    page_size = int(request.args.get("page_size") or 25)
    page = max(page, 1)
    page_size = min(max(page_size, 1), 200)

    total = q.with_entities(func.count(HealthCase.id)).scalar() or 0
    rows = q.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for hc, m in rows:
        items.append({
            "id": getattr(hc, "id", None),
            "dt_notific": hc.dt_notific.isoformat() if hc.dt_notific else None,
            "disease_name": hc.disease_name,
            "disease": hc.disease_name,
            "uf": m.uf,
            "municipality": m.name,
            "city": m.name,
            "ibge": m.id,
            "cases": 1,
        })

    return jsonify({
        "items": items,
        "total": int(total),
        "page": page,
        "page_size": page_size,
        "filters": {
            "disease": disease,
            "uf": uf,
            "start": start_d.isoformat(),
            "end": end_d.isoformat(),
            "search": search,
            "sort": sort,
            "dir": direction,
        },
        "scope": {
            "tenant_slug": tenant_slug,
            "scope_type": scope_type,
            "scope_value": scope_value,
            "mode": "prefeitura" if scope_type == "MUN" else "brasil"
        }
    }), 200


@data_bp.route("/data/meta", methods=["GET"])
@jwt_required()
def data_meta():
    scope_type, scope_value, tenant_slug = _tenant_scope()
    ds = _resolve_tenant_data_source(tenant_slug)

    if scope_type == "MUN" and ds:
        supported_diseases = _get_supported_diseases(ds)
        return jsonify({
            "diseases": [d.title() for d in supported_diseases],
            "ufs": [],
            "scope": {
                "tenant_slug": tenant_slug,
                "scope_type": scope_type,
                "scope_value": scope_value,
                "mode": "prefeitura"
            }
        }), 200

    diseases = [
        r[0] for r in db.session.query(HealthCase.disease_name)
        .filter(HealthCase.disease_name.isnot(None))
        .group_by(HealthCase.disease_name)
        .order_by(HealthCase.disease_name)
        .all()
    ]

    ufs = [
        r[0] for r in db.session.query(Municipality.uf)
        .filter(Municipality.uf.isnot(None))
        .group_by(Municipality.uf)
        .order_by(Municipality.uf)
        .all()
    ]

    return jsonify({
        "diseases": diseases,
        "ufs": ufs,
        "scope": {
            "tenant_slug": tenant_slug,
            "scope_type": scope_type,
            "scope_value": scope_value,
            "mode": "brasil"
        }
    }), 200