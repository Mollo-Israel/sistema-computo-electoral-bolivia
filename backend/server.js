const express = require("express");
const cors = require("cors");
const rrvRoutes = require("./app/routes/rrvRoutes");
const smsRoutes = require("./app/routes/smsRoutes");

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.get("/", (req, res) => {
  res.json({
    success: true,
    message: "Backend Sistema de Cómputo Electoral activo"
  });
});

app.use("/api/rrv", rrvRoutes);
app.use("/api/sms", smsRoutes);

app.listen(PORT, "0.0.0.0", () => {
  console.log(`Servidor backend activo en puerto ${PORT}`);
});