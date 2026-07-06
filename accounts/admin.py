from django.contrib import admin, messages

from .models import OTPVerification, Profile


@admin.action(description="Give selected users full admin privileges")
def make_full_admin(modeladmin, request, queryset):
    if not request.user.is_superuser:
        modeladmin.message_user(request, "Only the main superuser can promote admins.", messages.ERROR)
        return
    count = 0
    for profile in queryset.select_related("user"):
        profile.role = Profile.Role.ADMIN
        profile.save(update_fields=["role"])
        user = profile.user
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save(update_fields=["is_staff", "is_superuser", "is_active"])
        count += 1
    modeladmin.message_user(request, f"{count} user(s) promoted to full admin.", messages.SUCCESS)


@admin.action(description="Remove selected users' admin privileges")
def remove_admin_access(modeladmin, request, queryset):
    if not request.user.is_superuser:
        modeladmin.message_user(request, "Only the main superuser can remove admin access.", messages.ERROR)
        return
    count = 0
    for profile in queryset.select_related("user"):
        if profile.user == request.user:
            continue
        profile.role = Profile.Role.MEMBER if hasattr(profile.user, "member_record") else Profile.Role.APPLICANT
        profile.save(update_fields=["role"])
        user = profile.user
        user.is_staff = False
        user.is_superuser = False
        user.save(update_fields=["is_staff", "is_superuser"])
        count += 1
    modeladmin.message_user(request, f"Admin access removed for {count} user(s).", messages.WARNING)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "mobile_number", "role", "is_staff", "is_superuser", "mobile_verified", "email_verified")
    list_filter = ("role", "mobile_verified", "email_verified")
    search_fields = ("user__username", "user__email", "mobile_number")
    actions = [make_full_admin, remove_admin_access]

    @admin.display(boolean=True, ordering="user__is_staff")
    def is_staff(self, obj):
        return obj.user.is_staff

    @admin.display(boolean=True, ordering="user__is_superuser")
    def is_superuser(self, obj):
        return obj.user.is_superuser


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ("user", "channel", "purpose", "destination", "expires_at", "verified_at", "attempts", "created_at")
    list_filter = ("channel", "purpose", "verified_at", "created_at")
    search_fields = ("user__username", "user__email", "destination")
    readonly_fields = ("code_hash", "created_at", "verified_at", "attempts")
