from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone

from .models import AuditLog, BroadcastMessage, Member, MembershipApplication, Notification, PaymentProof
from .services import notify_member


def document_review_url(source, obj_id, field_name):
    return reverse("admin_document_review", args=[source, obj_id, field_name])


@admin.action(description="Mark documents verified and unlock payment")
def approve_applications(modeladmin, request, queryset):
    count = 0
    for application in queryset:
        remarks = application.remarks or "Documents verified successfully."
        application.approve_application(remarks)
        notify_member(
            application.applicant,
            title="Documents verified",
            message="Your documents have been verified. Payment details are now available on your dashboard.",
            remarks=remarks,
        )
        AuditLog.objects.create(
            actor=request.user,
            action="Documents verified",
            target=str(application),
        )
        count += 1
    modeladmin.message_user(request, f"Documents verified for {count} application(s).", messages.SUCCESS)


@admin.action(description="Reject selected applications")
def reject_applications(modeladmin, request, queryset):
    count = 0
    for application in queryset:
        remarks = application.remarks or "Documents did not meet verification requirements."
        application.reject_application(remarks)
        notify_member(
            application.applicant,
            title="Documents rejected",
            message="Your submitted documents could not be verified. Please review the remarks and contact the association office if needed.",
            remarks=remarks,
        )
        AuditLog.objects.create(
            actor=request.user,
            action="Documents rejected",
            target=str(application),
            notes=remarks,
        )
        count += 1
    modeladmin.message_user(request, f"{count} application(s) rejected.", messages.WARNING)


@admin.action(description="Request additional documents")
def request_additional_documents(modeladmin, request, queryset):
    count = 0
    for application in queryset:
        remarks = application.remarks or "Please upload clearer or missing documents."
        application.status = MembershipApplication.Status.ADDITIONAL_DOCUMENTS
        application.remarks = remarks
        application.save(update_fields=["status", "remarks", "updated_at"])
        notify_member(
            application.applicant,
            title="Additional documents requested",
            message="Additional documents are required for your membership application.",
            remarks=remarks,
        )
        count += 1
    modeladmin.message_user(request, f"Additional documents requested for {count} application(s).", messages.WARNING)


@admin.action(description="Generate final memberships")
def generate_memberships(modeladmin, request, queryset):
    count = 0
    skipped = 0
    for application in queryset.select_related("applicant"):
        if application.status != MembershipApplication.Status.PAYMENT_APPROVED:
            skipped += 1
            continue
        member = Member.objects.create_from_application(application)
        notify_member(
            application.applicant,
            title="Membership activated",
            message=f"Your membership has been activated successfully. Membership number: {member.membership_number}.",
        )
        AuditLog.objects.create(
            actor=request.user,
            action="Membership generated",
            target=member.membership_number,
        )
        count += 1
    message = f"{count} membership(s) generated."
    if skipped:
        message += f" {skipped} skipped because payment is not approved."
    modeladmin.message_user(request, message, messages.SUCCESS if count else messages.WARNING)


