import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from .utils import make_qr_file


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class MembershipApplication(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Application Submitted"
        APPROVED_PENDING_PAYMENT = "APPROVED_PENDING_PAYMENT", "Approved - Pending Payment"
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

    full_name = models.CharField(max_length=160)
    father_or_husband_name = models.CharField(max_length=160)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=Gender.choices)
    mobile_number = models.CharField(max_length=15)
    email = models.EmailField()
    residential_address = models.TextField()
    office_address = models.TextField(blank=True)

    shop_name = models.CharField(max_length=180)
    trade_license_number = models.CharField(max_length=80)
    excise_license_number = models.CharField(max_length=80)
    excise_license_type = models.CharField(max_length=80)
    gst_number = models.CharField(max_length=30, blank=True)
    pan_number = models.CharField(max_length=20)
    years_in_business = models.PositiveIntegerField(default=0)
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)

    passport_photo = models.ImageField(upload_to="kyc/photos/")
    aadhaar_card = models.FileField(upload_to="kyc/aadhaar/")
    pan_card = models.FileField(upload_to="kyc/pan/")
    excise_license = models.FileField(upload_to="kyc/excise/")
    trade_license = models.FileField(upload_to="kyc/trade/")
    gst_certificate = models.FileField(upload_to="kyc/gst/", blank=True)
    address_proof = models.FileField(upload_to="kyc/address/")
    signature = models.ImageField(upload_to="kyc/signatures/")
    declaration_accepted = models.BooleanField(default=False)
    digital_signature = models.CharField(max_length=160)

    def __str__(self):
        return f"{self.full_name} - {self.get_status_display()}"

    def approve_application(self, remarks=""):
        self.status = self.Status.APPROVED_PENDING_PAYMENT
        self.remarks = remarks
        self.save(update_fields=["status", "remarks", "updated_at"])

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
        return Member.objects.create_from_application(self.application)


class MemberManager(models.Manager):
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
        if created:
            member.qr_code.save(
                f"{member.membership_number}.png",
                make_qr_file(member.verification_payload, f"{member.membership_number}.png"),
                save=False,
            )
            member.save()
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
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=160)
    message = models.TextField()
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title


class AuditLog(TimeStampedModel):
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=120)
    target = models.CharField(max_length=160)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.action} - {self.target}"
