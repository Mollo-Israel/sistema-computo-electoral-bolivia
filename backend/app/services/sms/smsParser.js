function getValue(tokens, key) {
  const index = tokens.indexOf(key);
  if (index === -1 || index + 1 >= tokens.length) {
    return null;
  }

  return tokens[index + 1];
}

function toNumber(value) {
  if (value === null || value === undefined) {
    return null;
  }

  if (!/^\d+$/.test(value)) {
    return null;
  }

  return Number(value);
}

function parseSmsMessage(message, telefonoOrigen) {
  if (!message || typeof message !== "string") {
    return {
      success: false,
      message: "El mensaje SMS es obligatorio"
    };
  }

  const cleanMessage = message.trim().replace(/\s+/g, " ").toUpperCase();
  const tokens = cleanMessage.split(" ");

  const mesaCodigo = getValue(tokens, "MESA");
  const partido1 = toNumber(getValue(tokens, "P1"));
  const partido2 = toNumber(getValue(tokens, "P2"));
  const partido3 = toNumber(getValue(tokens, "P3"));
  const partido4 = toNumber(getValue(tokens, "P4"));
  const votosBlancos = toNumber(getValue(tokens, "VB"));
  const votosNulos = toNumber(getValue(tokens, "VN"));
  const votosValidos = toNumber(getValue(tokens, "VV"));
  const boletasNoUtilizadas = toNumber(getValue(tokens, "BNU"));
  const pinRecibido = getValue(tokens, "PIN");

  const requiredFields = [
    { name: "MESA", value: mesaCodigo },
    { name: "P1", value: partido1 },
    { name: "P2", value: partido2 },
    { name: "P3", value: partido3 },
    { name: "P4", value: partido4 },
    { name: "VB", value: votosBlancos },
    { name: "VN", value: votosNulos },
    { name: "VV", value: votosValidos },
    { name: "BNU", value: boletasNoUtilizadas },
    { name: "PIN", value: pinRecibido }
  ];

  const missingFields = requiredFields
    .filter((field) => field.value === null || field.value === undefined || field.value === "")
    .map((field) => field.name);

  if (missingFields.length > 0) {
    return {
      success: false,
      message: "El SMS tiene campos faltantes o inválidos",
      error: {
        campos_faltantes: missingFields
      }
    };
  }

  const votosEmitidos = votosValidos + votosNulos;
  const totalBoletas = votosEmitidos + boletasNoUtilizadas;

  return {
    success: true,
    message: "SMS convertido a JSON estándar",
    data: {
      mesa_codigo: mesaCodigo,
      partido_1_votos: partido1,
      partido_2_votos: partido2,
      partido_3_votos: partido3,
      partido_4_votos: partido4,
      votos_blancos: votosBlancos,
      votos_nulos: votosNulos,
      votos_validos: votosValidos,
      votos_emitidos: votosEmitidos,
      boletas_no_utilizadas: boletasNoUtilizadas,
      total_boletas: totalBoletas,
      pin_recibido: pinRecibido,
      telefono_origen: telefonoOrigen,
      origen: "SMS",
      fuente: "SMS",
      parser_estado: "OK",
      mensaje_original: message,
      fecha_recepcion: new Date().toISOString()
    }
  };
}

module.exports = {
  parseSmsMessage
};