from django import forms
from .models import HousingApplication

class HousingApplicationForm(forms.ModelForm):
    class Meta:
        model = HousingApplication
        fields = [
            'full_name',
            'phone',
            'email',
            'age',
            'income_source',
            'monthly_income',
            'housing_need',
            'additional_notes',
        ]
        widgets = {
            'housing_need': forms.Textarea(attrs={'rows': 4}),
            'additional_notes': forms.Textarea(attrs={'rows': 3}),
        }

