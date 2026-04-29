# Esquema Cluster 2 - PostgreSQL Oficial

**Tipo:** PostgreSQL replicado (primary + standby)  
**Base de datos:** `computo_oficial_db`  
**Responsable de infraestructura:** Escobar

## Tablas

### `territorios`
Catálogo territorial (departamentos, provincias, municipios).

```sql
CREATE TABLE territorios (
    id SERIAL PRIMARY KEY,
    codigo_territorial VARCHAR(20) UNIQUE NOT NULL,
    departamento VARCHAR(100) NOT NULL,
    provincia VARCHAR(100) NOT NULL,
    municipio VARCHAR(100) NOT NULL
);
```

---

### `recintos`
Catálogo de recintos electorales.

```sql
CREATE TABLE recintos (
    id SERIAL PRIMARY KEY,
    codigo_recinto VARCHAR(20) UNIQUE NOT NULL,
    recinto_nombre VARCHAR(200) NOT NULL,
    codigo_territorial VARCHAR(20) REFERENCES territorios(codigo_territorial)
);
```

---

### `mesas`
Catálogo de mesas de votación.

```sql
CREATE TABLE mesas (
    id SERIAL PRIMARY KEY,
    mesa_codigo VARCHAR(30) UNIQUE NOT NULL,
    nro_mesa INTEGER NOT NULL,
    codigo_recinto VARCHAR(20) REFERENCES recintos(codigo_recinto),
    nro_votantes INTEGER NOT NULL
);
```

---

### `usuarios_transcripcion`
Operadores del sistema de transcripción oficial.

```sql
CREATE TABLE usuarios_transcripcion (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    email VARCHAR(200) UNIQUE NOT NULL,
    activo BOOLEAN DEFAULT TRUE
);
```

---

### `actas_oficiales`
Actas del Cómputo Oficial.

```sql
CREATE TABLE actas_oficiales (
    id SERIAL PRIMARY KEY,
    mesa_codigo VARCHAR(30) REFERENCES mesas(mesa_codigo),
    codigo_recinto VARCHAR(20),
    codigo_territorial VARCHAR(20),
    partido_1_votos INTEGER NOT NULL CHECK (partido_1_votos >= 0),
    partido_2_votos INTEGER NOT NULL CHECK (partido_2_votos >= 0),
    partido_3_votos INTEGER NOT NULL CHECK (partido_3_votos >= 0),
    partido_4_votos INTEGER NOT NULL CHECK (partido_4_votos >= 0),
    votos_validos INTEGER NOT NULL,
    votos_blancos INTEGER NOT NULL,
    votos_nulos INTEGER NOT NULL,
    votos_emitidos INTEGER NOT NULL,
    boletas_no_utilizadas INTEGER NOT NULL,
    total_boletas INTEGER NOT NULL,
    nro_votantes INTEGER NOT NULL,
    fuente VARCHAR(50) DEFAULT 'AUTOMATIZADOR',
    fila_csv INTEGER,
    usuario_id INTEGER REFERENCES usuarios_transcripcion(id),
    estado VARCHAR(20) DEFAULT 'RECIBIDA',
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### `auditoria_oficial`
Trazabilidad de cambios en actas oficiales.

```sql
CREATE TABLE auditoria_oficial (
    id SERIAL PRIMARY KEY,
    acta_id INTEGER REFERENCES actas_oficiales(id),
    usuario_id INTEGER REFERENCES usuarios_transcripcion(id),
    accion VARCHAR(50) NOT NULL,
    detalle JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Configuración de Replicación
El cluster de PostgreSQL se despliega con un primary y un standby:
- `postgres-oficial-primary` — base de datos principal
- `postgres-oficial-standby` — réplica de lectura y conmutación por error

La configuración de streaming replication incluye:
- `wal_level=replica`
- `max_wal_senders=3`
- `wal_keep_size=64`
- `hot_standby=on`

El standby se inicializa usando `pg_basebackup` desde el primary y crea el archivo `standby.signal` para arrancar en modo réplica.

### Conexión de la aplicación
La aplicación debe acceder al primary en `postgres-oficial-primary:5432`.

### Tolerancia a fallos
Si `postgres-oficial-primary` queda inalcanzable, el standby ya tiene una copia de los WAL y puede asumir la carga de lectura/escritura tras la conmutación manual o automática configurada fuera de este repositorio.
