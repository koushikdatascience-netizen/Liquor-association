from django.contrib import admin, messages
from django.utils import timezone

from .models import AuditLog, Member, MembershipApplication, Notification, PaymentProof


@admin.action(description="Approve selected applications")
def approve_applications(modeladmin, request, queryset):
    count = 0
    for application in queryset:
        application.approve_application("Approved from admin panel.")
        Notification.objects.create(
            recipient=application.applicant,
            title="Application approved",
            message="Your application has been approved. Please complete membership fee payment.",
        )
        AuditLog.objects.create(
            actor=request.user,
            action="Application approved",
            target=str(application),
        )
        count += 1
    modeladmin.message_user(request, f"{count} application(s) approved.", messages.SUCCESS)


@admin.action(description="Reject selected applications")
def reject_applications(modeladmin, request, queryset):
    count = queryset.update(status=MembershipApplication.Status.REJECTED, remarks="Rejected from admin panel.")
    modeladmin.message_user(request, f"{count} application(s) rejected.", messages.WARNING)


@admin.action(description="Request additional documents")
def request_additional_documents(modeladmin, request, queryset):
    count = 0
    for application in queryset:
        application.status = MembershipApplication.Status.ADDITIONAL_DOCUMENTS
        application.remarks = "Please upload clearer or missing documents."
        application.save(update_fields=["status", "remarks", "updated_at"])
        Notification.objects.create(
            recipient=application.applicant,
            title="Additional documents requested",
            message="Please upload clearer or missing documents for your membership application.",
        )
        count += 1
    modeladmin.message_user(request, f"Additional documents requested for {count} application(s).", messages.WARNING)


@admin.register(MembershipApplication)
class MembershipApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "shop_name",
        "district",
        "excise_license_number",
        "status",
        "created_at",
    )
    list_filter = ("status", "district", "state", "excise_license_type", "created_at")
    search_fields = (
        "full_name",
        "mobile_number",
        "email",
        "shop_name",
        "excise_license_number",
        "trade_license_number",
    )
    readonly_fields = ("created_at", "updated_at")
    actions = [approve_applications, reject_applications, request_additional_documents]
    fieldsets = (
        ("Status", {"fields": ("applicant", "status", "remarks")}),
        (
            "Personal Details",
            {
                "fields": (
                    "full_name",
                    "father_or_husband_name",
                    "date_of_birth",
                    "gender",
                    "mobile_number",
                    "email",
                    "residential_address",
                    "office_address",
                )
            },
        ),
        (
            "Business Details",
            {
                "fields": (
                    "shop_name",
                    "trade_license_number",
                    "excise_license_number",
                    "excise_license_type",
                    "gst_number",
                    "pan_number",
                    "years_in_business",
                    "district",
                    "state",
                )
            },
        ),
        (
            "KYC Documents",
            {
                "fields": (
                    "passport_photo",
                    "aadhaar_card",
                    "pan_card",
                    "excise_license",
                    "trade_license",
                    "gst_certificate",
                    "address_proof",
                    "signature",
                    "declaration_accepted",
                    "digital_signature",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.action(description="Approve selected payments and generate memberships")
def approve_payments(modeladmin, request, queryset):
    count = 0
    for payment in queryset.select_related("application", "application__applicant"):
        payment.approve(request.user)
        Notification.objects.create(
            recipient=payment.application.applicant,
            title="Membership activated",
            message="Your payment has been approved and your membership card is ready.",
        )
        AuditLog.objects.create(
            actor=request.user,
            action="Payment approved",
            target=payment.utr_number,
        )
        count += 1
    modeladmin.message_user(request, f"{count} payment(s) approved.", messages.SUCCESS)


@admin.action(description="Request payment re-upload")
def request_payment_reupload(modeladmin, request, queryset):
    count = queryset.update(status=PaymentProof.Status.REUPLOAD_REQUESTED, verified_by=request.user, verified_at=timezone.now())
    modeladmin.message_user(request, f"Re-upload requested for {count} payment(s).", messages.WARNING)


@admin.register(PaymentProof)
class PaymentProofAdmin(admin.ModelAdmin):
    list_display = ("application", "utr_number", "amount", "bank_name", "payment_date", "status", "created_at")
    list_filter = ("status", "payment_date", "created_at")
    search_fields = ("utr_number", "bank_name", "application__full_name", "application__mobile_number")
    readonly_fields = ("created_at", "updated_at", "verified_at")
    actions = [approve_payments, request_payment_reupload]


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("membership_number", "application", "category", "district", "valid_till", "is_active")
    list_filter = ("is_active", "category", "valid_till", "application__district")
    search_fields = (
        "membership_number",
        "application__full_name",
        "application__shop_name",
        "application__mobile_number",
        "application__excise_license_number",
    )
    readonly_fields = ("public_id", "qr_code", "created_at", "updated_at")

    @admin.display(ordering="application__district")
    def district(self, obj):
        return obj.application.district


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "title", "created_at", "read_at")
    search_fields = ("recipient__username", "recipient__email", "title", "message")
    list_filter = ("created_at", "read_at")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("actor", "action", "target", "created_at")
    search_fields = ("actor__username", "action", "target", "notes")
    list_filter = ("action", "created_at")
    readonly_fields = ("created_at", "updated_at")
