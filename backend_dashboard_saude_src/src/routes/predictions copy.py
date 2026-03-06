from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
import mysql.connector
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import func
from datetime import timedelta
import math

from src.models.user import db
from src.models.health_data import HealthCase, Municipality
from src.routes.analytics import _base_query, _trend_bucket

predictions_bp = Blueprint("predictions", __name__)
# =========================
# DB CONNECTION
# =========================
def get_db_connection():
    return mysql.connector.connect(
        host="172.22.1.2",
        user="root",
        password="123456",
        database="dashboard_saude"
    )

# =========================
# CATALOG: DISEASES
# =========================
@predictions_bp.route("/diseases", methods=["GET"])
@jwt_required()
def list_diseases():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Ajuste a coluna se seu schema for outro
    cursor.execute("""
        SELECT DISTINCT TRIM(disease_name) AS disease
        FROM health_cases
        WHERE disease_name IS NOT NULL AND TRIM(disease_name) <> ''
        ORDER BY disease
    """)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    diseases = [r["disease"] for r in rows if r.get("disease")]
    return jsonify({"diseases": diseases}), 200

# =========================
# CATALOG: STATES (UFs)
# =========================
@predictions_bp.route("/states", methods=["GET"])
@jwt_required()
def list_states():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # melhor fonte: tabela municipalities
    cursor.execute("""
        SELECT DISTINCT UPPER(TRIM(uf)) AS uf
        FROM municipalities
        WHERE uf IS NOT NULL AND TRIM(uf) <> ''
        ORDER BY uf
    """)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    states = [r["uf"] for r in rows if r.get("uf")]
    return jsonify({"states": states}), 200

# =========================
# FORECAST
# =========================
@predictions_bp.route("/forecast", methods=["POST"])
@jwt_required()
def forecast():
    payload = request.get_json(silent=True) or {}
    disease = (payload.get("disease") or "").strip()
    months_ahead = int(payload.get("months_ahead") or 6)

    if not disease:
        return jsonify({"message": "Campo 'disease' é obrigatório."}), 400

    historical = get_historical_data(disease)

    if len(historical) < 3:
        return jsonify({
            "disease": disease,
            "historical_data": historical,
            "forecast": [],
            "confidence_interval": []
        }), 200

    forecast_data = generate_forecast(historical, months_ahead)
    confidence = confidence_interval(forecast_data)

    return jsonify({
        "disease": disease,
        "historical_data": historical,
        "forecast": forecast_data,
        "confidence_interval": confidence
    }), 200

# =========================
# RISK ANALYSIS
# =========================
@predictions_bp.route("/risk-analysis", methods=["POST"])
@jwt_required()
def risk_analysis():
    payload = request.get_json(silent=True) or {}
    state = (payload.get("state") or "RJ").strip().upper()

    factors = get_risk_factors(state)
    score = calculate_risk_score(factors)

    return jsonify({
        "state": state,
        "risk_factors": factors,
        "risk_score": score,
        "risk_level": risk_level(score),
        "recommendations": recommendations(score)
    }), 200

