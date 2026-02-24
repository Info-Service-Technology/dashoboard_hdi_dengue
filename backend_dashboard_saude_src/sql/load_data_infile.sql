-----
SHOW VARIABLES LIKE 'local_infile';
-----
docker cp municipios.csv <nome_do_container_mysql>:/municipios.csv
-----
CREATE TABLE municipios_coords (
    codigo_ibge VARCHAR(10) PRIMARY KEY,
    nome VARCHAR(100),
    latitude FLOAT,
    longitude FLOAT,
    uf VARCHAR(2),
    regiao VARCHAR(20)
);
-----
LOAD DATA LOCAL INFILE '/home/mauroslucios/workspace/docker/bancodedados/mysql/municipios.csv'
INTO TABLE municipios_coords
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

-----------
UPDATE municipalities m
JOIN municipios_coords c
ON m.id = c.codigo_ibge
SET
    m.latitude = c.latitude,
    m.longitude = c.longitude;
------

SELECT COUNT(*)
FROM municipalities
WHERE latitude IS NULL;
------
LOAD DATA INFILE '/caminho/municipios.csv'
INTO TABLE municipios_coords
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(codigo_ibge, nome, latitude, longitude, capital, codigo_uf, siafi_id, ddd, fuso_horario);
------
SELECT 
    m.name,
    m.latitude,
    m.longitude,
    COUNT(*) AS casos
FROM health_cases hc
JOIN municipalities m
ON SUBSTR(m.id,1,6) = SUBSTR(hc.id_municip,1,6)
WHERE m.name = 'Rio de Janeiro'
GROUP BY m.name, m.latitude, m.longitude;