import uuid
import logging
import threading
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.mail import BadHeaderError
from django.core.mail import send_mail
from django.db import models
from django.utils import timezone

from .delivery import send_whatsapp_message
from .utils import make_qr_file


logger = logging.getLogger(__name__)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SitePaymentSettings(TimeStampedModel):
    account_name = models.CharField(max_length=160, blank=True)
    bank_name = models.CharField(max_length=160, blank=True)
    account_number = models.CharField(max_length=80, blank=True)
    ifsc = models.CharField(max_length=40, blank=True)
    upi_id = models.CharField(max_length=120, blank=True)
    qr_code = models.ImageField(upload_to="payments/qr/", blank=True)
    membership_fee = models.DecimalField(max_digits=10, decimal_places=2, default=settings.MEMBERSHIP_FEE)

    class Meta:
        verbose_name = "payment setting"
        verbose_name_plural = "payment settings"

    def __str__(self):
        return "Payment settings"

    @classmethod
    def load(cls):
        instance, _created = cls.objects.get_or_create(
            pk=1,
            defaults={
                "account_name": settings.PAYMENT_ACCOUNT_NAME,
                "bank_name": settings.PAYMENT_BANK_NAME,
                "account_number": settings.PAYMENT_ACCOUNT_NUMBER,
                "ifsc": settings.PAYMENT_IFSC,
                "upi_id": settings.PAYMENT_UPI_ID,
                "membership_fee": settings.MEMBERSHIP_FEE,
            },
        )
        return instance


class MembershipApplication(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Application Submitted"
        APPROVED_PENDING_PAYMENT = "APPROVED_PENDING_PAYMENT", "Documents Verified - Pending Payment"
        ADDITIONAL_DOCUMENTS = "ADDITIONAL_DOCUMENTS", "Additional Documents Requested"
        PAYMENT_SUBMITTED = "PAYMENT_SUBMITTED", "Payment Verification Pending"
        PAYMENT_APPROVED = "PAYMENT_APPROVED", "Payment Approved"
        MEMBER_ACTIVE = "MEMBER_ACTIVE", "Member Active"
        REJECTED = "REJECTED", "Rejected"
        ON_HOLD = "ON_HOLD", "On Hold"

    class Gender(models.TextChoices):
        MALE = "MALE", "Male"
        FEMALE = "FEMALE", "Female"
        OTHER = "OTHER", "Other"

    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name="applications")
    status = models.CharField(max_length=40, choices=Status.choices, default=Status.DRAFT)
    remarks = models.TextField(blank=True)
    rejected_documents = models.JSONField(
        blank=True,
        default=list,
        help_text="List of document field keys rejected by admin (e.g. ['excise_license']).",
    )

    full_name = models.CharField(max_length=160)
    father_or_husband_name = models.CharField(max_length=160, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=80, default="Indian")
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices)
    mobile_number = models.CharField(max_length=15)
    whatsapp_number = models.CharField(max_length=15, blank=True)
    residence_phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField()
    residential_address = models.TextField()
    pin_code = models.CharField(max_length=6, blank=True)
    office_address = models.TextField(blank=True)

    entity_type = models.CharField(max_length=80, blank=True)
    licence_category = models.CharField(max_length=40, blank=True)
    style_name = models.CharField(max_length=180, blank=True)
    partner_md_names = models.TextField(blank=True)
    office_phone = models.CharField(max_length=20, blank=True)
    shop_phone = models.CharField(max_length=20, blank=True)
    shop_name = models.CharField(max_length=180)
    trade_license_number = models.CharField(max_length=80, blank=True)
    excise_license_number = models.CharField(max_length=80)
    excise_license_type = models.CharField(max_length=80)
    gst_number = models.CharField(max_length=30, blank=True)
    pan_number = models.CharField(max_length=20, blank=True)
    years_in_business = models.PositiveIntegerField(default=0)
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True, default="West Bengal")

    primary_delegate_name = models.CharField(max_length=160, blank=True)
    primary_delegate_designation = models.CharField(max_length=120, blank=True)
    primary_delegate_address = models.TextField(blank=True)
    alternate_delegate_name = models.CharField(max_length=160, blank=True)
    alternate_delegate_role = models.CharField(max_length=120, blank=True)
    alternate_delegate_address = models.TextField(blank=True)

    passport_photo = models.ImageField(upload_to="kyc/photos/", blank=True)
    primary_delegate_photo = models.ImageField(upload_to="kyc/delegates/primary/", blank=True)
    alternate_delegate_photo = models.ImageField(upload_to="kyc/delegates/alternate/", blank=True)
    aadhaar_card = models.FileField(upload_to="kyc/aadhaar/", blank=True)
    pan_card = models.FileField(upload_to="kyc/pan/", blank=True)
    excise_license = models.FileField(upload_to="kyc/excise/", blank=True)
    trade_license = models.FileField(upload_to="kyc/trade/", blank=True)
    gst_certificate = models.FileField(upload_to="kyc/gst/", blank=True)
    address_proof = models.FileField(upload_to="kyc/address/", blank=True)
    partnership_deed = models.FileField(upload_to="kyc/deed/", blank=True)
    signature = models.ImageField(upload_to="kyc/signatures/", blank=True)
    declaration_accepted = models.BooleanField(default=False)
    digital_signature = models.CharField(max_length=160)

    def __str__(self):
        return f"{self.full_name} - {self.get_status_display()}"

    def approve_application(self, remarks=""):
        self.status = self.Status.APPROVED_PENDING_PAYMENT
        self.remarks = remarks
        self.save(update_fields=["status", "remarks", "updated_at"])
        Member.objects.create_pending_from_application(self)

    def reject_application(self, remarks=""):
        self.status = self.Status.REJECTED
        self.remarks = remarks
        self.save(update_fields=["status", "remarks", "updated_at"])


