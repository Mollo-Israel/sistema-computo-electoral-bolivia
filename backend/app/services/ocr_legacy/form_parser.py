"""
Parser de texto OCR para actas electorales bolivianas.

Adaptado al formato real del Acta Electoral de Escrutinio y Conteo 2025 (OEP).

Estructura del formulario:
  - Codigo de acta: numero de 13 digitos (ej. 2020600556001) en el texto
  - Cabecera: Departamento, Provincia, Municipio, Localidad, Recinto
  - Tabla de candidatos con votos en cajas de digitos individuales
  - Seccion de totales: papeletas, no utilizadas

Partidos observados en actas 2025:
  partido_1 -> MAS-IPSP / Movimiento al Socialismo
  partido_2 -> Economia para Bolivia Sumate (u otro)
  partido_3 -> Democrata Cristiano (u otro)
  partido_4 -> Resto
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Campos numericos que determinan la confianza del parser.
# Los campos de texto (departamento, etc.) no penalizan la confianza.
_NUMERIC_FIELDS = [
    "nro_mesa",
    "partido_1_votos",
    "partido_2_votos",
    "partido_3_votos",
    "partido_4_votos",
    "votos_validos",
    "votos_blancos",
    "votos_nulos",
    "votos_emitidos",
    "boletas_no_utilizadas",
    "total_boletas",
    "nro_votantes",
]

# Campos de texto que SI se extraen pero no penalizan la confianza si faltan
_TEXT_FIELDS = [
    "codigo_mesa", "departamento", "provincia", "municipio",
    "recinto_nombre", "localidad",
]

# Correcciones OCR en secuencias que ya contienen un digito real
_OCR_NUM_FIXES: Dict[str, str] = {
    "O": "0", "o": "0",
    "l": "1", "I": "1", "i": "1",
    "B": "8",
    "S": "5",
    "Z": "2",
    "G": "6",
    "q": "9",
}

# Separador flexible: colon, semicolon, dash, spaces (actas 2025 usan cualquiera)
_SEP = r"\s*[:\-;\.]\s*(?:\-\s*)?"

_PATTERNS: Dict[str, List[str]] = {

    # ── Codigo de acta (13 digitos, aparece en el texto del formulario) ────────
    "codigo_mesa": [
        r"\b(20\d{11})\b",                              # 2020600556001
        r"c[oó]d(?:igo)?\.?\s*(?:de\s+)?mesa" + _SEP + r"([A-Z0-9\-]{3,20})",
    ],

    # ── Numero de mesa (si aparece separado del codigo) ────────────────────────
    "nro_mesa": [
        r"n[uú]mero\s+de\s+mesa" + _SEP + r"(\d+)",
        r"nro\.?\s+mesa" + _SEP + r"(\d+)",
        r"mesa\s+n[°º°]?\s*[:\-;]?\s*(\d{2,6})\b",   # Mesa N° 5001
        r"\bmesa\b\s*[:\-;]\s*(\d{2,6})\b",
    ],

    # ── Ubicacion geografica ───────────────────────────────────────────────────
    # El OCR (PSM 6) pone instrucciones del form en la misma "linea" que los
    # datos. Por eso usamos patrones de palabra UNICA para evitar capturar
    # texto de la columna derecha. Nota: "La Paz" aparece como "LaPaz" en OCR.
    # Tambien manejamos el typo OCR "Previncia" para "Provincia".
    "departamento": [
        r"departamento" + _SEP + r"([A-Za-záéíóúñÁÉÍÓÚÑ][A-Za-záéíóúñÁÉÍÓÚÑ]+)",
    ],
    "provincia": [
        r"pro?v[iu]?ncia" + _SEP + r"([A-Za-záéíóúñÁÉÍÓÚÑ][A-Za-záéíóúñÁÉÍÓÚÑ]+)",
    ],
    "municipio": [
        r"municipio" + _SEP + r"([A-Za-záéíóúñÁÉÍÓÚÑ][A-Za-záéíóúñÁÉÍÓÚÑ]+)",
    ],
    "localidad": [
        # Captura hasta el primer par de digitos consecutivos o fin de linea
        r"localidad" + _SEP + r"([A-Za-záéíóúñÁÉÍÓÚÑ][^\n]{3,55}?)(?=\s+\d{2,}|\s*\n|$)",
    ],
    "recinto_nombre": [
        r"recinto\s+electoral" + _SEP + r"([A-Za-záéíóúñÁÉÍÓÚÑ][^\n]{3,55}?)(?=\s+\d{2,}|\s*\n|$)",
        r"recinto" + _SEP + r"([A-Za-záéíóúñÁÉÍÓÚÑ][^\n]{3,55}?)(?=\s+\d{2,}|\s*\n|$)",
    ],

    # ── Votos por partido / organizacion politica ─────────────────────────────
    # MAS-IPSP (partido 1)
    "partido_1_votos": [
        r"mas[\s\-]*ipsp[^\n]*?(\d+)\s*$",
        r"movimiento\s+al\s+socialismo[^\n]*?(\d+)\s*$",
        r"socialismo[^\n]*?(\d+)\s*$",
    ],
    # Economia para Bolivia Sumate u otro (partido 2)
    "partido_2_votos": [
        r"econom[ií]a\s+para\s+bolivia[^\n]*?(\d+)\s*$",
        r"sumate[^\n]*?(\d+)\s*$",
        r"\bcc\b[^\n]*?(\d+)\s*$",
        r"comunidad\s+ciudadana[^\n]*?(\d+)\s*$",
    ],
    # Democrata Cristiano u otro (partido 3)
    "partido_3_votos": [
        r"dem[oó]crata\s+cristiano[^\n]*?(\d+)\s*$",
        r"creemos[^\n]*?(\d+)\s*$",
    ],
    # Resto agrupado (partido 4)
    "partido_4_votos": [
        r"(?:fpv|libre\s*21|pan[\s\-]*bol|mts|juntos|adn)[^\n]*?(\d+)\s*$",
        r"otros[:\s]*(\d+)",
        r"partido\s+4[:\s]*(\d+)",
    ],

    # ── Totales de escrutinio ─────────────────────────────────────────────────
    "votos_validos": [
        r"(?:total\s+)?votos?\s+v[aá]lidos?" + _SEP + r"(\d+)",
        r"v[aá]lidos?" + _SEP + r"(\d+)",
    ],
    "votos_blancos": [
        r"votos?\s+(?:en\s+)?blancos?" + _SEP + r"(\d+)",
        r"blancos?" + _SEP + r"(\d+)",
    ],
    "votos_nulos": [
        r"votos?\s+nulos?" + _SEP + r"(\d+)",
        r"nulos?" + _SEP + r"(\d+)",
    ],
    "votos_emitidos": [
        r"(?:total\s+)?votos?\s+emitidos?" + _SEP + r"(\d+)",
        r"emitidos?" + _SEP + r"(\d+)",
    ],
    "boletas_no_utilizadas": [
        r"(?:cantidad\s+total\s+de\s+)?papeletas?\s+no\s+utilizadas?" + _SEP + r"(\d+)",
        r"no\s+utilizadas?" + _SEP + r"(\d+)",
        r"boletas?\s+no\s+utilizadas?" + _SEP + r"(\d+)",
    ],
    "total_boletas": [
        r"cantidad\s+total\s+de\s+papeletas?\s+en\s+[aá]nfora" + _SEP + r"(\d+)",
        r"total\s+(?:de\s+)?(?:papeletas?|boletas?)" + _SEP + r"(\d+)",
        r"papeletas?\s+en\s+[aá]nfora" + _SEP + r"(\d+)",
    ],
    "nro_votantes": [
        r"(?:total\s+)?votantes?\s+habilitados?" + _SEP + r"(\d+)",
        r"padr[oó]n\s+electoral" + _SEP + r"(\d+)",
        r"habilitados?" + _SEP + r"(\d+)",
        r"ciudadanos?\s+habilitados?" + _SEP + r"(\d+)",
    ],
}


class FormParser:
    """
    Extrae campos estructurados del texto OCR de actas electorales bolivianas.
    Adaptado al formato real 2025 del OEP.
    """

    def parse(self, raw_text: str) -> Tuple[Dict[str, Any], float]:
        """
        Analiza el texto OCR y retorna los campos extraidos junto con su confianza.

        La confianza mide cuantos campos NUMERICOS se extrajeron (0.0 - 1.0).
        Los campos de texto (departamento, etc.) se extraen pero no penalizan.

        Returns:
            (campos, confianza)
        """
        normalized = _normalize(raw_text)
        campos: Dict[str, Any] = {}

        for field_name, patterns in _PATTERNS.items():
            value = self._extract(normalized, patterns, field_name)
            if value is not None:
                campos[field_name] = value

        # Si el codigo_mesa es el numero de 13 digitos, derivar nro_mesa de el
        if "codigo_mesa" in campos and "nro_mesa" not in campos:
            codigo = str(campos["codigo_mesa"])
            if len(codigo) == 13 and codigo.isdigit():
                # Los ultimos 3 digitos son el numero de mesa dentro del recinto
                campos["nro_mesa"] = int(codigo[-3:])

        # Fallback: tabla generica de partidos
        self._fallback_party_table(normalized, campos)

        # Confianza = fraccion de campos numericos extraidos
        found = sum(1 for f in _NUMERIC_FIELDS if f in campos)
        confianza = found / len(_NUMERIC_FIELDS)

        logger.debug(
            "Campos extraidos: %d numericos / %d — texto: %s — confianza: %.0f%%",
            found, len(_NUMERIC_FIELDS),
            [f for f in _TEXT_FIELDS if f in campos],
            confianza * 100,
        )
        return campos, confianza

    # ── Extraccion por campo ───────────────────────────────────────────────────

    def _extract(
        self, text: str, patterns: List[str], field_name: str
    ) -> Optional[Any]:
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if m:
                raw = m.group(1).strip()
                if _is_numeric_field(field_name):
                    return _parse_int(raw)
                return _clean_text(raw)
        return None

    def _fallback_party_table(
        self, text: str, campos: Dict[str, Any]
    ) -> None:
        """
        Detecta filas tipo 'NOMBRE_PARTIDO  NUMERO' cuando los patrones
        por nombre no funcionaron. Rellena partido_1..4 en orden.
        """
        missing = [
            f for f in ("partido_1_votos", "partido_2_votos",
                        "partido_3_votos", "partido_4_votos")
            if f not in campos
        ]
        if not missing:
            return

        rows = re.findall(
            r"^[A-ZÁÉÍÓÚÑ\s\-]{4,}\s+(\d+)\s*$",
            text, re.MULTILINE | re.IGNORECASE,
        )
        for i, field_name in enumerate(missing):
            if i < len(rows):
                v = _parse_int(rows[i])
                if v is not None:
                    campos[field_name] = v


# ── Normalizacion ──────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Corregir typos OCR SOLO en secuencias que ya tienen un digito real
    def _fix_num_run(m: re.Match) -> str:
        s = m.group(0)
        if not re.search(r"\d", s):
            return s  # es una palabra, no tocar
        for wrong, right in _OCR_NUM_FIXES.items():
            s = s.replace(wrong, right)
        return s

    text = re.sub(r"[0-9OolIBSZGq]{2,}", _fix_num_run, text)

    # Separadores de miles → sin separador
    text = re.sub(r"(\d)[.,](\d{3})\b", r"\1\2", text)

    # Multiples espacios (preservar saltos de linea)
    text = re.sub(r"[^\S\n]+", " ", text)

    return text


def _is_numeric_field(field_name: str) -> bool:
    return any(
        kw in field_name
        for kw in ("_votos", "boletas", "nro_mesa", "nro_votantes", "votos")
    )


def _parse_int(value: str) -> Optional[int]:
    clean = re.sub(r"[\s.,]", "", value)
    for wrong, right in _OCR_NUM_FIXES.items():
        clean = clean.replace(wrong, right)
    try:
        result = int(clean)
        return result if result >= 0 else None
    except ValueError:
        return None


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
