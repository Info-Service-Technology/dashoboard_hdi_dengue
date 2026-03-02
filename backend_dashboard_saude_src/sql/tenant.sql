-- 1) Tenants (escopos)
CREATE TABLE IF NOT EXISTS tenants (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  slug VARCHAR(64) NOT NULL UNIQUE,         -- ex: 'br', 'marica-rj', 'santos-sp'
  name VARCHAR(128) NOT NULL,               -- ex: 'Brasil', 'Maricá - RJ'
  scope_type ENUM('BR','UF','MUN') NOT NULL DEFAULT 'BR',
  scope_value VARCHAR(64) NOT NULL DEFAULT 'all', -- BR:'all' | UF:'RJ' | MUN:'330270'
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2) Associação usuários x tenants (muitos-para-muitos)
CREATE TABLE IF NOT EXISTS user_tenants (
  user_id INT NOT NULL,
  tenant_id BIGINT NOT NULL,
  PRIMARY KEY (user_id, tenant_id),
  CONSTRAINT fk_user_tenants_user
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
  CONSTRAINT fk_user_tenants_tenant
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

-- 3) Seeds (Brasil + Maricá + Santos)
INSERT IGNORE INTO tenants (slug, name, scope_type, scope_value) VALUES
('br', 'Brasil', 'BR', 'all'),
('marica-rj', 'Maricá - RJ', 'MUN', '330270'),
('santos-sp', 'Santos - SP', 'MUN', '354850');

-- 4) Dar acesso ao admin (troque o email se necessário)
INSERT IGNORE INTO user_tenants (user_id, tenant_id)
SELECT u.id, t.id
FROM user u
JOIN tenants t ON t.slug IN ('br','marica-rj','santos-sp')
WHERE u.email = 'admin@maricarj.com.br';