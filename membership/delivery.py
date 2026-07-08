from django.conf import settings

from config.pinbot import send_template_message


def send_whatsapp_message(mobile_number, message, reference="Notification"):
    if not mobile_number or not settings.WHATSAPP_NOTIFICATIONS_ENABLED:
        return False

    return send_template_message(
        mobile_number,
        settings.PINBOT_NOTIFICATION_TEMPLATE_NAME,
        [settings.ASSOCIATION_NAME, reference, message],
    )
