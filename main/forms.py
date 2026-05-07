from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import (
    HousingApplication,
    User,
    BlogComment,
    FinancialUpload,
    ResidentMessage,
)


class BlogCommentForm(forms.ModelForm):
    class Meta:
        model = BlogComment
        fields = ["name", "email", "comment"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Your name",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "Your email optional",
            }),
            "comment": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Write your comment...",
            }),
        }


class FinancialUploadForm(forms.ModelForm):
    class Meta:
        model = FinancialUpload
        fields = ["name", "file", "notes"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class ResidentMessageForm(forms.ModelForm):
    class Meta:
        model = ResidentMessage
        fields = ["message_type", "subject", "message"]
        widgets = {
            "message_type": forms.Select(attrs={"class": "form-select"}),
            "subject": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Subject",
            }),
            "message": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": "Write your request or message here...",
            }),
        }


class HousingApplicationForm(forms.ModelForm):
    class Meta:
        model = HousingApplication
        fields = [
            "full_name",
            "phone",
            "email",
            "age",
            "current_address",
            "current_address_length",
            "previous_address_1",
            "previous_address_1_length",
            "previous_address_2",
            "previous_address_2_length",
            "previous_address_3",
            "previous_address_3_length",
            "drivers_license_number",
            "has_valid_odl",
            "oregon_id_number",
            "id_upload",
            "income_source",
            "monthly_income",
            "employer_name",
            "employment_length",
            "previous_evictions",
            "in_recovery",
            "drug_of_choice",
            "on_parole",
            "parole_officer_name",
            "parole_officer_phone",
            "felony_history",
            "odoc_time_served",
            "reference_1_name",
            "reference_1_phone",
            "reference_1_relationship",
            "reference_1_type",
            "reference_2_name",
            "reference_2_phone",
            "reference_2_relationship",
            "reference_2_type",
            "housing_need",
            "additional_notes",
            "sobriety_acknowledgment",
            "unconditional_regard_acknowledgment",
        ]

        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "age": forms.NumberInput(attrs={"class": "form-control"}),

            "current_address": forms.TextInput(attrs={"class": "form-control"}),
            "current_address_length": forms.TextInput(attrs={"class": "form-control"}),
            "previous_address_1": forms.TextInput(attrs={"class": "form-control"}),
            "previous_address_1_length": forms.TextInput(attrs={"class": "form-control"}),
            "previous_address_2": forms.TextInput(attrs={"class": "form-control"}),
            "previous_address_2_length": forms.TextInput(attrs={"class": "form-control"}),
            "previous_address_3": forms.TextInput(attrs={"class": "form-control"}),
            "previous_address_3_length": forms.TextInput(attrs={"class": "form-control"}),

            "drivers_license_number": forms.TextInput(attrs={"class": "form-control"}),
            "has_valid_odl": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "oregon_id_number": forms.TextInput(attrs={"class": "form-control"}),
            "id_upload": forms.ClearableFileInput(attrs={"class": "form-control"}),

            "income_source": forms.TextInput(attrs={"class": "form-control"}),
            "monthly_income": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "employer_name": forms.TextInput(attrs={"class": "form-control"}),
            "employment_length": forms.TextInput(attrs={"class": "form-control"}),

            "previous_evictions": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "in_recovery": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "drug_of_choice": forms.TextInput(attrs={"class": "form-control"}),
            "on_parole": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "parole_officer_name": forms.TextInput(attrs={"class": "form-control"}),
            "parole_officer_phone": forms.TextInput(attrs={"class": "form-control"}),
            "felony_history": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "odoc_time_served": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            "reference_1_name": forms.TextInput(attrs={"class": "form-control"}),
            "reference_1_phone": forms.TextInput(attrs={"class": "form-control"}),
            "reference_1_relationship": forms.TextInput(attrs={"class": "form-control"}),
            "reference_1_type": forms.TextInput(attrs={"class": "form-control"}),

            "reference_2_name": forms.TextInput(attrs={"class": "form-control"}),
            "reference_2_phone": forms.TextInput(attrs={"class": "form-control"}),
            "reference_2_relationship": forms.TextInput(attrs={"class": "form-control"}),
            "reference_2_type": forms.TextInput(attrs={"class": "form-control"}),

            "housing_need": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "additional_notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "sobriety_acknowledgment": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "unconditional_regard_acknowledgment": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class InviteCodeForm(forms.Form):
    invite_code = forms.CharField(
        max_length=6,
        label="Enter your invite code",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter invite code",
        }),
    )


class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }
