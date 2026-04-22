from django.shortcuts import render, redirect
from .models import HomepageImage, ActiveHomepageImage
from .forms import HomepageImageForm, ActiveHomepageImageForm

# TEMPORARY HOMEPAGE — now loads the active image
def temp_home(request):
    active = ActiveHomepageImage.objects.first()
    hero = active.active_image if active else None
    return render(request, "home_temp.html", {"hero": hero})


# ADMIN — drag-and-drop uploader
def admin_upload_homepage_image(request):
    if request.method == "POST":
        form = HomepageImageForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("admin_select_homepage_image")
    else:
        form = HomepageImageForm()

    return render(request, "upload_homepage_image.html", {"form": form})


# ADMIN — choose which image is active
def admin_select_homepage_image(request):
    images = HomepageImage.objects.all()

    # Ensure there is always one ActiveHomepageImage row
    active_obj, created = ActiveHomepageImage.objects.get_or_create(id=1)

    if request.method == "POST":
        form = ActiveHomepageImageForm(request.POST, instance=active_obj)
        if form.is_valid():
            form.save()
            return redirect("home")
    else:
        form = ActiveHomepageImageForm(instance=active_obj)

    return render(request, "select_homepage_image.html", {
        "form": form,
        "images": images,
        "active": active_obj.active_image if active_obj else None
    })


# FUTURE — owner uploader (not used yet)
def owner_upload_image(request):
    if request.method == "POST":
        form = HomepageImageForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("home")
    else:
        form = HomepageImageForm()

    return render(request, "owner_upload_image.html", {"form": form})

