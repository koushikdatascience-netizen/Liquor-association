from .models import SitePaymentSettings


def association_settings(request):
    fee = SitePaymentSettings.load().membership_fee
    return {
        "ASSOCIATION_NAME": SitePaymentSettings.load().account_name or "WB Foreign Liquor and IML Licensees",
        "MEMBERSHIP_FEE": fee,
    }
