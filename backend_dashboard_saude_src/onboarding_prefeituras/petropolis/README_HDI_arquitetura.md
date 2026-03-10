
# Health Data Insights (HDI) – Arquitetura, Multi‑Tenant e Datalake Epidemiológico

Este documento registra **desde o início** a estratégia técnica para evolução da plataforma **Health Data Insights (HDI)**.

## Conteúdo
- Arquitetura da plataforma
- Estrutura multi‑tenant
- Tenant piloto Petrópolis
- Datalake epidemiológico
- Infraestrutura AWS
- ETL Spark
- Roadmap de evolução

---

# 1. Visão Geral

A HDI é uma plataforma de análise epidemiológica baseada em dados para apoiar gestores públicos.

Fluxo conceitual:

Dados → ETL → Datalake → Agregações → API → Dashboard

---

# 2. Multi‑Tenant

Banco principal:

dashboard_saude

Principais tabelas:

- tenants
- user_tenants
- tenant_data_sources
- users

Exemplo de tenant:

tenant_slug: petropolis-rj  
scope_type: MUN  
scope_value: 3303906

---

# 3. Remover Hardcode

Evitar lógica como:

if tenant_slug == "marica-rj"

Criar tabela:

tenant_data_sources

Campos sugeridos:

tenant_id  
bind_key  
datalake_db  
kpi_view_name  
supported_diseases  
is_active

---

# 4. Tenant Piloto Petrópolis

Diagnóstico inicial:

Dengue: 57  
Chikungunya: 4

Modelo recomendado:

petropolis_datalake

Tabela:

fact_epidemiology_monthly

Campos:

municipio  
disease_name  
ano  
periodo  
casos  
granularidade

View usada pela API:

vw_epidemiology_kpis

---

# 5. Modelo de View

SELECT
    id_municip_ibge_6 AS municipio,
    disease_name,
    YEAR(dt_notific) AS ano,
    MONTH(dt_notific) AS periodo,
    COUNT(*) AS casos,
    'mensal' AS granularidade
FROM health_cases
GROUP BY
    id_municip_ibge_6,
    disease_name,
    YEAR(dt_notific),
    MONTH(dt_notific);

---

# 6. Arquitetura AWS

Serviços principais:

S3 → datalake  
Glue → ETL Spark  
Athena → SQL sobre o datalake  
RDS → banco relacional  
ECS → containers da aplicação  
CloudWatch → logs

Estrutura S3:

hdi-datalake/

raw/  
trusted/  
curated/

---

# 7. Pipeline ETL Spark

ETL executado no AWS Glue.

Etapas:

1 ingestão DATASUS / IBGE  
2 limpeza e padronização  
3 enriquecimento territorial  
4 agregação epidemiológica  
5 gravação em Parquet

---

# 8. API

Principais endpoints:

/api/dashboard  
/api/maps  
/api/data  
/api/predictions  
/api/analytics

Join padrão:

LEFT(CAST(m.id AS CHAR),6) = v.municipio

---

# 9. Módulos futuros

Observatório epidemiológico  
Monitoramento territorial  
Gestão de filas assistenciais  
Integração APS e vigilância  
Previsão epidemiológica

---

# 10. Roadmap

Fase 1  
validar Macaé

Fase 2  
criar Petrópolis multi‑doença

Fase 3  
remover hardcodes

Fase 4  
subir datalake AWS

Fase 5  
deploy ECS

---

# Objetivo

Transformar o HDI em uma **plataforma nacional de inteligência epidemiológica**
