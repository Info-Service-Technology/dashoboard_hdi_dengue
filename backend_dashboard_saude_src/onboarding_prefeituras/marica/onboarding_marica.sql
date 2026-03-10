---criar tenant
INSERT INTO tenants (slug, name, scope_type, scope_value, is_active)
VALUES ('macae-rj', 'Macaé - RJ', 'MUN', '3302403', 1);
-----
SELECT id, slug, name, scope_type, scope_value
FROM tenants
WHERE slug = 'macae-rj';
--------------##################----------
---testar com usuario já existente
INSERT INTO user_tenants (user_id, tenant_id)
SELECT 2, t.id
FROM tenants t
WHERE t.slug = 'macae-rj';
---- cadastrar usuraio novo
INSERT INTO user
(first_name, last_name, email, password_hash, role, created_at, is_active)
VALUES
('Admin', 'Macaé', 'admin@macae-rj.com', '123456', 'admin', NOW(), 1);
---verifica usuarios

SELECT
u.email,
t.slug,
t.scope_value
FROM user u
JOIN user_tenants ut ON ut.user_id = u.id
JOIN tenants t ON t.id = ut.tenant_id
WHERE t.slug = 'macae-rj';
select * from user where email like '%macae%';
----- verificar tenant
SELECT id, slug FROM tenants WHERE slug='macae-rj';
------vincular tenant ao usuario
INSERT INTO user_tenants (user_id, tenant_id)
VALUES (2, 2);
--------verificar se o vículo esta correto
SELECT
u.email,
t.slug,
t.scope_value
FROM user u
JOIN user_tenants ut ON ut.user_id = u.id
JOIN tenants t ON t.id = ut.tenant_id
WHERE u.email = 'admin@macae-rj.com';


