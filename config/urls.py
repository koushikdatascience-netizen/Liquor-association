from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from membership import views as membership_views

admin.site.site_header = "Liquor Association Admin"
admin.site.site_title = "Liquor Association"
admin.site.index_title = "Membership Operations"

urlpatterns = [
    # Main admin panel: use the provided WBLiquor admin UI, not Django's default admin.
    path("admin/", membership_views.staff_dashboard, name="admin_dashboard"),
    path("django-admin/", admin.site.urls),
    path("", include("membership.urls")),
    path("accounts/", include("accounts.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
