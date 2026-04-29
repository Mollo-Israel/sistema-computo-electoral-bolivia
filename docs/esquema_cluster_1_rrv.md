# Esquema Cluster 1 - MongoDB RRV

**Tipo:** MongoDB Replica Set  
**Base de datos:** `rrv_db`  
**Responsable de infraestructura:** Escobar

## Colecciones

### `rrv_actas`
Almacena cada acta RRV procesada (desde OCR, SMS o app móvil).

```json
{
  "_id": "ObjectId",
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
  "nro_votantes": 75,
  "estado": "PROCESADA",
  "hash_contenido": "sha256...",
  "timestamp": "ISODate"
}
```
- Índice único en `mesa_codigo` (para detección de duplicados).

---

### `rrv_eventos`
Registro de eventos del ciclo de vida del acta.

```json
{
  "_id": "ObjectId",
  "mesa_codigo": "800412-1",
  "evento": "ACTA_RECIBIDA | ACTA_VALIDADA | ACTA_OBSERVADA | ACTA_RECHAZADA",
  "detalle": {},
  "timestamp": "ISODate"
}
```

---

### `rrv_logs`
Logs funcionales del sistema RRV.

```json
{
  "_id": "ObjectId",
  "nivel": "INFO | WARNING | ERROR",
  "mesa_codigo": "800412-1",
  "mensaje": "Texto del log",
  "origen": "rrv_validator",
  "timestamp": "ISODate"
}
```

---

### `rrv_metricas_tecnicas`
Métricas de rendimiento del pipeline RRV.

```json
{
  "_id": "ObjectId",
  "endpoint": "/api/rrv/acta/ocr",
  "latencia_ms": 245.3,
  "status_code": 200,
  "throughput_actas": 12,
  "timestamp": "ISODate"
}
```

## Configuración del Replica Set
El Replica Set de MongoDB está configurado como `rs0` con tres miembros:
- `mongo-rrv-primary:27017` (primary)
- `mongo-rrv-secondary-1:27017` (secondary)
- `mongo-rrv-secondary-2:27017` (secondary)

El despliegue se realiza con Docker Compose en `infra/docker-compose.yml`. El servicio `mongo-rrv-bootstrap` inicializa automáticamente el Replica Set usando `rs.initiate()` y habilita la elección automática de primary.

La cadena de conexión recomendada para la aplicación es:

```text
mongodb://mongo-rrv-primary:27017,mongo-rrv-secondary-1:27017,mongo-rrv-secondary-2:27017/rrv_db?replicaSet=rs0
```

### Tolerancia a fallos
Si el primary falla, el Replica Set elegirá automáticamente uno de los secundarios como nuevo primary. Los datos se replican continuamente entre los miembros, manteniendo persistencia y disponibilidad del cluster.
