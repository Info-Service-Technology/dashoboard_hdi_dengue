# src/routes/analytics.py
import csv
import io
from flask import Response
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func

from src.models.user import db
from src.models.health_data import HealthCase, Municipality

analytics_bp = Blueprint("analytics", __name__)


def _parse_dates():
    """
    Recebe start/end em ISO (YYYY-MM-DD) e devolve datetime.
    Defaults: últimos 90 dias.
    """
    end = request.args.get("end")
    start = request.args.get("start")

    # end_dt como hoje UTC (na data)
    end_dt = datetime.fromisoformat(end) if end else datetime.utcnow()
    start_dt = datetime.fromisoformat(start) if start else (end_dt - timedelta(days=90))

    # normaliza: garante start <= end
    if start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt

    return start_dt, end_dt


def _base_query():
    """
    Base da query:
    - Join HealthCase -> Municipality pelo IBGE (6 primeiros dígitos)
    - Filtros: disease, uf
    """
    disease = (request.args.get("disease") or "all").strip()
    uf = (request.args.get("uf") or "all").strip()
    start_dt, end_dt = _parse_dates()

    q = (
        db.session.query(HealthCase, Municipality)
        .join(
            Municipality,
            func.substr(Municipality.id, 1, 6) == func.substr(HealthCase.id_municip, 1, 6),
        )
        .filter(Municipality.latitude.isnot(None))
        .filter(Municipality.longitude.isnot(None))
    )

    if disease.lower() != "all":
        q = q.filter(func.lower(HealthCase.disease_name) == func.lower(disease))

    if uf.lower() != "all":
        q = q.filter(func.upper(Municipality.uf) == uf.upper())

    return q, disease, uf, start_dt, end_dt


