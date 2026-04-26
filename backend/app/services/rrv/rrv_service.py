"""
Orchestrates the RRV pipeline: validate → persist to MongoDB → emit event → log.
Responsible: Sanabria (orchestration), MOLLO (OCR input), Ferrufino (SMS/mobile input).
TODO (Sanabria): implement full RRV act processing flow.
"""


async def procesar_acta_rrv(data: dict) -> dict:
    # TODO (Sanabria): call rrv_validator → mongo_rrv_repository.save → log_evento
    # Returns persisted act with estado assigned
    raise NotImplementedError
