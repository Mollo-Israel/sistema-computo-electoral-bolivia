"""
Parses raw SMS text into standard electoral act fields.
Responsible: Ferrufino.
TODO (Ferrufino): implement format validation and field parsing.
Mark act as RECHAZADA if format is invalid.
"""


def parse_sms(mensaje_raw: str) -> dict:
    # TODO (Ferrufino): parse SMS according to agreed format
    # Must map to standard field names from CAMPOS_ESTANDAR
    # Return estado=RECHAZADA if format does not match
    raise NotImplementedError
