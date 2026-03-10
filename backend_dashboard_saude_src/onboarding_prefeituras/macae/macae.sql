CREATE DATABASE IF NOT EXISTS macae_datalake
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE macae_datalake;

CREATE TABLE fact_dengue_kpi_mensal (
    municipio VARCHAR(6) NOT NULL,
    ano INT NOT NULL,
    mes INT NOT NULL,
    casos INT DEFAULT 0,
    max_dt_notific DATE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (municipio, ano, mes),

    INDEX idx_municipio (municipio),
    INDEX idx_ano (ano)
);

CREATE TABLE fact_dengue_kpi_semanal (
    municipio VARCHAR(6) NOT NULL,
    ano INT NOT NULL,
    semana INT NOT NULL,
    casos INT DEFAULT 0,
    max_dt_notific DATE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (municipio, ano, semana),

    INDEX idx_municipio (municipio),
    INDEX idx_ano (ano)
);

CREATE TABLE municipalities (
    id VARCHAR(7) PRIMARY KEY,
    name VARCHAR(120),
    uf VARCHAR(2),

    INDEX idx_uf (uf)
);

INSERT INTO municipalities (id, name, uf)
VALUES ('3302403', 'Macaé', 'RJ');

CREATE VIEW vw_dengue_kpis AS

SELECT
    'mensal' AS granularidade,
    fact_dengue_kpi_mensal.municipio AS municipio,
    fact_dengue_kpi_mensal.ano AS ano,
    fact_dengue_kpi_mensal.mes AS periodo,
    fact_dengue_kpi_mensal.casos AS casos,
    fact_dengue_kpi_mensal.max_dt_notific AS max_dt_notific,
    fact_dengue_kpi_mensal.updated_at AS updated_at
FROM fact_dengue_kpi_mensal

UNION ALL

SELECT
    'semanal' AS granularidade,
    fact_dengue_kpi_semanal.municipio AS municipio,
    fact_dengue_kpi_semanal.ano AS ano,
    fact_dengue_kpi_semanal.semana AS periodo,
    fact_dengue_kpi_semanal.casos AS casos,
    fact_dengue_kpi_semanal.max_dt_notific AS max_dt_notific,
    fact_dengue_kpi_semanal.updated_at AS updated_at
FROM fact_dengue_kpi_semanal;

SHOW TABLES;

SHOW FULL TABLES WHERE TABLE_TYPE='VIEW';

SELECT * FROM vw_dengue_kpis LIMIT 5;