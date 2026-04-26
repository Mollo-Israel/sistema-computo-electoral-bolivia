"""
Project-wide constants and enumerations.
All field names must match the standard data contract exactly.
"""
from enum import Enum


class EstadoActa(str, Enum):
    RECIBIDA = "RECIBIDA"
    PROCESADA = "PROCESADA"
    PENDIENTE = "PENDIENTE"
    OBSERVADA = "OBSERVADA"
    RECHAZADA = "RECHAZADA"
    DUPLICADA = "DUPLICADA"
    PUBLICADA = "PUBLICADA"


class OrigenActa(str, Enum):
    OCR = "OCR"
    SMS = "SMS"
    APP_MOVIL = "APP_MOVIL"
    AUTOMATIZADOR = "AUTOMATIZADOR"


class FuenteActa(str, Enum):
    PDF = "PDF"
    IMAGEN = "IMAGEN"
    SMS = "SMS"
    CSV = "CSV"


# Standard field names — do NOT rename these anywhere in the codebase
CAMPOS_ESTANDAR = [
    "mesa_codigo", "nro_mesa", "codigo_recinto", "recinto_nombre",
    "codigo_territorial", "departamento", "provincia", "municipio",
    "partido_1_votos", "partido_2_votos", "partido_3_votos", "partido_4_votos",
    "votos_validos", "votos_blancos", "votos_nulos", "votos_emitidos",
    "boletas_no_utilizadas", "total_boletas", "nro_votantes",
    "origen", "fuente", "estado",
]
