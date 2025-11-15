from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

predictions_bp = Blueprint('predictions', __name__)

@predictions_bp.route('/forecast', methods=['POST'])
@jwt_required()
def forecast_cases():
    """Previsão de casos de doenças usando análise de tendências"""
    try:
        data = request.get_json()
        disease = data.get('disease', 'Dengue')
        months_ahead = data.get('months_ahead', 6)
        
        # Dados históricos simulados (em um cenário real, viriam do banco de dados)
        historical_data = generate_historical_data(disease)
        
        # Aplicar modelo de previsão simples (média móvel com tendência)
        forecast = simple_forecast_model(historical_data, months_ahead)
        
        return jsonify({
            'disease': disease,
            'historical_data': historical_data,
            'forecast': forecast,
            'months_ahead': months_ahead,
            'confidence_interval': calculate_confidence_interval(forecast)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@predictions_bp.route('/risk-analysis', methods=['POST'])
@jwt_required()
def risk_analysis():
    """Análise de risco por região"""
    try:
        data = request.get_json()
        state = data.get('state', 'SP')
        
        # Fatores de risco simulados
        risk_factors = {
            'temperature': np.random.uniform(20, 35),
            'humidity': np.random.uniform(60, 90),
            'population_density': np.random.uniform(100, 1000),
            'sanitation_index': np.random.uniform(0.5, 1.0),
            'previous_cases': np.random.randint(50, 500)
        }
        
        # Calcular score de risco
        risk_score = calculate_risk_score(risk_factors)
        
        return jsonify({
            'state': state,
            'risk_factors': risk_factors,
            'risk_score': risk_score,
            'risk_level': get_risk_level(risk_score),
            'recommendations': get_recommendations(risk_score)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def generate_historical_data(disease):
    """Gera dados históricos simulados para uma doença"""
    months = []
    base_cases = {'Dengue': 200, 'Chikungunya': 80, 'Zika': 60, 'Coqueluche': 40, 'Rotavirus': 50}
    
    for i in range(24):  # 24 meses de dados
        date = datetime.now() - timedelta(days=30 * (24 - i))
        
        # Adicionar sazonalidade e tendência
        seasonal_factor = 1 + 0.3 * np.sin(2 * np.pi * i / 12)  # Padrão anual
        trend_factor = 1 + 0.02 * i  # Tendência crescente leve
        noise = np.random.normal(1, 0.1)  # Ruído aleatório
        
        cases = int(base_cases.get(disease, 100) * seasonal_factor * trend_factor * noise)
        
        months.append({
            'date': date.strftime('%Y-%m'),
            'cases': max(0, cases)  # Garantir que não seja negativo
        })
    
    return months

def simple_forecast_model(historical_data, months_ahead):
    """Modelo simples de previsão baseado em média móvel com tendência"""
    cases = [item['cases'] for item in historical_data]
    
    # Calcular média móvel dos últimos 6 meses
    window_size = min(6, len(cases))
    recent_avg = np.mean(cases[-window_size:])
    
    # Calcular tendência
    if len(cases) >= 12:
        trend = (np.mean(cases[-6:]) - np.mean(cases[-12:-6])) / 6
    else:
        trend = 0
    
    forecast = []
    for i in range(months_ahead):
        future_date = datetime.now() + timedelta(days=30 * (i + 1))
        predicted_cases = int(recent_avg + trend * (i + 1))
        
        forecast.append({
            'date': future_date.strftime('%Y-%m'),
            'predicted_cases': max(0, predicted_cases)
        })
    
    return forecast

def calculate_confidence_interval(forecast):
    """Calcula intervalo de confiança para as previsões"""
    confidence = []
    for item in forecast:
        cases = item['predicted_cases']
        margin = int(cases * 0.2)  # 20% de margem
        
        confidence.append({
            'date': item['date'],
            'lower_bound': max(0, cases - margin),
            'upper_bound': cases + margin
        })
    
    return confidence

def calculate_risk_score(risk_factors):
    """Calcula score de risco baseado nos fatores"""
    # Normalizar fatores (0-1)
    temp_score = (risk_factors['temperature'] - 20) / 15  # 20-35°C
    humidity_score = (risk_factors['humidity'] - 60) / 30  # 60-90%
    density_score = risk_factors['population_density'] / 1000  # 0-1000
    sanitation_score = 1 - risk_factors['sanitation_index']  # Inverter (pior saneamento = maior risco)
    cases_score = risk_factors['previous_cases'] / 500  # 0-500
    
    # Pesos para cada fator
    weights = {
        'temperature': 0.25,
        'humidity': 0.20,
        'density': 0.20,
        'sanitation': 0.25,
        'cases': 0.10
    }
    
    risk_score = (
        temp_score * weights['temperature'] +
        humidity_score * weights['humidity'] +
        density_score * weights['density'] +
        sanitation_score * weights['sanitation'] +
        cases_score * weights['cases']
    )
    
    return min(1.0, max(0.0, risk_score))

def get_risk_level(risk_score):
    """Determina o nível de risco baseado no score"""
    if risk_score < 0.3:
        return 'Baixo'
    elif risk_score < 0.6:
        return 'Médio'
    elif risk_score < 0.8:
        return 'Alto'
    else:
        return 'Muito Alto'

def get_recommendations(risk_score):
    """Gera recomendações baseadas no nível de risco"""
    level = get_risk_level(risk_score)
    
    recommendations = {
        'Baixo': [
            'Manter vigilância epidemiológica de rotina',
            'Continuar campanhas educativas preventivas',
            'Monitorar indicadores ambientais'
        ],
        'Médio': [
            'Intensificar ações de controle vetorial',
            'Aumentar frequência de monitoramento',
            'Reforçar campanhas de conscientização'
        ],
        'Alto': [
            'Implementar medidas de controle emergencial',
            'Mobilizar equipes de saúde adicionais',
            'Intensificar eliminação de criadouros'
        ],
        'Muito Alto': [
            'Declarar estado de alerta epidemiológico',
            'Implementar plano de contingência',
            'Coordenar resposta intersetorial'
        ]
    }
    
    return recommendations.get(level, [])

