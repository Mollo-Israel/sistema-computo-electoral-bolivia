"""
Pruebas del modulo Validador + Logs + Reglas OEP
Ejecutar desde la carpeta backend/:  python test_validador.py
"""

import sys
sys.path.insert(0, ".")

from app.services.validation import RRVValidator, OficialValidator
from app.services.logging import FunctionalLogService

v   = RRVValidator()
ov  = OficialValidator()
log = FunctionalLogService()

PASS = "[PASS]"
FAIL = "[FAIL]"

resultados = []

def caso(nombre, resultado, estado_esperado):
    ok = resultado.estado.value == estado_esperado
    simbolo = PASS if ok else FAIL
    print(f"  {simbolo}  {nombre}")
    print(f"         estado={resultado.estado.value}  motivo={resultado.motivo_observacion}")
    if resultado.errores:
        for e in resultado.errores:
            print(f"         ? {e}")
    if not ok:
        print(f"         !! se esperaba '{estado_esperado}'")
    resultados.append(ok)
    return resultado

# ??? Acta base correcta ???????????????????????????????????????????????????????
BASE = {
    "mesa_codigo": "800412-1",
    "nro_mesa": 1,
    "codigo_recinto": "800412",
    "codigo_territorial": "800412",
    "origen": "OCR",
    "fuente": "PDF",
    "partido_1_votos": 8,
    "partido_2_votos": 1,
    "partido_3_votos": 7,
    "partido_4_votos": 10,
    "votos_validos": 26,    # 8+1+7+10 = 26
    "votos_blancos": 3,
    "votos_nulos": 7,
    "votos_emitidos": 36,   # 26+3+7 = 36
    "boletas_no_utilizadas": 10,
    "total_boletas": 46,    # 36+10 = 46
    "nro_votantes": 75,
    "confianza_ocr": 0.92,
    "calidad_imagen": "BUENA",
}

def acta(**overrides):
    return {**BASE, **overrides}


# ??? BLOQUE 1: Reglas numericas ???????????????????????????????????????????????
print("\n==========================================")
print("  BLOQUE 1 -- Reglas numericas OEP")
print("==========================================")

caso("Acta correcta -> VALIDADA",
     v.validate(acta()),
     "VALIDADA")

caso("Regla 1 violada: suma de partidos != votos_validos -> OBSERVADA",
     v.validate(acta(partido_1_votos=99)),
     "OBSERVADA")

caso("Regla 2 violada: validos+blancos+nulos != votos_emitidos -> OBSERVADA",
     v.validate(acta(votos_blancos=99)),
     "OBSERVADA")

caso("Regla 3 violada: emitidos+no_utilizadas != total_boletas -> OBSERVADA",
     v.validate(acta(boletas_no_utilizadas=999)),
     "OBSERVADA")

caso("Regla 4 violada: votos_emitidos > nro_votantes -> OBSERVADA",
     v.validate(acta(votos_emitidos=100, total_boletas=110, boletas_no_utilizadas=10)),
     "OBSERVADA")


# ??? BLOQUE 2: OCR ???????????????????????????????????????????????????????????
print("\n==========================================")
print("  BLOQUE 2 -- OCR")
print("==========================================")

caso("OCR confianza alta (0.92) -> VALIDADA",
     v.validate(acta(confianza_ocr=0.92)),
     "VALIDADA")

caso("OCR confianza baja (0.50) -> OBSERVADA",
     v.validate(acta(confianza_ocr=0.50)),
     "OBSERVADA")

caso("Calidad imagen REGULAR -> VALIDADA (por encima del umbral)",
     v.validate(acta(calidad_imagen="REGULAR")),
     "VALIDADA")

caso("Calidad imagen MALA -> OBSERVADA",
     v.validate(acta(calidad_imagen="MALA")),
     "OBSERVADA")


# ??? BLOQUE 3: SMS ???????????????????????????????????????????????????????????
print("\n==========================================")
print("  BLOQUE 3 -- SMS")
print("==========================================")

caso("SMS correcto (parser_estado=OK) -> VALIDADA",
     v.validate(acta(origen="SMS", fuente="SMS", parser_estado="OK")),
     "VALIDADA")

caso("SMS formato invalido -> RECHAZADA",
     v.validate(acta(origen="SMS", fuente="SMS", parser_estado="INVALIDO")),
     "RECHAZADA")

caso("SMS error de formato -> RECHAZADA",
     v.validate(acta(origen="SMS", fuente="SMS", parser_estado="ERROR_FORMATO")),
     "RECHAZADA")

caso("SMS PIN invalido -> RECHAZADA",
     v.validate(acta(origen="SMS", fuente="SMS", parser_estado="PIN_INVALIDO")),
     "RECHAZADA")


# ??? BLOQUE 4: Duplicados ????????????????????????????????????????????????????
print("\n==========================================")
print("  BLOQUE 4 -- Duplicados")
print("==========================================")