@admin.register(MembershipApplication)
class MembershipApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "shop_name",
        "district",
        "excise_license_number",
        "status_badge",
        "documents_badge",
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
    readonly_fields = ("document_downloads", "photo_preview", "signature_preview", "created_at", "updated_at")
    actions = [approve_applications, reject_applications, request_additional_documents, generate_memberships]
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
                    "document_downloads",
                    "photo_preview",
                    "passport_photo",
                    "aadhaar_card",
                    "pan_card",
                    "excise_license",
                    "trade_license",
                    "gst_certificate",
                    "address_proof",
                    "signature_preview",
                    "signature",
                    "declaration_accepted",
                    "digital_signature",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        tones = {
            MembershipApplication.Status.SUBMITTED: "warning",
            MembershipApplication.Status.APPROVED_PENDING_PAYMENT: "info",
            MembershipApplication.Status.ADDITIONAL_DOCUMENTS: "warning",
            MembershipApplication.Status.PAYMENT_SUBMITTED: "info",
            MembershipApplication.Status.PAYMENT_APPROVED: "success",
            MembershipApplication.Status.MEMBER_ACTIVE: "success",
            MembershipApplication.Status.REJECTED: "danger",
            MembershipApplication.Status.ON_HOLD: "neutral",
        }
        return format_html(
            '<span class="admin-status admin-status--{}">{}</span>',
            tones.get(obj.status, "neutral"),
            obj.get_status_display(),
        )

    @admin.display(description="Documents")
    def documents_badge(self, obj):
        required_files = [
            obj.passport_photo,
            obj.aadhaar_card,
            obj.pan_card,
            obj.excise_license,
            obj.trade_license,
            obj.address_proof,
            obj.signature,
        ]
        uploaded = sum(1 for file in required_files if file)
        tone = "success" if uploaded == len(required_files) else "warning"
        return format_html(
            '<span class="admin-status admin-status--{}">{}/{} uploaded</span>',
            tone,
            uploaded,
            len(required_files),
        )

    @admin.display(description="Document Downloads")
    def document_downloads(self, obj):
        documents = [
            ("Passport Photo", obj.passport_photo),
            ("Aadhaar Card", obj.aadhaar_card),
            ("PAN Card", obj.pan_card),
            ("Excise License", obj.excise_license),
            ("Trade License", obj.trade_license),
            ("GST Certificate", obj.gst_certificate),
            ("Address Proof", obj.address_proof),
            ("Signature", obj.signature),
        ]
        links = []
        for label, file in documents:
            if file:
                links.append(
                    format_html(
                        '<a class="button" href="{}">{}</a>',
                        document_review_url("application", obj.pk, file.field.name),
                        label,
                    )
                )
            else:
                links.append(format_html('<span class="admin-doc-missing">{} missing</span>', label))
        return format_html('<div class="admin-doc-grid">{}</div>', format_html("".join(str(link) for link in links)))

    @admin.display(description="Photo Preview")
    def photo_preview(self, obj):
        if not obj.passport_photo:
            return "-"
        return format_html(
            '<a href="{1}"><img class="admin-doc-preview" src="{0}" alt="Passport photo"></a>',
            obj.passport_photo.url,
            document_review_url("application", obj.pk, "passport_photo"),
        )

    @admin.display(description="Signature Preview")
    def signature_preview(self, obj):
        if not obj.signature:
            return "-"
        return format_html(
            '<a href="{1}"><img class="admin-signature-preview" src="{0}" alt="Signature"></a>',
            obj.signature.url,
            document_review_url("application", obj.pk, "signature"),
        )

    def save_model(self, request, obj, form, change):
        previous_status = None
        if change:
            previous_status = MembershipApplication.objects.filter(pk=obj.pk).values_list("status", flat=True).first()
        super().save_model(request, obj, form, change)
        if not change or previous_status == obj.status:
            return
        if obj.status == MembershipApplication.Status.APPROVED_PENDING_PAYMENT:
            Member.objects.create_pending_from_application(obj)
            title = "Documents verified"
            message = "Your documents have been verified. Payment details are now available on your dashboard."
        elif obj.status == MembershipApplication.Status.ADDITIONAL_DOCUMENTS:
            title = "Additional documents requested"
            message = "Additional documents are required for your membership application."
        elif obj.status == MembershipApplication.Status.REJECTED:
            title = "Documents rejected"
            message = "Your submitted documents could not be verified. Please review the remarks and contact the association office if needed."
        elif obj.status == MembershipApplication.Status.PAYMENT_APPROVED:
            title = "Payment approved"
            message = "Your payment has been approved. Final membership generation is pending."
        elif obj.status == MembershipApplication.Status.MEMBER_ACTIVE:
            member = Member.objects.create_from_application(obj)
            title = "Membership activated"
            message = f"Your membership has been activated successfully. Membership number: {member.membership_number}."
        else:
            return
        notify_member(obj.applicant, title=title, message=message, remarks=obj.remarks)
        AuditLog.objects.create(actor=request.user, action=title, target=str(obj), notes=obj.remarks)


