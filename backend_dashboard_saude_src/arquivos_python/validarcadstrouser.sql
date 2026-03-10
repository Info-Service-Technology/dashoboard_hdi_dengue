curl -s \
-H "Authorization: Bearer SEU_TOKEN_NOVO" \
"http://localhost:5000/api/analytics?disease=dengue&start=2019-01-01&end=2026-12-31&gran=month"

--- validar vinculo usuario tenant
SELECT
    u.id AS user_id,
    u.email,
    t.id AS tenant_id,
    t.slug,
    t.name,
    t.scope_type,
    t.scope_value
FROM dashboard_saude.users u
JOIN dashboard_saude.user_tenants ut
  ON ut.user_id = u.id
JOIN dashboard_saude.tenants t
  ON t.id = ut.tenant_id
WHERE u.email = 'teste.marica.01@email.com';

--- ver usuário recém criado
SELECT id, first_name, last_name, email, role
FROM dashboard_saude.users
WHERE email = 'teste.marica.01@email.com';

---
SELECT id, slug, name, scope_type, scope_value, is_active
FROM dashboard_saude.tenants
ORDER BY id;