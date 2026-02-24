from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func
from src.models.user import db
from src.models.health_data import HealthCase, Municipality

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def dashboard():
    """
    Dashboard com JOIN corrigido entre 6 e 7 dígitos do IBGE
    + Casos por UF filtrável por doença
    + Casos por UF e Doença (UF x doença)
    """
    disease_filter = (request.args.get("disease") or "all").strip()

    total_cases = db.session.query(func.count(HealthCase.id)).scalar() or 0

    if total_cases == 0:
        return jsonify({
            "total_cases": 0,
            "hospitalization_rate": 0,
            "hospitalization_count": 0,
            "death_rate": 0,
            "death_count": 0,
            "cases_by_disease": [],
            "cases_by_month": [],
            "cases_by_uf": [],
            "cases_by_uf_disease": [],
            "diseases": []
        }), 200

    # Hospitalização e Óbitos
    hosp_count = db.session.query(func.count(HealthCase.id)).filter(HealthCase.hospitaliz == 1).scalar() or 0
    hosp_rate = round((hosp_count / total_cases) * 100, 1)

    death_count = db.session.query(func.count(HealthCase.id)).filter(HealthCase.evolucao == 2).scalar() or 0
    death_rate = round((death_count / total_cases) * 100, 1)

    # Catálogo de doenças
    diseases = [
        r[0] for r in db.session.query(HealthCase.disease_name)
        .filter(HealthCase.disease_name.isnot(None))
        .filter(func.trim(HealthCase.disease_name) != "")
        .distinct()
        .order_by(HealthCase.disease_name.asc())
        .all()
    ]

    # Agrupamento por Doença
    cases_by_disease = db.session.query(
        HealthCase.disease_name.label("disease"),
        func.count(HealthCase.id).label("count")
    ).group_by(HealthCase.disease_name).all()

    # Evolução Mensal
    cases_by_month = db.session.query(
        func.date_format(HealthCase.dt_notific, "%Y-%m").label("month"),
        func.count(HealthCase.id).label("count")
    ).filter(HealthCase.dt_notific.isnot(None)).group_by("month").order_by("month").all()

    # Base do JOIN UF (6 dígitos)
    base_join = (
        db.session.query(
            Municipality.uf.label("uf_sigla"),
            func.count(HealthCase.id).label("count")
        )
        .join(
            Municipality,
            func.substr(Municipality.id, 1, 6) == func.substr(HealthCase.id_municip, 1, 6)
        )
    )

    # ✅ cases_by_uf filtrável por doença (para gráfico simples)
    if disease_filter.lower() != "all":
        base_join = base_join.filter(func.lower(HealthCase.disease_name) == disease_filter.lower())

    cases_by_uf = (
        base_join
        .group_by(Municipality.uf)
        .order_by(func.count(HealthCase.id).desc())
        .limit(10)
        .all()
    )

    # ✅ cases_by_uf_disease (UF x Doença) — útil p/ stacked chart
    uf_disease_q = (
        db.session.query(
            Municipality.uf.label("uf"),
            HealthCase.disease_name.label("disease"),
            func.count(HealthCase.id).label("count")
        )
        .join(
            Municipality,
            func.substr(Municipality.id, 1, 6) == func.substr(HealthCase.id_municip, 1, 6)
        )
        .filter(HealthCase.disease_name.isnot(None))
        .group_by(Municipality.uf, HealthCase.disease_name)
        .order_by(Municipality.uf.asc(), HealthCase.disease_name.asc())
    )

    # opcional: se você quiser que UF x Doença também respeite o filtro
    if disease_filter.lower() != "all":
        uf_disease_q = uf_disease_q.filter(func.lower(HealthCase.disease_name) == disease_filter.lower())

    cases_by_uf_disease = uf_disease_q.all()

    return jsonify({
        "total_cases": total_cases,
        "hospitalization_rate": hosp_rate,
        "hospitalization_count": hosp_count,
        "death_rate": death_rate,
        "death_count": death_count,
        "diseases": diseases,
        "cases_by_disease": [{"disease": d.disease, "count": int(d.count)} for d in cases_by_disease],
        "cases_by_month": [{"month": m.month, "count": int(m.count)} for m in cases_by_month],
        "cases_by_uf": [{"uf": u.uf_sigla, "count": int(u.count)} for u in cases_by_uf],
        "cases_by_uf_disease": [{"uf": u.uf, "disease": u.disease, "count": int(u.count)} for u in cases_by_uf_disease],
        "filters": {"disease": disease_filter}
    }), 200