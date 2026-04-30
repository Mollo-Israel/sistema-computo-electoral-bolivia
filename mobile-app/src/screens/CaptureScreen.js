import { useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  ScrollView,
  ActivityIndicator,
  Alert,
  Animated,
  Dimensions
} from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as ImagePicker from "expo-image-picker";
import * as Print from "expo-print";
import * as FileSystem from "expo-file-system/legacy";
import { uploadActaPdf } from "../services/rrvApi";

const { width } = Dimensions.get("window");

export default function CaptureScreen() {
  const [imageUri, setImageUri] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [permission, requestPermission] = useCameraPermissions();

  const cameraRef = useRef(null);

  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(28)).current;
  const scanAnim = useRef(new Animated.Value(0)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;

  const scannerHeight = width * 1.2;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 700,
        useNativeDriver: true
      }),
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 700,
        useNativeDriver: true
      })
    ]).start();
  }, [fadeAnim, slideAnim]);

  useEffect(() => {
    if (cameraOpen) {
      const animation = Animated.loop(
        Animated.sequence([
          Animated.timing(scanAnim, {
            toValue: 1,
            duration: 1900,
            useNativeDriver: true
          }),
          Animated.timing(scanAnim, {
            toValue: 0,
            duration: 1900,
            useNativeDriver: true
          })
        ])
      );

      animation.start();

      return () => animation.stop();
    }

    scanAnim.stopAnimation();
    scanAnim.setValue(0);
  }, [cameraOpen, scanAnim]);

  useEffect(() => {
    if (uploading) {
      const animation = Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 1.04,
            duration: 550,
            useNativeDriver: true
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 550,
            useNativeDriver: true
          })
        ])
      );

      animation.start();

      return () => animation.stop();
    }

    pulseAnim.stopAnimation();
    pulseAnim.setValue(1);
  }, [uploading, pulseAnim]);

  const seleccionarImagen = async () => {
    const permissionGallery = await ImagePicker.requestMediaLibraryPermissionsAsync();

    if (!permissionGallery.granted) {
      Alert.alert("Permiso requerido", "Se necesita acceso a la galería.");
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.9
    });

    if (!result.canceled) {
      setImageUri(result.assets[0].uri);
    }
  };

  const abrirCamara = async () => {
    if (!permission?.granted) {
      const response = await requestPermission();

      if (!response.granted) {
        Alert.alert("Permiso requerido", "Se necesita acceso a la cámara.");
        return;
      }
    }

    setCameraOpen(true);
  };

  const tomarFoto = async () => {
    try {
      if (!cameraRef.current) return;

      const photo = await cameraRef.current.takePictureAsync({
        quality: 1,
        skipProcessing: false
      });

      setImageUri(photo.uri);
      setCameraOpen(false);
    } catch (error) {
      Alert.alert("Error", "No se pudo tomar la foto del acta.");
    }
  };

  const crearPdfDesdeImagen = async (uri) => {
    const extension = uri.split(".").pop()?.toLowerCase();
    const mimeType = extension === "png" ? "image/png" : "image/jpeg";

    const base64Image = await FileSystem.readAsStringAsync(uri, {
      encoding: "base64"
    });

    const html = `
      <html>
        <head>
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <style>
            @page {
              size: A4;
              margin: 0;
            }

            html,
            body {
              width: 100%;
              height: 100%;
              margin: 0;
              padding: 0;
              background: white;
            }

            .page {
              width: 100%;
              height: 100%;
              display: flex;
              align-items: center;
              justify-content: center;
              background: white;
            }

            img {
              width: 100%;
              height: auto;
              max-height: 100%;
              object-fit: contain;
            }
          </style>
        </head>

        <body>
          <div class="page">
            <img src="data:${mimeType};base64,${base64Image}" />
          </div>
        </body>
      </html>
    `;

    const pdf = await Print.printToFileAsync({
      html,
      base64: false
    });

    return pdf.uri;
  };

  const enviarActa = async () => {
    if (!imageUri) {
      Alert.alert("Falta una imagen", "Primero toma o selecciona una foto del acta.");
      return;
    }

    try {
      setUploading(true);

      const pdfUri = await crearPdfDesdeImagen(imageUri);

      await uploadActaPdf(pdfUri);

      Alert.alert(
        "Acta enviada",
        "El acta fue convertida a PDF y enviada correctamente al backend."
      );

      setImageUri(null);
    } catch (error) {
      Alert.alert(
        "No se pudo enviar",
        error?.message || "Ocurrió un error al enviar el acta."
      );
    } finally {
      setUploading(false);
    }
  };

  const limpiarSeleccion = () => {
    setImageUri(null);
  };

  const scanLineTranslate = scanAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0, scannerHeight - 80]
  });

  if (cameraOpen) {
    return (
      <View style={styles.cameraContainer}>
        <CameraView
  ref={cameraRef}
  style={styles.camera}
  facing="back"
  zoom={0.1} />

        <View style={styles.cameraTopBar}>
          <TouchableOpacity
            style={styles.cameraCloseButton}
            onPress={() => setCameraOpen(false)}
          >
            <Text style={styles.cameraCloseText}>Cerrar</Text>
          </TouchableOpacity>

          <View style={styles.cameraMiniLogo}>
            <View style={[styles.logoSquare, { backgroundColor: "#e30613" }]} />
            <View style={[styles.logoSquare, { backgroundColor: "#ffd000" }]} />
            <View style={[styles.logoSquare, { backgroundColor: "#07813f" }]} />
          </View>
        </View>

        <View style={styles.scannerArea}>
          <View style={styles.scannerFrame}>
            <View style={[styles.corner, styles.cornerTopLeft]} />
            <View style={[styles.corner, styles.cornerTopRight]} />
            <View style={[styles.corner, styles.cornerBottomLeft]} />
            <View style={[styles.corner, styles.cornerBottomRight]} />

            <View style={styles.documentGuide} />

            <Animated.View
              style={[
                styles.scanLine,
                {
                  transform: [{ translateY: scanLineTranslate }]
                }
              ]}
            />

            <View style={styles.centerHint}>
              <Text style={styles.centerHintText}>Ubica el acta dentro del marco</Text>
            </View>
          </View>
        </View>

        <View style={styles.cameraBottomPanel}>
          <Text style={styles.cameraHelpText}>
            Mantén buena luz, evita sombras y procura que el acta esté completa.
          </Text>

          <TouchableOpacity style={styles.captureButton} onPress={tomarFoto}>
            <View style={styles.captureButtonInner} />
          </TouchableOpacity>

          <Text style={styles.cameraSmallText}>Tocar para capturar</Text>
        </View>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Animated.View
        style={[
          styles.animatedContainer,
          {
            opacity: fadeAnim,
            transform: [{ translateY: slideAnim }]
          }
        ]}
      >
        <View style={styles.hero}>
          <View style={styles.patternCircleOne} />
          <View style={styles.patternCircleTwo} />
          <View style={styles.patternCircleThree} />

          <View style={styles.brandRow}>
            <View style={styles.logoBox}>
              <View style={[styles.logoBlock, { backgroundColor: "#e30613" }]} />
              <View style={[styles.logoBlock, { backgroundColor: "#ffd000" }]} />
              <View style={[styles.logoBlock, { backgroundColor: "#07813f" }]} />
            </View>

            <View style={styles.brandTextBox}>
              <Text style={styles.brandTitle}>OEP Bolivia</Text>
              <Text style={styles.brandSubtitle}>Registro móvil de actas</Text>
            </View>
          </View>

          <Text style={styles.title}>Captura de acta electoral</Text>
          <Text style={styles.subtitle}>
            Toma una foto clara del acta para convertirla a PDF y enviarla al sistema.
          </Text>
        </View>

        <View style={styles.mainCard}>
          <View style={styles.cardHeader}>
            <View>
              <Text style={styles.cardTitle}>Imagen del acta</Text>
              <Text style={styles.cardSubtitle}>
                Puedes usar la cámara con marco escáner o cargar una imagen desde galería.
              </Text>
            </View>

            <View style={styles.statusBadge}>
              <Text style={styles.statusBadgeText}>{imageUri ? "Lista" : "Pendiente"}</Text>
            </View>
          </View>

          <View style={styles.actionsRow}>
            <TouchableOpacity style={styles.cameraButton} onPress={abrirCamara}>
              <Text style={styles.actionIcon}>📷</Text>
              <Text style={styles.actionText}>Abrir cámara</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.galleryButton} onPress={seleccionarImagen}>
              <Text style={styles.actionIcon}>🖼️</Text>
              <Text style={styles.actionText}>Galería</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.previewContainer}>
            {imageUri ? (
              <>
                <Image source={{ uri: imageUri }} style={styles.previewImage} />

                <View style={styles.previewOverlay}>
                  <View style={styles.previewBadge}>
                    <Text style={styles.previewBadgeText}>Acta seleccionada</Text>
                  </View>
                </View>
              </>
            ) : (
              <View style={styles.emptyPreview}>
                <View style={styles.emptyIconCircle}>
                  <Text style={styles.emptyIcon}>📄</Text>
                </View>

                <Text style={styles.emptyTitle}>Sin imagen cargada</Text>
                <Text style={styles.emptyText}>
                  Usa la cámara para escanear el acta o selecciona una imagen existente.
                </Text>

                <View style={styles.emptyScannerMock}>
                  <View style={[styles.mockCorner, styles.mockCornerOne]} />
                  <View style={[styles.mockCorner, styles.mockCornerTwo]} />
                  <View style={[styles.mockCorner, styles.mockCornerThree]} />
                  <View style={[styles.mockCorner, styles.mockCornerFour]} />
                  <View style={styles.mockLine} />
                </View>
              </View>
            )}
          </View>

          <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
            <TouchableOpacity
              style={[
                styles.primaryButton,
                !imageUri && styles.primaryButtonDisabled,
                uploading && styles.primaryButtonLoading
              ]}
              onPress={enviarActa}
              disabled={!imageUri || uploading}
            >
              {uploading ? (
                <View style={styles.loadingRow}>
                  <ActivityIndicator color="#ffffff" />
                  <Text style={styles.primaryButtonText}>Generando PDF y enviando...</Text>
                </View>
              ) : (
                <Text style={styles.primaryButtonText}>Convertir a PDF y enviar</Text>
              )}
            </TouchableOpacity>
          </Animated.View>

          {imageUri && (
            <TouchableOpacity style={styles.removeButton} onPress={limpiarSeleccion}>
              <Text style={styles.removeButtonText}>Quitar imagen</Text>
            </TouchableOpacity>
          )}
        </View>

        <View style={styles.infoPanel}>
          <Text style={styles.infoPanelTitle}>Recomendaciones para la foto</Text>

          <View style={styles.tipItem}>
            <Text style={styles.tipIcon}>☀️</Text>
            <Text style={styles.tipText}>Usa buena iluminación y evita reflejos.</Text>
          </View>

          <View style={styles.tipItem}>
            <Text style={styles.tipIcon}>📐</Text>
            <Text style={styles.tipText}>Coloca el acta completa dentro del marco.</Text>
          </View>

          <View style={styles.tipItem}>
            <Text style={styles.tipIcon}>✋</Text>
            <Text style={styles.tipText}>Mantén el celular quieto al tomar la foto.</Text>
          </View>

          <View style={styles.tipItem}>
            <Text style={styles.tipIcon}>🧾</Text>
            <Text style={styles.tipText}>
              Evita fotos borrosas, cortadas o con sombras fuertes.
            </Text>
          </View>
        </View>
      </Animated.View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    backgroundColor: "#f4f4f1",
    padding: 18,
    paddingTop: 48
  },
  animatedContainer: {
    flex: 1
  },
  hero: {
    backgroundColor: "#ffffff",
    borderRadius: 30,
    padding: 22,
    marginBottom: 18,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: "#eeeeea",
    elevation: 5,
    shadowColor: "#444444",
    shadowOpacity: 0.14,
    shadowRadius: 15,
    shadowOffset: { width: 0, height: 8 }
  },
  patternCircleOne: {
    position: "absolute",
    width: 180,
    height: 180,
    borderRadius: 90,
    backgroundColor: "rgba(255, 208, 0, 0.22)",
    right: -55,
    top: -70
  },
  patternCircleTwo: {
    position: "absolute",
    width: 140,
    height: 140,
    borderRadius: 70,
    backgroundColor: "rgba(7, 129, 63, 0.13)",
    left: -40,
    bottom: -45
  },
  patternCircleThree: {
    position: "absolute",
    width: 90,
    height: 90,
    borderRadius: 45,
    backgroundColor: "rgba(227, 6, 19, 0.11)",
    right: 30,
    bottom: 20
  },
  brandRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 22
  },
  logoBox: {
    flexDirection: "row",
    gap: 6,
    marginRight: 12
  },
  logoBlock: {
    width: 23,
    height: 23,
    borderRadius: 4
  },
  brandTextBox: {
    flex: 1
  },
  brandTitle: {
    fontSize: 20,
    fontWeight: "900",
    color: "#767676"
  },
  brandSubtitle: {
    fontSize: 12,
    fontWeight: "800",
    color: "#9a9a9a",
    letterSpacing: 1
  },
  title: {
    fontSize: 31,
    fontWeight: "900",
    color: "#4d4d4d",
    marginBottom: 8
  },
  subtitle: {
    fontSize: 15,
    color: "#6b6b6b",
    lineHeight: 22,
    marginBottom: 16,
    fontWeight: "600"
  },
  mainCard: {
    backgroundColor: "#ffffff",
    borderRadius: 30,
    padding: 18,
    marginBottom: 18,
    borderWidth: 1,
    borderColor: "#eeeeea",
    elevation: 5,
    shadowColor: "#444444",
    shadowOpacity: 0.12,
    shadowRadius: 15,
    shadowOffset: { width: 0, height: 8 }
  },
  cardHeader: {
    marginBottom: 16
  },
  cardTitle: {
    fontSize: 24,
    fontWeight: "900",
    color: "#4d4d4d",
    marginBottom: 5
  },
  cardSubtitle: {
    fontSize: 14,
    color: "#777777",
    lineHeight: 20,
    fontWeight: "600",
    marginBottom: 10
  },
  statusBadge: {
    alignSelf: "flex-start",
    backgroundColor: "#e8f6ee",
    paddingHorizontal: 13,
    paddingVertical: 7,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "#07813f"
  },
  statusBadgeText: {
    color: "#07813f",
    fontWeight: "900",
    fontSize: 12
  },
  actionsRow: {
    flexDirection: "row",
    gap: 10,
    marginBottom: 15
  },
  cameraButton: {
    flex: 1,
    backgroundColor: "#e30613",
    borderRadius: 20,
    paddingVertical: 15,
    alignItems: "center",
    elevation: 3,
    shadowColor: "#e30613",
    shadowOpacity: 0.25,
    shadowRadius: 9,
    shadowOffset: { width: 0, height: 5 }
  },
  galleryButton: {
    flex: 1,
    backgroundColor: "#07813f",
    borderRadius: 20,
    paddingVertical: 15,
    alignItems: "center",
    elevation: 3,
    shadowColor: "#07813f",
    shadowOpacity: 0.25,
    shadowRadius: 9,
    shadowOffset: { width: 0, height: 5 }
  },
  actionIcon: {
    fontSize: 23,
    marginBottom: 5
  },
  actionText: {
    color: "#ffffff",
    fontSize: 14,
    fontWeight: "900"
  },
  previewContainer: {
    minHeight: 340,
    backgroundColor: "#f7f7f2",
    borderRadius: 24,
    overflow: "hidden",
    marginBottom: 16,
    borderWidth: 1,
    borderColor: "#e2e2dc",
    position: "relative"
  },
  previewImage: {
    width: "100%",
    height: 360,
    resizeMode: "contain",
    backgroundColor: "#f7f7f2"
  },
  previewOverlay: {
    position: "absolute",
    top: 12,
    right: 12
  },
  previewBadge: {
    backgroundColor: "#07813f",
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 999
  },
  previewBadgeText: {
    color: "#ffffff",
    fontSize: 12,
    fontWeight: "900"
  },
  emptyPreview: {
    minHeight: 340,
    alignItems: "center",
    justifyContent: "center",
    padding: 22
  },
  emptyIconCircle: {
    width: 74,
    height: 74,
    borderRadius: 37,
    backgroundColor: "#fff3b0",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 12
  },
  emptyIcon: {
    fontSize: 38
  },
  emptyTitle: {
    fontSize: 21,
    fontWeight: "900",
    color: "#4d4d4d",
    marginBottom: 7
  },
  emptyText: {
    textAlign: "center",
    fontSize: 14,
    color: "#777777",
    lineHeight: 21,
    fontWeight: "600",
    marginBottom: 20
  },
  emptyScannerMock: {
    width: width * 0.58,
    height: 115,
    borderRadius: 15,
    borderWidth: 1,
    borderColor: "#d8d8d2",
    position: "relative",
    overflow: "hidden",
    backgroundColor: "#ffffff"
  },
  mockCorner: {
    position: "absolute",
    width: 26,
    height: 26,
    borderColor: "#ffd000"
  },
  mockCornerOne: {
    top: 8,
    left: 8,
    borderTopWidth: 5,
    borderLeftWidth: 5
  },
  mockCornerTwo: {
    top: 8,
    right: 8,
    borderTopWidth: 5,
    borderRightWidth: 5
  },
  mockCornerThree: {
    bottom: 8,
    left: 8,
    borderBottomWidth: 5,
    borderLeftWidth: 5
  },
  mockCornerFour: {
    bottom: 8,
    right: 8,
    borderBottomWidth: 5,
    borderRightWidth: 5
  },
  mockLine: {
    position: "absolute",
    left: 18,
    right: 18,
    top: 55,
    height: 3,
    backgroundColor: "#e30613",
    borderRadius: 999
  },
  primaryButton: {
    backgroundColor: "#ffd000",
    paddingVertical: 17,
    borderRadius: 20,
    alignItems: "center",
    borderBottomWidth: 5,
    borderBottomColor: "#d3aa00"
  },
  primaryButtonDisabled: {
    backgroundColor: "#b9b9b3",
    borderBottomColor: "#999993"
  },
  primaryButtonLoading: {
    opacity: 0.85
  },
  primaryButtonText: {
    color: "#4d4d4d",
    fontSize: 16,
    fontWeight: "900",
    textAlign: "center"
  },
  loadingRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10
  },
  removeButton: {
    marginTop: 13,
    alignItems: "center"
  },
  removeButtonText: {
    color: "#e30613",
    fontWeight: "900",
    fontSize: 14
  },
  infoPanel: {
    backgroundColor: "#4d4d4d",
    borderRadius: 28,
    padding: 18,
    marginBottom: 35
  },
  infoPanelTitle: {
    color: "#ffffff",
    fontSize: 20,
    fontWeight: "900",
    marginBottom: 13
  },
  tipItem: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(255,255,255,0.08)",
    padding: 12,
    borderRadius: 16,
    marginBottom: 9
  },
  tipIcon: {
    fontSize: 22,
    marginRight: 10
  },
  tipText: {
    flex: 1,
    color: "#f4f4f1",
    fontSize: 14,
    fontWeight: "700",
    lineHeight: 19
  },
  cameraContainer: {
    flex: 1,
    backgroundColor: "#000000",
    position: "relative"
  },
  camera: {
    ...StyleSheet.absoluteFillObject
  },
  cameraTopBar: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    paddingTop: 50,
    paddingHorizontal: 18,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    zIndex: 10
  },
  cameraCloseButton: {
    backgroundColor: "rgba(255,255,255,0.18)",
    paddingHorizontal: 16,
    paddingVertical: 9,
    borderRadius: 999
  },
  cameraCloseText: {
    color: "#ffffff",
    fontWeight: "900",
    fontSize: 14
  },
  cameraMiniLogo: {
    flexDirection: "row",
    gap: 5,
    backgroundColor: "rgba(255,255,255,0.18)",
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 999
  },
  logoSquare: {
    width: 16,
    height: 16,
    borderRadius: 3
  },
  scannerArea: {
    position: "absolute",
    top: 110,
    left: 0,
    right: 0,
    bottom: 170,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 16,
    zIndex: 5
  },
  scannerFrame: {
    width: width * 0.88,
    height: width * 1.2,
    maxHeight: 520,
    borderRadius: 24,
    position: "relative",
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "rgba(255,255,255,0.08)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.15)"
  },
  documentGuide: {
    position: "absolute",
    width: "86%",
    height: "90%",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.14)"
  },
  corner: {
    position: "absolute",
    width: 70,
    height: 70,
    borderColor: "#ffd000"
  },
  cornerTopLeft: {
    top: 0,
    left: 0,
    borderTopWidth: 8,
    borderLeftWidth: 8,
    borderTopLeftRadius: 28
  },
  cornerTopRight: {
    top: 0,
    right: 0,
    borderTopWidth: 8,
    borderRightWidth: 8,
    borderTopRightRadius: 28
  },
  cornerBottomLeft: {
    bottom: 0,
    left: 0,
    borderBottomWidth: 8,
    borderLeftWidth: 8,
    borderBottomLeftRadius: 28
  },
  cornerBottomRight: {
    bottom: 0,
    right: 0,
    borderBottomWidth: 8,
    borderRightWidth: 8,
    borderBottomRightRadius: 28
  },
  scanLine: {
    position: "absolute",
    top: 30,
    left: 26,
    right: 26,
    height: 4,
    borderRadius: 999,
    backgroundColor: "#e30613"
  },
  centerHint: {
    backgroundColor: "rgba(0,0,0,0.42)",
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 999
  },
  centerHintText: {
    color: "#ffffff",
    fontWeight: "900",
    fontSize: 14,
    textAlign: "center"
  },
  cameraBottomPanel: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 30,
    paddingHorizontal: 18,
    alignItems: "center",
    zIndex: 10
  },
  cameraHelpText: {
    color: "#ffffff",
    textAlign: "center",
    fontWeight: "700",
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 18,
    backgroundColor: "rgba(0,0,0,0.38)",
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 18
  },
  captureButton: {
    width: 82,
    height: 82,
    borderRadius: 41,
    borderWidth: 5,
    borderColor: "#ffffff",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 10
  },
  captureButtonInner: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: "#ffd000"
  },
  cameraSmallText: {
    color: "#ffffff",
    fontSize: 13,
    fontWeight: "800"
  }
});