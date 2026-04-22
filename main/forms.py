from django import forms
from .models import HomepageImage, ActiveHomepageImage

# Drag-and-drop upload form
class HomepageImageForm(forms.ModelForm):
    class Meta:
        model = HomepageImage
        fields = ["image"]


# Admin selects which image is active
class ActiveHomepageImageForm(forms.ModelForm):
    class Meta:
        model = ActiveHomepageImage
        fields = ["active_image"]
class HomepageImageSelectForm(forms.Form):
    image = forms.ModelChoiceField(
        queryset=HomepageImage.objects.all(),
        widget=forms.RadioSelect,
        empty_label=None
    )
