import { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  Button,
  Image,
  ScrollView,
  ActivityIndicator,
  Alert,
  TextInput
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import { uploadActaImage } from "../services/rrvApi";
import { sendSmsMessage } from "../services/smsApi";

export default function CaptureScreen() {
  const [imageUri, setImageUri] = useState(null);
  const [ocrResult, setOcrResult] = useState(null);
  const [loadingOcr, setLoadingOcr] = useState(false);

  const [telefonoOrigen, setTelefonoOrigen] = useState("70304788");
  const [mesa, setMesa] = useState("4016718");
  const [p1, setP1] = useState("10");
  const [p2, setP2] = useState("9");
  const [p3, setP3] = useState("15");
  const [p4, setP4] = useState("20");
  const [votosBlancos, setVotosBlancos] = useState("2");
  const [votosNulos, setVotosNulos] = useState("3");
  const [boletasNoUtilizadas, setBoletasNoUtilizadas] = useState("4");
  const [pin, setPin] = useState("1234");
  const [smsResult, setSmsResult] = useState(null);
  const [loadingSms, setLoadingSms] = useState(false);

  const toNumber = (value) => {
    const number = Number(value);
    return Number.isNaN(number) ? 0 : number;
  };

  const votosPartidos =
    toNumber(p1) + toNumber(p2) + toNumber(p3) + toNumber(p4);

  const votosValidos = votosPartidos + toNumber(votosBlancos);
  const votosEmitidos = votosValidos + toNumber(votosNulos);
  const totalBoletas = votosEmitidos + toNumber(boletasNoUtilizadas);

  const smsGenerado = `MESA ${mesa} P1 ${p1} P2 ${p2} P3 ${p3} P4 ${p4} VB ${votosBlancos} VN ${votosNulos} VV ${votosValidos} BNU ${boletasNoUtilizadas} PIN ${pin}`;

  const seleccionarImagen = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();

    if (!permission.granted) {
      Alert.alert("Permiso requerido", "Se necesita acceso a la galería.");
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.8
    });

    if (!result.canceled) {
      setImageUri(result.assets[0].uri);
      setOcrResult(null);
    }
  };

  const tomarFoto = async () => {
    const permission = await ImagePicker.requestCameraPermissionsAsync();

    if (!permission.granted) {
      Alert.alert("Permiso requerido", "Se necesita acceso a la cámara.");
      return;
    }

    const result = await ImagePicker.launchCameraAsync({
      quality: 0.8
    });

    if (!result.canceled) {
      setImageUri(result.assets[0].uri);
      setOcrResult(null);
    }
  };

  const subirActa = async () => {
    if (!imageUri) {
      Alert.alert("Sin imagen", "Primero selecciona o toma una foto del acta.");
      return;
    }

    try {
      setLoadingOcr(true);
      const data = await uploadActaImage(imageUri);
      setOcrResult(data);
    } catch (error) {
      Alert.alert("Error", error.message);
    } finally {
      setLoadingOcr(false);
    }
  };

  const enviarSms = async () => {
    if (!telefonoOrigen.trim()) {
      Alert.alert("Dato faltante", "Ingresa el teléfono de origen.");
      return;
    }

    if (!mesa.trim()) {
      Alert.alert("Dato faltante", "Ingresa el código de mesa.");
      return;
    }

    try {
      setLoadingSms(true);
      const data = await sendSmsMessage(telefonoOrigen, smsGenerado);
      setSmsResult(data);
    } catch (error) {
      Alert.alert("Error SMS", error.message);
    } finally {
      setLoadingSms(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Captura de acta electoral</Text>

      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Flujo APP móvil + OCR</Text>

        <View style={styles.buttonContainer}>
          <Button title="Seleccionar imagen" onPress={seleccionarImagen} />
        </View>

        <View style={styles.buttonContainer}>
          <Button title="Tomar foto" onPress={tomarFoto} />
        </View>

        {imageUri && <Image source={{ uri: imageUri }} style={styles.preview} />}

        <View style={styles.buttonContainer}>
          <Button title="Subir acta" onPress={subirActa} disabled={loadingOcr} />
        </View>

        {loadingOcr && <ActivityIndicator size="large" />}

        {ocrResult && (
          <View style={styles.resultBox}>
            <Text style={styles.resultTitle}>Resultado OCR</Text>
            <Text style={styles.resultText}>
              {JSON.stringify(ocrResult, null, 2)}
            </Text>
          </View>
        )}
      </View>

      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Flujo SMS</Text>

        <Text style={styles.description}>
          Formato oficial generado por la app para recintos sin internet.
        </Text>

        <Text style={styles.label}>Teléfono de origen</Text>
        <TextInput
          style={styles.input}
          value={telefonoOrigen}
          onChangeText={setTelefonoOrigen}
          keyboardType="phone-pad"
        />

        <Text style={styles.label}>Código de mesa</Text>
        <TextInput
          style={styles.input}
          value={mesa}
          onChangeText={setMesa}
        />

        <View style={styles.row}>
          <View style={styles.column}>
            <Text style={styles.label}>P1</Text>
            <TextInput style={styles.input} value={p1} onChangeText={setP1} keyboardType="numeric" />
          </View>

          <View style={styles.column}>
            <Text style={styles.label}>P2</Text>
            <TextInput style={styles.input} value={p2} onChangeText={setP2} keyboardType="numeric" />
          </View>
        </View>

        <View style={styles.row}>
          <View style={styles.column}>
            <Text style={styles.label}>P3</Text>
            <TextInput style={styles.input} value={p3} onChangeText={setP3} keyboardType="numeric" />
          </View>

          <View style={styles.column}>
            <Text style={styles.label}>P4</Text>
            <TextInput style={styles.input} value={p4} onChangeText={setP4} keyboardType="numeric" />
          </View>
        </View>

        <Text style={styles.label}>Votos blancos</Text>
        <TextInput
          style={styles.input}
          value={votosBlancos}
          onChangeText={setVotosBlancos}
          keyboardType="numeric"
        />

        <Text style={styles.label}>Votos nulos</Text>
        <TextInput
          style={styles.input}
          value={votosNulos}
          onChangeText={setVotosNulos}
          keyboardType="numeric"
        />

        <Text style={styles.label}>Boletas no utilizadas</Text>
        <TextInput
          style={styles.input}
          value={boletasNoUtilizadas}
          onChangeText={setBoletasNoUtilizadas}
          keyboardType="numeric"
        />

        <Text style={styles.label}>PIN de seguridad</Text>
        <TextInput
          style={styles.input}
          value={pin}
          onChangeText={setPin}
          keyboardType="numeric"
        />

        <View style={styles.summaryBox}>
          <Text style={styles.summaryText}>Votos por partidos: {votosPartidos}</Text>
          <Text style={styles.summaryText}>Votos válidos: {votosValidos}</Text>
          <Text style={styles.summaryText}>Votos emitidos: {votosEmitidos}</Text>
          <Text style={styles.summaryText}>Total boletas: {totalBoletas}</Text>
        </View>

        <Text style={styles.label}>SMS generado</Text>
        <View style={styles.smsBox}>
          <Text style={styles.smsText}>{smsGenerado}</Text>
        </View>

        <View style={styles.buttonContainer}>
          <Button title="Enviar SMS de prueba" onPress={enviarSms} disabled={loadingSms} />
        </View>

        {loadingSms && <ActivityIndicator size="large" />}

        {smsResult && (
          <View style={styles.resultBox}>
            <Text style={styles.resultTitle}>Resultado SMS</Text>
            <Text style={styles.resultText}>
              {JSON.stringify(smsResult, null, 2)}
            </Text>
          </View>
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 20,
    paddingTop: 50,
    backgroundColor: "#f5f5f5",
    flexGrow: 1
  },
  title: {
    fontSize: 24,
    fontWeight: "bold",
    marginBottom: 20,
    textAlign: "center"
  },
  card: {
    backgroundColor: "#ffffff",
    padding: 16,
    borderRadius: 12,
    marginBottom: 20
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: "bold",
    marginBottom: 14
  },
  description: {
    fontSize: 14,
    marginBottom: 14,
    color: "#555"
  },
  buttonContainer: {
    marginBottom: 12
  },
  preview: {
    width: "100%",
    height: 320,
    resizeMode: "contain",
    backgroundColor: "#ddd",
    marginVertical: 16,
    borderRadius: 10
  },
  label: {
    fontSize: 15,
    fontWeight: "bold",
    marginBottom: 6
  },
  input: {
    backgroundColor: "#f1f1f1",
    borderWidth: 1,
    borderColor: "#ccc",
    borderRadius: 8,
    padding: 10,
    marginBottom: 14,
    fontSize: 15
  },
  row: {
    flexDirection: "row",
    gap: 10
  },
  column: {
    flex: 1
  },
  summaryBox: {
    backgroundColor: "#eef6ff",
    padding: 12,
    borderRadius: 8,
    marginBottom: 14
  },
  summaryText: {
    fontSize: 14,
    fontWeight: "bold",
    marginBottom: 4
  },
  smsBox: {
    backgroundColor: "#f1f1f1",
    borderWidth: 1,
    borderColor: "#ccc",
    borderRadius: 8,
    padding: 12,
    marginBottom: 14
  },
  smsText: {
    fontSize: 14,
    fontFamily: "monospace"
  },
  resultBox: {
    backgroundColor: "#f7f7f7",
    padding: 14,
    borderRadius: 10,
    marginTop: 14
  },
  resultTitle: {
    fontSize: 18,
    fontWeight: "bold",
    marginBottom: 10
  },
  resultText: {
    fontSize: 13,
    fontFamily: "monospace"
  }
});