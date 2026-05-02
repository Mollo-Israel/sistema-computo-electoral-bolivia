function processMockOcr(file) {
  return {
    mesa_codigo: "4006716",
    nro_mesa: 1,
    codigo_recinto: "10301",
    recinto_nombre: "U.E. San Martín",
    codigo_territorial: "30101",
    departamento: "Cochabamba",
    provincia: "Cercado",
    municipio: "Cochabamba",
    partido_1_votos: 20,
    partido_2_votos: 9,
    partido_3_votos: 9,
    partido_4_votos: 18,
    votos_validos: 56,
    votos_blancos: 2,
    votos_nulos: 3,
    votos_emitidos: 61,
    boletas_no_utilizadas: 4,
    total_boletas: 65,
    nro_votantes: 75,
    origen: "APP",
    fuente: "FOTO_MOVIL",
    estado: "PROCESADA",
    archivo_tipo: file?.mimetype || "image/jpeg",
archivo_nombre_original: file?.originalname || "acta-electoral.jpg",
archivo_nombre_guardado: file?.filename || "acta-electoral.jpg",
archivo_ruta: file?.filename
  ? `samples/actas/raw/${file.filename}`
  : "samples/actas/raw/acta-electoral.jpg",
    confianza_ocr: 0.91,
    calidad_imagen: "BUENA",
    fecha_recepcion: new Date().toISOString()
  };
}

module.exports = {
  processMockOcr
};