@analytics_bp.route("/analytics/kpi", methods=["GET"])
@jwt_required()
def analytics_kpi():
    try:
        q, disease, uf, start_dt, end_dt = _base_query()

        # ----------------------------
        # Período (DATA OFICIAL: dt_notific)
        # ----------------------------
        q = q.filter(HealthCase.dt_notific.isnot(None))
        q = q.filter(HealthCase.dt_notific >= start_dt.date())
        q = q.filter(HealthCase.dt_notific < end_dt.date())

        total_cases = q.with_entities(func.count(HealthCase.id)).scalar() or 0
        uf_count = q.with_entities(func.count(func.distinct(Municipality.uf))).scalar() or 0
        city_count = q.with_entities(func.count(func.distinct(Municipality.name))).scalar() or 0

        top_uf_row = (
            q.with_entities(Municipality.uf, func.count(HealthCase.id).label("cases"))
            .group_by(Municipality.uf)
            .order_by(func.count(HealthCase.id).desc())
            .first()
        )
        top_uf = {"uf": top_uf_row[0], "cases": int(top_uf_row[1])} if top_uf_row else None

                # ----------------------------
        # Δ (padrão mercado): YoY ou PoP
        # delta_mode=yoy|pop (default=yoy)
        # Guardrails:
        # - delta calculado na "janela" (cap) ancorada no ÚLTIMO dia com dado do período filtrado
        # - evita -100% falso quando end_dt está além do último dado existente
        # ----------------------------
        delta_mode = (request.args.get("delta_mode") or "yoy").strip().lower()

        # tamanho do período selecionado
        period_days = (end_dt.date() - start_dt.date()).days
        if period_days <= 0:
            period_days = 1

        # CAP: janela interpretável pro executivo (ajuste 28/60/90)
        delta_window_days = min(period_days, 90)

        # Descobre o último dia com dado DENTRO do filtro (disease/uf + start/end)
        # Isso previne Δ=-100% quando o "end" está muito no futuro.
        last_dt = q.with_entities(func.max(HealthCase.dt_notific)).scalar()  # date ou None

        # base_end inclusivo é o último dia com dado; se não houver dado, cai no end_dt-1
        if last_dt is None:
            base_end_incl = (end_dt.date() - timedelta(days=1))
            base_has_data = False
        else:
            base_end_incl = last_dt
            base_has_data = True

        # base_start (incl.) respeita janela e também o start_dt do filtro
        base_start_incl = base_end_incl - timedelta(days=delta_window_days - 1)
        if base_start_incl < start_dt.date():
            base_start_incl = start_dt.date()

        # Usamos fim EXCLUSIVO nos filtros SQL
        base_end_excl = base_end_incl + timedelta(days=1)

        # total da janela-base do Δ (pode ser 0)
        q_delta, *_ = _base_query()
        q_delta = q_delta.filter(HealthCase.dt_notific.isnot(None))
        q_delta = q_delta.filter(HealthCase.dt_notific >= base_start_incl)
        q_delta = q_delta.filter(HealthCase.dt_notific < base_end_excl)
        base_total = q_delta.with_entities(func.count(HealthCase.id)).scalar() or 0

        # Define janela anterior (mesma duração)
        if delta_mode == "pop":
            prev_end_excl = base_start_incl  # exclusivo
            prev_start_incl = prev_end_excl - timedelta(days=delta_window_days)
            prev_end_incl = prev_end_excl - timedelta(days=1)
        else:
            # YoY: mesma janela, 1 ano antes
            prev_start_incl = base_start_incl - timedelta(days=365)
            prev_end_excl = base_end_excl - timedelta(days=365)
            prev_end_incl = prev_end_excl - timedelta(days=1)

        q_prev, *_ = _base_query()
        q_prev = q_prev.filter(HealthCase.dt_notific.isnot(None))
        q_prev = q_prev.filter(HealthCase.dt_notific >= prev_start_incl)
        q_prev = q_prev.filter(HealthCase.dt_notific < prev_end_excl)

        prev_total = q_prev.with_entities(func.count(HealthCase.id)).scalar() or 0

        # Regra de mercado: se não tem base ou não tem janela atual com dado, Δ vira N/A (None)
        delta_pct = None
        if base_total > 0 and prev_total > 0:
            delta_pct = ((base_total - prev_total) / prev_total) * 100.0

        delta_base = {
            "mode": delta_mode,
            "window_days": int(delta_window_days),
            "base_has_data": bool(base_has_data),
            "base_start": base_start_incl.isoformat(),
            "base_end": base_end_incl.isoformat(),
            "base_total": int(base_total),
            "prev_total": int(prev_total),
            "prev_start": prev_start_incl.isoformat(),
            "prev_end": prev_end_incl.isoformat(),
        }

        
                # ----------------------------
        # Executive Summary + Score (0–100)
        # ----------------------------
        def _clamp(x, lo, hi):
            return max(lo, min(hi, x))

        # 1) componente de tendência (Δ)
        # delta_pct: negativo ou None => 0; 0..20 => 0..20; 20..60 => 20..40; >60 => 40
        if delta_pct is None:
            trend_score = 0
            trend_label = "Indisponível"
        else:
            if delta_pct <= 0:
                trend_score = 0
                trend_label = "Queda/Estável"
            elif delta_pct <= 20:
                trend_score = (delta_pct / 20.0) * 20.0
                trend_label = "Alta leve"
            elif delta_pct <= 60:
                trend_score = 20.0 + ((delta_pct - 20.0) / 40.0) * 20.0
                trend_label = "Alta"
            else:
                trend_score = 40.0
                trend_label = "Alta forte"

        trend_score = _clamp(trend_score, 0, 40)

        # 2) componente de concentração (Top UF)
        top_share = 0.0
        if top_uf and total_cases > 0:
            top_share = float(top_uf["cases"]) / float(total_cases)

        # 0..1 vira 0..40, mas cap em 0.6 pra não explodir
        conc_score = _clamp((min(top_share, 0.6) / 0.6) * 40.0, 0, 40)

        # 3) componente de volume (usa base_total da janela do delta)
        # volume grande aumenta risco operacional (cap em 20)
        base_total = int(delta_base.get("base_total") or 0)
        # escala simples: 0..2000 => 0..10 ; 2000..20000 => 10..20 ; >20000 => 20
        if base_total <= 0:
            vol_score = 0
        elif base_total <= 2000:
            vol_score = (base_total / 2000.0) * 10.0
        elif base_total <= 20000:
            vol_score = 10.0 + ((base_total - 2000.0) / 18000.0) * 10.0
        else:
            vol_score = 20.0

        vol_score = _clamp(vol_score, 0, 20)

        # Score final
        risk_score = int(round(_clamp(trend_score + conc_score + vol_score, 0, 100)))

        # Faixas padrão mercado (ajuste se quiser)
        if risk_score < 30:
            risk_level = "Baixo"
            badge = "🟢"
        elif risk_score < 60:
            risk_level = "Moderado"
            badge = "🟡"
        elif risk_score < 80:
            risk_level = "Alto"
            badge = "🔴"
        else:
            risk_level = "Crítico"
            badge = "🔴"

        # Mensagens executivas (simples e objetivas)
        alert = "Situação sob controle."
        recommendation = "Manter monitoramento regular."

        if delta_pct is None:
            alert = "Base histórica insuficiente para variação. Usando sinais de volume e concentração."
            recommendation = "Validar cobertura de dados e manter monitoramento."
        else:
            if delta_pct > 20:
                alert = "Crescimento acelerado no curto prazo."
                recommendation = "Reforçar vigilância e plano de contingência."
            elif delta_pct > 5:
                alert = "Crescimento acima do esperado."
                recommendation = "Acompanhar evolução e preparar contingência."
            elif delta_pct < -10:
                alert = "Queda relevante no curto prazo."
                recommendation = "Manter acompanhamento para confirmar tendência."

        # reforço por concentração (independente do delta)
        if top_share >= 0.4 and top_uf:
            alert = f"Concentração elevada em {top_uf['uf']}."
            recommendation = "Priorizar ações e alocação de recursos na UF líder."

        context = {
            "disease": disease,                    # "Dengue" ou "all"
            "uf": uf,                              # "SP" ou "all"
            "period_start": start_dt.date().isoformat(),
            "period_end": end_dt.date().isoformat(),
            "delta_mode": delta_mode,
            "window_days": int(delta_window_days),
        }

        executive_summary = {
            "trend": trend_label,
            "risk_level": risk_level,
            "risk_score": risk_score,   # ✅ novo
            "badge": badge,             # ✅ novo
            "top_share": round(top_share * 100, 1),  # opcional (%)
            "alert": alert,
            "recommendation": recommendation,
            "context": context,
        }
        executive_summary["context"] = {
            "disease": disease,
            "uf": uf,
            "period_start": start_dt.date().isoformat(),
            "period_end": end_dt.date().isoformat(),
            "delta_mode": delta_mode,
            "window_days": delta_base.get("window_days")
        }
        executive_summary["scope"] = (
            f"{'Multidoença' if disease == 'all' else disease} | "
            f"{'Todas as UFs' if uf == 'all' else uf}"
        )

        return jsonify(
            {
                "total_cases": int(total_cases),
                "uf_affected": int(uf_count),
                "cities_affected": int(city_count),
                "top_uf": top_uf,
                "delta_pct": delta_pct,
                "delta_base": delta_base,
                "executive_summary": executive_summary,  # ✅ novo
            }
        ), 200

    except Exception as e:
        print(f"❌ analytics_kpi: {e}")
        return jsonify({"error": "Erro interno ao processar KPI"}), 500

