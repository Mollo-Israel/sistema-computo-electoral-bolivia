const API_URL = "http://192.168.0.95:3001/api/rrv/upload-acta";

export async function uploadActaPdf(pdfUri) {
  const formData = new FormData();

  formData.append("acta", {
    uri: pdfUri,
    name: "acta-electoral.pdf",
    type: "application/pdf"
  });

  const response = await fetch(API_URL, {
    method: "POST",
    body: formData
  });

  const responseText = await response.text();

  let data = null;

  try {
    data = JSON.parse(responseText);
  } catch {
    throw new Error(
      `El backend no devolvió JSON. Estado: ${response.status}. Respuesta: ${responseText.substring(0, 180)}`
    );
  }

  if (!response.ok) {
    throw new Error(data?.message || "No se pudo enviar el acta en PDF");
  }

  return data;
}