class PaymentProof(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending Verification"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        REUPLOAD_REQUESTED = "REUPLOAD_REQUESTED", "Re-upload Requested"

    application = models.OneToOneField(MembershipApplication, on_delete=models.CASCADE, related_name="payment")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=settings.MEMBERSHIP_FEE)
    screenshot = models.FileField(upload_to="payments/screenshots/")
    utr_number = models.CharField(max_length=80)
    payment_date = models.DateField()
    bank_name = models.CharField(max_length=120)
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="verified_payments"
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.application.full_name} - {self.utr_number}"

    def approve(self, user):
        self.status = self.Status.APPROVED
        self.verified_by = user
        self.verified_at = timezone.now()
        self.save(update_fields=["status", "verified_by", "verified_at", "updated_at"])
        self.application.status = MembershipApplication.Status.PAYMENT_APPROVED
        self.application.save(update_fields=["status", "updated_at"])
        return self.application


class MemberManager(models.Manager):
    def create_pending_from_application(self, application):
        member, created = self.get_or_create(
            application=application,
            defaults={
                "user": application.applicant,
                "membership_number": self.next_membership_number(),
                "membership_since": timezone.localdate(),
                "valid_till": timezone.localdate() + timedelta(days=365),
                "category": "Regular",
                "is_active": False,
            },
        )
        if not member.qr_code:
            member.qr_code.save(
                f"{member.membership_number}.png",
                make_qr_file(member.verification_payload, f"{member.membership_number}.png"),
                save=False,
            )
            member.save(update_fields=["qr_code", "updated_at"])
        if not created and member.is_active:
            return member
        return member

    def create_from_application(self, application):
        member, created = self.get_or_create(
            application=application,
            defaults={
                "user": application.applicant,
                "membership_number": self.next_membership_number(),
                "membership_since": timezone.localdate(),
                "valid_till": timezone.localdate() + timedelta(days=365),
                "category": "Regular",
            },
        )
        if not member.qr_code:
            member.qr_code.save(
                f"{member.membership_number}.png",
                make_qr_file(member.verification_payload, f"{member.membership_number}.png"),
                save=False,
            )
        member.is_active = True
        member.membership_since = timezone.localdate()
        member.valid_till = timezone.localdate() + timedelta(days=365)
        member.save(update_fields=["qr_code", "is_active", "membership_since", "valid_till", "updated_at"])
        application.status = MembershipApplication.Status.MEMBER_ACTIVE
        application.save(update_fields=["status", "updated_at"])
        profile = application.applicant.profile
        profile.role = "MEMBER"
        profile.save(update_fields=["role"])
        return member

    def next_membership_number(self):
        year = timezone.localdate().year
        prefix = f"LA-{year}-"
        last = self.filter(membership_number__startswith=prefix).order_by("-membership_number").first()
        if not last:
            return f"{prefix}0001"
        next_number = int(last.membership_number.split("-")[-1]) + 1
        return f"{prefix}{next_number:04d}"


