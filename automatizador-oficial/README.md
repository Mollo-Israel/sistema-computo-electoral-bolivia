# Automatizador Oficial - Cómputo Oficial

## Responsable: Erick Diaz

## Descripción
Script de automatización que lee archivos CSV con datos de transcripción oficial y los envía al backend para su procesamiento en el pipeline de Cómputo Oficial.

## Flujo
```
CSV oficial → automatizador → POST /api/oficial/acta → PostgreSQL Cluster 2
```

## Restricciones
- No usa OCR, imágenes ni SMS.
- Los campos del CSV deben mapearse a los nombres del diccionario de datos estándar.
- Cada fila del CSV debe registrar su `fila_csv` y `usuario_id`.

## Carpetas
- `data/` — CSVs de entrada (no subir datos reales al repositorio)
- `scripts/` — scripts de procesamiento y envío al backend
