const { processMockOcr } = require("../services/ocr/mockOcrService");
const { validateRrvActa } = require("../services/rrv/rrvValidator");

function uploadActa(req, res) {
  try {
    if (!req.file) {
      return res.status(400).json({
        success: false,
        message: "No se recibió ninguna imagen del acta"
      });
    }

    const ocrData = processMockOcr(req.file);
    const validacion = validateRrvActa(ocrData);

    return res.status(200).json({
      success: true,
      message: "Acta recibida desde app móvil y procesada por el flujo RRV",
      data: {
        ...ocrData,
        estado: validacion.estado,
        validacion_rrv: validacion
      }
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      message: "Error al procesar el acta",
      error: error.message
    });
  }
}

module.exports = {
  uploadActa
};