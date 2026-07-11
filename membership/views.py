from io import BytesIO
import csv

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from cloudinary.exceptions import BadRequest as CloudinaryBadRequest
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .forms import MembershipApplicationForm, PaymentProofForm, SitePaymentSettingsForm
from .models import AuditLog, BroadcastMessage, Member, MembershipApplication, PaymentProof, SitePaymentSettings, notify_staff
from .services import notify_member


APPLICATION_DOCUMENT_FIELDS = (
    "excise_license",
    "passport_photo",
    "primary_delegate_photo",
    "alternate_delegate_photo",
    "pan_card",
    "aadhaar_card",
    "partnership_deed",
    "gst_certificate",
    "address_proof",
)

DOCUMENT_REVIEW_STATUSES = {
    MembershipApplication.Status.SUBMITTED,
    "PENDING",
    "PENDING_REVIEW",
    "APPLICATION_PENDING",
    "DOCUMENTS_SUBMITTED",
    "DOCUMENTS_REUPLOADED",
}

PAYMENT_WAITING_STATUSES = {
    MembershipApplication.Status.APPROVED_PENDING_PAYMENT,
    "DOCUMENTS_APPROVED",
    "APPROVED",
    "PENDING_PAYMENT",
    "PAYMENT_PENDING",
}

PAYMENT_REVIEW_STATUSES = {
    MembershipApplication.Status.PAYMENT_SUBMITTED,
    "PAYMENT_UPLOADED",
    "PAYMENT_PENDING_VERIFICATION",
    "PAYMENT_VERIFICATION_PENDING",
}

PAYMENT_APPROVED_STATUSES = {
    MembershipApplication.Status.PAYMENT_APPROVED,
    "PAYMENT_VERIFIED",
}

MEMBERSHIP_ACTIVE_STATUSES = {
    MembershipApplication.Status.MEMBER_ACTIVE,
    "ACTIVE",
    "MEMBERSHIP_ACTIVE",
}

REJECTED_APPLICATION_STATUSES = {
    MembershipApplication.Status.REJECTED,
    "REJECTED_APPLICATION",
}

PENDING_PAYMENT_PROOF_STATUSES = {
    PaymentProof.Status.PENDING,
    "PAYMENT_UPLOADED",
    "PAYMENT_PENDING",
    "PAYMENT_VERIFICATION_PENDING",
}

REUPLOAD_PAYMENT_PROOF_STATUSES = {
    PaymentProof.Status.REUPLOAD_REQUESTED,
    "PAYMENT_REUPLOAD_REQUESTED",
}


def is_document_review_status(status):
    """Return True only when admins should review KYC/application documents."""
    return status in DOCUMENT_REVIEW_STATUSES


def storage_url(file):
    if not file:
        return ""
    try:
        url = file.url
    except (ValueError, OSError):
        return ""
    return str(url)


def file_kind(file):
    """Return 'image', 'pdf', or 'other' for a FieldFile (Cloudinary-aware).

    Cloudinary stores files without a file extension and may serve PDFs from an
    ``/image/upload/`` delivery path, so we cannot rely on the URL alone. We
    inspect the file's magic bytes (``%PDF`` for PDFs, image signatures for
    images) to determine the real type. Falls back to the URL/extension when the
    file cannot be read.
    """
    if not file:
        return "other"

    try:
        file.open("rb")
        head = file.read(8)
        file.close()
    except (OSError, ValueError):
        head = b""

    if head.startswith(b"%PDF"):
        return "pdf"
    if head.startswith(b"\xff\xd8\xff") or head.startswith(b"\x89PNG") or head.startswith(b"GIF8") or head.startswith(b"RIFF"):
        return "image"

    # Fallback: use the URL / filename extension.
    name = (getattr(file, "name", "") or "").lower()
    url = storage_url(file)
    if url:
        url_l = url.lower()
        if "/raw/upload/" in url_l or url_l.endswith(".pdf"):
            return "pdf"
        if "/image/upload/" in url_l or name.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
            return "image"
    if name.endswith(".pdf"):
        return "pdf"
    if name.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
        return "image"
    return "other"


def preview_url(file):
    """URL suitable for <img>/<iframe> preview.

    Cloudinary serves raw PDFs without a file extension, which browsers will not
    render as a PDF inside an iframe. Appending ``.pdf`` forces the correct
    content type and lets the browser display the document.
    """
    url = storage_url(file)
    if not url or file_kind(file) != "pdf":
        return url
    if not url.lower().endswith(".pdf"):
        url = f"{url}.pdf"
    return url


def document_content_type(file, kind):
    if kind == "pdf":
        return "application/pdf"
    if kind == "image":
        name = (getattr(file, "name", "") or "").lower()
        if name.endswith(".png"):
            return "image/png"
        if name.endswith(".gif"):
            return "image/gif"
        if name.endswith(".webp"):
            return "image/webp"
        return "image/jpeg"
    return "application/octet-stream"


def portal_url(path):
    return f"{settings.SITE_URL.rstrip('/')}{path}"


def payment_settings_context():
    payment_settings = SitePaymentSettings.load()
    return {
        "upi_id": payment_settings.upi_id,
        "bank_name": payment_settings.bank_name,
        "account_name": payment_settings.account_name,
        "account_number": payment_settings.account_number,
        "ifsc": payment_settings.ifsc,
        "qr_url": storage_url(payment_settings.qr_code),
        "membership_fee": payment_settings.membership_fee,
    }


def membership_activation_message(member):
    return (
        "Your payment has been approved and your final membership is active.\n\n"
        f"Membership number: {member.membership_number}\n"
        f"Membership category: {member.category}\n"
        f"Valid from: {member.membership_since:%d %b %Y}\n"
        f"Valid till: {member.valid_till:%d %b %Y}\n\n"
        f"Digital card: {portal_url(reverse('membership_card'))}\n"
        f"Card PDF: {portal_url(reverse('membership_card_pdf'))}\n"
        f"Certificate: {portal_url(reverse('membership_certificate'))}"
    )


def open_storage_image(file):
    file.open("rb")
    try:
        image = Image.open(file)
        image.load()
        return image
    finally:
        file.close()


def home(request):
    if request.user.is_authenticated:
        return redirect("member_dashboard")
    return render(request, "membership/home.html")