class Member(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="member_record")
    application = models.OneToOneField(MembershipApplication, on_delete=models.PROTECT, related_name="member")
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    membership_number = models.CharField(max_length=40, unique=True)
    membership_since = models.DateField()
    category = models.CharField(max_length=80, default="Regular")
    valid_till = models.DateField()
    qr_code = models.ImageField(upload_to="members/qr/", blank=True)
    is_active = models.BooleanField(default=True)

    objects = MemberManager()

    @property
    def verification_payload(self):
        return f"{settings.SITE_URL}/verify/{self.public_id}/"

    def __str__(self):
        return self.membership_number


class Notification(TimeStampedModel):
    class Channel(models.TextChoices):
        IN_APP = "IN_APP", "In-app"
        EMAIL = "EMAIL", "Email"
        WHATSAPP = "WHATSAPP", "WhatsApp"
        EMAIL_WHATSAPP = "EMAIL_WHATSAPP", "Email + WhatsApp"

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=160)
    message = models.TextField()
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.IN_APP)
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title


def notify_staff(title, message):
    staff_users = User.objects.filter(is_staff=True, is_active=True)
    Notification.objects.bulk_create(
        [Notification(recipient=user, title=title, message=message) for user in staff_users]
    )

    if not settings.ADMIN_NOTIFICATION_EMAIL:
        return

    def send_admin_email():
        try:
            send_mail(
                subject=f"{settings.ASSOCIATION_NAME} - {title}",
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_NOTIFICATION_EMAIL],
                fail_silently=True,
            )
        except (OSError, TimeoutError, BadHeaderError):
            logger.exception("Admin notification email failed")

    threading.Thread(target=send_admin_email, daemon=True).start()


