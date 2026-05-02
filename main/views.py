from django.shortcuts import render, redirect, get_object_or_404
from .models import Property, BlogPost, BlogComment
from .forms import BlogCommentForm


def home(request):
    properties = Property.objects.all()

    # 🔥 FIX: removed published=True
    posts = BlogPost.objects.all().order_by("-created_at")[:5]

    return render(request, "home.html", {
        "properties": properties,
        "posts": posts,
    })


def add_blog_comment(request, post_id):
    post = get_object_or_404(BlogPost, id=post_id)

    if request.method == "POST":
        form = BlogCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.approved = False
            comment.save()

    return redirect("home")
