import json
import urllib.error
import urllib.request

from django.conf import settings


def send_whatsapp_message(mobile_number, message):
    if not mobile_number or not settings.WHATSAPP_API_URL or not settings.WHATSAPP_API_TOKEN:
        return False

    payload = {
        "to": mobile_number,
        "from": settings.WHATSAPP_FROM,
        "message": message,
    }
    request = urllib.request.Request(
        settings.WHATSAPP_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10):
            return True
    except (urllib.error.URLError, TimeoutError):
        return False
