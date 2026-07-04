from django.conf import settings


def association_settings(request):
    return {
        "ASSOCIATION_NAME": settings.ASSOCIATION_NAME,
        "MEMBERSHIP_FEE": settings.MEMBERSHIP_FEE,
    }
