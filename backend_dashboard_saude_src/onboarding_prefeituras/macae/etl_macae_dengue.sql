
-- =====================================================
-- ETL Dengue - Município de Macaé (IBGE 3302403)
-- Health Data Insights
-- =====================================================

USE macae_datalake;

-- -----------------------------------------------------
-- 1. Garantir a existência da view analítica
-- -----------------------------------------------------
DROP VIEW IF EXISTS vw_dengue_kpis;

CREATE VIEW vw_dengue_kpis AS
SELECT
    'mensal' AS granularidade,
    municipio,
    ano,
    mes AS periodo,
    casos,
    max_dt_notific,
    updated_at
FROM fact_dengue_kpi_mensal

UNION ALL

SELECT
    'semanal' AS granularidade,
    municipio,
    ano,
    semana AS periodo,
    casos,
    max_dt_notific,
    updated_at
FROM fact_dengue_kpi_semanal;

-- -----------------------------------------------------
-- 2. Limpar dados anteriores
-- -----------------------------------------------------
TRUNCATE TABLE fact_dengue_kpi_mensal;
TRUNCATE TABLE fact_dengue_kpi_semanal;

-- -----------------------------------------------------
-- 3. Inserção mensal (agregação por mês)
-- -----------------------------------------------------
INSERT INTO fact_dengue_kpi_mensal
(municipio, ano, mes, casos, max_dt_notific)
SELECT
    LEFT(hc.id_municip, 6) AS municipio,
    YEAR(hc.dt_notific) AS ano,
    MONTH(hc.dt_notific) AS mes,
    COUNT(*) AS casos,
    MAX(hc.dt_notific) AS max_dt_notific
FROM dashboard_saude.health_cases hc
WHERE hc.id_municip LIKE '330240%'
  AND hc.disease_name = 'Dengue'
  AND hc.dt_notific IS NOT NULL
GROUP BY
    LEFT(hc.id_municip, 6),
    YEAR(hc.dt_notific),
    MONTH(hc.dt_notific);

-- -----------------------------------------------------
-- 4. Inserção semanal (semana epidemiológica)
-- -----------------------------------------------------
INSERT INTO fact_dengue_kpi_semanal
(municipio, ano, semana, casos, max_dt_notific)
SELECT
    LEFT(hc.id_municip, 6) AS municipio,
    FLOOR(YEARWEEK(hc.dt_notific, 3) / 100) AS ano,
    MOD(YEARWEEK(hc.dt_notific, 3), 100) AS semana,
    COUNT(*) AS casos,
    MAX(hc.dt_notific) AS max_dt_notific
FROM dashboard_saude.health_cases hc
WHERE hc.id_municip LIKE '330240%'
  AND hc.disease_name = 'Dengue'
  AND hc.dt_notific IS NOT NULL
GROUP BY
    LEFT(hc.id_municip, 6),
    FLOOR(YEARWEEK(hc.dt_notific, 3) / 100),
    MOD(YEARWEEK(hc.dt_notific, 3), 100);

-- -----------------------------------------------------
-- 5. Garantir dimensão municipalities
-- -----------------------------------------------------
INSERT INTO municipalities (id, name, uf)
SELECT '3302403', 'Macaé', 'RJ'
WHERE NOT EXISTS (
    SELECT 1 FROM municipalities WHERE id = '3302403'
);

-- -----------------------------------------------------
-- 6. Validação dos totais
-- -----------------------------------------------------
SELECT 'mensal' AS tipo, SUM(casos) AS total
FROM fact_dengue_kpi_mensal
WHERE municipio = '330240'

UNION ALL

SELECT 'semanal', SUM(casos)
FROM fact_dengue_kpi_semanal
WHERE municipio = '330240';

-- -----------------------------------------------------
-- 7. Validação da view
-- -----------------------------------------------------
SELECT granularidade, SUM(casos) AS total
FROM vw_dengue_kpis
WHERE municipio = '330240'
GROUP BY granularidade;
-------------------
INSERT INTO fact_dengue_kpi_mensal
(municipio, ano, mes, casos, max_dt_notific, updated_at)
SELECT
    LEFT(hc.id_municip, 6) AS municipio,
    YEAR(hc.dt_notific) AS ano,
    MONTH(hc.dt_notific) AS mes,
    COUNT(*) AS casos,
    MAX(hc.dt_notific) AS max_dt_notific,
    NOW() AS updated_at
FROM dashboard_saude.health_cases hc
WHERE hc.id_municip LIKE '330240%'
  AND hc.disease_name = 'Dengue'
  AND hc.dt_notific IS NOT NULL
GROUP BY
    LEFT(hc.id_municip, 6),
    YEAR(hc.dt_notific),
    MONTH(hc.dt_notific);
    -------------------------------
INSERT INTO fact_dengue_kpi_semanal
(municipio, ano, semana, casos, max_dt_notific, updated_at)
SELECT
    LEFT(hc.id_municip, 6) AS municipio,
    FLOOR(YEARWEEK(hc.dt_notific, 3) / 100) AS ano,
    MOD(YEARWEEK(hc.dt_notific, 3), 100) AS semana,
    COUNT(*) AS casos,
    MAX(hc.dt_notific) AS max_dt_notific,
    NOW() AS updated_at
FROM dashboard_saude.health_cases hc
WHERE hc.id_municip LIKE '330240%'
  AND hc.disease_name = 'Dengue'
  AND hc.dt_notific IS NOT NULL
GROUP BY
    LEFT(hc.id_municip, 6),
    FLOOR(YEARWEEK(hc.dt_notific, 3) / 100),
    MOD(YEARWEEK(hc.dt_notific, 3), 100);
    -----------------
SELECT 'mensal' AS tipo, SUM(casos) AS total
FROM fact_dengue_kpi_mensal
WHERE municipio = '330240'

UNION ALL

SELECT 'semanal', SUM(casos)
FROM fact_dengue_kpi_semanal
WHERE municipio = '330240';
--------------
SELECT granularidade, SUM(casos) AS total
FROM vw_dengue_kpis
WHERE municipio = '330240'
GROUP BY granularidade;
--------------
ALTER TABLE fact_dengue_kpi_mensal
MODIFY updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

ALTER TABLE fact_dengue_kpi_semanal
MODIFY updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;