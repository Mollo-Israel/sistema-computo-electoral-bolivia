"""
Queries both databases to produce comparative dashboard data.
Responsible: Erick Diaz.
TODO (Erick Diaz): implement aggregation queries across MongoDB and PostgreSQL.
"""


async def get_resumen_votos() -> dict:
    # TODO (Erick Diaz): aggregate totals from both rrv_actas and actas_oficiales
    raise NotImplementedError


async def get_comparativo_rrv_oficial() -> list:
    # TODO (Erick Diaz): join RRV and official data by mesa_codigo to find differences
    raise NotImplementedError


async def get_estado_actas() -> dict:
    # TODO (Erick Diaz): count acts by estado in both pipelines
    raise NotImplementedError
