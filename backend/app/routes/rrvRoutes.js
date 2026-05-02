const express = require("express");
const multer = require("multer");
const fs = require("fs");
const path = require("path");
const { uploadActa } = require("../controllers/rrvController");

const router = express.Router();

const rawDir = path.join(__dirname, "../../../samples/actas/raw");

if (!fs.existsSync(rawDir)) {
  fs.mkdirSync(rawDir, { recursive: true });
}

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, rawDir);
  },
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname) || ".jpg";
    const filename = `acta-${Date.now()}-${Math.round(Math.random() * 1e9)}${ext}`;
    cb(null, filename);
  }
});

const fileFilter = (req, file, cb) => {
  const allowedTypes = ["image/jpeg", "image/png", "image/jpg", "application/pdf"];

  if (!allowedTypes.includes(file.mimetype)) {
    return cb(new Error("Solo se permiten imágenes JPG, PNG o archivos PDF"));
  }

  cb(null, true);
};

const upload = multer({
  storage,
  fileFilter,
  limits: {
    fileSize: 10 * 1024 * 1024
  }
});

router.post("/upload-acta", upload.single("acta"), uploadActa);

module.exports = router;