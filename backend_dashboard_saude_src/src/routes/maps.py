from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func
from src.models.user import db
from src.models.health_data import HealthCase, Municipality

maps_bp = Blueprint("maps", __name__)

@maps_bp.route("/maps", methods=["GET"])
@jwt_required()
def maps_data():
    """
    Retorna dados do mapa agregados por município + doença.
    (Já pronto para filtrar por disease e bbox)
    """
    try:
        disease = (request.args.get("disease") or "all").strip()

        # bbox esperado: "lng1,lat1,lng2,lat2"
        bbox = request.args.get("bbox")
        lng1 = lat1 = lng2 = lat2 = None
        if bbox:
            parts = bbox.split(",")
            if len(parts) == 4:
                lng1, lat1, lng2, lat2 = map(float, parts)

        q = (
            db.session.query(
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
            .filter(Municipality.longitude.isnot(None))  # ✅ IMPORTANTE
        )

        if disease.lower() != "all":
            q = q.filter(func.lower(HealthCase.disease_name) == func.lower(disease))

        if bbox:
            # normaliza (caso usuário arraste invertido)
            min_lng, max_lng = sorted([lng1, lng2])
            min_lat, max_lat = sorted([lat1, lat2])
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

        output = [
            {
                "state": r.state,
                "city": r.city,
                "disease": r.disease,
                "cases": int(r.cases or 0),
                "lat": float(r.lat),
                "lng": float(r.lng),
            }
            for r in results
        ]

        return jsonify(output), 200

    except Exception as e:
        print(f"❌ Erro ao buscar dados do mapa: {e}")
        return jsonify({"error": "Erro interno ao processar mapa"}), 500
    
@maps_bp.route("/maps/uf", methods=["GET"])
@jwt_required()
def maps_data_uf():
    """
    Retorna dados agregados por UF + doença.
    Para o MVP, usamos o centroide aproximado via AVG(lat/lng) dos municípios da UF.
    (Se quiser choropleth real, aí entra GeoJSON do IBGE no frontend.)
    """
    try:
        disease = (request.args.get("disease") or "all").strip()

        bbox = request.args.get("bbox")
        lng1 = lat1 = lng2 = lat2 = None
        if bbox:
            parts = bbox.split(",")
            if len(parts) == 4:
                lng1, lat1, lng2, lat2 = map(float, parts)

        q = (
            db.session.query(
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

        if bbox:
            min_lng, max_lng = sorted([lng1, lng2])
            min_lat, max_lat = sorted([lat1, lat2])
            q = q.filter(Municipality.longitude.between(min_lng, max_lng))
            q = q.filter(Municipality.latitude.between(min_lat, max_lat))

        results = q.group_by(Municipality.uf, HealthCase.disease_name).all()

        output = [
            {
                "state": r.state,
                "disease": r.disease,
                "cases": int(r.cases or 0),
                "lat": float(r.lat) if r.lat is not None else None,
                "lng": float(r.lng) if r.lng is not None else None,
            }
            for r in results
            if r.lat is not None and r.lng is not None
        ]

        return jsonify(output), 200

    except Exception as e:
        print(f"❌ Erro ao buscar dados UF: {e}")
        return jsonify({"error": "Erro interno ao processar mapa UF"}), 500