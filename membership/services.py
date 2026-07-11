from django.conf import settings
from django.core.mail import BadHeaderError
from django.core.mail import send_mail

from .models import Notification


def notify_member(user, title, message, remarks="", send_email=True):
    full_message = message
    if remarks:
        full_message = f"{message}\n\nRemarks: {remarks}"

    Notification.objects.create(
        recipient=user,
        title=title,
        message=full_message,
        channel=Notification.Channel.IN_APP,
    )

    if send_email and user.email:
        email_body = (
            f"Dear {user.get_full_name() or user.username},\n\n"
            f"{message}\n\n"
        )
        if remarks:
            email_body += f"Remarks from admin:\n{remarks}\n\n"
        email_body += (
            f"You can log in to the membership portal for the latest status.\n\n"
            f"Portal: {settings.SITE_URL}\n\n"
            f"Regards,\n{settings.ASSOCIATION_NAME}"
        )
        try:
            send_mail(
                subject=f"{settings.ASSOCIATION_NAME} - {title}",
                message=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except (OSError, TimeoutError, BadHeaderError):
            pass


def notify_member_email_only(user, title, message):
    if not user.email:
        return
    try:
        send_mail(
            subject=f"{settings.ASSOCIATION_NAME} - {title}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except (OSError, TimeoutError, BadHeaderError):
        pass
