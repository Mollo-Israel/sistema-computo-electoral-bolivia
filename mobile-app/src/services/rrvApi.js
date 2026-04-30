const API_URL = "http://192.168.0.95:3001/api";

export async function uploadActaImage(imageUri) {
  const formData = new FormData();

  formData.append("acta", {
    uri: imageUri,
    name: "acta-electoral.jpg",
    type: "image/jpeg",
  });

  const response = await fetch(`${API_URL}/rrv/upload-acta`, {
    method: "POST",
    body: formData,
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.message || "Error al subir el acta");
  }

  return data;
}