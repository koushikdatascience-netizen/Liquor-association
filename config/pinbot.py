import json
import urllib.error
import urllib.request

from django.conf import settings


def normalize_whatsapp_number(value):
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) == 10:
        return f"91{digits}"
    if len(digits) == 11 and digits.startswith("0"):
        return f"91{digits[1:]}"
    return digits


def send_template_message(to, template_name, body_parameters):
    phone_number = normalize_whatsapp_number(to)
    if not phone_number or not template_name or not settings.PINBOT_API_KEY or not settings.PINBOT_PHONE_NUMBER_ID:
        return False

    payload = {
        "to": phone_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": settings.PINBOT_LANGUAGE_CODE},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": str(value)} for value in body_parameters],
                }
            ],
        },
        "messaging_product": "whatsapp",
    }
    url = f"{settings.PINBOT_API_BASE_URL.rstrip('/')}/{settings.PINBOT_PHONE_NUMBER_ID}/messages"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "apikey": settings.PINBOT_API_KEY,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.PINBOT_TIMEOUT_SECONDS) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError):
        return False
