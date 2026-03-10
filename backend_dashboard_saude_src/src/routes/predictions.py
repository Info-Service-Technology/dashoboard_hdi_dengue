from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from src.models.user import db
from src.models.health_data import HealthCase

predictions_bp = Blueprint("predictions", __name__)


def _tenant_scope():
    claims = get_jwt() or {}
    scope_type = (claims.get("tenant_scope_type") or "BR").strip().upper()
    scope_value = (claims.get("tenant_scope_value") or "all").strip()
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


def _add_months(year: int, month: int, add: int):
    total = (year * 12 + (month - 1)) + add
    y = total // 12
    m = (total % 12) + 1
    return y, m


@predictions_bp.route("/trends", methods=["GET"])
@jwt_required()
def prediction_trends():
    try:
        scope_type, scope_value, tenant_slug = _tenant_scope()

        disease = (request.args.get("disease") or "all").strip().lower()
        horizon = int(request.args.get("horizon") or 12)

        if horizon < 1:
            horizon = 1
        if horizon > 24:
            horizon = 24

        # =================================================
        # PREFEITURA COM DATALAKE PRÓPRIO
        # =================================================
        if scope_type == "MUN" and _has_tenant_bind(tenant_slug):
            if disease not in ("all", "dengue"):
                return jsonify([]), 200

            sess = _get_session_for_tenant(tenant_slug)
            mun6 = _mun_code6(scope_value)

            if not mun6:
                return jsonify({"error": "Tenant MUN inválido (scope_value)"}), 400

            sql = """
                SELECT
                    v.ano AS ano,
                    v.periodo AS periodo,
                    SUM(v.casos) AS cases
                FROM vw_dengue_kpis v
                WHERE v.granularidade = 'mensal'
                  AND v.municipio = :municipio
                GROUP BY v.ano, v.periodo
                ORDER BY v.ano, v.periodo
            """

            rows = sess.execute(text(sql), {"municipio": mun6}).mappings().all()

            if not rows:
                return jsonify([]), 200

            series = []
            for r in rows:
                ano = int(r["ano"])
                periodo = int(r["periodo"])
                cases = int(r["cases"] or 0)
                series.append({
                    "year": ano,
                    "month": periodo,
                    "cases": cases
                })

            last_values = [s["cases"] for s in series[-3:]]
            avg_last = sum(last_values) / len(last_values) if last_values else 0
            last_val = series[-1]["cases"]

            growth_factor = 1.0
            if avg_last > 0:
                growth_factor = max(0.7, min(1.3, last_val / avg_last))

            pred = []
            base_year = series[-1]["year"]
            base_month = series[-1]["month"]
            current = last_val if last_val > 0 else avg_last

            for i in range(1, horizon + 1):
                y, m = _add_months(base_year, base_month, i)
                current = max(0, round(current * ((growth_factor + 1.0) / 2.0)))
                pred.append({
                    "bucket": f"{y}-{str(m).zfill(2)}",
                    "cases_pred": int(current)
                })

            return jsonify(pred), 200

        # =================================================
        # BASE GERAL
        # =================================================
        q = (
            db.session.query(
                func.date_format(HealthCase.dt_notific, "%Y-%m").label("bucket"),
                func.count(HealthCase.id).label("cases")
            )
            .filter(HealthCase.dt_notific.isnot(None))
        )

        if disease != "all":
            q = q.filter(func.lower(HealthCase.disease_name) == disease)

        if scope_type == "UF":
            q = q.filter(func.upper(HealthCase.sg_uf_not) == scope_value)

        if scope_type == "MUN":
            mun6 = _mun_code6(scope_value)
            if not mun6:
                return jsonify({"error": "Tenant MUN inválido (scope_value)"}), 400
            q = q.filter(func.substr(HealthCase.id_municip, 1, 6) == mun6)

        rows = (
            q.group_by("bucket")
            .order_by("bucket")
            .all()
        )

        if not rows:
            return jsonify([]), 200

        series = []
        for r in rows:
            bucket = str(r.bucket)
            try:
                y, m = bucket.split("-")
                series.append({
                    "year": int(y),
                    "month": int(m),
                    "cases": int(r.cases or 0)
                })
            except Exception:
                continue

        if not series:
            return jsonify([]), 200

        last_values = [s["cases"] for s in series[-3:]]
        avg_last = sum(last_values) / len(last_values) if last_values else 0
        last_val = series[-1]["cases"]

        growth_factor = 1.0
        if avg_last > 0:
            growth_factor = max(0.7, min(1.3, last_val / avg_last))

        pred = []
        base_year = series[-1]["year"]
        base_month = series[-1]["month"]
        current = last_val if last_val > 0 else avg_last

        for i in range(1, horizon + 1):
            y, m = _add_months(base_year, base_month, i)
            current = max(0, round(current * ((growth_factor + 1.0) / 2.0)))
            pred.append({
                "bucket": f"{y}-{str(m).zfill(2)}",
                "cases_pred": int(current)
            })

        return jsonify(pred), 200

    except Exception as e:
        print(f"❌ prediction_trends: {e}")
        return jsonify({"error": "Erro interno ao processar previsões"}), 500


@predictions_bp.route("/diseases", methods=["GET"])
@jwt_required()
def prediction_diseases():
    try:
        scope_type, _scope_value, tenant_slug = _tenant_scope()

        if scope_type == "MUN" and _has_tenant_bind(tenant_slug):
            return jsonify(["Dengue"]), 200

        rows = (
            db.session.query(HealthCase.disease_name)
            .filter(HealthCase.disease_name.isnot(None))
            .filter(func.trim(HealthCase.disease_name) != "")
            .distinct()
            .order_by(HealthCase.disease_name.asc())
            .all()
        )

        return jsonify([r[0] for r in rows]), 200

    except Exception as e:
        print(f"❌ prediction_diseases: {e}")
        return jsonify({"error": "Erro interno ao listar doenças"}), 500