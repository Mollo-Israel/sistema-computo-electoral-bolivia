# Diccionario de Datos - Contrato Estándar

Todos los módulos del sistema deben usar exactamente los nombres de campo de esta tabla.
No usar variantes (`candidato_1`, `p1`, `vv`, `validos`, `votosPartido1`, etc.).

| Campo                | Tipo     | Descripción                                                  | Obligatorio |
|----------------------|----------|--------------------------------------------------------------|-------------|
| `mesa_codigo`        | string   | Identificador único de la mesa (ej. `"800412-1"`)            | Sí          |
| `nro_mesa`           | integer  | Número de mesa dentro del recinto                            | Sí (RRV)    |
| `codigo_recinto`     | string   | Código del recinto electoral                                 | Sí          |
| `recinto_nombre`     | string   | Nombre del recinto electoral                                 | Sí (RRV)    |
| `codigo_territorial` | string   | Código territorial (municipio/localidad)                     | Sí          |
| `departamento`       | string   | Nombre del departamento boliviano                            | Sí (RRV)    |
| `provincia`          | string   | Nombre de la provincia                                       | Sí (RRV)    |
| `municipio`          | string   | Nombre del municipio                                         | Sí (RRV)    |
| `partido_1_votos`    | integer  | Votos válidos para el partido 1                              | Sí          |
| `partido_2_votos`    | integer  | Votos válidos para el partido 2                              | Sí          |
| `partido_3_votos`    | integer  | Votos válidos para el partido 3                              | Sí          |
| `partido_4_votos`    | integer  | Votos válidos para el partido 4                              | Sí          |
| `votos_validos`      | integer  | Total de votos válidos (suma de todos los partidos)          | Sí          |
| `votos_blancos`      | integer  | Total de votos en blanco                                     | Sí          |
| `votos_nulos`        | integer  | Total de votos nulos                                         | Sí          |
| `votos_emitidos`     | integer  | Total de votos emitidos (válidos + blancos + nulos)          | Sí          |
| `boletas_no_utilizadas` | integer | Boletas no usadas en la mesa                              | Sí          |
| `total_boletas`      | integer  | Total de boletas distribuidas a la mesa                      | Sí          |
| `nro_votantes`       | integer  | Número de votantes habilitados en el padrón de la mesa       | Sí          |
| `origen`             | string   | Origen del dato: `OCR`, `SMS`, `APP_MOVIL`, `AUTOMATIZADOR`  | Sí          |
| `fuente`             | string   | Fuente del documento: `PDF`, `IMAGEN`, `SMS`, `CSV`          | Sí          |
| `estado`             | string   | Estado del acta: `RECIBIDA`, `PROCESADA`, `PENDIENTE`, `OBSERVADA`, `RECHAZADA`, `DUPLICADA`, `PUBLICADA` | Sí |

## Restricciones
- `mesa_codigo` es la clave natural del sistema. Debe ser única por acta publicada.
- Ningún campo puede ser nulo si el acta está en estado `PROCESADA` o `PUBLICADA`.
- Los campos de votos deben ser enteros no negativos.
