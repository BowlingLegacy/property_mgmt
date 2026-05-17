from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render

from .models import BlogPost
from .views import staff_required


class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ["title", "body", "image"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Post title"}),
            "body": forms.Textarea(attrs={"class": "form-control", "rows": 10, "placeholder": "Write the journal update here..."}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


@login_required
@user_passes_test(staff_required)
def blog_manager(request):
    if not request.user.is_superuser and getattr(request.user, "role", "") != "admin":
        return redirect("tenant_dashboard")

    posts = BlogPost.objects.all().order_by("-created_at")
    return render(request, "superadmin_blog_manager.html", {"posts": posts})


@login_required
@user_passes_test(staff_required)
def blog_create(request):
    if not request.user.is_superuser and getattr(request.user, "role", "") != "admin":
        return redirect("tenant_dashboard")

    form = BlogPostForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Blog / journal post created successfully.")
        return redirect("superadmin_blog_manager")

    return render(request, "superadmin_blog_form.html", {"form": form})
