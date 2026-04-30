const API_URL = "http://192.168.0.95:3001/api";

export async function sendSmsMessage(telefonoOrigen, mensaje) {
  const response = await fetch(`${API_URL}/sms/receive`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      telefono_origen: telefonoOrigen,
      mensaje
    })
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.message || "Error al procesar el SMS");
  }

  return data;
}