# Sistema de Cómputo Electoral Bolivia

## Objetivo
Sistema distribuido para el recuento de votos en elecciones nacionales de Bolivia. Implementa dos pipelines desacoplados: Recuento Rápido de Votos (RRV) y Cómputo Oficial (CO).

## Pipelines

### 1. RRV - Recuento Rápido de Votos
- **Entrada:** PDF/imagen de actas electorales, foto desde app móvil, o SMS.
- **Flujo:** entrada → OCR o parser SMS → validador RRV → logs/eventos → MongoDB → dashboard.
- **Propósito:** resultados preliminares, baja latencia, consistencia eventual.
- **Cluster 1:** MongoDB Replica Set.

### 2. CO - Cómputo Oficial
- **Entrada:** CSV oficial / datos de transcripción.
- **Flujo:** CSV → automatizador oficial → validador oficial → PostgreSQL → dashboard.
- **Sin OCR, sin imágenes, sin SMS.**
- **Propósito:** resultados auditables, consistencia fuerte.
- **Cluster 2:** PostgreSQL replicado.

## Asignación del equipo

| Miembro       | Módulo                                          |
|---------------|-------------------------------------------------|
| MOLLO         | OCR RRV + procesamiento de imágenes             |
| Ferrufino     | App móvil + SMS + receptor                      |
| Sanabria      | Validador + logs + reglas OEP                   |
| Escobar       | Clusters + persistencia + tolerancia a fallos   |
| Erick Diaz    | Automatizador oficial + dashboard comparativo   |

## Contrato de datos estándar
Todos los módulos deben usar los nombres de campos definidos en `docs/diccionario_datos.md`.
No usar variantes como `candidato_1`, `p1`, `vv`, `validos`, `votosPartido1`, etc.

## Documentación
- `docs/arquitectura.md` — descripción de la arquitectura
- `docs/diccionario_datos.md` — campos estándar y tipos
- `docs/contratos_api.md` — ejemplos JSON de entrada/salida
- `docs/reglas_validacion.md` — reglas de validación de actas
- `docs/esquema_cluster_1_rrv.md` — colecciones MongoDB
- `docs/esquema_cluster_2_oficial.md` — tablas PostgreSQL
