SELECT 
    m.name,
    m.uf,
    COUNT(*) AS total_casos
FROM health_cases hc
JOIN municipalities m 
ON SUBSTR(m.id, 1, 6) = SUBSTR(hc.id_municip, 1, 6)
WHERE m.uf = 'RJ'
AND hc.disease_name = 'Dengue'
GROUP BY m.name, m.uf
ORDER BY total_casos DESC;

---
SELECT DISTINCT m.uf
FROM health_cases hc
JOIN municipalities m 
ON SUBSTR(m.id, 1, 6) = SUBSTR(hc.id_municip, 1, 6);

----
SELECT *
FROM health_cases
WHERE id_municip LIKE '33%'
LIMIT 10;

-----

SELECT 
    LEFT(id_municip, 2) AS estado,
    COUNT(*) 
FROM health_cases
GROUP BY estado;
-----
SELECT COUNT(*) FROM health_cases;
-----
SELECT m.id, m.name
FROM municipalities m
WHERE m.name = 'Rio de Janeiro';
---------
SHOW VARIABLES LIKE 'collation%';
SHOW VARIABLES LIKE 'character_set%';
--------
SELECT 
    m.id,
    m.name,
    COUNT(*) casos
FROM health_cases hc
JOIN municipalities m 
ON m.id = hc.id_municip
WHERE hc.disease_name = 'Dengue'
AND m.uf = 'RJ'
GROUP BY m.id, m.name;
----------
SELECT name, latitude, longitude
FROM municipalities
WHERE name = 'Rio de Janeiro';
-----------
SELECT COUNT(*)
FROM municipalities
WHERE latitude IS NULL OR longitude IS NULL;
-----------
SELECT name
FROM municipalities
WHERE latitude IS NULL;
