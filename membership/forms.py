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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                continue
            if isinstance(widget, forms.FileInput):
                widget.attrs.setdefault("hidden", True)
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


class PaymentProofForm(forms.ModelForm):
    class Meta:
        model = PaymentProof
        fields = ["screenshot", "utr_number", "payment_date", "bank_name", "remarks"]
        widgets = {
            "payment_date": forms.DateInput(attrs={"type": "date"}),
            "remarks": forms.Textarea(attrs={"rows": 3}),
        }
