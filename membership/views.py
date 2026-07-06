from io import BytesIO
import csv

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .forms import MembershipApplicationForm, PaymentProofForm
from .models import Member, MembershipApplication, PaymentProof, notify_staff


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
    return render(
        request,
        "membership/dashboard.html",
        {
            "application": application,
            "applications": applications,
            "member": member,
            "notifications": notifications,
            "payment": getattr(application, "payment", None) if application else None,
            "payment_settings": {
                "upi_id": settings.PAYMENT_UPI_ID,
                "bank_name": settings.PAYMENT_BANK_NAME,
                "account_name": settings.PAYMENT_ACCOUNT_NAME,
                "account_number": settings.PAYMENT_ACCOUNT_NUMBER,
                "ifsc": settings.PAYMENT_IFSC,
            },
        },
    )


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
        and (not profile.email_verified or not profile.mobile_verified)
    ):
        messages.error(request, "Please verify your email and mobile OTP before submitting the application.")
        return redirect("verify_registration_otp")

    existing = MembershipApplication.objects.filter(applicant=request.user).exclude(
        status=MembershipApplication.Status.REJECTED
    ).first()
    can_update_documents = existing and existing.status == MembershipApplication.Status.ADDITIONAL_DOCUMENTS
    if existing and not can_update_documents:
        messages.info(request, "You already have an active application.")
        return redirect("member_dashboard")

    if request.method == "POST":
        form = MembershipApplicationForm(request.POST, request.FILES, instance=existing if can_update_documents else None)
        if form.is_valid():
            application = form.save(commit=False)
            application.applicant = request.user
            application.status = MembershipApplication.Status.SUBMITTED
            application.remarks = ""
            application.save()
            notify_staff(
                "New membership application" if not can_update_documents else "Documents resubmitted",
                f"{application.full_name} / {application.shop_name} is ready for document verification.",
            )
            messages.success(request, "Application submitted successfully." if not can_update_documents else "Documents updated and resubmitted for admin review.")
            return redirect("member_dashboard")
    else:
        form = MembershipApplicationForm(
            instance=existing if can_update_documents else None,
            initial={
                "email": request.user.email,
                "mobile_number": profile.mobile_number,
                "full_name": request.user.get_full_name() or request.user.username,
            }
        )
    return render(request, "membership/application_form.html", {"form": form, "is_update": can_update_documents})


@login_required
def payment_upload(request, application_id):
    application = get_object_or_404(
        MembershipApplication,
        id=application_id,
        applicant=request.user,
        status__in=[
            MembershipApplication.Status.APPROVED_PENDING_PAYMENT,
            MembershipApplication.Status.PAYMENT_SUBMITTED,
        ],
    )
    instance = getattr(application, "payment", None)
    if request.method == "POST":
        form = PaymentProofForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.application = application
            payment.amount = settings.MEMBERSHIP_FEE
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
        form = PaymentProofForm(instance=instance)
    return render(request, "membership/payment_form.html", {"form": form, "application": application})


def verify_member(request, public_id):
    member = get_object_or_404(Member.objects.select_related("application"), public_id=public_id, is_active=True)
    return render(request, "membership/verify_member.html", {"member": member})


@login_required
def card(request):
    member = get_object_or_404(Member.objects.select_related("application"), user=request.user, is_active=True)
    return render(request, "membership/card.html", {"member": member})


@login_required
def card_pdf(request):
    member = get_object_or_404(Member.objects.select_related("application"), user=request.user, is_active=True)
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
    member = get_object_or_404(Member.objects.select_related("application"), user=request.user, is_active=True)
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
            photo = Image.open(application.passport_photo.path).convert("RGB").resize((130, 160))
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
            qr = Image.open(member.qr_code.path).convert("RGB").resize((132, 132))
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
    member = get_object_or_404(Member.objects.select_related("application"), user=request.user, is_active=True)
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
    application = get_object_or_404(MembershipApplication, applicant=request.user)
    payment = get_object_or_404(PaymentProof, application=application, status=PaymentProof.Status.APPROVED)
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


@staff_member_required
def admin_document_review(request, source, pk, field_name):
    application_fields = {
        "passport_photo": "Passport Photo",
        "aadhaar_card": "Aadhaar Card",
        "pan_card": "PAN Card",
        "excise_license": "Excise License",
        "trade_license": "Trade License",
        "gst_certificate": "GST Certificate",
        "address_proof": "Address Proof",
        "signature": "Signature",
    }
    payment_fields = {
        "screenshot": "Payment Screenshot",
    }

    if source == "application" and field_name in application_fields:
        obj = get_object_or_404(MembershipApplication, pk=pk)
        label = application_fields[field_name]
        owner = obj.full_name
        back_url = f"/admin/membership/membershipapplication/{obj.pk}/change/"
    elif source == "payment" and field_name in payment_fields:
        obj = get_object_or_404(PaymentProof, pk=pk)
        label = payment_fields[field_name]
        owner = obj.application.full_name
        back_url = f"/admin/membership/paymentproof/{obj.pk}/change/"
    else:
        raise Http404("Document not found")

    file = getattr(obj, field_name)
    if not file:
        raise Http404("Document not uploaded")

    file_name = file.name.lower()
    is_image = file_name.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp"))
    is_pdf = file_name.endswith(".pdf")

    return render(
        request,
        "membership/admin_document_review.html",
        {
            "label": label,
            "owner": owner,
            "file": file,
            "is_image": is_image,
            "is_pdf": is_pdf,
            "back_url": request.META.get("HTTP_REFERER") or back_url,
        },
    )
