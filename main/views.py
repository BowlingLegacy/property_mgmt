from django.shortcuts import render, redirect
from .models import HomepageImage
from .forms import HomepageImageForm, HomepageImageSelectForm

def admin_upload_homepage_image(request):
    if request.method == "POST":
        form = HomepageImageForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("admin_select_homepage_image")
    else:
        form = HomepageImageForm()

    return render(request, "upload_homepage_image.html", {"form": form})


def admin_select_homepage_image(request):
    images = HomepageImage.objects.all()
    active = HomepageImage.objects.filter(is_active=True).first()

    if request.method == "POST":
        form = HomepageImageSelectForm(request.POST)
        if form.is_valid():
            HomepageImage.objects.update(is_active=False)
            selected = form.cleaned_data["image"]
            selected.is_active = True
            selected.save()
            return redirect("home_temp")
    else:
        form = HomepageImageSelectForm()

    return render(
        request,
        "select_homepage_image.html",
        {"form": form, "images": images, "active": active},
    )


def home_temp(request):
    hero = HomepageImage.objects.filter(is_active=True).first()
    return render(request, "home_temp.html", {"hero": hero})
