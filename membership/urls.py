from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.member_dashboard, name="member_dashboard"),
    path("apply/", views.application_create, name="application_create"),
    path("payments/<int:application_id>/upload/", views.payment_upload, name="payment_upload"),
    path("membership/card/", views.card, name="membership_card"),
    path("membership/card/download/", views.card_pdf, name="membership_card_pdf"),
    path("membership/card/image/", views.card_image, name="membership_card_image"),
    path("membership/certificate/", views.membership_certificate, name="membership_certificate"),
    path("payments/receipt/", views.payment_receipt, name="payment_receipt"),
    path("verify/<uuid:public_id>/", views.verify_member, name="verify_member"),
    path("reports/", views.reports, name="reports"),
    path("reports/export/<str:report_type>/<str:file_type>/", views.export_report, name="export_report"),
    path(
        "admin-documents/<str:source>/<int:pk>/<str:field_name>/",
        views.admin_document_review,
        name="admin_document_review",
    ),
]