class BroadcastMessage(TimeStampedModel):
    class Audience(models.TextChoices):
        ALL_MEMBERS = "ALL_MEMBERS", "All Members"
        DISTRICT = "DISTRICT", "District-wise"
        INDIVIDUAL = "INDIVIDUAL", "Individual Member"
        PENDING_APPLICANTS = "PENDING_APPLICANTS", "Pending Applicants"

    class Channel(models.TextChoices):
        IN_APP = "IN_APP", "In-app"
        EMAIL = "EMAIL", "Email"
        WHATSAPP = "WHATSAPP", "WhatsApp"
        EMAIL_WHATSAPP = "EMAIL_WHATSAPP", "Email + WhatsApp"

    title = models.CharField(max_length=160)
    message = models.TextField()
    audience = models.CharField(max_length=30, choices=Audience.choices)
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.IN_APP)
    district = models.CharField(max_length=100, blank=True)
    recipient = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    recipient_email = models.EmailField(blank=True)
    recipient_mobile = models.CharField(max_length=15, blank=True)
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="sent_broadcasts")
    sent_at = models.DateTimeField(null=True, blank=True)
    sent_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title

    def clean(self):
        errors = {}
        if self.audience == self.Audience.DISTRICT and not self.district:
            errors["district"] = "District is required for district-wise broadcasts."
        if self.audience == self.Audience.INDIVIDUAL and not self.recipient:
            if self.channel in [self.Channel.EMAIL, self.Channel.EMAIL_WHATSAPP] and not self.recipient_email:
                errors["recipient_email"] = "Customer email is required for individual email notifications."
            if self.channel in [self.Channel.WHATSAPP, self.Channel.EMAIL_WHATSAPP] and not self.recipient_mobile:
                errors["recipient_mobile"] = "Customer WhatsApp/mobile is required for individual WhatsApp notifications."
        if errors:
            raise ValidationError(errors)

    def recipients(self):
        if self.audience == self.Audience.ALL_MEMBERS:
            return User.objects.filter(member_record__is_active=True, is_active=True)
        if self.audience == self.Audience.DISTRICT:
            return User.objects.filter(
                member_record__is_active=True,
                member_record__application__district__iexact=self.district,
                is_active=True,
            )
        if self.audience == self.Audience.INDIVIDUAL and self.recipient:
            return User.objects.filter(pk=self.recipient_id, is_active=True)
        if self.audience == self.Audience.PENDING_APPLICANTS:
            return User.objects.filter(
                applications__status__in=[
                    MembershipApplication.Status.SUBMITTED,
                    MembershipApplication.Status.ADDITIONAL_DOCUMENTS,
                    MembershipApplication.Status.APPROVED_PENDING_PAYMENT,
                    MembershipApplication.Status.PAYMENT_SUBMITTED,
                ],
                is_active=True,
            ).distinct()
        return User.objects.none()

    def whatsapp_template_parameters(self, user, mobile_number):
        application = None
        member = getattr(user, "member_record", None)
        if member:
            application = member.application
        if application is None:
            application = user.applications.order_by("-created_at").first()

        customer_name = (
            getattr(application, "shop_name", "")
            or getattr(application, "full_name", "")
            or user.get_full_name()
            or user.username
        )
        reference = (
            getattr(member, "membership_number", "")
            or (f"APP-{application.id:04d}" if application else "")
            or f"CUS-{user.id:04d}"
        )
        detail = f"{mobile_number} | {self.title} - {self.message}"
        return [customer_name, reference, detail]

    def direct_whatsapp_template_parameters(self):
        customer_name = self.recipient_email or self.recipient_mobile or "Customer"
        reference = f"NOTIFY-{self.pk or 'NEW'}"
        detail = f"{self.recipient_mobile} | {self.title} - {self.message}"
        return [customer_name, reference, detail]

    def send(self, actor=None):
        users = list(self.recipients())
        sent_count = len(users)
        Notification.objects.bulk_create(
            [
                Notification(
                    recipient=user,
                    title=self.title,
                    message=self.message,
                    channel=self.channel,
                )
                for user in users
            ]
        )
        if self.channel in [self.Channel.EMAIL, self.Channel.EMAIL_WHATSAPP]:
            for user in users:
                if user.email:
                    send_mail(
                        subject=f"{settings.ASSOCIATION_NAME} - {self.title}",
                        message=self.message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=True,
                    )
            if self.recipient_email:
                send_mail(
                    subject=f"{settings.ASSOCIATION_NAME} - {self.title}",
                    message=self.message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[self.recipient_email],
                    fail_silently=True,
                )
                sent_count += 1
        direct_whatsapp_sent = False
        if self.channel in [self.Channel.WHATSAPP, self.Channel.EMAIL_WHATSAPP]:
            for user in users:
                mobile_number = ""
                if hasattr(user, "profile"):
                    mobile_number = user.profile.mobile_number
                if not mobile_number and hasattr(user, "member_record"):
                    mobile_number = user.member_record.application.mobile_number
                if not mobile_number:
                    latest_application = user.applications.order_by("-created_at").first()
                    mobile_number = latest_application.mobile_number if latest_application else ""
                send_whatsapp_message(
                    mobile_number,
                    self.message,
                    reference=self.title,
                    template_parameters=self.whatsapp_template_parameters(user, mobile_number),
                )
            if self.recipient_mobile and not users:
                send_whatsapp_message(
                    self.recipient_mobile,
                    self.message,
                    reference=self.title,
                    template_parameters=self.direct_whatsapp_template_parameters(),
                )
                direct_whatsapp_sent = True
        if direct_whatsapp_sent and not self.recipient_email:
            sent_count += 1
        self.sent_by = actor
        self.sent_at = timezone.now()
        self.sent_count = sent_count
        self.save(update_fields=["sent_by", "sent_at", "sent_count", "updated_at"])
        return self.sent_count


class AuditLog(TimeStampedModel):
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=120)
    target = models.CharField(max_length=160)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.action} - {self.target}"