@analytics_bp.route("/analytics/compare", methods=["GET"])
@jwt_required()
def analytics_compare():
    """
    Se uf=all -> Top 10 UFs por casos
    Se uf=XX -> Top 10 municípios da UF por casos
    """
    try:
        q, disease, uf, start_dt, end_dt = _base_query()

        q = q.filter(HealthCase.dt_notific.isnot(None))
        q = q.filter(HealthCase.dt_notific >= start_dt.date())
        q = q.filter(HealthCase.dt_notific < end_dt.date())

        if uf.lower() == "all":
            rows = (
                q.with_entities(Municipality.uf.label("label"), func.count(HealthCase.id).label("cases"))
                .group_by(Municipality.uf)
                .order_by(func.count(HealthCase.id).desc())
                .limit(10)
                .all()
            )
        else:
            rows = (
                q.with_entities(Municipality.name.label("label"), func.count(HealthCase.id).label("cases"))
                .group_by(Municipality.name)
                .order_by(func.count(HealthCase.id).desc())
                .limit(10)
                .all()
            )

        data = [{"label": r.label, "cases": int(r.cases)} for r in rows]
        return jsonify(data), 200

    except Exception as e:
        print(f"❌ analytics_compare: {e}")
        return jsonify({"error": "Erro interno ao processar comparativos"}), 500


@analytics_bp.route("/analytics/trends", methods=["GET"])
@jwt_required()
def analytics_trends():
    """
    Série temporal por dt_notific:
    gran = day | week | month
    """
    try:
        q, disease, uf, start_dt, end_dt = _base_query()

        q = q.filter(HealthCase.dt_notific.isnot(None))
        q = q.filter(HealthCase.dt_notific >= start_dt.date())
        q = q.filter(HealthCase.dt_notific < end_dt.date())

        gran = (request.args.get("gran") or "week").strip().lower()

        if gran == "day":
            bucket = HealthCase.dt_notific  # Date
        elif gran == "month":
            # YYYY-MM-01 (MySQL). Se você estiver em SQLite, isso pode variar.
            bucket = func.date_format(HealthCase.dt_notific, "%Y-%m-01")
        else:
            # week: YYYY-WW (MySQL)
            bucket = func.date_format(HealthCase.dt_notific, "%Y-%u")

        rows = (
            q.with_entities(bucket.label("bucket"), func.count(HealthCase.id).label("cases"))
            .group_by("bucket")
            .order_by("bucket")
            .all()
        )

        data = [{"bucket": str(r.bucket), "cases": int(r.cases)} for r in rows]
        return jsonify(data), 200

    except Exception as e:
        print(f"❌ analytics_trends: {e}")
        return jsonify({"error": "Erro interno ao processar tendências"}), 500

