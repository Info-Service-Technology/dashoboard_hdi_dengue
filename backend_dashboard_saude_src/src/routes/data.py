from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import func, desc, asc, text
from sqlalchemy.orm import Session

from src.models.user import db
from src.models.health_data import HealthCase, Municipality

data_bp = Blueprint("data", __name__)


def _tenant_scope():
    claims = get_jwt() or {}

    scope_type = (claims.get("tenant_scope_type") or "BR").strip().upper()
    scope_value = str(claims.get("tenant_scope_value") or "all").strip()
    tenant_slug = (claims.get("tenant") or "br").strip().lower()

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


@data_bp.route("/data/cases", methods=["GET"])
@jwt_required()
def list_cases():
    """
    GET /api/data/cases?disease=...&uf=...&start=YYYY-MM-DD&end=YYYY-MM-DD
      &page=1&page_size=25&sort=dt_notific&dir=desc&search=texto
    """
    scope_type, scope_value, tenant_slug = _tenant_scope()

    # =================================================
    # TENANT PREFEITURA (MARICÁ)
    # =================================================
    if tenant_slug == "marica-rj":
        try:
            sess = _get_session_for_tenant(tenant_slug)

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

            mun6 = _mun_code6(scope_value) if scope_type == "MUN" else None
            if scope_type == "MUN" and not mun6:
                return jsonify({"error": "Tenant MUN inválido (scope_value)"}), 400

            if disease not in ("all", "dengue"):
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

            where_clauses = [
                "v.granularidade = 'mensal'",
                "STR_TO_DATE(CONCAT(v.ano, '-', LPAD(v.periodo, 2, '0'), '-01'), '%Y-%m-%d') >= :start_d",
                "STR_TO_DATE(CONCAT(v.ano, '-', LPAD(v.periodo, 2, '0'), '-01'), '%Y-%m-%d') <= :end_d",
            ]
            params = {
                "start_d": start_d.isoformat(),
                "end_d": end_d.isoformat(),
            }

            if scope_type == "MUN":
                where_clauses.append("v.municipio = :municipio")
                params["municipio"] = mun6

            if search:
                where_clauses.append("(LOWER(m.name) LIKE :search OR LOWER(m.uf) LIKE :search)")
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
                        'Dengue' AS disease_name,
                        m.uf AS uf,
                        m.name AS municipality,
                        m.id AS ibge,
                        v.casos AS count
                    FROM vw_dengue_kpis v
                    JOIN municipalities m
                      ON m.id = CONCAT(v.municipio, '0')
                    {where_sql}
                ) x
            """

            total = int(sess.execute(text(total_sql), params).scalar() or 0)

            data_sql = f"""
                SELECT
                    STR_TO_DATE(CONCAT(v.ano, '-', LPAD(v.periodo, 2, '0'), '-01'), '%Y-%m-%d') AS dt_notific_ref,
                    'Dengue' AS disease_name,
                    m.uf AS uf,
                    m.name AS municipality,
                    m.id AS ibge,
                    v.casos AS count,
                    CONCAT('Agregado mensal do tenant prefeitura - ', v.ano, '-', LPAD(v.periodo, 2, '0')) AS note
                FROM vw_dengue_kpis v
                JOIN municipalities m
                  ON m.id = CONCAT(v.municipio, '0')
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
                    "id": f"{r['ibge']}-{r['dt_notific_ref']}",
                    "dt_notific": r["dt_notific_ref"].isoformat() if r["dt_notific_ref"] else None,
                    "disease_name": r["disease_name"],
                    "uf": r["uf"],
                    "municipality": r["municipality"],
                    "ibge": r["ibge"],
                    "count": int(r["count"] or 0),
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
            print(f"❌ data prefeitura: {e}")
            return jsonify({"error": "Erro interno ao processar dados da prefeitura"}), 500

    # =================================================
    # MODO BRASIL
    # =================================================
    q, disease, uf, start_d, end_d = _base_query()

    search = (request.args.get("search") or request.args.get("q") or "").strip()
    if search:
        s = f"%{search.lower()}%"
        q = q.filter(
            func.lower(Municipality.name).like(s) |
            func.lower(HealthCase.disease_name).like(s)
        )

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
            "uf": m.uf,
            "municipality": m.name,
            "ibge": m.id,
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
            "mode": "brasil"
        }
    }), 200


@data_bp.route("/data/meta", methods=["GET"])
@jwt_required()
def data_meta():
    scope_type, scope_value, tenant_slug = _tenant_scope()

    if tenant_slug == "marica-rj":
        return jsonify({
            "diseases": ["Dengue"],
            "ufs": ["RJ"],
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