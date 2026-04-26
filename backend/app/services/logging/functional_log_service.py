"""
Records functional events: act received, validated, stored, observed, rejected.
Responsible: Sanabria.
TODO (Sanabria): implement functional log writing to rrv_logs / rrv_eventos MongoDB collections.
"""


async def log_evento(mesa_codigo: str, evento: str, detalle: dict):
    # TODO (Sanabria): persist event to rrv_eventos collection
    raise NotImplementedError


async def log_funcional(mesa_codigo: str, nivel: str, mensaje: str):
    # TODO (Sanabria): persist log to rrv_logs collection
    raise NotImplementedError
