function toNumber(value) {
  const number = Number(value);
  return Number.isNaN(number) ? null : number;
}

function validateRrvActa(acta) {
  const errores = [];
  const advertencias = [];

  const requiredFields = [
    "mesa_codigo",
    "partido_1_votos",
    "partido_2_votos",
    "partido_3_votos",
    "partido_4_votos",
    "votos_blancos",
    "votos_nulos",
    "votos_validos",
    "boletas_no_utilizadas"
  ];

  requiredFields.forEach((field) => {
    if (acta[field] === undefined || acta[field] === null || acta[field] === "") {
      errores.push(`Campo obligatorio faltante: ${field}`);
    }
  });

  const partido1 = toNumber(acta.partido_1_votos);
  const partido2 = toNumber(acta.partido_2_votos);
  const partido3 = toNumber(acta.partido_3_votos);
  const partido4 = toNumber(acta.partido_4_votos);
  const votosBlancos = toNumber(acta.votos_blancos);
  const votosNulos = toNumber(acta.votos_nulos);
  const votosValidos = toNumber(acta.votos_validos);
  const boletasNoUtilizadas = toNumber(acta.boletas_no_utilizadas);
  const nroVotantes = toNumber(acta.nro_votantes);

  const numericValues = {
    partido_1_votos: partido1,
    partido_2_votos: partido2,
    partido_3_votos: partido3,
    partido_4_votos: partido4,
    votos_blancos: votosBlancos,
    votos_nulos: votosNulos,
    votos_validos: votosValidos,
    boletas_no_utilizadas: boletasNoUtilizadas
  };

  Object.entries(numericValues).forEach(([field, value]) => {
    if (value === null || value < 0) {
      errores.push(`Campo numérico inválido: ${field}`);
    }
  });

  if (errores.length > 0) {
    return {
      es_valida: false,
      estado: "OBSERVADA",
      errores,
      advertencias
    };
  }

  const votosPorPartidos = partido1 + partido2 + partido3 + partido4;
  const votosValidosCalculados = votosPorPartidos + votosBlancos;
  const votosEmitidosCalculados = votosValidos + votosNulos;
  const totalBoletasCalculado = votosEmitidosCalculados + boletasNoUtilizadas;

  if (votosValidosCalculados !== votosValidos) {
    errores.push("La suma de votos por partido más blancos no coincide con votos válidos");
  }

  if (nroVotantes !== null && totalBoletasCalculado !== nroVotantes) {
    errores.push("El total de boletas no coincide con la cantidad de votantes habilitados");
  }

  if (nroVotantes !== null && votosEmitidosCalculados > nroVotantes) {
    errores.push("Los votos emitidos superan la cantidad de votantes habilitados");
  }

  if (!acta.pin_recibido && acta.origen === "SMS") {
    advertencias.push("SMS recibido sin PIN de seguridad");
  }

  return {
    es_valida: errores.length === 0,
    estado: errores.length === 0 ? "VALIDADA" : "OBSERVADA",
    errores,
    advertencias,
    calculos: {
      votos_por_partidos: votosPorPartidos,
      votos_validos_calculados: votosValidosCalculados,
      votos_emitidos_calculados: votosEmitidosCalculados,
      total_boletas_calculado: totalBoletasCalculado
    }
  };
}

module.exports = {
  validateRrvActa
};