@login_required
def member_dashboard(request):
    applications = MembershipApplication.objects.filter(applicant=request.user).order_by("-created_at")
    application = applications.first()
    member = Member.objects.filter(user=request.user).select_related("application").first()
    notifications = request.user.notifications.order_by("-created_at")[:10]
    payment = getattr(application, "payment", None) if application else None
    can_upload_payment = bool(
        application
        and (
            application.status == MembershipApplication.Status.APPROVED_PENDING_PAYMENT
            or (
                application.status == MembershipApplication.Status.PAYMENT_SUBMITTED
                and payment
                and payment.status == PaymentProof.Status.REUPLOAD_REQUESTED
            )
        )
    )
    # Prepare additional context for simplified landing
    passport_photo_url = storage_url(application.passport_photo) if application else ""
    qr_code_url = storage_url(member.qr_code) if member else ""
    card_locked = not (member and member.is_active)
    # Status banner
    if not application:
        status_message = "No application submitted."
        banner_class = "warn"
        banner_icon = "bi bi-file-earmark"
    else:
        status = application.status
        if status == MembershipApplication.Status.SUBMITTED or status in ("PENDING", "PENDING_REVIEW", "APPLICATION_PENDING", "DOCUMENTS_SUBMITTED", "DOCUMENTS_REUPLOADED"):
            status_message = "Your application is submitted and pending document approval."
            banner_class = "warn"
            banner_icon = "bi bi-hourglass-split"
        elif status == MembershipApplication.Status.APPROVED_PENDING_PAYMENT:
            status_message = "Documents verified. Please complete your payment."
            banner_class = "ok"
            banner_icon = "bi bi-credit-card"
        elif status == MembershipApplication.Status.PAYMENT_SUBMITTED:
            status_message = "Payment submitted. Waiting for verification."
            banner_class = "warn"
            banner_icon = "bi bi-hourglass"
        elif status == MembershipApplication.Status.MEMBER_ACTIVE:
            status_message = "Your membership is active."
            banner_class = "ok"
            banner_icon = "bi bi-check-circle"
        elif status == MembershipApplication.Status.REJECTED:
            status_message = f"Application rejected. {application.remarks or ''}"
            banner_class = "warn"
            banner_icon = "bi bi-x-circle"
        elif status == MembershipApplication.Status.ADDITIONAL_DOCUMENTS:
            status_message = f"Additional documents requested. {application.remarks or ''}"
            banner_class = "warn"
            banner_icon = "bi bi-file-earmark"
        else:
            status_message = "Status unknown."
            banner_class = "warn"
            banner_icon = "bi bi-question-circle"
    payment_unlocked = bool(
        application
        and (
            application.status == MembershipApplication.Status.APPROVED_PENDING_PAYMENT
            or payment
        )
    )
    return render(
        request,
        "membership/dashboard.html",
        {
            "application": application,
            "applications": applications,
            "member": member,
            "notifications": notifications,
            "payment": payment,
            "can_upload_payment": can_upload_payment,
            "payment_settings": payment_settings_context(),
            "passport_photo_url": passport_photo_url,
            "qr_code_url": qr_code_url,
            "card_locked": card_locked,
            "status_message": status_message,
            "banner_class": banner_class,
            "banner_icon": banner_icon,
            "payment_unlocked": payment_unlocked,
        },
    )


def member_portal_context(request):
    applications = MembershipApplication.objects.filter(applicant=request.user).order_by("-created_at")
    application = applications.first()
    member = Member.objects.filter(user=request.user).select_related("application").first()
    payment = getattr(application, "payment", None) if application else None
    notifications = request.user.notifications.order_by("-created_at")
    return {
        "application": application,
        "applications": applications,
        "member": member,
        "notifications": notifications,
        "payment": payment,
        "payment_settings": payment_settings_context(),
    }


@login_required
def member_profile(request):
    context = member_portal_context(request)
    application = context.get("application")
    context["documents"] = application_documents(application) if application else []
    return render(request, "membership/profile.html", context)


@login_required
def member_notifications(request):
    return render(request, "membership/notifications.html", member_portal_context(request))


@login_required
def membership_status(request):
    return render(request, "membership/status.html", member_portal_context(request))


@login_required
def application_create(request):
    profile = request.user.profile
    if not settings.ACCOUNT_REQUIRE_OTP_VERIFICATION and (
        not profile.email_verified or not profile.mobile_verified
    ):
        profile.email_verified = True
        profile.mobile_verified = True
        profile.save(update_fields=["email_verified", "mobile_verified"])

    if (
        settings.ACCOUNT_REQUIRE_OTP_VERIFICATION
        and not request.user.is_staff
        and not profile.email_verified
    ):
        messages.error(request, "Please verify your email OTP before submitting the application.")
        return redirect("verify_registration_otp")

    # Active (non-draft) applications block a new one; drafts are resumable.
    existing = MembershipApplication.objects.filter(applicant=request.user).exclude(
        status__in=[
            MembershipApplication.Status.REJECTED,
            MembershipApplication.Status.DRAFT,
        ]
    ).first()
    draft = MembershipApplication.objects.filter(
        applicant=request.user, status=MembershipApplication.Status.DRAFT
    ).first()
    can_update_documents = existing and existing.status == MembershipApplication.Status.ADDITIONAL_DOCUMENTS
    if existing and not can_update_documents:
        messages.info(request, "You already have an active application.")
        return redirect("member_dashboard")

    instance = draft or (existing if can_update_documents else None)

    if request.method == "POST":
        # ---- Save draft (lenient, no strict validation) ----
        if request.POST.get("save_draft"):
            form = MembershipApplicationForm(request.POST, request.FILES, instance=instance)
            form.is_valid()  # populate cleaned_data; ignore errors for draft
            application = form.save(commit=False)
            application.applicant = request.user
            application.status = MembershipApplication.Status.DRAFT
            for field in [
                "full_name",
                "gender",
                "residential_address",
                "pin_code",
                "email",
                "excise_license_number",
                "primary_delegate_name",
            ]:
                if not getattr(application, field, ""):
                    setattr(application, field, "(draft)")
            application.save()
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"ok": True})
            messages.success(request, "Draft saved.")
            return redirect("application_create")

        # ---- Submit application ----
        form = MembershipApplicationForm(request.POST, request.FILES, instance=instance)
        submitted_document_fields = set(request.FILES).intersection(APPLICATION_DOCUMENT_FIELDS)
        existing_document_fields = {
            field_name
            for field_name in APPLICATION_DOCUMENT_FIELDS
            if can_update_documents and existing and getattr(existing, field_name)
        }
        has_document_uploads = bool(submitted_document_fields or existing_document_fields)
        if form.is_valid() and has_document_uploads:
            application = form.save(commit=False)
            application.applicant = request.user
            application.mobile_number = application.whatsapp_number or profile.mobile_number
            application.shop_name = application.style_name or application.full_name
            application.excise_license_type = application.licence_category
            application.district = application.district or ""
            application.state = application.state or "West Bengal"
            application.digital_signature = application.digital_signature or application.full_name
            application.status = MembershipApplication.Status.SUBMITTED
            application.remarks = ""
            try:
                application.save()
            except CloudinaryBadRequest:
                form.add_error(None, "One of the uploaded image files is invalid. Please upload JPG, PNG or WebP images and submit again.")
            else:
                notify_staff(
                    "New membership application" if not can_update_documents else "Documents resubmitted",
                    f"{application.full_name} / {application.shop_name} is ready for document verification.",
                )
                messages.success(request, "Application submitted successfully." if not can_update_documents else "Documents updated and resubmitted for admin review.")
                return redirect("member_dashboard")
        if form.is_valid() and not has_document_uploads:
            form.add_error(None, "Please upload at least one application document before submitting.")
        messages.error(request, "Application was not submitted. Please fix the highlighted fields and submit again.")
    else:
        form = MembershipApplicationForm(
            instance=instance,
            initial={
                "email": request.user.email,
                "mobile_number": profile.mobile_number,
                "whatsapp_number": profile.mobile_number,
                "full_name": request.user.get_full_name(),
                "nationality": "Indian",
            } if not instance else {},
        )
    return render(
        request,
        "membership/application_form.html",
        {
            "form": form,
            "is_update": can_update_documents,
            "has_form_errors": form.is_bound and form.errors,
        },
    )


