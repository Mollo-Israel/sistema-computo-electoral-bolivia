const express = require("express");
const {
  receiveSms,
  receiveRealSmsWebhook
} = require("../controllers/smsController");

const router = express.Router();

router.post("/receive", receiveSms);
router.post("/webhook", receiveRealSmsWebhook);

module.exports = router;