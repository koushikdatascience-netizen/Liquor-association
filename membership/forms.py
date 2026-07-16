from django import forms
from django.core.exceptions import ValidationError

from .models import MembershipApplication, PaymentProof, SitePaymentSettings

# Allowed upload types
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
DOCUMENT_TYPES = IMAGE_TYPES | {"application/pdf"}
DOCUMENT_EXTENSIONS = IMAGE_EXTENSIONS | {".pdf"}
MAX_IMAGE_UPLOAD_SIZE = 5 * 1024 * 1024
MAX_DOCUMENT_UPLOAD_SIZE = 15 * 1024 * 1024
MAX_PAYMENT_SCREENSHOT_SIZE = 5 * 1024 * 1024

IMAGE_MAGIC = (
    b"\xff\xd8\xff",  # JPEG
    b"\x89PNG",      # PNG
    b"GIF8",         # GIF
    b"RIFF",         # WEBP (RIFF....WEBP)
)
PDF_MAGIC = b"%PDF"


def _file_signature(uploaded_file):
    """Return 'pdf', 'image', or 'other' based on the file's magic bytes."""
    try:
        uploaded_file.seek(0)
        head = uploaded_file.read(8)
        uploaded_file.seek(0)
    except (OSError, ValueError):
        return "other"
    if head.startswith(PDF_MAGIC):
        return "pdf"
    if head.startswith(IMAGE_MAGIC):
        return "image"
    return "other"


def _has_allowed_extension(uploaded_file, allowed):
    name = (getattr(uploaded_file, "name", "") or "").lower()
    return any(name.endswith(ext) for ext in allowed)


def _file_size(uploaded_file):
    return getattr(uploaded_file, "size", 0) or 0


def _format_mb(size):
    return f"{size / (1024 * 1024):.0f} MB"


