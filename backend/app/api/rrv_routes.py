"""
RRV API routes: receive acts from OCR, SMS, and mobile app.
Responsible: MOLLO (OCR), Ferrufino (SMS/mobile), Sanabria (validation).
TODO: implement endpoints once services are ready.
"""
from fastapi import APIRouter

router = APIRouter()

# TODO (MOLLO): POST /acta/ocr — receive OCR-processed act (PDF/image)
# TODO (Ferrufino): POST /acta/sms — receive SMS act
# TODO (Ferrufino): POST /acta/mobile — receive act from mobile app
# TODO (Sanabria): GET /actas — list RRV acts with filters
# TODO (Sanabria): GET /acta/{mesa_codigo} — get act by mesa_codigo
