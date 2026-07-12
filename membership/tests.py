import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import MembershipApplication


TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
    MEDIA_ROOT=TEMP_MEDIA_ROOT,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ACCOUNT_REQUIRE_OTP_VERIFICATION=False,
)
class MembershipApplicationDocumentUploadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="abhi",
            email="abhi@example.com",
            password="pass12345",
            first_name="Abhi",
            last_name="Singh",
        )
        self.user.profile.mobile_number = "9876543210"
        self.user.profile.save(update_fields=["mobile_number"])
        self.client.force_login(self.user)

    def valid_payload(self):
        return {
            "full_name": "Abhi Singh",
            "nationality": "Indian",
            "age": "32",
            "gender": MembershipApplication.Gender.MALE,
            "residential_address": "Kolkata",
            "pin_code": "700001",
            "whatsapp_number": "9876543210",
            "email": "abhi@example.com",
            "residence_phone": "",
            "entity_type": "Proprietorship",
            "licence_category": "Off",
            "style_name": "Abhi Stores",
            "excise_license_number": "EX-123",
            "partner_md_names": "",
            "office_phone": "",
            "shop_phone": "",
            "primary_delegate_name": "Abhi Singh",
            "primary_delegate_designation": "Owner",
            "primary_delegate_address": "Kolkata",
            "alternate_delegate_name": "",
            "alternate_delegate_role": "",
            "alternate_delegate_address": "",
            "declaration_accepted": "on",
            "digital_signature": "Abhi Singh",
        }

    def upload_file(self, name="document.pdf", content=b"%PDF-1.4 test"):
        return SimpleUploadedFile(name, content, content_type="application/pdf")

    @patch("membership.views.notify_staff")
    def test_application_submit_saves_uploaded_documents_on_correct_application(self, _notify_staff):
        payload = self.valid_payload()
        payload["excise_license"] = self.upload_file("excise.pdf")
        payload["pan_card"] = self.upload_file("pan.pdf")

        response = self.client.post(reverse("application_create"), payload, follow=True)

        self.assertRedirects(response, reverse("member_dashboard"))
        application = MembershipApplication.objects.get(applicant=self.user)
        self.assertTrue(application.excise_license.name)
        self.assertTrue(application.pan_card.name)
        self.assertTrue(application.excise_license.storage.exists(application.excise_license.name))
        self.assertTrue(application.pan_card.storage.exists(application.pan_card.name))

    @patch("membership.views.notify_staff")
    def test_application_submit_does_not_require_typed_signature(self, _notify_staff):
        payload = self.valid_payload()
        payload.pop("digital_signature")
        payload["excise_license"] = self.upload_file("excise.pdf")

        response = self.client.post(reverse("application_create"), payload, follow=True)

        self.assertRedirects(response, reverse("member_dashboard"))
        application = MembershipApplication.objects.get(applicant=self.user)
        self.assertEqual(application.digital_signature, application.full_name)

    @patch("membership.views.notify_staff")
    def test_empty_file_submission_does_not_create_successful_application(self, _notify_staff):
        response = self.client.post(reverse("application_create"), self.valid_payload(), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(MembershipApplication.objects.filter(applicant=self.user).exists())
        self.assertContains(response, "Please upload at least one application document before submitting.")
        self.assertNotContains(response, "Application submitted successfully.")

    @patch("membership.views.notify_staff")
    def test_invalid_photo_upload_does_not_save_application(self, _notify_staff):
        payload = self.valid_payload()
        payload["passport_photo"] = self.upload_file("not-a-photo.pdf")

        response = self.client.post(reverse("application_create"), payload, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(MembershipApplication.objects.filter(applicant=self.user).exists())
        self.assertContains(response, "Upload a valid image.")
        self.assertNotContains(response, "Application submitted successfully.")

    @patch("membership.views.notify_staff")
    def test_document_resubmission_preserves_existing_documents_when_no_new_file_uploaded(self, _notify_staff):
        application = MembershipApplication.objects.create(
            applicant=self.user,
            status=MembershipApplication.Status.ADDITIONAL_DOCUMENTS,
            full_name="Abhi Singh",
            gender=MembershipApplication.Gender.MALE,
            mobile_number="9876543210",
            email="abhi@example.com",
            residential_address="Kolkata",
            shop_name="Abhi Stores",
            excise_license_number="EX-123",
            excise_license_type="Off",
            district="",
            primary_delegate_name="Abhi Singh",
            declaration_accepted=True,
            digital_signature="Abhi Singh",
        )
        application.excise_license.save("existing.pdf", self.upload_file("existing.pdf"), save=True)
        original_file_name = application.excise_license.name

        response = self.client.post(reverse("application_create"), self.valid_payload(), follow=True)

        self.assertRedirects(response, reverse("member_dashboard"))
        application.refresh_from_db()
        self.assertEqual(application.excise_license.name, original_file_name)
        self.assertTrue(application.excise_license.storage.exists(original_file_name))
        self.assertEqual(application.status, MembershipApplication.Status.SUBMITTED)

    def test_profile_documents_tab_shows_real_resubmit_form_for_legacy_rejected_status(self):
        application = MembershipApplication.objects.create(
            applicant=self.user,
            status="DOCUMENTS_REJECTED",
            full_name="Abhi Singh",
            gender=MembershipApplication.Gender.MALE,
            mobile_number="9876543210",
            email="abhi@example.com",
            residential_address="Kolkata",
            shop_name="Abhi Stores",
            excise_license_number="EX-123",
            excise_license_type="Off",
            district="",
            primary_delegate_name="Abhi Singh",
            declaration_accepted=True,
            digital_signature="Abhi Singh",
            rejected_documents=["excise_license"],
        )
        application.excise_license.save("existing.pdf", self.upload_file("existing.pdf"), save=True)

        response = self.client.get(reverse("member_profile"))

        self.assertContains(response, reverse("member_document_resubmit"))
        self.assertContains(response, 'name="excise_license"')
        self.assertNotContains(response, 'name="clear_excise_license"')
        self.assertNotContains(response, "Remove")
        self.assertContains(response, "Replace")

    @patch("membership.views.notify_staff")
    def test_profile_document_resubmit_replaces_only_requested_documents(self, _notify_staff):
        application = MembershipApplication.objects.create(
            applicant=self.user,
            status=MembershipApplication.Status.ADDITIONAL_DOCUMENTS,
            full_name="Abhi Singh",
            gender=MembershipApplication.Gender.MALE,
            mobile_number="9876543210",
            email="abhi@example.com",
            residential_address="Kolkata",
            shop_name="Abhi Stores",
            excise_license_number="EX-123",
            excise_license_type="Off",
            district="",
            primary_delegate_name="Abhi Singh",
            declaration_accepted=True,
            digital_signature="Abhi Singh",
            rejected_documents=["excise_license"],
        )
        application.excise_license.save("old-excise.pdf", self.upload_file("old-excise.pdf"), save=True)
        application.pan_card.save("old-pan.pdf", self.upload_file("old-pan.pdf"), save=True)
        old_excise_name = application.excise_license.name

        response = self.client.post(
            reverse("member_document_resubmit"),
            {
                "excise_license": self.upload_file("new-excise.pdf"),
                "clear_pan_card": "1",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("member_profile"))
        application.refresh_from_db()
        self.assertNotEqual(application.excise_license.name, old_excise_name)
        self.assertTrue(application.pan_card.name)
        self.assertEqual(application.status, MembershipApplication.Status.SUBMITTED)
        self.assertEqual(application.rejected_documents, [])

    @patch("membership.views.notify_member")
    def test_request_reupload_saves_selected_documents_for_member_ui(self, _notify_member):
        staff = User.objects.create_user(username="staff", password="pass12345", is_staff=True)
        application = MembershipApplication.objects.create(
            applicant=self.user,
            status=MembershipApplication.Status.SUBMITTED,
            full_name="Abhi Singh",
            gender=MembershipApplication.Gender.MALE,
            mobile_number="9876543210",
            email="abhi@example.com",
            residential_address="Kolkata",
            shop_name="Abhi Stores",
            excise_license_number="EX-123",
            excise_license_type="Off",
            district="",
            primary_delegate_name="Abhi Singh",
            declaration_accepted=True,
            digital_signature="Abhi Singh",
        )
        application.aadhaar_card.save("aadhaar.pdf", self.upload_file("aadhaar.pdf"), save=True)
        application.pan_card.save("pan.pdf", self.upload_file("pan.pdf"), save=True)

        self.client.force_login(staff)
        response = self.client.post(
            reverse("staff_application_action", args=[application.pk]),
            {
                "action": "request_documents",
                "remarks": "Aadhaar is unclear.",
                "rejected_documents": ["aadhaar_card"],
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("staff_application_detail", args=[application.pk]))
        application.refresh_from_db()
        self.assertEqual(application.status, MembershipApplication.Status.ADDITIONAL_DOCUMENTS)
        self.assertEqual(application.rejected_documents, ["aadhaar_card"])

        self.client.force_login(self.user)
        response = self.client.get(reverse("member_profile"))
        self.assertContains(response, 'name="aadhaar_card"')
        self.assertContains(response, "Aadhaar")
        self.assertNotContains(response, 'name="pan_card"')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        media_root = Path(TEMP_MEDIA_ROOT)
        shutil.rmtree(media_root, ignore_errors=True)
