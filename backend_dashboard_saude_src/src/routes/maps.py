from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import func, text
from sqlalchemy.orm import Session

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


def _tenant_binds():
    return {
        "marica-rj": "marica",
        "macae-rj": "macae",
        "petropolis-rj": "petropolis",
    }


def _has_tenant_bind(tenant_slug: str) -> bool:
    return tenant_slug in _tenant_binds()


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


# -------------------------------------------------
# MAPA MUNICÍPIOS
# GET /api/maps
# -------------------------------------------------
@maps_bp.route("/maps", methods=["GET"])
@jwt_required()
def maps_data():
    scope_type, scope_value, tenant_slug = _tenant_scope()
    disease = (request.args.get("disease") or "all").strip()
    bbox = _parse_bbox()

    # ==========================
    # MODO PREFEITURA (AGREGADO NO DATALAKE DO TENANT)
    # ==========================
    if scope_type == "MUN" and _has_tenant_bind(tenant_slug):
        try:
            sess = _get_session_for_tenant(tenant_slug)

            mun6 = _mun_code6(scope_value)
            if not mun6:
                return jsonify({"error": "Tenant MUN inválido (scope_value)"}), 400

            if disease.lower() not in ("all", "dengue"):
                return jsonify([]), 200

            sql = """
            SELECT
                m.uf AS state,
                m.name AS city,
                'Dengue' AS disease,
                m.latitude AS lat,
                m.longitude AS lng,
                SUM(v.casos) AS cases
            FROM vw_dengue_kpis v
            JOIN municipalities m
              ON LEFT(CAST(m.id AS CHAR), 6) = v.municipio
            WHERE m.latitude IS NOT NULL
              AND m.longitude IS NOT NULL
              AND v.granularidade = 'mensal'
              AND v.municipio = :municipio
            """

            params = {"municipio": mun6}

            if bbox:
                min_lng, min_lat, max_lng, max_lat = bbox
                sql += " AND m.longitude BETWEEN :min_lng AND :max_lng "
                sql += " AND m.latitude BETWEEN :min_lat AND :max_lat "
                params.update({
                    "min_lng": min_lng,
                    "max_lng": max_lng,
                    "min_lat": min_lat,
                    "max_lat": max_lat,
                })

            sql += """
            GROUP BY m.uf, m.name, m.latitude, m.longitude
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
            print(f"❌ Erro ao buscar mapa prefeitura ({tenant_slug}): {e}")
            return jsonify({"error": "Erro interno ao processar mapa da prefeitura"}), 500

    # ==========================
    # MODO PADRÃO (LINHA-A-LINHA)
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

        if disease.lower() != "all":
            q = q.filter(func.lower(HealthCase.disease_name) == func.lower(disease))

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


# -------------------------------------------------
# MAPA UF
# GET /api/maps/uf
# -------------------------------------------------
@maps_bp.route("/maps/uf", methods=["GET"])
@jwt_required()
def maps_data_uf():
    scope_type, scope_value, tenant_slug = _tenant_scope()
    disease = (request.args.get("disease") or "all").strip()
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

        if disease.lower() != "all":
            q = q.filter(func.lower(HealthCase.disease_name) == func.lower(disease))

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