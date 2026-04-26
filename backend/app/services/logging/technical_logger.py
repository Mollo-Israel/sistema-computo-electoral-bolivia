"""
Records technical metrics: latency, throughput, errors, security events.
Responsible: Escobar.
TODO (Escobar): implement technical metric writing to rrv_metricas_tecnicas collection.
"""


async def log_metrica(endpoint: str, latencia_ms: float, status_code: int):
    # TODO (Escobar): persist metric to rrv_metricas_tecnicas collection
    raise NotImplementedError