@login_required
def payment_upload(request, application_id):
    # Check if user has any application at all
    any_application = MembershipApplication.objects.filter(applicant=request.user).first()
    if not any_application:
        messages.error(request, "Please submit your membership application before opening payment.")
        return redirect("member_dashboard")

    application = MembershipApplication.objects.filter(id=application_id, applicant=request.user).first()
    if application is None:
        fallback_application = MembershipApplication.objects.filter(applicant=request.user).order_by("-created_at").first()
        if fallback_application:
            messages.info(request, "Opening the payment page for your latest application.")
            return redirect("payment_upload", application_id=fallback_application.id)
        messages.error(request, "Please submit your membership application before opening payment.")
        return redirect("member_dashboard")

    # If application exists but is not in a state where payment should be shown
    if application.status in [
        MembershipApplication.Status.DRAFT,
        MembershipApplication.Status.SUBMITTED,
        MembershipApplication.Status.ADDITIONAL_DOCUMENTS,
        MembershipApplication.Status.REJECTED
    ]:
        instance = getattr(application, "payment", None)
        payment_unlocked = False
        can_submit_payment = False
        show_payment_form = False
        return render(
            request,
            "membership/payment_form.html",
            {
                "form": None,
                "application": application,
                "payment": instance,
                "can_submit_payment": can_submit_payment,
                "show_payment_form": show_payment_form,
                "payment_unlocked": payment_unlocked,
                "payment_settings": payment_settings_context(),
            },
        )

    instance = getattr(application, "payment", None)
    can_submit_payment = (
        application.status == MembershipApplication.Status.APPROVED_PENDING_PAYMENT
        or (
            application.status == MembershipApplication.Status.PAYMENT_SUBMITTED
            and instance
            and instance.status == PaymentProof.Status.REUPLOAD_REQUESTED
        )
    )
    # Only show payment form if documents are approved and payment is not already submitted
    show_payment_form = can_submit_payment and not (
        application.status == MembershipApplication.Status.PAYMENT_SUBMITTED
        and instance
        and instance.status == PaymentProof.Status.PENDING
    )
    payment_unlocked = application.status in [
        MembershipApplication.Status.APPROVED_PENDING_PAYMENT,
        MembershipApplication.Status.PAYMENT_SUBMITTED,
        MembershipApplication.Status.PAYMENT_APPROVED,
        MembershipApplication.Status.MEMBER_ACTIVE,
    ]
    if request.method == "POST" and not can_submit_payment:
        messages.error(request, "Payment upload is available only after document approval.")
        return redirect("payment_upload", application_id=application.id)
    if (
        request.method == "POST"
        and application.status == MembershipApplication.Status.PAYMENT_SUBMITTED
        and (not instance or instance.status != PaymentProof.Status.REUPLOAD_REQUESTED)
    ):
        messages.info(request, "Your payment proof is already waiting for admin verification.")
        return redirect("payment_upload", application_id=application.id)
    if request.method == "POST":
        form = PaymentProofForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.application = application
            payment.amount = SitePaymentSettings.load().membership_fee
            payment.status = payment.Status.PENDING
            payment.save()
            application.status = MembershipApplication.Status.PAYMENT_SUBMITTED
            application.save(update_fields=["status", "updated_at"])
            notify_staff(
                "Payment submitted for verification",
                f"{application.full_name} submitted payment proof. UTR: {payment.utr_number}.",
            )
            messages.success(request, "Payment proof submitted for admin verification.")
            return redirect("member_dashboard")
    else:
        form = PaymentProofForm(instance=instance) if can_submit_payment else None
    return render(
        request,
        "membership/payment_form.html",
        {
            "form": form,
            "application": application,
            "payment": instance,
            "can_submit_payment": can_submit_payment,
            "show_payment_form": show_payment_form,
            "payment_unlocked": payment_unlocked,
            "payment_settings": payment_settings_context(),
        },
    )


def verify_member(request, public_id):
    member = get_object_or_404(Member.objects.select_related("application"), public_id=public_id, is_active=True)
    return render(request, "membership/verify_member.html", {"member": member})


@login_required
def card(request):
    # Check if user has any application at all
    any_application = MembershipApplication.objects.filter(applicant=request.user).first()
    if not any_application:
        messages.error(request, "Please submit your membership application to view your membership card.")
        return redirect("member_dashboard")

    # Check if user has an active membership
    member = Member.objects.filter(user=request.user, is_active=True).select_related("application").first()

    # If no active member, check if there's an application in progress
    if not member:
        application = MembershipApplication.objects.filter(applicant=request.user).order_by("-created_at").first()
        if not application:
            messages.error(request, "Please submit your membership application to view your membership card.")
            return redirect("member_dashboard")

        # Show waiting message based on application status
        if application.status in [
            MembershipApplication.Status.DRAFT,
            MembershipApplication.Status.SUBMITTED,
            MembershipApplication.Status.ADDITIONAL_DOCUMENTS,
            MembershipApplication.Status.REJECTED
        ]:
            return render(
                request,
                "membership/card.html",
                {
                    "member": None,
                    "application": application,
                    "locked": True,
                },
            )

    # If we get here, we have an active member
    application = member.application
    # Card is locked if member is not active (payment not completed)
    card_locked = not member.is_active
    return render(
        request,
        "membership/card.html",
        {
            "member": member,
            "passport_photo_url": storage_url(application.passport_photo),
            "qr_code_url": storage_url(member.qr_code),
            "locked": card_locked,
        },
    )


@login_required
def card_pdf(request):
    member = Member.objects.filter(user=request.user, is_active=True).select_related("application").first()
    if not member:
        messages.error(request, "Your membership card is not available yet. Please complete your application and payment process.")
        return redirect("member_dashboard")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{member.membership_number}.pdf"'

    page = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 72
    application = member.application

    page.setFont("Helvetica-Bold", 18)
    page.drawString(72, y, settings.ASSOCIATION_NAME)
    page.setFont("Helvetica", 12)
    page.drawString(72, y - 28, "Digital Membership Card")
    page.line(72, y - 42, width - 72, y - 42)

    rows = [
        ("Member Name", application.full_name),
        ("Membership Number", member.membership_number),
        ("Shop Name", application.shop_name),
        ("District", application.district),
        ("Mobile", application.mobile_number),
        ("Category", member.category),
        ("Membership Since", member.membership_since.strftime("%d %b %Y")),
        ("Valid Till", member.valid_till.strftime("%d %b %Y")),
        ("Verification", member.verification_payload),
    ]
    y -= 78
    for label, value in rows:
        page.setFont("Helvetica-Bold", 11)
        page.drawString(72, y, f"{label}:")
        page.setFont("Helvetica", 11)
        page.drawString(220, y, str(value))
        y -= 24

    page.setFont("Helvetica-Bold", 11)
    page.drawString(72, 96, f"Digitally signed by {settings.ASSOCIATION_NAME}")
    page.showPage()
    page.save()
    return response


@login_required
def card_image(request):
    member = Member.objects.filter(user=request.user, is_active=True).select_related("application").first()
    if not member:
        messages.error(request, "Your membership card is not available yet. Please complete your application and payment process.")
        return redirect("member_dashboard")
    return render_member_card_image(member)


@staff_member_required
def staff_member_card_pdf(request, pk):
    member = get_object_or_404(Member.objects.select_related("application"), pk=pk)
    return render_member_card_pdf(member)


@staff_member_required
def staff_member_card_image(request, pk):
    member = get_object_or_404(Member.objects.select_related("application"), pk=pk)
    return render_member_card_image(member)


