UPDATE municipalities m -> JOIN municipios_coords c -> ON m.id = c.codigo_ibge -> SET -> m.latitude = c.latitude, -> m.longitude = c.longitude;
----
UPDATE health_cases hc
JOIN municipalities m
  ON LEFT(m.id, 6) = hc.id_municip
SET hc.id_municip_ibge = m.id
WHERE hc.id_municip_ibge IS NULL
  AND hc.id_municip IS NOT NULL;