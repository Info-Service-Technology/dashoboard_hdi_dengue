# src/routes/geo.py
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from src.models.user import db
from src.models.health_data import Municipality

geo_bp = Blueprint("geo", __name__)

@geo_bp.route("/geo/municipality/<mun_id>", methods=["GET"])
@jwt_required()
def get_municipality(mun_id):
    m = Municipality.query.filter_by(id=str(mun_id)).first()
    if not m:
        return jsonify({"error": "Município não encontrado"}), 404
    return jsonify({
        "id": m.id,
        "name": m.name,
        "uf": m.uf,
        "latitude": m.latitude,
        "longitude": m.longitude
    }), 200