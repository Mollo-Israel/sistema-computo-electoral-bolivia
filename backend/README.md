# Backend - Sistema de Cómputo Electoral

## Responsabilidades
- Exponer la API REST para los dos pipelines (RRV y Cómputo Oficial).
- Recibir actas vía OCR, SMS y transcripción CSV.
- Validar datos contra las reglas OEP antes de persistir.
- Registrar logs funcionales y técnicos.
- Alimentar el dashboard comparativo.

## Grupos de API planificados

| Prefijo          | Responsable | Descripción                              |
|------------------|-------------|------------------------------------------|
| `/api/rrv`       | MOLLO / Ferrufino / Sanabria | Ingesta y consulta RRV  |
| `/api/oficial`   | Erick Diaz  | Ingesta y consulta Cómputo Oficial       |
| `/api/dashboard` | Erick Diaz  | Datos consolidados para el dashboard     |
| `/api/health`    | Escobar     | Estado de clusters y servicios           |

## Stack
- **Framework:** FastAPI (Python)
- **Base de datos RRV:** MongoDB (Cluster 1)
- **Base de datos Oficial:** PostgreSQL (Cluster 2)

## Instrucciones de inicio
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
