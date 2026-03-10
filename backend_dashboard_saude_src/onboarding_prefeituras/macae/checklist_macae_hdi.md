
# Checklist de Validação do Tenant Macaé — Health Data Insights (HDI)

## 1. Tenant cadastrado corretamente
Validar no banco `dashboard_saude`:

```sql
SELECT id, slug, name, scope_type, scope_value, is_active
FROM dashboard_saude.tenants
WHERE slug = 'macae-rj';
```

### Esperado
- slug = macae-rj
- scope_type = MUN
- scope_value = 3302403
- is_active = 1

---

## 2. Vínculo do usuário ao tenant

```sql
SELECT
    u.id,
    u.email,
    t.slug,
    ut.role
FROM user u
JOIN user_tenants ut ON ut.user_id = u.id
JOIN tenants t ON t.id = ut.tenant_id
WHERE t.slug = 'macae-rj';
```

### Esperado
- admin@macae-rj.com vinculado ao tenant macae-rj

---

## 3. Login no tenant Macaé

```json
{
  "email": "admin@macae-rj.com",
  "password": "SUA_SENHA",
  "tenant_slug": "macae-rj"
}
```

### Esperado
JWT contendo:

- tenant = macae-rj
- tenant_scope_type = MUN
- tenant_scope_value = 3302403

---

## 4. Estrutura do banco do tenant

```sql
USE macae_datalake;

SHOW TABLES;
SHOW FULL TABLES WHERE TABLE_TYPE='VIEW';
```

### Esperado
Tabelas:

- fact_dengue_kpi_mensal
- fact_dengue_kpi_semanal
- municipalities

Views:

- vw_dengue_kpis

---

## 5. Doença dominante em Macaé

```sql
SELECT disease_name, COUNT(*)
FROM health_cases
WHERE id_municip LIKE '330240%'
GROUP BY disease_name
ORDER BY COUNT(*) DESC;
```

### Resultado esperado

| Doença | Casos |
|------|------|
| Dengue | 105 |
| Chikungunya | 21 |

### Decisão
ETL municipal inicial focado em **Dengue**.

---

## 6. Carga do ETL de Dengue

```sql
SELECT 'mensal' AS tipo, SUM(casos) AS total
FROM macae_datalake.fact_dengue_kpi_mensal
WHERE municipio = '330240'

UNION ALL

SELECT 'semanal', SUM(casos)
FROM macae_datalake.fact_dengue_kpi_semanal
WHERE municipio = '330240';
```

### Esperado

- mensal = 105
- semanal = 105

---

## 7. Validação da View Analítica

```sql
SELECT granularidade, SUM(casos) AS total
FROM macae_datalake.vw_dengue_kpis
WHERE municipio = '330240'
GROUP BY granularidade;
```

### Esperado

| granularidade | total |
|---------------|------|
| mensal | 105 |
| semanal | 105 |

---

## 8. Dashboard

Endpoint:

GET /api/dashboard

### Esperado

- mode = prefeitura
- tenant_slug = macae-rj
- dados somente do município Macaé

---

## 9. Analytics

Teste:

GET /api/analytics?disease=dengue&start=2019-01-01&end=2026-12-31&gran=month

### Resultado esperado

- cases_in_period = 105
- municipality_count = 1
- uf_count = 1
- tenant_slug = macae-rj

### Série esperada

| Mês | Casos |
|----|------|
| 2024-12 | 2 |
| 2025-01 | 67 |
| 2025-02 | 36 |

---

## 10. Dados (/data)

### Critério correto

Tela `/data` deve:

- usar `macae_datalake`
- respeitar escopo do tenant
- mostrar somente Macaé

### Não pode ocorrer

- aparecer municípios como Sinop
- aparecer dados nacionais

---

## 11. Maps (/maps)

### Critério correto

Mapa deve:

- usar datalake do tenant
- usar granularidade mensal
- mostrar apenas Macaé

### Esperado

| Município | Doença | Casos |
|-----------|--------|------|
| Macaé | Dengue | 105 |

### Não esperado

- total 126
- mistura com Chikungunya

---

## 12. Predictions (/predictions)

Endpoint:

GET /api/predictions/diseases

### Esperado

["Dengue"]

### Previsão

GET /api/predictions/trends?disease=dengue

Deve usar `vw_dengue_kpis` do tenant.

---

## 13. Usuários

Tela:

/admin/users

### Esperado

- usuários apenas do tenant macae-rj
- admin local pode gerenciar usuários do tenant

---

## 14. Registro de usuários no tenant

Criar usuário:

/register?tenant=macae-rj

Validar:

```sql
SELECT
    u.email,
    t.slug
FROM user u
JOIN user_tenants ut ON ut.user_id = u.id
JOIN tenants t ON t.id = ut.tenant_id
WHERE u.email = 'EMAIL_TESTE';
```

### Esperado

- usuário vinculado ao tenant macae-rj

---

# Critério final de aprovação

Macaé estará **100% validada** quando:

- login no tenant funciona
- ETL Dengue carregado
- vw_dengue_kpis retorna 105
- dashboard respeita tenant
- analytics retorna 105
- data mostra apenas Macaé
- maps mostra Dengue 105
- predictions mostra apenas Dengue
- usuários respeitam escopo do tenant

---

# Próximos passos

Após validação completa de Macaé:

1. Identificar doença dominante em Petrópolis
2. Criar ETL inicial do tenant Petrópolis
3. Repetir checklist
4. Evoluir HDI com base no Plano DANT 2022–2030