def render_member_card_pdf(member):
    application = member.application
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{member.membership_number}.pdf"'

    page = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 72

    page.setFont("Helvetica-Bold", 18)
    page.drawString(72, y, settings.ASSOCIATION_NAME)
    page.setFont("Helvetica", 12)
    page.drawString(72, y - 28, "Digital Membership Card")
    page.line(72, y - 42, width - 72, y - 42)

    rows = [
        ("Member Name", application.full_name),
        ("Membership Number", member.membership_number),
        ("Shop Name", application.shop_name),
        ("District", application.district),
        ("Mobile", application.mobile_number),
        ("Category", member.category),
        ("Membership Since", member.membership_since.strftime("%d %b %Y")),
        ("Valid Till", member.valid_till.strftime("%d %b %Y")),
        ("Verification", member.verification_payload),
    ]
    y -= 78
    for label, value in rows:
        page.setFont("Helvetica-Bold", 11)
        page.drawString(72, y, f"{label}:")
        page.setFont("Helvetica", 11)
        page.drawString(220, y, str(value))
        y -= 24

    page.setFont("Helvetica-Bold", 11)
    page.drawString(72, 96, f"Digitally signed by {settings.ASSOCIATION_NAME}")
    page.showPage()
    page.save()
    return response


def render_member_card_image(member):
    application = member.application
    image = Image.new("RGB", (900, 540), "#ffffff")
    draw = ImageDraw.Draw(image)
    font_large = ImageFont.load_default()
    font_regular = ImageFont.load_default()

    draw.rectangle((0, 0, 900, 120), fill="#123829")
    draw.text((36, 30), settings.ASSOCIATION_NAME, fill="#ffffff", font=font_large)
    draw.text((36, 68), "Digital Membership Card", fill="#f6d7a3", font=font_regular)

    if application.passport_photo:
        try:
            photo = open_storage_image(application.passport_photo).convert("RGB").resize((130, 160))
            image.paste(photo, (36, 156))
        except (FileNotFoundError, OSError, ValueError):
            draw.rectangle((36, 156, 166, 316), outline="#d6e1df", width=2)

    rows = [
        ("Member Name", application.full_name),
        ("Membership No.", member.membership_number),
        ("Shop Name", application.shop_name),
        ("District", application.district),
        ("Mobile", application.mobile_number),
        ("Valid Till", member.valid_till.strftime("%d %b %Y")),
    ]
    y = 156
    for label, value in rows:
        draw.text((200, y), f"{label}: {value}", fill="#1f2933", font=font_regular)
        y += 34

    if member.qr_code:
        try:
            qr = open_storage_image(member.qr_code).convert("RGB").resize((132, 132))
            image.paste(qr, (720, 352))
        except (FileNotFoundError, OSError, ValueError):
            draw.rectangle((720, 352, 852, 484), outline="#d6e1df", width=2)

    draw.text((36, 480), f"Digitally signed by {settings.ASSOCIATION_NAME}", fill="#123829", font=font_regular)

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    response = HttpResponse(buffer.getvalue(), content_type="image/png")
    response["Content-Disposition"] = f'attachment; filename="{member.membership_number}.png"'
    return response


@login_required
def membership_certificate(request):
    member = Member.objects.filter(user=request.user, is_active=True).select_related("application").first()
    if not member:
        messages.error(request, "Your membership certificate is not available yet. Please complete your application and payment process.")
        return redirect("member_dashboard")
    application = member.application
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{member.membership_number}-certificate.pdf"'
    page = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    page.setFont("Helvetica-Bold", 22)
    page.drawCentredString(width / 2, height - 110, settings.ASSOCIATION_NAME)
    page.setFont("Helvetica-Bold", 18)
    page.drawCentredString(width / 2, height - 155, "Membership Certificate")
    page.setFont("Helvetica", 12)
    page.drawCentredString(width / 2, height - 210, f"This is to certify that {application.full_name}")
    page.drawCentredString(width / 2, height - 238, f"of {application.shop_name}, {application.district}")
    page.drawCentredString(width / 2, height - 266, f"is an active member with Membership Number {member.membership_number}.")
    page.drawCentredString(width / 2, height - 294, f"Valid Till: {member.valid_till.strftime('%d %b %Y')}")
    page.setFont("Helvetica-Bold", 11)
    page.drawString(72, 120, f"Digitally signed by {settings.ASSOCIATION_NAME}")
    page.showPage()
    page.save()
    return response


@login_required
def payment_receipt(request):
    application = MembershipApplication.objects.filter(applicant=request.user).order_by("-created_at").first()
    if not application:
        messages.error(request, "No membership application found.")
        return redirect("member_dashboard")

    payment = PaymentProof.objects.filter(application=application, status=PaymentProof.Status.APPROVED).first()
    if not payment:
        messages.error(request, "No approved payment receipt found. Please complete your payment process.")
        return redirect("member_dashboard")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="payment-receipt-{payment.utr_number}.pdf"'
    page = canvas.Canvas(response, pagesize=A4)
    y = A4[1] - 72
    page.setFont("Helvetica-Bold", 18)
    page.drawString(72, y, settings.ASSOCIATION_NAME)
    page.setFont("Helvetica-Bold", 14)
    page.drawString(72, y - 38, "Payment Receipt")
    rows = [
        ("Member/Applicant", application.full_name),
        ("Shop Name", application.shop_name),
        ("Amount", f"Rs. {payment.amount}"),
        ("UTR Number", payment.utr_number),
        ("Payment Date", payment.payment_date.strftime("%d %b %Y")),
        ("Bank Name", payment.bank_name),
        ("Status", payment.get_status_display()),
    ]
    y -= 82
    for label, value in rows:
        page.setFont("Helvetica-Bold", 11)
        page.drawString(72, y, f"{label}:")
        page.setFont("Helvetica", 11)
        page.drawString(210, y, str(value))
        y -= 24
    page.showPage()
    page.save()
    return response


@login_required
def reports(request):
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to view reports.")
        return redirect("member_dashboard")
    stats = {
        "total_members": Member.objects.count(),
        "active_members": Member.objects.filter(is_active=True).count(),
        "pending_applications": MembershipApplication.objects.filter(status=MembershipApplication.Status.SUBMITTED).count(),
        "pending_payments": MembershipApplication.objects.filter(status=MembershipApplication.Status.PAYMENT_SUBMITTED).count(),
        "expired_members": Member.objects.filter(valid_till__lt=timezone.localdate()).count(),
        "renewals_due": Member.objects.filter(valid_till__range=(timezone.localdate(), timezone.localdate() + timezone.timedelta(days=30))).count(),
        "payment_collection": PaymentProof.objects.filter(status=PaymentProof.Status.APPROVED).aggregate(total=Sum("amount"))["total"] or 0,
        "pending_kyc": MembershipApplication.objects.filter(
            status__in=[MembershipApplication.Status.SUBMITTED, MembershipApplication.Status.ADDITIONAL_DOCUMENTS]
        ).count(),
        "districts": MembershipApplication.objects.values("district").annotate(total=Count("id")).order_by("district"),
        "license_types": MembershipApplication.objects.values("excise_license_type").annotate(total=Count("id")),
    }
    return render(request, "membership/reports.html", {"stats": stats})


def admin_stats():
    today = timezone.localdate()
    return {
        "total_members": Member.objects.count(),
        "active_members": Member.objects.filter(is_active=True).count(),
        "pending_applications": MembershipApplication.objects.filter(status=MembershipApplication.Status.SUBMITTED).count(),
        "pending_payments": MembershipApplication.objects.filter(status=MembershipApplication.Status.PAYMENT_SUBMITTED).count(),
        "expired_members": Member.objects.filter(valid_till__lt=today).count(),
        "renewals_due": Member.objects.filter(valid_till__range=(today, today + timezone.timedelta(days=30))).count(),
        "payment_collection": PaymentProof.objects.filter(status=PaymentProof.Status.APPROVED).aggregate(total=Sum("amount"))["total"] or 0,
        "today_registrations": MembershipApplication.objects.filter(created_at__date=today).count(),
    }


