from io import BytesIO

from django.core.files.base import ContentFile
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from .models import Property, BlogPost, HousingApplication, ApplicantDocument
from .forms import HousingApplicationForm, SignUpForm, InviteCodeForm

from django.shortcuts import redirect, get_object_or_404
from .models import BlogPost
from .forms import BlogCommentForm

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

def create_application_pdf(application):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)

    y = 750

    def line(text):
        nonlocal y
        p.drawString(50, y, str(text))
        y -= 18

    p.setFont("Helvetica-Bold", 14)
    line("Painted Lady Inn - Housing Application")

    p.setFont("Helvetica", 10)
    line(f"Name: {application.full_name}")
    line(f"Phone: {application.phone}")
    line(f"Email: {application.email}")
    line(f"Age: {application.age}")
    line("")
    line(f"Current Address: {application.current_address}")
    line(f"Length at Address: {application.current_address_length}")
    line("")
    line(f"Income Source: {application.income_source}")
    line(f"Monthly Income: {application.monthly_income}")
    line(f"Employer: {application.employer_name}")
    line(f"Employment Length: {application.employment_length}")
    line("")
    line(f"Previous Evictions: {application.previous_evictions}")
    line(f"In Recovery: {application.in_recovery}")
    line(f"Drug of Choice: {application.drug_of_choice}")
    line(f"On Parole: {application.on_parole}")
    line(f"Felony History: {application.felony_history}")
    line("")
    line(f"Housing Need: {application.housing_need}")
    line(f"Additional Notes: {application.additional_notes}")
    line("")
    line("Certification: I certify this information is true to the best of my knowledge.")

    p.showPage()
    p.save()

    buffer.seek(0)
    return buffer


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

            pdf_buffer = create_application_pdf(application)
            filename = f"application_{application.id}_{application.full_name.replace(' ', '_')}.pdf"

            document = ApplicantDocument(
                application=application,
                document_type="application_pdf",
                name=f"{application.full_name} Application PDF",
                status="locked",
                locked=True,
                signed_at=timezone.now(),
                submitted_at=timezone.now(),
            )

            document.file.save(
                filename,
                ContentFile(pdf_buffer.read()),
                save=True
            )

            return redirect("apply_success")
    else:
        form = HousingApplicationForm()

    return render(request, "apply.html", {"form": form})


def apply_success(request):
    return render(request, "apply_success.html")


def printable_application(request, pk):
    application = get_object_or_404(HousingApplication, pk=pk)
    return render(request, "printable_application.html", {
        "application": application,
    })


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
