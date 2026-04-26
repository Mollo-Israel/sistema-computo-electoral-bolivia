# Arquitectura del Sistema

## Visión General

El sistema implementa dos pipelines completamente desacoplados que convergen en un dashboard comparativo.

```
[ENTRADA RRV]                          [ENTRADA CO]
PDF / Imagen                           CSV Oficial
App Móvil (foto)                       Transcripción
SMS                                    Automatizador
      |                                      |
      v                                      v
[OCR / SMS Parser]              [Automatizador Oficial]
(MOLLO / Ferrufino)                  (Erick Diaz)
      |                                      |
      v                                      v
[Validador RRV]                  [Validador Oficial]
  (Sanabria)                       (Erick Diaz)
      |                                      |
      v                                      v
[Logs / Eventos]                  [Auditoría Oficial]
  (Sanabria)                       (Erick Diaz)
      |                                      |
      v                                      v
[MongoDB Cluster 1]             [PostgreSQL Cluster 2]
  (Escobar)                          (Escobar)
      |                                      |
      +-----------> [DASHBOARD] <-----------+
                    (Erick Diaz)
```

## Principios
- Los dos pipelines no se mezclan en ninguna etapa de ingesta o validación.
- El dashboard es el único punto donde se cruzan los datos de ambos clusters.
- Todos los módulos deben usar los nombres de campo del diccionario de datos estándar.

## Responsabilidades

| Módulo                  | Responsable   |
|-------------------------|---------------|
| OCR + procesamiento     | MOLLO         |
| App móvil + SMS         | Ferrufino     |
| Validación + logs       | Sanabria      |
| Clusters + persistencia | Escobar       |
| Automatizador + dashboard | Erick Diaz  |
