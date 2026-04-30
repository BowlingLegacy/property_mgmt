from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required

from .models import Property, BlogPost
from .forms import HousingApplicationForm, SignUpForm, InviteCodeForm


def home(request):
    properties = Property.objects.all()
    posts = BlogPost.objects.filter(published=True)[:3]
    return render(request, "home.html", {
        "properties": properties,
        "posts": posts,
    })


def creed(request):
    return render(request, "creed.html")


def apply(request):
    property_id = request.GET.get("property")

    if request.method == "POST":
        form = HousingApplicationForm(request.POST, request.FILES)

        if form.is_valid():
            application = form.save(commit=False)

            if property_id:
                try:
                    property_obj = Property.objects.get(id=property_id)
                    application.property = property_obj
                except Property.DoesNotExist:
                    pass

            application.save()
            return redirect("apply_success")
    else:
        form = HousingApplicationForm()

    return render(request, "apply.html", {"form": form})


def apply_success(request):
    return render(request, "apply_success.html")


def enter_invite_code(request):
    form = InviteCodeForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        invite_code = form.cleaned_data["invite_code"]
        request.session["invite_code"] = invite_code
        return redirect("apply")

    return render(request, "enter_invite_code.html", {"form": form})


@login_required
def landlord_dashboard(request):
    return render(request, "landlord_dashboard.html")


@login_required
def tenant_dashboard(request):
    return render(request, "tenant_dashboard.html")


def property_detail(request, pk):
    property_obj = get_object_or_404(Property, pk=pk)
    gallery_images = property_obj.images.all()

    return render(request, "property_detail.html", {
        "property": property_obj,
        "gallery_images": gallery_images,
    })


def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("tenant_dashboard")
    else:
        form = SignUpForm()

    return render(request, "signup.html", {"form": form})


def blog_detail(request, pk):
    post = get_object_or_404(BlogPost, pk=pk, published=True)
    return render(request, "blog_detail.html", {"post": post})
