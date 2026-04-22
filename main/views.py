from django.shortcuts import render, redirect
from .forms import HousingApplicationForm

def home(request):
    return render(request, "home.html")

def apply(request):
    if request.method == "POST":
        form = HousingApplicationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("apply_success")
    else:
        form = HousingApplicationForm()

    return render(request, "apply.html", {"form": form})

def apply_success(request):
    return render(request, "apply_success.html")
