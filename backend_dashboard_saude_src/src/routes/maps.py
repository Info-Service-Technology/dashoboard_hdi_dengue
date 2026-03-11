from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import func, text
from sqlalchemy.orm import Session
import json

from src.models.user import db
from src.models.health_data import HealthCase, Municipality

maps_bp = Blueprint("maps", __name__)


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


def _municipality_join_sql():
    return (
        "LEFT(CAST(m.id AS CHAR) COLLATE utf8mb4_unicode_ci, 6) = "
        "v.municipio COLLATE utf8mb4_unicode_ci"
    )


def _parse_bbox():
    bbox = request.args.get("bbox")
    if not bbox:
        return None

    parts = bbox.split(",")
    if len(parts) != 4:
        return None

    try:
        lng1, lat1, lng2, lat2 = map(float, parts)
        min_lng, max_lng = sorted([lng1, lng2])
        min_lat, max_lat = sorted([lat1, lat2])
        return (min_lng, min_lat, max_lng, max_lat)
    except Exception:
        return None


@maps_bp.route("/maps", methods=["GET"])
@jwt_required()
def maps_data():
    scope_type, scope_value, tenant_slug = _tenant_scope()
    disease = (request.args.get("disease") or "all").strip().lower()
    bbox = _parse_bbox()

    ds = _resolve_tenant_data_source(tenant_slug)

    # ==========================
    # MODO TENANT MUNICIPAL
    # ==========================
    if scope_type == "MUN" and ds:
        try:
            sess = _get_tenant_session(ds["bind_key"])
            view_name = ds["aggregate_view_name"]
            supported_diseases = _get_supported_diseases(ds)
            mun6 = _mun_code6(scope_value)

            if not mun6:
                return jsonify({"error": "Tenant MUN inválido (scope_value)"}), 400

            if disease != "all" and disease not in supported_diseases:
                return jsonify([]), 200

            join_sql = _municipality_join_sql()
            where_clauses = [
                "m.latitude IS NOT NULL",
                "m.longitude IS NOT NULL",
                "v.granularidade = 'mensal'",
                "v.municipio = :municipio",
            ]
            params = {"municipio": mun6}

            if disease != "all":
                where_clauses.append("LOWER(v.disease_name) = :disease_name")
                params["disease_name"] = disease

            if bbox:
                min_lng, min_lat, max_lng, max_lat = bbox
                where_clauses.append("m.longitude BETWEEN :min_lng AND :max_lng")
                where_clauses.append("m.latitude BETWEEN :min_lat AND :max_lat")
                params.update({
                    "min_lng": min_lng,
                    "max_lng": max_lng,
                    "min_lat": min_lat,
                    "max_lat": max_lat,
                })

            where_sql = "WHERE " + " AND ".join(where_clauses)

            sql = f"""
                SELECT
                    m.uf AS state,
                    m.name AS city,
                    v.disease_name AS disease,
                    m.latitude AS lat,
                    m.longitude AS lng,
                    SUM(v.casos) AS cases
                FROM {view_name} v
                JOIN municipalities m
                  ON {join_sql}
                {where_sql}
                GROUP BY m.uf, m.name, v.disease_name, m.latitude, m.longitude
                ORDER BY cases DESC
            """

            rows = sess.execute(text(sql), params).mappings().all()

            return jsonify([
                {
                    "state": r["state"],
                    "city": r["city"],
                    "disease": r["disease"],
                    "cases": int(r["cases"] or 0),
                    "lat": float(r["lat"]),
                    "lng": float(r["lng"]),
                }
                for r in rows
            ]), 200

        except Exception as e:
            print(f"❌ Erro ao buscar mapa tenant ({tenant_slug}): {e}")
            return jsonify({"error": "Erro interno ao processar mapa do tenant"}), 500

    # ==========================
    # MODO PADRÃO
    # ==========================
    try:
        sess = db.session

        q = (
            sess.query(
                Municipality.uf.label("state"),
                Municipality.name.label("city"),
                HealthCase.disease_name.label("disease"),
                Municipality.latitude.label("lat"),
                Municipality.longitude.label("lng"),
                func.count(HealthCase.id).label("cases"),
            )
            .join(
                Municipality,
                func.substr(Municipality.id, 1, 6) == func.substr(HealthCase.id_municip, 1, 6),
            )
            .filter(Municipality.latitude.isnot(None))
            .filter(Municipality.longitude.isnot(None))
        )

        if disease != "all":
            q = q.filter(func.lower(HealthCase.disease_name) == disease)

        if scope_type == "UF":
            q = q.filter(func.upper(Municipality.uf) == scope_value)
        elif scope_type == "MUN":
            mun6 = _mun_code6(scope_value)
            if not mun6:
                return jsonify({"error": "Tenant MUN inválido (scope_value)"}), 400
            q = q.filter(func.substr(HealthCase.id_municip, 1, 6) == mun6)

        if bbox:
            min_lng, min_lat, max_lng, max_lat = bbox
            q = q.filter(Municipality.longitude.between(min_lng, max_lng))
            q = q.filter(Municipality.latitude.between(min_lat, max_lat))

        results = (
            q.group_by(
                Municipality.uf,
                Municipality.name,
                HealthCase.disease_name,
                Municipality.latitude,
                Municipality.longitude,
            )
            .all()
        )

        return jsonify([
            {
                "state": r.state,
                "city": r.city,
                "disease": r.disease,
                "cases": int(r.cases or 0),
                "lat": float(r.lat),
                "lng": float(r.lng),
            }
            for r in results
        ]), 200

    except Exception as e:
        print(f"❌ Erro ao buscar dados do mapa: {e}")
        return jsonify({"error": "Erro interno ao processar mapa"}), 500


@maps_bp.route("/maps/uf", methods=["GET"])
@jwt_required()
def maps_data_uf():
    scope_type, scope_value, _tenant_slug = _tenant_scope()
    disease = (request.args.get("disease") or "all").strip().lower()
    bbox = _parse_bbox()

    if scope_type == "MUN":
        return jsonify([]), 200

    try:
        sess = db.session

        q = (
            sess.query(
                Municipality.uf.label("state"),
                HealthCase.disease_name.label("disease"),
                func.avg(Municipality.latitude).label("lat"),
                func.avg(Municipality.longitude).label("lng"),
                func.count(HealthCase.id).label("cases"),
            )
            .join(
                Municipality,
                func.substr(Municipality.id, 1, 6) == func.substr(HealthCase.id_municip, 1, 6),
            )
            .filter(Municipality.latitude.isnot(None))
            .filter(Municipality.longitude.isnot(None))
        )

        if disease != "all":
            q = q.filter(func.lower(HealthCase.disease_name) == disease)

        if scope_type == "UF":
            q = q.filter(func.upper(Municipality.uf) == scope_value)

        if bbox:
            min_lng, min_lat, max_lng, max_lat = bbox
            q = q.filter(Municipality.longitude.between(min_lng, max_lng))
            q = q.filter(Municipality.latitude.between(min_lat, max_lat))

        results = q.group_by(Municipality.uf, HealthCase.disease_name).all()

        return jsonify([
            {
                "state": r.state,
                "disease": r.disease,
                "cases": int(r.cases or 0),
                "lat": float(r.lat) if r.lat is not None else None,
                "lng": float(r.lng) if r.lng is not None else None,
            }
            for r in results
            if r.lat is not None and r.lng is not None
        ]), 200

    except Exception as e:
        print(f"❌ Erro ao buscar dados UF: {e}")
        return jsonify({"error": "Erro interno ao processar mapa UF"}), 500