from django import forms
from .models import Application

class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = [
            'full_name',
            'dob',
            'phone',
            'email',
            'income',
            'current_address',
            'emergency_contact',
            'background_info',
        ]
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'background_info': forms.Textarea(attrs={'rows': 4}),
        }