class MembershipApplicationForm(forms.ModelForm):
    image_upload_fields = {
        "passport_photo",
        "primary_delegate_photo",
        "alternate_delegate_photo",
    }

    document_fields = {
        "excise_license",
        "pan_card",
        "aadhaar_card",
        "partnership_deed",
        "gst_certificate",
        "address_proof",
    }

    class Meta:
        model = MembershipApplication
        fields = [
            "full_name",
            "nationality",
            "age",
            "gender",
            "residential_address",
            "pin_code",
            "whatsapp_number",
            "email",
            "residence_phone",
            "entity_type",
            "licence_category",
            "style_name",
            "excise_license_number",
            "partner_md_names",
            "office_phone",
            "shop_phone",
            "primary_delegate_name",
            "primary_delegate_designation",
            "primary_delegate_address",
            "primary_delegate_photo",
            "alternate_delegate_name",
            "alternate_delegate_role",
            "alternate_delegate_address",
            "alternate_delegate_photo",
            "excise_license",
            "passport_photo",
            "pan_card",
            "aadhaar_card",
            "partnership_deed",
            "gst_certificate",
            "address_proof",
            "declaration_accepted",
            "digital_signature",
        ]
        widgets = {
            "residential_address": forms.Textarea(attrs={"rows": 3}),
            "partner_md_names": forms.Textarea(attrs={"rows": 3}),
            "primary_delegate_address": forms.Textarea(attrs={"rows": 3}),
            "alternate_delegate_address": forms.Textarea(attrs={"rows": 3}),
            "declaration_accepted": forms.CheckboxInput(),
            "digital_signature": forms.HiddenInput(),
        }
        labels = {
            "full_name": "Full name (1-A)",
            "gender": "Sex",
            "residential_address": "Complete mailing address",
            "pin_code": "PIN",
            "whatsapp_number": "WhatsApp",
            "residence_phone": "Telephone (residence)",
            "entity_type": "Entity type",
            "licence_category": "Category of licence",
            "style_name": "Specific style name",
            "excise_license_number": "Licence ID",
            "partner_md_names": "Partner / MD names (if applicable)",
            "office_phone": "Telephone (office)",
            "shop_phone": "Telephone (shop / bar)",
            "primary_delegate_name": "Name",
            "primary_delegate_designation": "Designation",
            "primary_delegate_address": "Address",
            "primary_delegate_photo": "Photograph (23mm x 23mm)",
            "alternate_delegate_name": "Name",
            "alternate_delegate_role": "Relationship / Role",
            "alternate_delegate_address": "Address",
            "alternate_delegate_photo": "Photograph (23mm x 23mm)",
            "excise_license": "Licence copy",
            "passport_photo": "Proprietor / Partner photo",
            "pan_card": "PAN card",
            "aadhaar_card": "Aadhaar",
            "partnership_deed": "Partnership deed / MOA",
            "gst_certificate": "GST certificate",
            "address_proof": "Address proof",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        required_fields = {
            "full_name",
            "gender",
            "residential_address",
            "pin_code",
            "email",
            "excise_license_number",
            "declaration_accepted",
        }
        for field_name, field in self.fields.items():
            field.required = field_name in required_fields
        self.fields["nationality"].initial = self.fields["nationality"].initial or "Indian"
        self.fields["entity_type"].widget = forms.Select(
            choices=[
                ("", "Select entity type"),
                ("Proprietorship", "Proprietorship"),
                ("Partnership Firm", "Partnership Firm"),
                ("Private Limited Co.", "Private Limited Co."),
            ]
        )
        self.fields["licence_category"].widget = forms.Select(
            choices=[
                ("", "Select category"),
                ("Off", "Off"),
                ("On", "On"),
                ("CS", "CS"),
                ("Bar", "Bar"),
            ]
        )
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                continue
            if isinstance(widget, forms.FileInput):
                widget.attrs.setdefault("hidden", True)
                if field_name in self.image_upload_fields:
                    widget.attrs["accept"] = "image/jpeg,image/png,image/webp"
                else:
                    widget.attrs["accept"] = "application/pdf,image/jpeg,image/png,image/webp"
                continue
            if isinstance(widget, forms.Textarea):
                widget.attrs["class"] = "textarea"
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "select"
            else:
                widget.attrs["class"] = "input"

    def clean_declaration_accepted(self):
        accepted = self.cleaned_data["declaration_accepted"]
        if not accepted:
            raise forms.ValidationError("You must accept the declaration to submit.")
        return accepted

    def clean(self):
        cleaned_data = super().clean()

        # Photo fields: images only (JPG / JPEG / PNG / WebP).
        for field_name in self.image_upload_fields:
            if field_name not in self.files:
                continue
            uploaded_file = cleaned_data.get(field_name)
            if not uploaded_file:
                continue
            if _file_size(uploaded_file) > MAX_IMAGE_UPLOAD_SIZE:
                self.add_error(
                    field_name,
                    ValidationError(
                        f"Image is too large. Please upload an image up to {_format_mb(MAX_IMAGE_UPLOAD_SIZE)}."
                    ),
                )
                continue
            signature = _file_signature(uploaded_file)
            if signature != "image" or not _has_allowed_extension(uploaded_file, IMAGE_EXTENSIONS):
                self.add_error(
                    field_name,
                    ValidationError(
                        "File type not supported. Please upload only a JPG, JPEG or PNG image."
                    ),
                )

        # Document fields: PDF or image (JPG / JPEG / PNG / WebP) only.
        for field_name in self.document_fields:
            if field_name not in self.files:
                continue
            uploaded_file = cleaned_data.get(field_name)
            if not uploaded_file:
                continue
            if _file_size(uploaded_file) > MAX_DOCUMENT_UPLOAD_SIZE:
                self.add_error(
                    field_name,
                    ValidationError(
                        f"Document is too large. Please upload a file up to {_format_mb(MAX_DOCUMENT_UPLOAD_SIZE)}."
                    ),
                )
                continue
            signature = _file_signature(uploaded_file)
            if signature not in {"pdf", "image"} or not _has_allowed_extension(
                uploaded_file, DOCUMENT_EXTENSIONS
            ):
                self.add_error(
                    field_name,
                    ValidationError(
                        "File type not supported. Please upload only a PDF or a JPG, JPEG, PNG image."
                    ),
                )

        return cleaned_data


class ApplicationDocumentResubmissionForm(forms.ModelForm):
    image_upload_fields = MembershipApplicationForm.image_upload_fields
    document_fields = MembershipApplicationForm.document_fields

    class Meta:
        model = MembershipApplication
        fields = [
            "excise_license",
            "passport_photo",
            "primary_delegate_photo",
            "alternate_delegate_photo",
            "pan_card",
            "aadhaar_card",
            "partnership_deed",
            "gst_certificate",
            "address_proof",
        ]

    def __init__(self, *args, allowed_fields=None, **kwargs):
        super().__init__(*args, **kwargs)
        allowed = set(allowed_fields or self.fields)
        for field_name in list(self.fields):
            if field_name not in allowed:
                self.fields.pop(field_name)
                continue
            field = self.fields[field_name]
            field.required = False
            field.widget.attrs.setdefault("hidden", True)
            if field_name in self.image_upload_fields:
                field.widget.attrs["accept"] = "image/jpeg,image/png,image/webp"
            else:
                field.widget.attrs["accept"] = "application/pdf,image/jpeg,image/png,image/webp"

    def clean(self):
        cleaned_data = super().clean()

        # Validate only files uploaded in this request. Existing stored files may
        # be Cloudinary/R2 URLs without normal extensions and must be preserved.
        for field_name, uploaded_file in self.files.items():
            if field_name not in self.fields:
                continue
            if field_name in self.image_upload_fields:
                if _file_size(uploaded_file) > MAX_IMAGE_UPLOAD_SIZE:
                    self.add_error(
                        field_name,
                        ValidationError(
                            f"Image is too large. Please upload an image up to {_format_mb(MAX_IMAGE_UPLOAD_SIZE)}."
                        ),
                    )
                    continue
                if _file_signature(uploaded_file) != "image" or not _has_allowed_extension(uploaded_file, IMAGE_EXTENSIONS):
                    self.add_error(
                        field_name,
                        ValidationError("File type not supported. Please upload only a JPG, JPEG or PNG image."),
                    )
            else:
                if _file_size(uploaded_file) > MAX_DOCUMENT_UPLOAD_SIZE:
                    self.add_error(
                        field_name,
                        ValidationError(
                            f"Document is too large. Please upload a file up to {_format_mb(MAX_DOCUMENT_UPLOAD_SIZE)}."
                        ),
                    )
                    continue
                signature = _file_signature(uploaded_file)
                if signature not in {"pdf", "image"} or not _has_allowed_extension(uploaded_file, DOCUMENT_EXTENSIONS):
                    self.add_error(
                        field_name,
                        ValidationError("File type not supported. Please upload only a PDF or a JPG, JPEG, PNG image."),
                    )

        return cleaned_data


class PaymentProofForm(forms.ModelForm):
    class Meta:
        model = PaymentProof
        fields = ["screenshot", "utr_number", "payment_date", "bank_name", "remarks"]
        widgets = {
            "payment_date": forms.DateInput(attrs={"type": "date"}),
            "remarks": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_screenshot(self):
        uploaded_file = self.cleaned_data.get("screenshot")
        if not uploaded_file:
            return uploaded_file
        if _file_size(uploaded_file) > MAX_PAYMENT_SCREENSHOT_SIZE:
            raise ValidationError(
                f"Payment screenshot is too large. Please upload an image up to {_format_mb(MAX_PAYMENT_SCREENSHOT_SIZE)}."
            )
        if _file_signature(uploaded_file) != "image" or not _has_allowed_extension(
            uploaded_file, IMAGE_EXTENSIONS
        ):
            raise ValidationError(
                "File type not supported. Please upload only a JPG, JPEG or PNG payment screenshot."
            )
        return uploaded_file


class SitePaymentSettingsForm(forms.ModelForm):
    class Meta:
        model = SitePaymentSettings
        fields = ["account_name", "bank_name", "account_number", "ifsc", "upi_id", "qr_code", "membership_fee"]
        labels = {
            "account_name": "Account holder",
            "bank_name": "Bank",
            "account_number": "Account No.",
            "ifsc": "IFSC",
            "upi_id": "UPI ID",
            "qr_code": "UPI QR code",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.FileInput):
                field.widget.attrs["class"] = "input"
                field.widget.attrs["accept"] = "image/*"
            else:
                field.widget.attrs["class"] = "input"
