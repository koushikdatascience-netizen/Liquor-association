from django import forms
from django.core.exceptions import ValidationError

from .models import MembershipApplication, PaymentProof, SitePaymentSettings


class MembershipApplicationForm(forms.ModelForm):
    image_upload_fields = {
        "passport_photo",
        "primary_delegate_photo",
        "alternate_delegate_photo",
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
            "primary_delegate_name",
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
        for field_name in self.image_upload_fields:
            uploaded_file = cleaned_data.get(field_name)
            if not uploaded_file:
                continue
            content_type = getattr(uploaded_file, "content_type", "")
            if content_type and content_type not in {"image/jpeg", "image/png", "image/webp"}:
                self.add_error(
                    field_name,
                    ValidationError("Upload a valid JPG, PNG or WebP image."),
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


class SitePaymentSettingsForm(forms.ModelForm):
    class Meta:
        model = SitePaymentSettings
        fields = ["account_name", "bank_name", "account_number", "ifsc", "upi_id", "qr_code"]
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
