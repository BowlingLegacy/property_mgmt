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
            "income_source",
            "monthly_income",
            "housing_need",
            "additional_notes",
        ]
        widgets = {
            "housing_need": forms.Textarea(attrs={"rows": 4}),
            "additional_notes": forms.Textarea(attrs={"rows": 3}),
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
