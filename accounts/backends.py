from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


def normalize_mobile(value):
    return "".join(ch for ch in value if ch.isdigit())


class EmailOrMobileBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = (username or kwargs.get("identifier") or "").strip()
        if not identifier or password is None:
            return None

        user = self.get_user_by_identifier(identifier)
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user

        return super().authenticate(request, username=username, password=password, **kwargs)

    def get_user_by_identifier(self, identifier):
        UserModel = get_user_model()
        identifier = identifier.strip()
        try:
            if "@" in identifier:
                return UserModel.objects.get(Q(email__iexact=identifier) | Q(username__iexact=identifier))

            normalized_mobile = normalize_mobile(identifier)
            lookup = Q(username__iexact=identifier) | Q(profile__mobile_number__iexact=identifier)
            if len(normalized_mobile) >= 10:
                lookup |= Q(profile__mobile_number__contains=normalized_mobile[-10:])
            users = UserModel.objects.select_related("profile").filter(lookup)
            for user in users:
                stored_mobile = normalize_mobile(getattr(user.profile, "mobile_number", ""))
                if normalized_mobile and (
                    stored_mobile == normalized_mobile or stored_mobile.endswith(normalized_mobile[-10:])
                ):
                    return user
            return users.first()
        except UserModel.DoesNotExist:
            return None
        except UserModel.MultipleObjectsReturned:
            return None
