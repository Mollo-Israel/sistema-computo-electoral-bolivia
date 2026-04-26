"""
Data access layer for PostgreSQL Cluster 2 (Official Computation pipeline).
Responsible: Escobar.
Tables: territorios, recintos, mesas, usuarios_transcripcion, actas_oficiales, auditoria_oficial.
TODO (Escobar): implement CRUD operations with asyncpg / SQLAlchemy async.
"""


async def save_acta_oficial(acta: dict) -> int:
    # TODO (Escobar): insert into actas_oficiales table, return id
    raise NotImplementedError


async def get_acta_oficial_by_mesa(mesa_codigo: str) -> dict | None:
    # TODO (Escobar): query actas_oficiales by mesa_codigo
    raise NotImplementedError


async def list_actas_oficiales(filtros: dict) -> list:
    # TODO (Escobar): query actas_oficiales with optional filters
    raise NotImplementedError


async def save_auditoria(registro: dict) -> int:
    # TODO (Escobar): insert audit trail into auditoria_oficial table
    raise NotImplementedError
