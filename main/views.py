from django.shortcuts import render, get_object_or_404
from .models import Property

def home(request):
    # Homepage no longer needs property list, but keeping this is harmless.
    properties = Property.objects.all()
    return render(request, "home.html", {"properties": properties})

def creed(request):
    return render(request, "creed.html")

def apply(request):
    return render(request, "apply.html")

def apply_success(request):
    return render(request, "apply_success.html")

def enter_invite_code(request):
    return render(request, "enter_invite_code.html")

def landlord_dashboard(request):
    return render(request, "landlord_dashboard.html")

def property_detail(request, pk):
    property_obj = get_object_or_404(Property, pk=pk)
    return render(request, "property_detail.html", {"property": property_obj})
