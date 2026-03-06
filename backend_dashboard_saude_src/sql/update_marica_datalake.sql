-- 1) Copia dimensão inteira (id, nome, uf, region, population)
INSERT INTO marica_datalake.municipalities (id, name, uf, region, population)
SELECT id, name, uf, region, population
FROM dashboard_saude.municipalities
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  uf = VALUES(uf),
  region = VALUES(region),
  population = VALUES(population);

-- 2) Completa latitude/longitude usando a tabela de coords do dashboard_saude
UPDATE marica_datalake.municipalities m
JOIN dashboard_saude.municipios_coords c
  ON m.id = c.codigo_ibge
SET
  m.latitude = c.latitude,
  m.longitude = c.longitude
WHERE
  (m.latitude IS NULL OR m.longitude IS NULL);

SELECT COUNT(*) FROM marica_datalake.municipalities;
SELECT * FROM marica_datalake.municipalities WHERE id='3302700';