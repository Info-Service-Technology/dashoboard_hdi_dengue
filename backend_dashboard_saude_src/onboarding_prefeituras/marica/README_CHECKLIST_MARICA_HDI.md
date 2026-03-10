# Health Data Insights --- Checklist de Validação do Tenant Maricá

Este documento descreve o **processo completo de validação do tenant
Maricá** na plataforma **Health Data Insights (HDI)**.

O objetivo é garantir que todos os componentes do sistema estejam
funcionando corretamente em **modo prefeitura (MUN)** antes de replicar
o processo para outros municípios como **Macaé** e **Petrópolis**.

------------------------------------------------------------------------

# 1. Verificação do Tenant

Confirmar que o tenant está cadastrado corretamente no banco
**dashboard_saude**.

``` sql
SELECT id, slug, name, scope_type, scope_value, is_active
FROM tenants
WHERE slug = 'marica-rj';
```

Resultado esperado:

  Campo         Valor esperado
  ------------- ----------------
  slug          marica-rj
  scope_type    MUN
  scope_value   3302700
  is_active     1

------------------------------------------------------------------------

# 2. Verificar vínculo do usuário ao tenant

``` sql
SELECT
    u.id,
    u.email,
    t.slug,
    ut.role
FROM user u
JOIN user_tenants ut ON ut.user_id = u.id
JOIN tenants t ON t.id = ut.tenant_id
WHERE t.slug = 'marica-rj';
```

Resultado esperado:

-   usuário administrador vinculado ao tenant
-   papel adequado (`admin` ou `viewer`)

------------------------------------------------------------------------

# 3. Login no tenant Maricá

Testar autenticação usando **tenant_slug**.

Endpoint:

    POST /api/auth/login

Payload:

``` json
{
  "email": "SEU_EMAIL",
  "password": "SUA_SENHA",
  "tenant_slug": "marica-rj"
}
```

Resultado esperado:

``` json
{
  "tenant": {
    "slug": "marica-rj",
    "scope_type": "MUN",
    "scope_value": "3302700"
  }
}
```

------------------------------------------------------------------------

# 4. Verificar banco de dados do tenant

Conectar ao banco:

    marica_datalake

Verificar estrutura:

``` sql
SHOW TABLES;
```

Esperado:

    fact_dengue_kpi_mensal
    fact_dengue_kpi_semanal
    municipalities

Verificar views:

``` sql
SHOW FULL TABLES WHERE TABLE_TYPE = 'VIEW';
```

Esperado:

    vw_dengue_kpis

------------------------------------------------------------------------

# 5. Testar view principal

``` sql
SELECT *
FROM marica_datalake.vw_dengue_kpis
WHERE municipio = 330270
LIMIT 10;
```

Esperado:

    granularidade = mensal
    granularidade = semanal

------------------------------------------------------------------------

# 6. Validar totais epidemiológicos

``` sql
SELECT granularidade, SUM(casos) AS total
FROM marica_datalake.vw_dengue_kpis
WHERE municipio = 330270
GROUP BY granularidade;
```

Resultado esperado:

  granularidade   total
  --------------- -------
  mensal          6095
  semanal         6095

------------------------------------------------------------------------

# 7. Teste do Dashboard

``` bash
curl -s \
-H "Authorization: Bearer TOKEN_MARICA" \
"http://localhost:5000/api/dashboard"
```

Esperado:

    mode = prefeitura
    scope.tenant_slug = marica-rj
    total_cases = 6095

Interface:

-   Casos totais: **6.095**
-   gráfico mensal preenchido
-   cidade exibida: **Maricá**

------------------------------------------------------------------------

# 8. Teste do Maps

``` bash
curl -s \
-H "Authorization: Bearer TOKEN_MARICA" \
"http://localhost:5000/api/maps?disease=all"
```

Esperado:

-   mapa com dados apenas de Maricá
-   total = **6095**
-   não somar mensal + semanal

------------------------------------------------------------------------

# 9. Teste do Analytics

``` bash
curl -s \
-H "Authorization: Bearer TOKEN_MARICA" \
"http://localhost:5000/api/analytics?disease=dengue&start=2019-01-01&end=2026-12-31&gran=month"
```

Esperado:

``` json
{
  "mode": "prefeitura",
  "cases_in_period": 6095,
  "municipality_count": 1,
  "uf_count": 1,
  "scope": {
    "tenant_slug": "marica-rj"
  }
}
```

------------------------------------------------------------------------

# 10. Teste do módulo de dados

``` bash
curl -s \
-H "Authorization: Bearer TOKEN_MARICA" \
"http://localhost:5000/api/data/cases"
```

Esperado:

-   somente registros de Maricá
-   filtro aplicado via JWT
-   não enviar município na querystring

------------------------------------------------------------------------

# 11. Teste do módulo de previsões

``` bash
curl -s \
-H "Authorization: Bearer TOKEN_MARICA" \
"http://localhost:5000/api/predictions/trends?disease=dengue&horizon=12"
```

Esperado:

-   previsão baseada apenas nos dados de Maricá
-   resposta JSON válida
-   sem HTML retornado

------------------------------------------------------------------------

# 12. Teste de criação de usuário no tenant

Acessar:

    /register?tenant=marica-rj

Criar usuário.

Validar:

``` sql
SELECT
    u.email,
    t.slug
FROM user u
JOIN user_tenants ut ON ut.user_id = u.id
JOIN tenants t ON t.id = ut.tenant_id
WHERE u.email = 'EMAIL_TESTE';
```

Esperado:

    marica-rj

------------------------------------------------------------------------

# 13. Regressões que não podem ocorrer

Confirmar que não ocorreram:

-   React dentro de arquivos Python
-   rota duplicada `/api/predictions/predictions`
-   endpoints retornando HTML
-   mapa somando mensal + semanal
-   frontend enviando município na querystring
-   erro de variável `kpi` não inicializada

------------------------------------------------------------------------

# Critério final de aprovação

O tenant **Maricá está validado** quando:

-   login funciona
-   dashboard mostra **6095 casos**
-   mapa mostra **6095 casos**
-   analytics retorna **6095 casos**
-   previsões funcionam
-   dados respeitam escopo do JWT

------------------------------------------------------------------------

# Próximos passos

Após validação de Maricá:

1.  ETL de dados para **Macaé**
2.  Identificar **doença mais prevalente em Macaé**
3.  Repetir checklist
4.  ETL para **Petrópolis**
5.  Evolução do HDI com base no **Plano DANT 2022--2030**
