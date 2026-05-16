from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import (
    HousingApplication,
    User,
    BlogComment,
    FinancialUpload,
    ResidentMessage,
    ApplicantDocument,
    Property,
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


class LandlordCreateTenantForm(forms.Form):
    full_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Resident full legal name"}),
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Phone number"}),
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Resident email"}),
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Portal username"}),
    )
    temporary_password = forms.CharField(
        max_length=128,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Temporary password"}),
        help_text="Give this temporary password to the tenant. They can change it later.",
    )

    property = forms.ModelChoiceField(
        queryset=Property.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    space_type = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Room, Unit, Space, Suite"}),
    )
    space_label = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Example: A, 101, Suite 2"}),
    )

    monthly_rent = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )
    balance = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )
    rent_due_day = forms.IntegerField(
        initial=1,
        min_value=1,
        max_value=31,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    lease_start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    deposit_required = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        initial=450,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )
    deposit_paid = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )
    utility_monthly = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        initial=66,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )
    utility_balance = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )

    age = forms.IntegerField(
        initial=55,
        min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    income_source = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Income source"}),
    )
    monthly_income = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )
    housing_need = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Internal housing notes"}),
    )
    additional_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Landlord notes"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["property"].queryset = Property.objects.all().order_by("name")

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("That username is already in use.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email


class ResidentDocumentUploadForm(forms.ModelForm):
    class Meta:
        model = ApplicantDocument
        fields = ["document_type", "name", "file"]
        widgets = {
            "document_type": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Example: May pay stub, Social Security award letter, bank statement",
            }),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
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
