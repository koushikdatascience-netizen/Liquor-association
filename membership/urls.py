from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.member_dashboard, name="member_dashboard"),
    path("apply/", views.application_create, name="application_create"),
    path("payments/<int:application_id>/upload/", views.payment_upload, name="payment_upload"),
    path("membership/card/", views.card, name="membership_card"),
    path("membership/card/download/", views.card_pdf, name="membership_card_pdf"),
    path("verify/<uuid:public_id>/", views.verify_member, name="verify_member"),
    path("reports/", views.reports, name="reports"),
]
