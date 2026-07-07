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
from .models import AuditLog, BroadcastMessage, Member, MembershipApplication, PaymentProof, notify_staff
from .services import notify_member


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
        "payment_settings": {
            "upi_id": settings.PAYMENT_UPI_ID,
            "bank_name": settings.PAYMENT_BANK_NAME,
            "account_name": settings.PAYMENT_ACCOUNT_NAME,
            "account_number": settings.PAYMENT_ACCOUNT_NUMBER,
            "ifsc": settings.PAYMENT_IFSC,
        },
    }


@login_required
def member_profile(request):
    return render(request, "membership/profile.html", member_portal_context(request))


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
    return render(
        request,
        "admin_portal/applications.html",
        {
            "active_page": "applications",
            "applications": MembershipApplication.objects.select_related("applicant").order_by("-created_at")[:50],
            "counts": {
                "pending": MembershipApplication.objects.filter(status=MembershipApplication.Status.SUBMITTED).count(),
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
        {"key": "passport_photo", "label": "Passport Photo", "file": application.passport_photo, "required": True},
        {"key": "aadhaar_card", "label": "Aadhaar Card", "file": application.aadhaar_card, "required": True},
        {"key": "pan_card", "label": "PAN Card", "file": application.pan_card, "required": True},
        {"key": "excise_license", "label": "Excise License", "file": application.excise_license, "required": True},
        {"key": "trade_license", "label": "Trade License", "file": application.trade_license, "required": True},
        {"key": "gst_certificate", "label": "GST Certificate", "file": application.gst_certificate, "required": False},
        {"key": "address_proof", "label": "Address Proof", "file": application.address_proof, "required": True},
        {"key": "signature", "label": "Signature", "file": application.signature, "required": True},
    ]
    for document in documents:
        file = document["file"]
        document["is_image"] = bool(file and file.name.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")))
    return documents


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

    if action == "approve_documents":
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
    elif action == "reject_documents":
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
                message=f"Your membership has been activated successfully. Membership number: {member.membership_number}.",
            )
            AuditLog.objects.create(actor=request.user, action="Membership generated", target=member.membership_number)
            messages.success(request, f"Membership generated: {member.membership_number}.")
    else:
        messages.error(request, "Unknown application action.")

    return redirect("staff_application_detail", pk=application.pk)


@staff_member_required
def staff_payments(request):
    return render(
        request,
        "admin_portal/payments.html",
        {
            "active_page": "payments",
            "payments": PaymentProof.objects.select_related("application").order_by("-created_at")[:50],
        },
    )


@staff_member_required
def staff_payment_detail(request, pk):
    payment = get_object_or_404(PaymentProof.objects.select_related("application", "application__applicant"), pk=pk)
    application = payment.application
    member = Member.objects.filter(application=application).first()
    return render(
        request,
        "admin_portal/payment_detail.html",
        {
            "active_page": "payments",
            "payment": payment,
            "application": application,
            "member": member,
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

    if action == "approve_payment":
        if payment.status == PaymentProof.Status.APPROVED:
            messages.info(request, "This payment is already approved.")
        else:
            payment.remarks = remarks
            payment.save(update_fields=["remarks", "updated_at"])
            payment.approve(request.user)
            notify_member(
                payment.application.applicant,
                title="Payment approved",
                message="Your payment has been approved. Final membership generation is pending.",
                remarks=remarks,
            )
            AuditLog.objects.create(actor=request.user, action="Payment approved", target=payment.utr_number, notes=remarks)
            messages.success(request, "Payment approved. Final membership can now be generated.")
    elif action == "reject_payment":
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

    return redirect("staff_payment_detail", pk=payment.pk)


@staff_member_required
def staff_members(request):
    return render(
        request,
        "admin_portal/members.html",
        {
            "active_page": "members",
            "members": Member.objects.select_related("application").order_by("-created_at")[:50],
        },
    )


@staff_member_required
def staff_notifications(request):
    broadcasts = BroadcastMessage.objects.select_related("sent_by", "recipient").order_by("-created_at")[:20]
    return render(
        request,
        "admin_portal/notifications.html",
        {
            "active_page": "notifications",
            "broadcasts": broadcasts,
            "email_count": BroadcastMessage.objects.filter(
                channel__in=[BroadcastMessage.Channel.EMAIL, BroadcastMessage.Channel.EMAIL_WHATSAPP]
            ).count(),
            "whatsapp_count": BroadcastMessage.objects.filter(
                channel__in=[BroadcastMessage.Channel.WHATSAPP, BroadcastMessage.Channel.EMAIL_WHATSAPP]
            ).count(),
        },
    )


@staff_member_required
def staff_reports(request):
    districts = list(
        MembershipApplication.objects.values("district").annotate(total=Count("id")).order_by("-total")[:6]
    )
    return render(
        request,
        "admin_portal/reports.html",
        {
            "active_page": "reports",
            "stats": admin_stats(),
            "districts": districts,
            "max_district_total": max([item["total"] for item in districts] or [1]),
            "recent_logs": AuditLog.objects.select_related("actor").order_by("-created_at")[:6],
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
