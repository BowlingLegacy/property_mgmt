from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import BlogComment, BlogPost, Property
from .permissions import is_assistant_admin, is_super_admin


class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ["property", "title", "body", "image"]
        widgets = {
            "property": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Post title"}),
            "body": forms.Textarea(attrs={"class": "form-control", "rows": 10, "placeholder": "Write the property update here..."}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user and not can_manage_all_property_blogs(user):
            self.fields["property"].queryset = Property.objects.filter(owner_email__iexact=user.email)
        else:
            self.fields["property"].queryset = Property.objects.all().order_by("name")


def can_manage_all_property_blogs(user):
    return user.is_staff or is_super_admin(user) or is_assistant_admin(user)


def can_manage_property_blog(user, property_obj):
    if can_manage_all_property_blogs(user):
        return True

    return bool(property_obj.owner_email and property_obj.owner_email.lower() == user.email.lower())


@login_required
def blog_manager(request):
    if can_manage_all_property_blogs(request.user):
        posts = BlogPost.objects.select_related("property", "author").all().order_by("-created_at")
        properties = Property.objects.all().order_by("name")
    else:
        properties = Property.objects.filter(owner_email__iexact=request.user.email).order_by("name")
        posts = BlogPost.objects.select_related("property", "author").filter(property__in=properties).order_by("-created_at")

    if not can_manage_all_property_blogs(request.user) and not properties.exists():
        return redirect("tenant_dashboard")

    pending_comments = BlogComment.objects.select_related("post", "post__property").filter(
        approved=False,
        post__in=posts,
    )

    return render(request, "property_blog_manager.html", {
        "posts": posts,
        "properties": properties,
        "pending_comments": pending_comments,
    })


@login_required
def blog_create(request):
    if not can_manage_all_property_blogs(request.user) and not Property.objects.filter(owner_email__iexact=request.user.email).exists():
        return redirect("tenant_dashboard")

    form = BlogPostForm(request.POST or None, request.FILES or None, user=request.user)

    if request.method == "POST" and form.is_valid():
        post = form.save(commit=False)

        if not post.property or not can_manage_property_blog(request.user, post.property):
            messages.error(request, "You do not have access to post for that property.")
            return redirect("property_blog_manager")

        post.author = request.user
        post.save()
        messages.success(request, "Property blog post created.")
        return redirect("property_blog_manager")

    return render(request, "property_blog_form.html", {"form": form})


@login_required
def approve_blog_comment(request, comment_id):
    comment = get_object_or_404(BlogComment.objects.select_related("post", "post__property"), id=comment_id)

    if not can_manage_property_blog(request.user, comment.post.property):
        return redirect("tenant_dashboard")

    comment.approved = True
    comment.save(update_fields=["approved"])
    messages.success(request, "Comment approved.")
    return redirect("property_blog_manager")