@staff_member_required
def staff_dashboard(request):
    districts = list(
        MembershipApplication.objects.values("district").annotate(total=Count("id")).order_by("-total")[:6]
    )
    max_district_total = max([item["total"] for item in districts] or [1])
    return render(
        request,
        "admin_portal/dashboard.html",
        {
            "active_page": "dashboard",
            "stats": admin_stats(),
            "districts": districts,
            "max_district_total": max_district_total,
            "recent_logs": AuditLog.objects.select_related("actor").order_by("-created_at")[:6],
        },
    )


@staff_member_required
def staff_applications(request):
    active_filter = request.GET.get("status", "")
    qs = MembershipApplication.objects.select_related("applicant")
    if active_filter == "pending":
        qs = qs.filter(status__in=DOCUMENT_REVIEW_STATUSES)
    elif active_filter == "approved":
        qs = qs.filter(
            status__in=[
                MembershipApplication.Status.APPROVED_PENDING_PAYMENT,
                MembershipApplication.Status.PAYMENT_APPROVED,
                MembershipApplication.Status.MEMBER_ACTIVE,
            ]
        )
    elif active_filter == "rejected":
        qs = qs.filter(status=MembershipApplication.Status.REJECTED)
    elif active_filter == "docs_requested":
        qs = qs.filter(status=MembershipApplication.Status.ADDITIONAL_DOCUMENTS)
    elif active_filter == "today":
        qs = qs.filter(created_at__date=timezone.localdate())
    applications = list(qs.order_by("-created_at")[:200])
    for application in applications:
        application.can_inline_review = is_document_review_status(application.status)
    return render(
        request,
        "admin_portal/applications.html",
        {
            "active_page": "applications",
            "applications": applications,
            "active_filter": active_filter,
            "counts": {
                "pending": MembershipApplication.objects.filter(status__in=DOCUMENT_REVIEW_STATUSES).count(),
                "approved": MembershipApplication.objects.filter(
                    status__in=[
                        MembershipApplication.Status.APPROVED_PENDING_PAYMENT,
                        MembershipApplication.Status.PAYMENT_APPROVED,
                        MembershipApplication.Status.MEMBER_ACTIVE,
                    ]
                ).count(),
                "rejected": MembershipApplication.objects.filter(status=MembershipApplication.Status.REJECTED).count(),
                "docs_requested": MembershipApplication.objects.filter(
                    status=MembershipApplication.Status.ADDITIONAL_DOCUMENTS
                ).count(),
            },
        },
    )


def application_documents(application):
    documents = [
        {"key": "excise_license", "label": "Licence copy", "file": application.excise_license, "required": False},
        {"key": "passport_photo", "label": "Proprietor / Partner photo", "file": application.passport_photo, "required": False},
        {"key": "primary_delegate_photo", "label": "Primary representative photo", "file": application.primary_delegate_photo, "required": False},
        {"key": "alternate_delegate_photo", "label": "Alternate representative photo", "file": application.alternate_delegate_photo, "required": False},
        {"key": "pan_card", "label": "PAN card", "file": application.pan_card, "required": False},
        {"key": "aadhaar_card", "label": "Aadhaar", "file": application.aadhaar_card, "required": False},
        {"key": "partnership_deed", "label": "Partnership deed / MOA", "file": application.partnership_deed, "required": False},
        {"key": "gst_certificate", "label": "GST certificate", "file": application.gst_certificate, "required": False},
        {"key": "address_proof", "label": "Address proof", "file": application.address_proof, "required": False},
    ]
    for document in documents:
        file = document["file"]
        document["is_image"] = file_kind(file) == "image"
        document["url"] = storage_url(file)
        document["uploaded"] = bool(document["url"])
    return documents


def staff_application_action_context(application, payment=None, member=None):
    payment = payment if payment is not None else PaymentProof.objects.filter(application=application).first()
    member = member if member is not None else Member.objects.filter(application=application).first()
    membership_active = bool(application.status in MEMBERSHIP_ACTIVE_STATUSES or (member and member.is_active))
    show_payment_actions = bool(
        payment
        and payment.status in PENDING_PAYMENT_PROOF_STATUSES
        and application.status in PAYMENT_REVIEW_STATUSES
        and application.status not in REJECTED_APPLICATION_STATUSES
        and not membership_active
    )
    waiting_for_payment = application.status in PAYMENT_WAITING_STATUSES and not show_payment_actions
    payment_missing_for_review = application.status in PAYMENT_REVIEW_STATUSES and not payment
    can_activate_membership = application.status in PAYMENT_APPROVED_STATUSES and not membership_active
    waiting_for_payment_reupload = bool(payment and payment.status in REUPLOAD_PAYMENT_PROOF_STATUSES)
    waiting_for_documents = application.status == MembershipApplication.Status.ADDITIONAL_DOCUMENTS
    show_document_actions = bool(
        is_document_review_status(application.status)
        and application.status not in REJECTED_APPLICATION_STATUSES
        and not membership_active
        and not waiting_for_documents
    )
    return {
        "show_document_actions": show_document_actions,
        "show_payment_actions": show_payment_actions,
        "waiting_for_payment": waiting_for_payment,
        "payment_missing_for_review": payment_missing_for_review,
        "waiting_for_payment_reupload": waiting_for_payment_reupload,
        "waiting_for_documents": waiting_for_documents,
        "can_activate_membership": can_activate_membership,
        "membership_active": membership_active,
        "has_pending_admin_action": show_document_actions or show_payment_actions or can_activate_membership,
    }


def staff_application_status_context(application):
    return [
        {
            "label": "Application Submitted",
            "done": application.status
            in [
                MembershipApplication.Status.SUBMITTED,
                MembershipApplication.Status.APPROVED_PENDING_PAYMENT,
                MembershipApplication.Status.PAYMENT_SUBMITTED,
                MembershipApplication.Status.PAYMENT_APPROVED,
                MembershipApplication.Status.MEMBER_ACTIVE,
                MembershipApplication.Status.ADDITIONAL_DOCUMENTS,
                MembershipApplication.Status.REJECTED,
            ],
        },
        {
            "label": "Documents Verified",
            "done": application.status
            in [
                MembershipApplication.Status.APPROVED_PENDING_PAYMENT,
                MembershipApplication.Status.PAYMENT_SUBMITTED,
                MembershipApplication.Status.PAYMENT_APPROVED,
                MembershipApplication.Status.MEMBER_ACTIVE,
            ],
        },
        {
            "label": "Payment Submitted",
            "done": application.status
            in [
                MembershipApplication.Status.PAYMENT_SUBMITTED,
                MembershipApplication.Status.PAYMENT_APPROVED,
                MembershipApplication.Status.MEMBER_ACTIVE,
            ],
        },
        {
            "label": "Membership Active",
            "done": application.status == MembershipApplication.Status.MEMBER_ACTIVE,
        },
    ]


@staff_member_required
def staff_application_detail(request, pk):
    application = get_object_or_404(MembershipApplication.objects.select_related("applicant"), pk=pk)
    payment = PaymentProof.objects.filter(application=application).first()
    member = Member.objects.filter(application=application).first()
    action_context = staff_application_action_context(application, payment, member)
    return render(
        request,
        "admin_portal/application_detail.html",
        {
            "active_page": "applications",
            "application": application,
            "documents": application_documents(application),
            "payment": payment,
            "member": member,
            "status_steps": staff_application_status_context(application),
            **action_context,
            "recent_logs": AuditLog.objects.filter(target__icontains=application.full_name).select_related("actor").order_by("-created_at")[:6],
        },
    )


