from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


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
        try:
            if "@" in identifier:
                return UserModel.objects.get(email__iexact=identifier)
            return UserModel.objects.get(profile__mobile_number=identifier)
        except UserModel.DoesNotExist:
            return None
        except UserModel.MultipleObjectsReturned:
            return None
