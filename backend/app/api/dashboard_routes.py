"""
Dashboard API routes: comparative data between RRV and official count.
Responsible: Erick Diaz.
TODO: implement once both pipelines persist data.
"""
from fastapi import APIRouter

router = APIRouter()

# TODO (Erick Diaz): GET /resumen — participation, votes by party, margins
# TODO (Erick Diaz): GET /comparativo — RRV vs official differences
# TODO (Erick Diaz): GET /geografico — geographic breakdown by departamento/municipio
# TODO (Erick Diaz): GET /tecnico — latency, throughput, availability metrics
# TODO (Erick Diaz): GET /anomalias — detected anomalies and logs