@staff_member_required
def staff_application_action(request, pk):
    if request.method != "POST":
        return redirect("staff_application_detail", pk=pk)

    application = get_object_or_404(MembershipApplication.objects.select_related("applicant"), pk=pk)
    action = request.POST.get("action")
    remarks = request.POST.get("remarks", "").strip()
    next_url = request.POST.get("next") or reverse("staff_application_detail", args=[application.pk])

    if action in {"save_remarks", "save_remark"}:
        application.remarks = remarks
        application.save(update_fields=["remarks", "updated_at"])
        AuditLog.objects.create(actor=request.user, action="Remark saved", target=str(application), notes=remarks)
        messages.success(request, "Remark saved without changing application status.")
    elif action == "approve_documents":
        if not is_document_review_status(application.status):
            messages.error(request, "Documents can only be approved while the application is waiting for document review.")
            return redirect("staff_application_detail", pk=application.pk)
        remarks = remarks or "Documents verified successfully."
        application.approve_application(remarks)
        notify_member(
            application.applicant,
            title="Documents verified",
            message="Your documents have been verified. Payment details are now available on your dashboard.",
            remarks=remarks,
        )
        AuditLog.objects.create(actor=request.user, action="Documents verified", target=str(application), notes=remarks)
        messages.success(request, "Documents approved and payment stage unlocked.")
    elif action == "request_documents":
        if not is_document_review_status(application.status):
            messages.error(request, "Updated documents can only be requested during document review.")
            return redirect("staff_application_detail", pk=application.pk)
        remarks = remarks or "Please upload clearer or missing documents."
        application.status = MembershipApplication.Status.ADDITIONAL_DOCUMENTS
        application.remarks = remarks
        application.save(update_fields=["status", "remarks", "updated_at"])
        notify_member(
            application.applicant,
            title="Additional documents requested",
            message="Additional documents are required for your membership application.",
            remarks=remarks,
        )
        AuditLog.objects.create(actor=request.user, action="Additional documents requested", target=str(application), notes=remarks)
        messages.warning(request, "Additional documents requested from applicant.")
    elif action in {"reject_documents", "reject_application"}:
        if not is_document_review_status(application.status):
            messages.error(request, "Applications can only be rejected from the document review stage.")
            return redirect("staff_application_detail", pk=application.pk)
        remarks = remarks or "Documents did not meet verification requirements."
        application.reject_application(remarks)
        notify_member(
            application.applicant,
            title="Documents rejected",
            message="Your submitted documents could not be verified. Please review the remarks and contact the association office if needed.",
            remarks=remarks,
        )
        AuditLog.objects.create(actor=request.user, action="Documents rejected", target=str(application), notes=remarks)
        messages.warning(request, "Application rejected and applicant notified.")
    elif action == "generate_membership":
        if application.status != MembershipApplication.Status.PAYMENT_APPROVED:
            messages.error(request, "Payment must be approved before generating final membership.")
        else:
            member = Member.objects.create_from_application(application)
            notify_member(
                application.applicant,
                title="Membership activated",
                message=membership_activation_message(member),
            )
            AuditLog.objects.create(actor=request.user, action="Membership generated", target=member.membership_number)
            messages.success(request, f"Membership generated: {member.membership_number}.")
    else:
        messages.error(request, "Unknown application action.")

    return redirect(next_url)


@staff_member_required
def staff_payments(request):
    active_filter = request.GET.get("status", "")
    qs = PaymentProof.objects.select_related("application")
    if active_filter == "pending":
        qs = qs.filter(status=PaymentProof.Status.PENDING)
    elif active_filter == "approved":
        qs = qs.filter(status=PaymentProof.Status.APPROVED)
    elif active_filter == "rejected":
        qs = qs.filter(status=PaymentProof.Status.REJECTED)
    elif active_filter == "reupload":
        qs = qs.filter(status=PaymentProof.Status.REUPLOAD_REQUESTED)
    payments = qs.order_by("-created_at")[:50]
    return render(
        request,
        "admin_portal/payments.html",
        {
            "active_page": "payments",
            "payments": payments,
            "active_filter": active_filter,
        },
    )


@staff_member_required
def staff_payment_detail(request, pk):
    payment = get_object_or_404(PaymentProof.objects.select_related("application", "application__applicant"), pk=pk)
    application = payment.application
    member = Member.objects.filter(application=application).first()
    member_is_active = bool(application.status in MEMBERSHIP_ACTIVE_STATUSES or (member and member.is_active))
    show_payment_actions = bool(
        payment.status in PENDING_PAYMENT_PROOF_STATUSES
        and application.status in PAYMENT_REVIEW_STATUSES
        and application.status not in REJECTED_APPLICATION_STATUSES
        and not member_is_active
    )
    return render(
        request,
        "admin_portal/payment_detail.html",
        {
            "active_page": "payments",
            "payment": payment,
            "application": application,
            "member": member,
            "show_payment_actions": show_payment_actions,
            "membership_active": member_is_active,
            "payment_proof_url": storage_url(payment.screenshot),
            "recent_logs": AuditLog.objects.filter(target__icontains=payment.utr_number).select_related("actor").order_by("-created_at")[:6],
        },
    )


@staff_member_required
def staff_payment_action(request, pk):
    if request.method != "POST":
        return redirect("staff_payment_detail", pk=pk)

    payment = get_object_or_404(PaymentProof.objects.select_related("application", "application__applicant"), pk=pk)
    action = request.POST.get("action")
    remarks = request.POST.get("remarks", "").strip()
    next_url = request.POST.get("next") or reverse("staff_payment_detail", args=[payment.pk])

    if action == "approve_payment":
        if payment.status == PaymentProof.Status.APPROVED:
            messages.info(request, "This payment is already approved.")
        elif (
            payment.application.status not in PAYMENT_REVIEW_STATUSES
            or payment.application.status in REJECTED_APPLICATION_STATUSES
            or payment.status not in PENDING_PAYMENT_PROOF_STATUSES
        ):
            messages.error(request, "Payment can only be approved after a proof upload is pending verification.")
        else:
            payment.remarks = remarks
            payment.save(update_fields=["remarks", "updated_at"])
            payment.approve(request.user)
            member = Member.objects.create_from_application(payment.application)
            notify_member(
                payment.application.applicant,
                title="Payment verified",
                message="Your payment proof has been verified successfully. Final membership activation is complete.",
                remarks=remarks,
            )
            notify_member(
                payment.application.applicant,
                title="Membership activated",
                message=membership_activation_message(member),
                remarks=remarks,
            )
            AuditLog.objects.create(actor=request.user, action="Payment approved and membership activated", target=payment.utr_number, notes=remarks)
            messages.success(request, f"Payment approved and membership activated: {member.membership_number}.")
    elif action == "reject_payment":
        if (
            payment.application.status not in PAYMENT_REVIEW_STATUSES
            or payment.application.status in REJECTED_APPLICATION_STATUSES
            or payment.status not in PENDING_PAYMENT_PROOF_STATUSES
        ):
            messages.error(request, "Payment can only be rejected while it is pending verification.")
            return redirect(next_url)
        remarks = remarks or "Payment proof could not be verified with the submitted details."
        payment.status = PaymentProof.Status.REJECTED
        payment.remarks = remarks
        payment.verified_by = request.user
        payment.verified_at = timezone.now()
        payment.save(update_fields=["status", "remarks", "verified_by", "verified_at", "updated_at"])
        payment.application.status = MembershipApplication.Status.APPROVED_PENDING_PAYMENT
        payment.application.remarks = remarks
        payment.application.save(update_fields=["status", "remarks", "updated_at"])
        notify_member(
            payment.application.applicant,
            title="Payment failed verification",
            message="Your payment proof could not be verified. Please review the remarks and submit correct payment details again.",
            remarks=remarks,
        )
        AuditLog.objects.create(actor=request.user, action="Payment rejected", target=payment.utr_number, notes=remarks)
        messages.warning(request, "Payment rejected and applicant notified.")
    elif action == "request_reupload":
        if (
            payment.application.status not in PAYMENT_REVIEW_STATUSES
            or payment.application.status in REJECTED_APPLICATION_STATUSES
            or payment.status not in PENDING_PAYMENT_PROOF_STATUSES
        ):
            messages.error(request, "Payment re-upload can only be requested while proof is pending verification.")
            return redirect(next_url)
        remarks = remarks or "Please upload a clearer screenshot or correct UTR/payment details."
        payment.status = PaymentProof.Status.REUPLOAD_REQUESTED
        payment.remarks = remarks
        payment.verified_by = request.user
        payment.verified_at = timezone.now()
        payment.save(update_fields=["status", "remarks", "verified_by", "verified_at", "updated_at"])
        payment.application.status = MembershipApplication.Status.PAYMENT_SUBMITTED
        payment.application.remarks = remarks
        payment.application.save(update_fields=["status", "remarks", "updated_at"])
        notify_member(
            payment.application.applicant,
            title="Payment re-upload requested",
            message="Your payment proof requires re-upload before verification can be completed.",
            remarks=remarks,
        )
        AuditLog.objects.create(actor=request.user, action="Payment re-upload requested", target=payment.utr_number, notes=remarks)
        messages.warning(request, "Payment re-upload requested.")
    else:
        messages.error(request, "Unknown payment action.")

    return redirect(next_url)


