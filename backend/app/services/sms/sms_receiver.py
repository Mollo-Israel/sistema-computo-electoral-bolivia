"""
Receives incoming SMS messages from the gateway or webhook.
Responsible: Ferrufino.
TODO (Ferrufino): implement SMS gateway integration (e.g., Twilio or local gateway).
"""


async def receive_sms(raw_payload: dict) -> dict:
    # TODO (Ferrufino): extract numero_telefono and mensaje_raw from gateway payload
    raise NotImplementedError
