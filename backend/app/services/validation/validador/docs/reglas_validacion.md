# Reglas de validación — Sistema Nacional de Cómputo Electoral Bolivia

**Módulo:** Validador + Logs + Reglas OEP  
**Responsable:** Sanabria  
**Aplica a:** Flujo RRV (Recuento Rápido de Votos) y Cómputo Oficial

---

## 1. Reglas numéricas obligatorias

Estas reglas aplican en **ambos flujos**. El Cómputo Oficial las aplica con mayor estrictez (ningún campo puede ser nulo).

### Regla 1 — Votos por partido

```
partido_1_votos + partido_2_votos + partido_3_votos + partido_4_votos = votos_validos
```

### Regla 2 — Votos emitidos

```
votos_validos + votos_blancos + votos_nulos = votos_emitidos
```

### Regla 3 — Total de boletas

```
votos_emitidos + boletas_no_utilizadas = total_boletas
```

### Regla 4 — Límite de votantes

```
votos_emitidos <= nro_votantes
```

---

## 2. Regla de duplicados (Regla 5)

Si ya existe un acta con estado `VALIDADA` o `PUBLICADA` para una `mesa_codigo`, toda entrada nueva para esa misma mesa se marca como **DUPLICADA**.

- El registro original **nunca se reemplaza automáticamente**.
- Se genera un log de tipo `DUPLICADO` con nivel `WARNING`.

---

## 3. Regla OCR baja confianza (Regla 6)

Si el módulo OCR reporta:

| Condición | Estado resultante | Motivo |
|-----------|------------------|--------|
| `calidad_imagen = MALA` | `OBSERVADA` | `IMAGEN_ILEGIBLE` |
| `confianza_ocr < 0.75` | `OBSERVADA` | `OCR_BAJA_CONFIANZA` |

El umbral mínimo de confianza es **75 %** (`OCR_CONFIANZA_MINIMA = 0.75`).

---

## 4. Regla SMS inválido (Regla 7)

Si el parser SMS reporta uno de los siguientes estados:

| `parser_estado` | Estado resultante | Motivo |
|-----------------|------------------|--------|
| `INVALIDO` | `RECHAZADA` | `SMS_FORMATO_INVALIDO` |
| `ERROR_FORMATO` | `RECHAZADA` | `SMS_FORMATO_INVALIDO` |
| `PIN_INVALIDO` | `RECHAZADA` | `SMS_NO_AUTORIZADO` |

---

## 5. Estados de acta

### RRV

| Estado | Descripción |
|--------|-------------|
| `RECIBIDA` | Acta ingresada al sistema, pendiente de procesamiento |
| `PROCESANDO` | En proceso de OCR o parsing |
| `VALIDADA` | Pasó todas las reglas OEP |
| `OBSERVADA` | Tiene inconsistencias; requiere revisión manual |
| `RECHAZADA` | SMS inválido o error irrecuperable |
| `DUPLICADA` | Ya existe un acta válida para esa mesa |
| `PUBLICADA` | Resultado publicado en el dashboard |

### Cómputo Oficial

| Estado | Descripción |
|--------|-------------|
| `TRANSCRITA` | Registrada desde CSV/formulario, pendiente de validación |
| `VALIDADA` | Pasó todas las reglas OEP |
| `OBSERVADA` | Tiene inconsistencias; requiere corrección |
| `APROBADA` | Revisada y aprobada por supervisor |
| `PUBLICADA` | Resultado oficial publicado |
| `DUPLICADA` | Ya existe un acta oficial para esa mesa |

---

## 6. Tipos y niveles de log funcional

Los logs registran **errores de negocio**, no errores técnicos del servidor.

| Tipo | Nivel | Descripción |
|------|-------|-------------|
| `DUPLICADO` | WARNING | Acta duplicada detectada |
| `TOTAL_NO_COINCIDE` | ERROR | Subtotales no suman correctamente |
| `INCOHERENCIA_NUMERICA` | ERROR | Votos por partido vs votos_validos no coinciden |
| `OCR_BAJA_CONFIANZA` | WARNING | Confianza OCR por debajo del umbral |
| `IMAGEN_ILEGIBLE` | ERROR | Calidad de imagen insuficiente |
| `SMS_FORMATO_INVALIDO` | ERROR | SMS no cumple el formato oficial |
| `SMS_NO_AUTORIZADO` | CRITICAL | PIN inválido o remitente no autorizado |
| `MESA_NO_EXISTE` | ERROR | mesa_codigo no existe en el catálogo |
| `VOTOS_EXCEDEN_HABILITADOS` | CRITICAL | Votos emitidos superan votantes habilitados |
| `ERROR_SISTEMA` | CRITICAL | Error interno inesperado |

---

## 7. Respuesta estándar del validador

```json
// Caso exitoso
{
  "estado": "VALIDADA",
  "motivo_observacion": null,
  "errores": []
}

// Caso con error
{
  "estado": "OBSERVADA",
  "motivo_observacion": "TOTAL_NO_COINCIDE",
  "errores": [
    "votos_validos+blancos+nulos (64) != votos_emitidos (65)"
  ]
}

// Caso duplicado
{
  "estado": "DUPLICADA",
  "motivo_observacion": "DUPLICADO",
  "errores": [
    "Ya existe un acta válida o publicada para esta mesa"
  ]
}

// Caso SMS rechazado
{
  "estado": "RECHAZADA",
  "motivo_observacion": "SMS_FORMATO_INVALIDO",
  "errores": [
    "SMS con formato inválido; no se pudo interpretar el mensaje"
  ]
}
```

---

## 8. Archivos del módulo

| Archivo | Descripción |
|---------|-------------|
| `backend/app/services/validation/validation_rules.py` | Reglas OEP puras (sin dependencias de framework) |
| `backend/app/services/validation/rrv_validator.py` | Validador RRV (OCR, APP, SMS) |
| `backend/app/services/validation/oficial_validator.py` | Validador Oficial (CSV, formulario, automatizador) |
| `backend/app/services/logging/functional_log_service.py` | Servicio de logs funcionales |
| `backend/app/schemas/acta_rrv.py` | Schema Pydantic entrada RRV |
| `backend/app/schemas/acta_oficial.py` | Schema Pydantic entrada Oficial |
| `backend/app/schemas/validation_response.py` | Schema Pydantic respuesta del validador |

---

## 9. Cómo integrar el validador en un endpoint

```python
from app.services.validation import RRVValidator, OficialValidator
from app.services.logging import FunctionalLogService

# --- RRV ---
rrv_validator = RRVValidator(actas_repository=mongo_repo)
log_service = FunctionalLogService(logs_repository=logs_repo)

result = rrv_validator.validate(acta_dict)
log_service.log_from_validation(result, acta_rrv_id=acta_id, mesa_codigo=mesa)

# --- Oficial ---
oficial_validator = OficialValidator(actas_repository=postgres_repo)
result = oficial_validator.validate(acta_dict)
log_service.log_from_validation(result, mesa_codigo=mesa)
```
