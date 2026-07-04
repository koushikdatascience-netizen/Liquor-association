from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .forms import MembershipApplicationForm, PaymentProofForm
from .models import Member, MembershipApplication


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
    existing = MembershipApplication.objects.filter(applicant=request.user).exclude(
        status=MembershipApplication.Status.REJECTED
    ).first()
    if existing:
        messages.info(request, "You already have an active application.")
        return redirect("member_dashboard")

    if request.method == "POST":
        form = MembershipApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.applicant = request.user
            application.status = MembershipApplication.Status.SUBMITTED
            application.save()
            messages.success(request, "Application submitted successfully.")
            return redirect("member_dashboard")
    else:
        profile = request.user.profile
        form = MembershipApplicationForm(
            initial={
                "email": request.user.email,
                "mobile_number": profile.mobile_number,
                "full_name": request.user.get_full_name() or request.user.username,
            }
        )
    return render(request, "membership/application_form.html", {"form": form})


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
    member = get_object_or_404(Member.objects.select_related("application"), user=request.user)
    return render(request, "membership/card.html", {"member": member})


@login_required
def card_pdf(request):
    member = get_object_or_404(Member.objects.select_related("application"), user=request.user)
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
def reports(request):
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to view reports.")
        return redirect("member_dashboard")
    stats = {
        "total_members": Member.objects.count(),
        "active_members": Member.objects.filter(is_active=True).count(),
        "pending_applications": MembershipApplication.objects.filter(status=MembershipApplication.Status.SUBMITTED).count(),
        "pending_payments": MembershipApplication.objects.filter(status=MembershipApplication.Status.PAYMENT_SUBMITTED).count(),
        "districts": MembershipApplication.objects.values("district").annotate(total=Count("id")).order_by("district"),
        "license_types": MembershipApplication.objects.values("excise_license_type").annotate(total=Count("id")),
    }
    return render(request, "membership/reports.html", {"stats": stats})