# =========================
# HISTORICAL DATA
# =========================
def get_historical_data(disease: str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            DATE_FORMAT(dt_notific, '%Y-%m') AS date,
            COUNT(*) AS cases
        FROM health_cases
        WHERE LOWER(disease_name) = LOWER(%s)
        GROUP BY date
        ORDER BY date
    """
    cursor.execute(query, (disease,))
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return [{"date": r["date"], "cases": int(r["cases"])} for r in rows]

# =========================
# FORECAST MODEL
# =========================
def generate_forecast(historical, months: int):
    cases = np.array([h["cases"] for h in historical], dtype=float)
    window = min(6, len(cases))
    avg = float(np.mean(cases[-window:]))

    trend = float(np.polyfit(range(len(cases)), cases, 1)[0]) if len(cases) >= 2 else 0.0

    forecast = []
    for i in range(1, months + 1):
        date = (datetime.now() + timedelta(days=30 * i)).strftime("%Y-%m")
        predicted = max(0, int(avg + trend * i))
        forecast.append({"date": date, "predicted_cases": predicted})

    return forecast

# =========================
# CONFIDENCE INTERVAL
# =========================
def confidence_interval(forecast):
    result = []
    for f in forecast:
        margin = int(f["predicted_cases"] * 0.2)
        result.append({
            "date": f["date"],
            "lower_bound": max(0, f["predicted_cases"] - margin),
            "upper_bound": f["predicted_cases"] + margin
        })
    return result

# =========================
# RISK FACTORS
# =========================
def get_risk_factors(state: str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT COUNT(hc.id) AS cases
        FROM health_cases hc
        JOIN municipalities m ON m.id = hc.id_municip
        WHERE m.uf = %s
    """, (state,))
    row = cursor.fetchone() or {}

    cursor.close()
    conn.close()

    return {
        "temperature": 28.0,
        "humidity": 75.0,
        "population_density": 350,
        "sanitation_index": 0.7,
        "previous_cases": int(row.get("cases") or 0)
    }

# =========================
# RISK RULES
# =========================
def calculate_risk_score(f):
    score = (
        (f["temperature"] - 20) / 15 * 0.25 +
        (f["humidity"] - 60) / 30 * 0.2 +
        (f["population_density"] / 1000) * 0.2 +
        (1 - f["sanitation_index"]) * 0.25 +
        (f["previous_cases"] / 500) * 0.1
    )
    return max(0, min(1, float(score)))

def risk_level(score: float):
    if score < 0.3:
        return "Baixo"
    if score < 0.6:
        return "Médio"
    if score < 0.8:
        return "Alto"
    return "Muito Alto"

def recommendations(score: float):
    return {
        "Baixo": ["Manter vigilância"],
        "Médio": ["Reforçar monitoramento"],
        "Alto": ["Ações preventivas urgentes"],
        "Muito Alto": ["Plano de contingência imediato"]
    }[risk_level(score)]

@predictions_bp.route("/trends", methods=["GET"])
@jwt_required()
def prediction_trends():
    """
    Projeção linear simples baseada na série histórica.
    """
    try:
        horizon = int(request.args.get("horizon", 12))
        gran = (request.args.get("gran") or "week").strip().lower()

        q, disease, uf, start_dt, end_dt = _base_query()

        q = q.filter(HealthCase.dt_notific.isnot(None))
        q = q.filter(HealthCase.dt_notific >= start_dt.date())
        q = q.filter(HealthCase.dt_notific < end_dt.date())

        bucket = _trend_bucket(gran)

        rows = (
            q.with_entities(bucket.label("bucket"), func.count(HealthCase.id).label("cases"))
            .group_by("bucket")
            .order_by("bucket")
            .all()
        )

        if len(rows) < 2:
            return jsonify([]), 200

        # Série histórica
        y = [int(r.cases) for r in rows]
        n = len(y)

        # Índices 0..n-1
        x = list(range(n))

        # Regressão linear OLS fechada
        x_mean = sum(x) / n
        y_mean = sum(y) / n

        num = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        den = sum((x[i] - x_mean) ** 2 for i in range(n))

        slope = num / den if den != 0 else 0
        intercept = y_mean - slope * x_mean

        # Gera buckets futuros
        last_bucket = rows[-1].bucket
        predictions = []

        for i in range(1, horizon + 1):
            future_x = n - 1 + i
            pred = intercept + slope * future_x
            pred = max(0, round(pred))

            # Bucket futuro (simplificado por string)
            if gran == "day":
                # assume formato YYYY-MM-DD
                future_bucket = str(last_bucket)
            else:
                future_bucket = f"future_{i}"

            predictions.append({
                "bucket": future_bucket,
                "cases_pred": int(pred)
            })

        return jsonify(predictions), 200

    except Exception as e:
        print(f"❌ prediction_trends: {e}")
        return jsonify({"error": "Erro ao gerar previsão"}), 500