@staff_member_required
def staff_members(request):
    active_filter = request.GET.get("status", "")
    qs = Member.objects.select_related("application")
    if active_filter == "active":
        qs = qs.filter(is_active=True)
    elif active_filter == "expired":
        qs = qs.filter(is_active=False)
    elif active_filter == "renewals":
        today = timezone.localdate()
        qs = qs.filter(valid_till__range=(today, today + timezone.timedelta(days=30)))
    members = qs.order_by("-created_at")[:50]
    return render(
        request,
        "admin_portal/members.html",
        {
            "active_page": "members",
            "members": members,
            "active_filter": active_filter,
        },
    )


@staff_member_required
def staff_member_detail(request, pk):
    member = get_object_or_404(Member.objects.select_related("application", "user"), pk=pk)
    application = member.application
    payment = PaymentProof.objects.filter(application=application).first()
    documents = application_documents(application)
    recent_logs = AuditLog.objects.filter(target__icontains=application.full_name).select_related("actor").order_by("-created_at")[:8]
    return render(
        request,
        "admin_portal/member_detail.html",
        {
            "active_page": "members",
            "member": member,
            "application": application,
            "payment": payment,
            "documents": documents,
            "recent_logs": recent_logs,
        },
    )


@staff_member_required
def staff_membership_cards(request):
    members = Member.objects.select_related("application").order_by("-created_at")[:50]
    selected_member = members[0] if members else None
    selected_id = request.GET.get("member")
    if selected_id:
        selected_member = get_object_or_404(Member.objects.select_related("application"), pk=selected_id)
    return render(
        request,
        "admin_portal/membership_card.html",
        {
            "active_page": "cards",
            "members": members,
            "selected_member": selected_member,
        },
    )


@staff_member_required
def staff_settings(request):
    payment_settings = SitePaymentSettings.load()
    if request.method == "POST":
        form = SitePaymentSettingsForm(request.POST, request.FILES, instance=payment_settings)
        if form.is_valid():
            form.save()
            messages.success(request, "Payment settings updated successfully.")
        else:
            messages.error(request, "Settings were not saved. Please fix the highlighted fields.")
            return render(
                request,
                "admin_portal/settings.html",
                {
                    "active_page": "settings",
                    "membership_fee": payment_settings.membership_fee,
                    "payment_settings": payment_settings_context(),
                    "payment_settings_form": form,
                },
            )
        return redirect("staff_settings")

    form = SitePaymentSettingsForm(instance=payment_settings)
    return render(
        request,
        "admin_portal/settings.html",
        {
            "active_page": "settings",
            "membership_fee": payment_settings.membership_fee,
            "payment_settings": payment_settings_context(),
            "payment_settings_form": form,
        },
    )


