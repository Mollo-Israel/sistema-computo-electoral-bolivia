# Contratos de API - Ejemplos JSON

Todos los campos siguen el diccionario de datos estándar (`docs/diccionario_datos.md`).

## Pipeline RRV — Ingesta de Acta

**Endpoint:** `POST /api/rrv/acta/ocr`

**Request Body:**
```json
{
  "mesa_codigo": "800412-1",
  "nro_mesa": 1,
  "codigo_recinto": "800412",
  "recinto_nombre": "Escuela Espiritu Santo",
  "codigo_territorial": "800412",
  "departamento": "Beni",
  "provincia": "Cercado",
  "municipio": "San Javier",
  "origen": "OCR",
  "fuente": "PDF",
  "partido_1_votos": 8,
  "partido_2_votos": 1,
  "partido_3_votos": 7,
  "partido_4_votos": 10,
  "votos_validos": 55,
  "votos_blancos": 3,
  "votos_nulos": 7,
  "votos_emitidos": 65,
  "boletas_no_utilizadas": 10,
  "total_boletas": 75,
  "nro_votantes": 75
}
```

**Response (éxito):**
```json
{
  "status": "success",
  "message": "Acta RRV registrada",
  "data": {
    "mesa_codigo": "800412-1",
    "estado": "PROCESADA"
  }
}
```

---

## Pipeline CO — Ingesta de Acta Oficial

**Endpoint:** `POST /api/oficial/acta`

**Request Body:**
```json
{
  "mesa_codigo": "800412-1",
  "codigo_recinto": "800412",
  "codigo_territorial": "800412",
  "partido_1_votos": 8,
  "partido_2_votos": 1,
  "partido_3_votos": 7,
  "partido_4_votos": 10,
  "votos_validos": 55,
  "votos_blancos": 3,
  "votos_nulos": 7,
  "votos_emitidos": 65,
  "boletas_no_utilizadas": 10,
  "total_boletas": 75,
  "nro_votantes": 75,
  "fuente": "AUTOMATIZADOR",
  "fila_csv": 12,
  "usuario_id": 4
}
```

**Response (éxito):**
```json
{
  "status": "success",
  "message": "Acta oficial registrada",
  "data": {
    "mesa_codigo": "800412-1",
    "estado": "PROCESADA"
  }
}
```

---

## Dashboard — Resumen

**Endpoint:** `GET /api/dashboard/resumen`

**Response:**
```json
{
  "status": "success",
  "data": {
    "total_mesas": 29574,
    "mesas_procesadas": 15000,
    "votos_validos": 3200000,
    "votos_blancos": 45000,
    "votos_nulos": 30000,
    "votos_emitidos": 3275000,
    "participacion_porcentaje": 82.5,
    "votos_por_partido": {
      "partido_1_votos": 1500000,
      "partido_2_votos": 900000,
      "partido_3_votos": 500000,
      "partido_4_votos": 300000
    }
  }
}
```
