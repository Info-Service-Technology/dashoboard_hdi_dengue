from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import User
from src.models.health_data import HealthCase, Municipality, HealthUnit, db
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
import pandas as pd

health_data_bp = Blueprint('health_data', __name__)

@health_data_bp.route('/dashboard/overview', methods=['GET'])
@jwt_required()
def get_dashboard_overview():
    """Obter dados gerais do dashboard"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Estatísticas gerais
        total_cases = HealthCase.query.count()
        
        # Casos por doença
        cases_by_disease = db.session.query(
            HealthCase.disease_name,
            func.count(HealthCase.id).label('count')
        ).group_by(HealthCase.disease_name).all()
        
        # Casos por mês (últimos 12 meses)
        twelve_months_ago = datetime.now() - timedelta(days=365)
        cases_by_month = db.session.query(
            func.strftime('%Y-%m', HealthCase.dt_notific).label('month'),
            func.count(HealthCase.id).label('count')
        ).filter(
            HealthCase.dt_notific >= twelve_months_ago
        ).group_by(
            func.strftime('%Y-%m', HealthCase.dt_notific)
        ).order_by('month').all()
        
        # Casos por UF
        cases_by_uf = db.session.query(
            HealthCase.sg_uf_not,
            func.count(HealthCase.id).label('count')
        ).group_by(HealthCase.sg_uf_not).order_by(
            func.count(HealthCase.id).desc()
        ).limit(10).all()
        
        # Taxa de hospitalização
        hospitalized_cases = HealthCase.query.filter_by(hospitaliz=1).count()
        hospitalization_rate = (hospitalized_cases / total_cases * 100) if total_cases > 0 else 0
        
        # Taxa de óbitos
        death_cases = HealthCase.query.filter_by(evolucao=2).count()
        death_rate = (death_cases / total_cases * 100) if total_cases > 0 else 0
        
        return jsonify({
            'total_cases': total_cases,
            'hospitalization_rate': round(hospitalization_rate, 2),
            'death_rate': round(death_rate, 2),
            'cases_by_disease': [{'disease': row[0], 'count': row[1]} for row in cases_by_disease],
            'cases_by_month': [{'month': row[0], 'count': row[1]} for row in cases_by_month],
            'cases_by_uf': [{'uf': row[0], 'count': row[1]} for row in cases_by_uf]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@health_data_bp.route('/cases', methods=['GET'])
@jwt_required()
def get_cases():
    """Obter casos com filtros"""
    try:
        # Parâmetros de filtro
        disease = request.args.get('disease')
        uf = request.args.get('uf')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        # Construir query
        query = HealthCase.query
        
        if disease:
            query = query.filter(HealthCase.disease_name == disease)
        
        if uf:
            query = query.filter(HealthCase.sg_uf_not == uf)
        
        if start_date:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(HealthCase.dt_notific >= start_date_obj)
        
        if end_date:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(HealthCase.dt_notific <= end_date_obj)
        
        # Paginação
        paginated_cases = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'cases': [case.to_dict() for case in paginated_cases.items],
            'total': paginated_cases.total,
            'pages': paginated_cases.pages,
            'current_page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@health_data_bp.route('/analytics/symptoms', methods=['GET'])
@jwt_required()
def get_symptoms_analytics():
    """Análise de sintomas por doença"""
    try:
        disease = request.args.get('disease')
        
        query = HealthCase.query
        if disease:
            query = query.filter(HealthCase.disease_name == disease)
        
        cases = query.all()
        
        if not cases:
            return jsonify({'symptoms': []}), 200
        
        # Contar sintomas
        symptoms_count = {
            'febre': sum(1 for case in cases if case.febre == 1),
            'mialgia': sum(1 for case in cases if case.mialgia == 1),
            'cefaleia': sum(1 for case in cases if case.cefaleia == 1),
            'exantema': sum(1 for case in cases if case.exantema == 1),
            'vomito': sum(1 for case in cases if case.vomito == 1),
            'nausea': sum(1 for case in cases if case.nausea == 1),
            'dor_costas': sum(1 for case in cases if case.dor_costas == 1),
            'artralgia': sum(1 for case in cases if case.artralgia == 1),
            'diarreia': sum(1 for case in cases if case.diarreia == 1)
        }
        
        total_cases = len(cases)
        symptoms_percentage = {
            symptom: round((count / total_cases * 100), 2) 
            for symptom, count in symptoms_count.items()
        }
        
        return jsonify({
            'symptoms_count': symptoms_count,
            'symptoms_percentage': symptoms_percentage,
            'total_cases': total_cases
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@health_data_bp.route('/analytics/demographics', methods=['GET'])
@jwt_required()
def get_demographics_analytics():
    """Análise demográfica"""
    try:
        disease = request.args.get('disease')
        
        query = HealthCase.query
        if disease:
            query = query.filter(HealthCase.disease_name == disease)
        
        # Distribuição por sexo
        sex_distribution = db.session.query(
            HealthCase.cs_sexo,
            func.count(HealthCase.id).label('count')
        )
        if disease:
            sex_distribution = sex_distribution.filter(HealthCase.disease_name == disease)
        sex_distribution = sex_distribution.group_by(HealthCase.cs_sexo).all()
        
        # Distribuição por faixa etária
        age_groups = db.session.query(
            func.case(
                (HealthCase.nu_idade_n < 1, '0-1 anos'),
                (HealthCase.nu_idade_n < 5, '1-4 anos'),
                (HealthCase.nu_idade_n < 15, '5-14 anos'),
                (HealthCase.nu_idade_n < 25, '15-24 anos'),
                (HealthCase.nu_idade_n < 35, '25-34 anos'),
                (HealthCase.nu_idade_n < 45, '35-44 anos'),
                (HealthCase.nu_idade_n < 55, '45-54 anos'),
                (HealthCase.nu_idade_n < 65, '55-64 anos'),
                else_='65+ anos'
            ).label('age_group'),
            func.count(HealthCase.id).label('count')
        )
        if disease:
            age_groups = age_groups.filter(HealthCase.disease_name == disease)
        age_groups = age_groups.group_by('age_group').all()
        
        return jsonify({
            'sex_distribution': [{'sex': row[0], 'count': row[1]} for row in sex_distribution],
            'age_distribution': [{'age_group': row[0], 'count': row[1]} for row in age_groups]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@health_data_bp.route('/analytics/geographic', methods=['GET'])
@jwt_required()
def get_geographic_analytics():
    """Análise geográfica para mapas"""
    try:
        disease = request.args.get('disease')
        
        query = db.session.query(
            HealthCase.sg_uf_not,
            HealthCase.id_municip,
            func.count(HealthCase.id).label('cases_count')
        )
        
        if disease:
            query = query.filter(HealthCase.disease_name == disease)
        
        geographic_data = query.group_by(
            HealthCase.sg_uf_not, 
            HealthCase.id_municip
        ).all()
        
        # Dados por UF
        uf_data = {}
        for row in geographic_data:
            uf = row[0]
            if uf not in uf_data:
                uf_data[uf] = 0
            uf_data[uf] += row[2]
        
        return jsonify({
            'by_municipality': [
                {
                    'uf': row[0], 
                    'municipality_id': row[1], 
                    'cases_count': row[2]
                } 
                for row in geographic_data
            ],
            'by_uf': [
                {'uf': uf, 'cases_count': count} 
                for uf, count in uf_data.items()
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@health_data_bp.route('/diseases', methods=['GET'])
@jwt_required()
def get_diseases():
    """Listar doenças disponíveis"""
    try:
        diseases = db.session.query(
            HealthCase.disease_name,
            HealthCase.id_agravo,
            func.count(HealthCase.id).label('total_cases')
        ).group_by(
            HealthCase.disease_name, 
            HealthCase.id_agravo
        ).all()
        
        return jsonify({
            'diseases': [
                {
                    'name': row[0],
                    'code': row[1],
                    'total_cases': row[2]
                } 
                for row in diseases
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