@staff_member_required
def staff_profile(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "update_account":
            full_name = request.POST.get("full_name", "").strip()
            first_name, _, last_name = full_name.partition(" ")
            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.email = request.POST.get("email", "").strip()
            request.user.username = request.POST.get("username", request.user.username).strip() or request.user.username
            request.user.save(update_fields=["first_name", "last_name", "email", "username"])
            if hasattr(request.user, "profile"):
                request.user.profile.mobile_number = request.POST.get("mobile_number", "").strip()
                request.user.profile.save(update_fields=["mobile_number"])
            AuditLog.objects.create(actor=request.user, action="Profile updated", target=request.user.username)
            messages.success(request, "Profile updated successfully.")
        elif action == "change_password":
            current_password = request.POST.get("current_password", "")
            new_password = request.POST.get("new_password", "")
            confirm_password = request.POST.get("confirm_password", "")
            if not request.user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
            elif len(new_password) < 8:
                messages.error(request, "New password must be at least 8 characters.")
            elif new_password != confirm_password:
                messages.error(request, "New passwords do not match.")
            else:
                request.user.set_password(new_password)
                request.user.save(update_fields=["password"])
                update_session_auth_hash(request, request.user)
                AuditLog.objects.create(actor=request.user, action="Password changed", target=request.user.username)
                messages.success(request, "Password updated successfully.")
        return redirect("staff_profile")

    return render(
        request,
        "admin_portal/profile.html",
        {
            "active_page": "profile",
            "recent_logs": AuditLog.objects.filter(actor=request.user).order_by("-created_at")[:8],
        },
    )


@staff_member_required
def staff_notifications(request):
    if request.method == "POST":
        broadcast = BroadcastMessage(
            title=request.POST.get("title", "").strip(),
            message=request.POST.get("message", "").strip(),
            audience=request.POST.get("audience", BroadcastMessage.Audience.ALL_MEMBERS),
            channel=request.POST.get("channel", BroadcastMessage.Channel.IN_APP),
            district=request.POST.get("district", "").strip(),
            recipient_id=request.POST.get("recipient") or None,
            recipient_email=request.POST.get("recipient_email", "").strip(),
            recipient_mobile=request.POST.get("recipient_mobile", "").strip(),
        )
        try:
            broadcast.full_clean()
            sent_count = broadcast.send(actor=request.user)
            AuditLog.objects.create(actor=request.user, action="Broadcast sent", target=broadcast.title, notes=f"{sent_count} recipients")
            messages.success(request, f"Broadcast sent to {sent_count} recipient(s).")
        except Exception as exc:
            messages.error(request, f"Could not send broadcast: {exc}")
        return redirect("staff_notifications")

    broadcasts = BroadcastMessage.objects.select_related("sent_by", "recipient").order_by("-created_at")[:20]
    return render(
        request,
        "admin_portal/notifications.html",
        {
            "active_page": "notifications",
            "broadcasts": broadcasts,
            "members": User.objects.filter(is_active=True).order_by("first_name", "username")[:100],
            "districts": MembershipApplication.objects.values_list("district", flat=True).distinct().order_by("district"),
            "email_count": BroadcastMessage.objects.filter(
                channel__in=[BroadcastMessage.Channel.EMAIL, BroadcastMessage.Channel.EMAIL_WHATSAPP]
            ).count(),
            "whatsapp_count": BroadcastMessage.objects.filter(
                channel__in=[BroadcastMessage.Channel.WHATSAPP, BroadcastMessage.Channel.EMAIL_WHATSAPP]
            ).count(),
        },
    )


@login_required
def export_report(request, report_type, file_type):
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to export reports.")
        return redirect("member_dashboard")

    rows = report_rows(report_type)
    if file_type == "excel":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{report_type}.csv"'
        writer = csv.writer(response)
        writer.writerows(rows)
        return response
    if file_type == "pdf":
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{report_type}.pdf"'
        page = canvas.Canvas(response, pagesize=A4)
        y = A4[1] - 72
        page.setFont("Helvetica-Bold", 16)
        page.drawString(72, y, report_type.replace("-", " ").title())
        y -= 34
        page.setFont("Helvetica", 9)
        for row in rows:
            page.drawString(72, y, " | ".join(str(value) for value in row))
            y -= 18
            if y < 72:
                page.showPage()
                y = A4[1] - 72
                page.setFont("Helvetica", 9)
        page.showPage()
        page.save()
        return response
    raise Http404("Unsupported export format")


def report_rows(report_type):
    if report_type == "district-wise-members":
        return [["District", "Members"], *MembershipApplication.objects.values_list("district").annotate(total=Count("id"))]
    if report_type == "license-type-members":
        return [["License Type", "Members"], *MembershipApplication.objects.values_list("excise_license_type").annotate(total=Count("id"))]
    if report_type == "payment-collection":
        rows = [["Applicant", "UTR", "Amount", "Payment Date", "Bank", "Status"]]
        rows += list(
            PaymentProof.objects.select_related("application").values_list(
                "application__full_name", "utr_number", "amount", "payment_date", "bank_name", "status"
            )
        )
        return rows
    if report_type == "pending-payments":
        rows = [["Applicant", "Mobile", "Shop", "Status"]]
        rows += list(
            MembershipApplication.objects.filter(status=MembershipApplication.Status.PAYMENT_SUBMITTED).values_list(
                "full_name", "mobile_number", "shop_name", "status"
            )
        )
        return rows
    if report_type == "pending-kyc":
        rows = [["Applicant", "Mobile", "Shop", "Status"]]
        rows += list(
            MembershipApplication.objects.filter(
                status__in=[MembershipApplication.Status.SUBMITTED, MembershipApplication.Status.ADDITIONAL_DOCUMENTS]
            ).values_list("full_name", "mobile_number", "shop_name", "status")
        )
        return rows
    if report_type == "renewal-report":
        rows = [["Membership Number", "Name", "Valid Till", "Active"]]
        rows += list(Member.objects.select_related("application").values_list("membership_number", "application__full_name", "valid_till", "is_active"))
        return rows
    if report_type == "gst-report":
        rows = [["Name", "Shop", "GST", "District"]]
        rows += list(MembershipApplication.objects.exclude(gst_number="").values_list("full_name", "shop_name", "gst_number", "district"))
        return rows
    raise Http404("Report not found")


@login_required
def document_file(request, source, pk, field_name):
    """Stream a stored document (image or PDF) with correct content-type.

    Cloudinary's raw delivery URLs often carry headers (content-disposition /
    nosniff) that block in-browser preview and downloads. This view proxies the
    file through Django so the browser always receives a usable response.
    """
    if source == "application":
        obj = get_object_or_404(MembershipApplication, pk=pk)
        if not request.user.is_staff and obj.applicant_id != request.user.id:
            raise Http404("Document not found")
    elif source == "payment":
        obj = get_object_or_404(PaymentProof, pk=pk)
        if not request.user.is_staff and obj.application.applicant_id != request.user.id:
            raise Http404("Document not found")
    else:
        raise Http404("Document not found")

    file = getattr(obj, field_name, None)
    if not file:
        raise Http404("Document not uploaded")

    url = storage_url(file)
    if not url:
        raise Http404("Document URL is not available")

    kind = file_kind(file)
    content_type = document_content_type(file, kind)

    try:
        file.open("rb")
        data = file.read()
        file.close()
    except (OSError, ValueError):
        # Fall back to redirecting to the remote URL if we cannot read locally.
        return redirect(preview_url(file) or url)

    response = HttpResponse(data, content_type=content_type)
    disposition = request.GET.get("disposition", "inline")
    if disposition == "attachment":
        response["Content-Disposition"] = f'attachment; filename="{file.name.rsplit("/", 1)[-1]}"'
    else:
        response["Content-Disposition"] = f'inline; filename="{file.name.rsplit("/", 1)[-1]}"'
    response["X-Content-Type-Options"] = "nosniff"
    response["X-Frame-Options"] = "SAMEORIGIN"
    return response


def admin_document_review(request, source, pk, field_name):
    application_fields = {
        "excise_license": "Licence copy",
        "passport_photo": "Proprietor / Partner photo",
        "primary_delegate_photo": "Primary representative photo",
        "alternate_delegate_photo": "Alternate representative photo",
        "pan_card": "PAN card",
        "aadhaar_card": "Aadhaar",
        "partnership_deed": "Partnership deed / MOA",
        "gst_certificate": "GST certificate",
        "address_proof": "Address proof",
    }
    payment_fields = {
        "screenshot": "Payment Screenshot",
    }

    if source == "application" and field_name in application_fields:
        obj = get_object_or_404(MembershipApplication, pk=pk)
        if not request.user.is_staff and obj.applicant_id != request.user.id:
            raise Http404("Document not found")
        label = application_fields[field_name]
        owner = obj.full_name
        back_url = reverse("staff_application_detail", args=[obj.pk]) if request.user.is_staff else reverse("member_profile")
    elif source == "payment" and field_name in payment_fields:
        obj = get_object_or_404(PaymentProof, pk=pk)
        if not request.user.is_staff and obj.application.applicant_id != request.user.id:
            raise Http404("Document not found")
        label = payment_fields[field_name]
        owner = obj.application.full_name
        back_url = reverse("staff_payment_detail", args=[obj.pk]) if request.user.is_staff else reverse("payment_upload", args=[obj.application_id])
    else:
        raise Http404("Document not found")

    file = getattr(obj, field_name)
    if not file:
        raise Http404("Document not uploaded")

    kind = file_kind(file)
    is_image = kind == "image"
    is_pdf = kind == "pdf"
    file_url = preview_url(file)
    doc_url = reverse("document_file", args=[source, obj.pk, field_name])
    preview_src = doc_url
    if not file_url and not preview_src:
        raise Http404("Document URL is not available")

    return render(
        request,
        "membership/admin_document_review.html",
        {
            "label": label,
            "owner": owner,
            "file": file,
            "file_name": file.name.rsplit("/", 1)[-1],
            "file_url": file_url,
            "doc_url": doc_url,
            "preview_src": preview_src,
            "is_image": is_image,
            "is_pdf": is_pdf,
            "back_url": request.META.get("HTTP_REFERER") or back_url,
        },
    )
