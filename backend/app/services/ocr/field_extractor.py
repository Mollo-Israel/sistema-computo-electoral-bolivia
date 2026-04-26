"""
Extracts standard fields from OCR raw text output.
Responsible: MOLLO.
TODO (MOLLO): implement regex/ML-based extraction mapping raw text to standard field names.
"""


def extract_fields(ocr_text: str) -> dict:
    # TODO (MOLLO): parse ocr_text and map to standard fields
    # Must return keys matching CAMPOS_ESTANDAR in constants.py
    # If confidence is low, mark estado=OBSERVADA
    raise NotImplementedError