@admin.action(description="Approve selected payments")
def approve_payments(modeladmin, request, queryset):
    count = 0
    for payment in queryset.select_related("application", "application__applicant"):
        payment.approve(request.user)
        notify_member(
            payment.application.applicant,
            title="Payment approved",
            message="Your payment has been approved. Final membership generation is pending.",
            remarks=payment.remarks,
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
    count = 0
    for payment in queryset.select_related("application", "application__applicant"):
        remarks = payment.remarks or "Please upload a clearer screenshot or correct UTR/payment details."
        payment.status = PaymentProof.Status.REUPLOAD_REQUESTED
        payment.verified_by = request.user
        payment.verified_at = timezone.now()
        payment.save(update_fields=["status", "verified_by", "verified_at", "updated_at"])
        payment.application.status = MembershipApplication.Status.PAYMENT_SUBMITTED
        payment.application.remarks = remarks
        payment.application.save(update_fields=["status", "remarks", "updated_at"])
        notify_member(
            payment.application.applicant,
            title="Payment re-upload requested",
            message="Your payment proof requires re-upload before verification can be completed.",
            remarks=remarks,
        )
        AuditLog.objects.create(
            actor=request.user,
            action="Payment re-upload requested",
            target=payment.utr_number,
        )
        count += 1
    modeladmin.message_user(request, f"Re-upload requested for {count} payment(s).", messages.WARNING)


@admin.action(description="Reject selected payments")
def reject_payments(modeladmin, request, queryset):
    count = 0
    for payment in queryset.select_related("application", "application__applicant"):
        remarks = payment.remarks or "Payment proof could not be verified with the submitted details."
        payment.status = PaymentProof.Status.REJECTED
        payment.verified_by = request.user
        payment.verified_at = timezone.now()
        payment.save(update_fields=["status", "verified_by", "verified_at", "updated_at"])
        payment.application.status = MembershipApplication.Status.APPROVED_PENDING_PAYMENT
        payment.application.remarks = remarks
        payment.application.save(update_fields=["status", "remarks", "updated_at"])
        notify_member(
            payment.application.applicant,
            title="Payment failed verification",
            message="Your payment proof could not be verified. Please review the remarks and submit correct payment details again.",
            remarks=remarks,
        )
        AuditLog.objects.create(
            actor=request.user,
            action="Payment rejected",
            target=payment.utr_number,
        )
        count += 1
    modeladmin.message_user(request, f"{count} payment(s) rejected.", messages.WARNING)


@admin.register(PaymentProof)
class PaymentProofAdmin(admin.ModelAdmin):
    list_display = (
        "application",
        "utr_number",
        "amount",
        "bank_name",
        "payment_date",
        "status_badge",
        "payment_file",
        "created_at",
    )
    list_filter = ("status", "payment_date", "created_at")
    search_fields = ("utr_number", "bank_name", "application__full_name", "application__mobile_number")
    readonly_fields = ("screenshot_download", "created_at", "updated_at", "verified_at")
    actions = [approve_payments, request_payment_reupload, reject_payments]

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        tones = {
            PaymentProof.Status.PENDING: "warning",
            PaymentProof.Status.APPROVED: "success",
            PaymentProof.Status.REJECTED: "danger",
            PaymentProof.Status.REUPLOAD_REQUESTED: "info",
        }
        return format_html(
            '<span class="admin-status admin-status--{}">{}</span>',
            tones.get(obj.status, "neutral"),
            obj.get_status_display(),
        )

    @admin.display(description="Slip")
    def payment_file(self, obj):
        if not obj.screenshot:
            return "-"
        return format_html('<a href="{}">Review</a>', document_review_url("payment", obj.pk, "screenshot"))

    @admin.display(description="Payment Screenshot")
    def screenshot_download(self, obj):
        if not obj.screenshot:
            return "-"
        return format_html(
            '<a class="button" href="{}">Review payment screenshot</a>',
            document_review_url("payment", obj.pk, "screenshot"),
        )

    def save_model(self, request, obj, form, change):
        previous_status = None
        if change:
            previous_status = PaymentProof.objects.filter(pk=obj.pk).values_list("status", flat=True).first()
        super().save_model(request, obj, form, change)
        if not change or previous_status == obj.status:
            return
        if obj.status == PaymentProof.Status.APPROVED:
            obj.approve(request.user)
            notify_member(
                obj.application.applicant,
                title="Payment approved",
                message="Your payment has been approved. Final membership generation is pending.",
                remarks=obj.remarks,
            )
            AuditLog.objects.create(actor=request.user, action="Payment approved", target=obj.utr_number)
        elif obj.status == PaymentProof.Status.REJECTED:
            remarks = obj.remarks or "Payment proof could not be verified with the submitted details."
            obj.application.status = MembershipApplication.Status.APPROVED_PENDING_PAYMENT
            obj.application.remarks = remarks
            obj.application.save(update_fields=["status", "remarks", "updated_at"])
            notify_member(
                obj.application.applicant,
                title="Payment failed verification",
                message="Your payment proof could not be verified. Please review the remarks and submit correct payment details again.",
                remarks=remarks,
            )
            AuditLog.objects.create(actor=request.user, action="Payment rejected", target=obj.utr_number, notes=remarks)
        elif obj.status == PaymentProof.Status.REUPLOAD_REQUESTED:
            remarks = obj.remarks or "Please upload a clearer screenshot or correct UTR/payment details."
            obj.application.status = MembershipApplication.Status.PAYMENT_SUBMITTED
            obj.application.remarks = remarks
            obj.application.save(update_fields=["status", "remarks", "updated_at"])
            notify_member(
                obj.application.applicant,
                title="Payment re-upload requested",
                message="Your payment proof requires re-upload before verification can be completed.",
                remarks=remarks,
            )
            AuditLog.objects.create(actor=request.user, action="Payment re-upload requested", target=obj.utr_number, notes=remarks)


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("membership_number", "member_name", "shop_name", "district", "mobile", "category", "valid_till", "active_badge")
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

    @admin.display(ordering="application__full_name")
    def member_name(self, obj):
        return obj.application.full_name

    @admin.display(ordering="application__shop_name")
    def shop_name(self, obj):
        return obj.application.shop_name

    @admin.display(ordering="application__mobile_number")
    def mobile(self, obj):
        return obj.application.mobile_number

    @admin.display(description="Active", boolean=False, ordering="is_active")
    def active_badge(self, obj):
        tone = "success" if obj.is_active else "danger"
        text = "Active" if obj.is_active else "Inactive"
        return format_html('<span class="admin-status admin-status--{}">{}</span>', tone, text)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "title", "channel", "created_at", "read_at")
    search_fields = ("recipient__username", "recipient__email", "title", "message")
    list_filter = ("channel", "created_at", "read_at")


