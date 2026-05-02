const { parseSmsMessage } = require("../services/sms/smsParser");
const { validateRrvActa } = require("../services/rrv/rrvValidator");

function receiveSms(req, res) {
  try {
    const { telefono_origen, mensaje } = req.body;

    console.log("SMS de prueba recibido:", {
      telefono_origen,
      mensaje
    });

    if (!telefono_origen) {
      return res.status(400).json({
        success: false,
        message: "El teléfono de origen es obligatorio"
      });
    }

    const parsedSms = parseSmsMessage(mensaje, telefono_origen);

    if (!parsedSms.success) {
      return res.status(400).json(parsedSms);
    }

    const validacion = validateRrvActa(parsedSms.data);

    return res.status(200).json({
      success: true,
      message: "SMS recibido, convertido y validado por el flujo RRV",
      data: {
        ...parsedSms.data,
        estado: validacion.estado,
        validacion_rrv: validacion
      }
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      message: "Error al procesar el SMS",
      error: error.message
    });
  }
}

function receiveRealSmsWebhook(req, res) {
  try {
    let telefonoOrigen = null;
    let telefonoDestino = null;
    let mensaje = null;

    if (typeof req.body === "string") {
      telefonoOrigen = "MACRODROID";
      telefonoDestino = "CELULAR_RECEPTOR";
      mensaje = req.body.trim();
    } else {
      telefonoOrigen = req.body.From || req.body.from || req.body.telefono_origen;
      telefonoDestino = req.body.To || req.body.to || req.body.telefono_destino;
      mensaje = req.body.Body || req.body.body || req.body.mensaje;
    }

    console.log("SMS REAL RECIBIDO DESDE GATEWAY:");
    console.log({
      telefono_origen: telefonoOrigen,
      telefono_destino: telefonoDestino,
      mensaje
    });

    if (!mensaje) {
      console.log("El SMS real llegó sin cuerpo de mensaje.");

      return res.status(200).json({
        success: false,
        message: "SMS sin cuerpo de mensaje"
      });
    }

    const parsedSms = parseSmsMessage(mensaje, telefonoOrigen);

    if (!parsedSms.success) {
      console.log("SMS real con error de formato:");
      console.log(JSON.stringify(parsedSms, null, 2));

      return res.status(200).json({
        success: false,
        message: "SMS recibido pero con error de formato",
        detalle: parsedSms
      });
    }

    const validacion = validateRrvActa(parsedSms.data);

    const result = {
      success: true,
      message: "SMS real recibido, parseado y validado",
      data: {
        ...parsedSms.data,
        estado: validacion.estado,
        validacion_rrv: validacion
      }
    };

    console.log("SMS REAL PARSEADO Y VALIDADO:");
    console.log(JSON.stringify(result, null, 2));

    return res.status(200).json(result);
  } catch (error) {
    console.log("Error procesando SMS real:", error.message);

    return res.status(500).json({
      success: false,
      message: "Error procesando SMS real",
      error: error.message
    });
  }
}

module.exports = {
  receiveSms,
  receiveRealSmsWebhook
};