class MockRepo:
    """Simula que ya existe un acta valida para la mesa 800412-1."""
    def existe_acta_valida(self, mesa_codigo):
        return mesa_codigo == "800412-1"

v_con_repo = RRVValidator(actas_repository=MockRepo())

caso("Mesa ya tiene acta valida -> DUPLICADA",
     v_con_repo.validate(acta()),
     "DUPLICADA")

caso("Mesa diferente, sin duplicado -> VALIDADA",
     v_con_repo.validate(acta(mesa_codigo="800412-2")),
     "VALIDADA")


# ??? BLOQUE 5: Validador Oficial ?????????????????????????????????????????????
print("\n==========================================")
print("  BLOQUE 5 -- Validador Oficial")
print("==========================================")

OFICIAL_BASE = {
    "mesa_codigo": "800412-1",
    "codigo_recinto": "800412",
    "codigo_territorial": "800412",
    "partido_1_votos": 8,
    "partido_2_votos": 1,
    "partido_3_votos": 7,
    "partido_4_votos": 10,
    "votos_validos": 26,
    "votos_blancos": 3,
    "votos_nulos": 7,
    "votos_emitidos": 36,
    "boletas_no_utilizadas": 10,
    "total_boletas": 46,
    "nro_votantes": 75,
    "fuente": "AUTOMATIZADOR",
    "fila_csv": 12,
    "usuario_id": 4,
}

def ofic(**overrides):
    return {**OFICIAL_BASE, **overrides}

caso("Acta oficial correcta -> VALIDADA",
     ov.validate(ofic()),
     "VALIDADA")

caso("Fuente invalida -> OBSERVADA",
     ov.validate(ofic(fuente="DESCONOCIDA")),
     "OBSERVADA")

caso("Campo obligatorio faltante (usuario_id=None) -> OBSERVADA",
     ov.validate(ofic(usuario_id=None)),
     "OBSERVADA")

caso("Oficial con incoherencia numerica -> OBSERVADA",
     ov.validate(ofic(votos_validos=99)),
     "OBSERVADA")


# ??? BLOQUE 6: Logs funcionales ??????????????????????????????????????????????
print("\n==========================================")
print("  BLOQUE 6 -- Logs funcionales")
print("==========================================")

r_obs  = v.validate(acta(partido_1_votos=99))
r_dup  = v_con_repo.validate(acta())
r_val  = v.validate(acta())
r_rech = v.validate(acta(origen="SMS", fuente="SMS", parser_estado="INVALIDO"))

entrada_log = log.log_from_validation(r_obs,  acta_rrv_id="rrv-001", mesa_codigo="800412-1")
dup_log     = log.log_from_validation(r_dup,  acta_rrv_id="rrv-002", mesa_codigo="800412-1")
sin_log     = log.log_from_validation(r_val,  acta_rrv_id="rrv-003", mesa_codigo="800412-2")
rech_log    = log.log_from_validation(r_rech, acta_rrv_id="rrv-004", mesa_codigo="800412-3")

def check_log(nombre, entry, tipo_esperado, nivel_esperado):
    ok = entry is not None and entry.tipo == tipo_esperado and entry.nivel == nivel_esperado
    simbolo = PASS if ok else FAIL
    print(f"  {simbolo}  {nombre}")
    if entry:
        print(f"         tipo={entry.tipo}  nivel={entry.nivel}")
        print(f"         detalle: {entry.detalle[:80]}")
    else:
        print("         (sin log -- esperado)" if tipo_esperado is None else "         !! no se genero log")
    resultados.append(ok)

check_log("Incoherencia genera log INCOHERENCIA_NUMERICA / ERROR",
          entrada_log, "INCOHERENCIA_NUMERICA", "ERROR")

check_log("Duplicado genera log DUPLICADO / WARNING",
          dup_log, "DUPLICADO", "WARNING")

ok_sin = sin_log is None
simbolo = PASS if ok_sin else FAIL
print(f"  {simbolo}  Acta VALIDADA no genera log")
resultados.append(ok_sin)

check_log("SMS invalido genera log SMS_FORMATO_INVALIDO / ERROR",
          rech_log, "SMS_FORMATO_INVALIDO", "ERROR")

mesa_log = log.log_mesa_no_existe("800412-99")
check_log("Mesa inexistente genera log MESA_NO_EXISTE / ERROR",
          mesa_log, "MESA_NO_EXISTE", "ERROR")


# ??? Resumen final ????????????????????????????????????????????????????????????
total  = len(resultados)
pasados = sum(resultados)
print(f"\n==========================================")
print(f"  Resultado: {pasados}/{total} casos pasaron")
if pasados == total:
    print("  Todo correcto!")
else:
    print(f"  {total - pasados} caso(s) fallaron -- revisar arriba")
print("==========================================\n")

sys.exit(0 if pasados == total else 1)
