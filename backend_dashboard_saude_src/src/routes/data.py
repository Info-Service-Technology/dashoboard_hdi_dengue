# src/routes/data.py
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func, desc, asc

from src.models.user import db
from src.models.health_data import HealthCase, Municipality

data_bp = Blueprint("data", __name__)

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
        .filter(HealthCase.dt_notific < end_d)
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

    Retorna lista paginada (pra DataGrid).
    """
    q, disease, uf, start_d, end_d = _base_query()

    # busca simples
    search = (request.args.get("search") or "").strip()
    if search:
        s = f"%{search.lower()}%"
        q = q.filter(
            func.lower(Municipality.name).like(s) |
            func.lower(HealthCase.disease_name).like(s)
        )

    # ordenação
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

    # paginação
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
            # coloque aqui outros campos do HealthCase que você quiser exibir
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
        }
    }), 200

@data_bp.route("/data/meta", methods=["GET"])
@jwt_required()
def data_meta():
    """
    Retorna listas para popular selects (doenças/ufs) direto do banco.
    """
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

    return jsonify({"diseases": diseases, "ufs": ufs}), 200