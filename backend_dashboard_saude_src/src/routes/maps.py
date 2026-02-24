from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import func
from src.models.user import db
from src.models.health_data import HealthCase, Municipality

maps_bp = Blueprint("maps", __name__)

@maps_bp.route("/maps", methods=["GET"])
@jwt_required()
def maps_data():
    """
    Retorna dados geográficos reais cruzando casos de saúde com a tabela de municípios
    """
    try:
        # Query utilizando JOIN com SUBSTR para bater os 6 dígitos do SINAN com os 7 do IBGE
        # Buscamos: UF, Nome da Cidade, Nome da Doença, Latitude, Longitude e Contagem
        results = (
            db.session.query(
                Municipality.uf.label("state"),
                Municipality.name.label("city"),
                HealthCase.disease_name.label("disease"),
                Municipality.latitude.label("lat"),
                Municipality.longitude.label("lng"),
                func.count(HealthCase.id).label("cases")
            )
            .join(
                Municipality, 
                func.substr(Municipality.id, 1, 6) == func.substr(HealthCase.id_municip, 1, 6)
            )
            .filter(Municipality.latitude.isnot(None))
            .group_by(
                Municipality.uf, 
                Municipality.name, 
                HealthCase.disease_name, 
                Municipality.latitude, 
                Municipality.longitude
            )
            .all()
        )

        # Formata o resultado para o JSON esperado pelo maps.jsx
        output = []
        for r in results:
            output.append({
                "state": r.state,
                "city": r.city,
                "disease": r.disease,
                "cases": r.cases,
                "lat": float(r.lat),
                "lng": float(r.lng)
            })

        return jsonify(output)

    except Exception as e:
        print(f"❌ Erro ao buscar dados do mapa: {e}")
        return jsonify({"error": "Erro interno ao processar mapa"}), 500
