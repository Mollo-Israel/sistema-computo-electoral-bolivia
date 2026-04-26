# Reglas de Validación de Actas - OEP

Estas reglas deben aplicarse en `validation_rules.py` antes de persistir cualquier acta.
Ver también: `docs/diccionario_datos.md`.

## Reglas Aritméticas

### R1 - Suma de votos por partido igual a votos válidos
```
partido_1_votos + partido_2_votos + partido_3_votos + partido_4_votos == votos_validos
```
- Fallo → `estado = OBSERVADA` (si es OCR) o `estado = RECHAZADA` (si es SMS sin posibilidad de corrección).

### R2 - Suma de categorías igual a votos emitidos
```
votos_validos + votos_blancos + votos_nulos == votos_emitidos
```
- Fallo → `estado = OBSERVADA`.

### R3 - Total de boletas
```
votos_emitidos + boletas_no_utilizadas == total_boletas
```
- Fallo → `estado = OBSERVADA`.

### R4 - Votos emitidos no superan el padrón
```
votos_emitidos <= nro_votantes
```
- Fallo → `estado = OBSERVADA` (requiere revisión manual).

## Reglas de Integridad

### R5 - Acta duplicada
- Una `mesa_codigo` que ya tiene un acta en estado `PUBLICADA` o `PROCESADA` **NO** puede ser reemplazada automáticamente.
- Un segundo envío del mismo `mesa_codigo` se marca como `DUPLICADA` y queda en cola de revisión.

### R6 - Confianza OCR baja
- Si la confianza del OCR es menor al umbral definido (p.ej. < 0.85), el acta se marca como `OBSERVADA`.
- Requiere revisión manual antes de cambiar a `PROCESADA`.

### R7 - Formato SMS inválido
- Si el mensaje SMS no cumple el formato acordado, el acta se marca como `RECHAZADA`.
- Se registra el evento en `rrv_logs`.

## Estados de Acta

| Estado      | Descripción                                                  |
|-------------|--------------------------------------------------------------|
| RECIBIDA    | Ingresada al sistema, pendiente de validación               |
| PROCESADA   | Validada y almacenada correctamente                         |
| PENDIENTE   | En espera de procesamiento                                  |
| OBSERVADA   | Requiere revisión manual (aritmética o confianza OCR baja)  |
| RECHAZADA   | Inválida (formato SMS incorrecto u otro error grave)        |
| DUPLICADA   | Mesa ya tiene acta válida; duplicado en cola de revisión    |
| PUBLICADA   | Resultado oficial publicado                                 |
