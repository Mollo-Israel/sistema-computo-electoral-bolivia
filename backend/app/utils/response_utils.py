"""
Standard API response wrappers for consistency across all endpoints.
TODO: adopt these helpers in all route handlers.
"""


def success_response(data, message: str = "OK") -> dict:
    return {"status": "success", "message": message, "data": data}


def error_response(message: str, errors: list = None) -> dict:
    return {"status": "error", "message": message, "errors": errors or []}
