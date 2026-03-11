def _resolve_tenant_data_source(tenant_slug: str):
    sql = text("""
        SELECT
            t.slug AS tenant_slug,
            t.scope_type,
            t.scope_value,
            ds.bind_key,
            ds.datalake_db,
            ds.aggregate_view_name,
            ds.supported_diseases_json,
            ds.municipality_join_mode,
            ds.is_active
        FROM tenants t
        JOIN tenant_data_sources ds
          ON ds.tenant_id = t.id
        WHERE LOWER(t.slug) = :tenant_slug
          AND t.is_active = 1
          AND ds.is_active = 1
        LIMIT 1
    """)
    row = db.session.execute(sql, {"tenant_slug": tenant_slug.lower()}).mappings().first()
    return row

def _get_tenant_session(bind_key: str):
    if not bind_key:
        return db.session
    engine = db.get_engine(bind=bind_key)
    return Session(bind=engine)

def _get_supported_diseases(ds_row):
    raw = ds_row["supported_diseases_json"]
    if isinstance(raw, str):
        import json
        return [x.lower() for x in json.loads(raw)]
    return [str(x).lower() for x in raw]