@admin.action(description="Send selected broadcasts")
def send_broadcasts(modeladmin, request, queryset):
    total = 0
    for broadcast in queryset:
        total += broadcast.send(request.user)
        AuditLog.objects.create(
            actor=request.user,
            action="Broadcast sent",
            target=broadcast.title,
            notes=f"{broadcast.get_channel_display()} to {broadcast.get_audience_display()}",
        )
    modeladmin.message_user(request, f"Broadcast sent to {total} recipient(s).", messages.SUCCESS)


@admin.register(BroadcastMessage)
class BroadcastMessageAdmin(admin.ModelAdmin):
    list_display = ("title", "audience", "channel", "district", "recipient", "sent_count", "sent_at", "created_at")
    list_filter = ("audience", "channel", "sent_at", "created_at")
    search_fields = ("title", "message", "district", "recipient__username", "recipient__email")
    readonly_fields = ("sent_by", "sent_at", "sent_count", "created_at", "updated_at")
    autocomplete_fields = ("recipient",)
    fieldsets = (
        (
            "Manual Template",
            {
                "description": "Write the exact message the association wants to send.",
                "fields": ("title", "message"),
            },
        ),
        (
            "Delivery",
            {
                "description": "Choose Email or WhatsApp, then select the required audience.",
                "fields": ("channel", "audience", "district", "recipient"),
            },
        ),
        (
            "Sent Status",
            {
                "fields": ("sent_by", "sent_at", "sent_count", "created_at", "updated_at"),
            },
        ),
    )
    actions = [send_broadcasts]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("actor", "action", "target", "created_at")
    search_fields = ("actor__username", "action", "target", "notes")
    list_filter = ("action", "created_at")
    readonly_fields = ("created_at", "updated_at")