def _trend_bucket(gran: str):
    """
    Retorna expressão SQL do bucket conforme granularidade.
    MySQL: usa date_format.
    """
    g = (gran or "week").strip().lower()

    if g == "day":
        return HealthCase.dt_notific
    if g == "month":
        return func.date_format(HealthCase.dt_notific, "%Y-%m-01")
    # week
    return func.date_format(HealthCase.dt_notific, "%Y-%u")

@analytics_bp.route("/analytics/export/csv", methods=["GET"])
@jwt_required()
def analytics_export_csv():
    """
    Exporta CSV do painel (KPI + Compare + Trends) usando os mesmos filtros.
    """
    try:
        q, disease, uf, start_dt, end_dt = _base_query()

        # período
        q = q.filter(HealthCase.dt_notific.isnot(None))
        q = q.filter(HealthCase.dt_notific >= start_dt.date())
        q = q.filter(HealthCase.dt_notific < end_dt.date())

        gran = (request.args.get("gran") or "week").strip().lower()

        # -------- KPI --------
        total_cases = q.with_entities(func.count(HealthCase.id)).scalar() or 0
        uf_count = q.with_entities(func.count(func.distinct(Municipality.uf))).scalar() or 0
        city_count = q.with_entities(func.count(func.distinct(Municipality.name))).scalar() or 0

        top_uf_row = (
            q.with_entities(Municipality.uf, func.count(HealthCase.id).label("cases"))
            .group_by(Municipality.uf)
            .order_by(func.count(HealthCase.id).desc())
            .first()
        )
        top_uf = top_uf_row[0] if top_uf_row else ""
        top_uf_cases = int(top_uf_row[1]) if top_uf_row else 0

        # -------- Compare --------
        if (uf or "").lower() == "all":
            compare_rows = (
                q.with_entities(Municipality.uf.label("label"), func.count(HealthCase.id).label("cases"))
                .group_by(Municipality.uf)
                .order_by(func.count(HealthCase.id).desc())
                .limit(10)
                .all()
            )
            compare_kind = "UF"
        else:
            compare_rows = (
                q.with_entities(Municipality.name.label("label"), func.count(HealthCase.id).label("cases"))
                .group_by(Municipality.name)
                .order_by(func.count(HealthCase.id).desc())
                .limit(10)
                .all()
            )
            compare_kind = "Municipio"

        # -------- Trends --------
        # IMPORTANTE: isto é MySQL (você está usando date_format).
        # Se futuramente mudar pra SQLite, a gente ajusta igual fizemos antes.
        if gran == "day":
            bucket = HealthCase.dt_notific
        elif gran == "month":
            bucket = func.date_format(HealthCase.dt_notific, "%Y-%m-01")
        else:
            bucket = func.date_format(HealthCase.dt_notific, "%Y-%u")

        trend_rows = (
            q.with_entities(bucket.label("bucket"), func.count(HealthCase.id).label("cases"))
            .group_by("bucket")
            .order_by("bucket")
            .all()
        )

        # -------- monta CSV (3 seções) --------
        out = io.StringIO()
        w = csv.writer(out, delimiter=";")

        # Metadados / Filtros
        w.writerow(["HDI - Export Analytics"])
        w.writerow(["generated_at_utc", datetime.utcnow().isoformat()])
        w.writerow(["disease", disease])
        w.writerow(["uf", uf])
        w.writerow(["start", start_dt.date().isoformat()])
        w.writerow(["end", end_dt.date().isoformat()])
        w.writerow(["gran", gran])
        w.writerow([])

        # KPI
        w.writerow(["[KPI]"])
        w.writerow(["total_cases", "uf_affected", "cities_affected", "top_uf", "top_uf_cases"])
        w.writerow([int(total_cases), int(uf_count), int(city_count), top_uf, int(top_uf_cases)])
        w.writerow([])

        # Compare
        w.writerow([f"[COMPARE] Top 10 {compare_kind}"])
        w.writerow(["label", "cases"])
        for r in compare_rows:
            w.writerow([r.label, int(r.cases)])
        w.writerow([])

        # Trends
        w.writerow(["[TRENDS]"])
        w.writerow(["bucket", "cases"])
        for r in trend_rows:
            w.writerow([str(r.bucket), int(r.cases)])

        csv_text = out.getvalue()
        out.close()

        filename = f"hdi_analytics_{(disease or 'all').lower()}_{(uf or 'all').lower()}_{start_dt.date()}_{end_dt.date()}.csv"

        return Response(
            csv_text,
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except Exception as e:
        print(f"❌ analytics_export_csv: {e}")
        return jsonify({"error": "Erro interno ao exportar CSV"}), 500