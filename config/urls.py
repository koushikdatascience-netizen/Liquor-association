from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.views.generic import RedirectView
from membership import views as membership_views

urlpatterns = [
    # Main admin panel: use the provided WBLiquor admin UI, not Django's default admin.
    path("admin/", membership_views.staff_dashboard, name="admin_dashboard"),
    path("django-admin/", RedirectView.as_view(pattern_name="staff_dashboard", permanent=False)),
    path("django-admin/<path:unused>", RedirectView.as_view(pattern_name="staff_dashboard", permanent=False)),
    path("", include("membership.urls")),
    path("accounts/", include("accounts.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
