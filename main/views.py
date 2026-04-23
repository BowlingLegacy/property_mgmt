from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import User, Property


# -----------------------------------------
# Custom Signup Form (User + Role Selection)
# -----------------------------------------
class SignUpForm(UserCreationForm):
    role = forms.ChoiceField(choices=User.ROLE_CHOICES)

    class Meta:
        model = User
        fields = ("username", "email", "role", "password1", "password2")


# -------------------------
# Signup View
# -------------------------
def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)

            if user.role == "landlord":
                return redirect("landlord_dashboard")
            elif user.role == "tenant":
                return redirect("tenant_dashboard")

            return redirect("home")
    else:
        form = SignUpForm()

    return render(request, "signup.html", {"form": form})


# -------------------------
# Tenant Dashboard
# -------------------------
def tenant_dashboard(request):
    return render(request, "tenant_dashboard.html")


# -------------------------
# Landlord Dashboard
# -------------------------
def landlord_dashboard(request):
    return render(request, "landlord_dashboard.html")


# -------------------------
# Homepage (Property List)
# -------------------------
def home(request):
    properties = Property.objects.all()
    return render(request, "home.html", {"properties": properties})


# -------------------------
# Property Detail Page
# -------------------------
def property_detail(request, pk):
    property_obj = get_object_or_404(Property, pk=pk)
    return render(request, "property_detail.html", {"property": property_obj})
