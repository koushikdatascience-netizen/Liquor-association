from django import forms

from .models import MembershipApplication, PaymentProof


class MembershipApplicationForm(forms.ModelForm):
    class Meta:
        model = MembershipApplication
        exclude = ["applicant", "status", "remarks"]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "residential_address": forms.Textarea(attrs={"rows": 3}),
            "office_address": forms.Textarea(attrs={"rows": 3}),
            "declaration_accepted": forms.CheckboxInput(),
        }

    def clean_declaration_accepted(self):
        accepted = self.cleaned_data["declaration_accepted"]
        if not accepted:
            raise forms.ValidationError("You must accept the declaration to submit.")
        return accepted


class PaymentProofForm(forms.ModelForm):
    class Meta:
        model = PaymentProof
        fields = ["screenshot", "utr_number", "payment_date", "bank_name", "remarks"]
        widgets = {
            "payment_date": forms.DateInput(attrs={"type": "date"}),
            "remarks": forms.Textarea(attrs={"rows": 3}),
        }
