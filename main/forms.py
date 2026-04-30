from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import HousingApplication, User


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
            "housing_need": forms.Textarea(attrs={"rows": 4}),
            "additional_notes": forms.Textarea(attrs={"rows": 3}),
            "previous_evictions": forms.Textarea(attrs={"rows": 3}),
            "felony_history": forms.Textarea(attrs={"rows": 3}),
        }


class InviteCodeForm(forms.Form):
    invite_code = forms.CharField(
        max_length=6,
        label="Enter your invite code",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )


class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]
