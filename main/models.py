from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.mail import send_mail
from django.conf import settings
import random
import string


class BlogPost(models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    image = models.ImageField(upload_to="blog_images/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class BlogComment(models.Model):
    post = models.ForeignKey("BlogPost", on_delete=models.CASCADE, related_name="comments")
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    comment = models.TextField()
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comment by {self.name} on {self.post.title}"


class User(AbstractUser):
    ROLE_CHOICES = [
        ("tenant", "Tenant / Applicant"),
        ("landlord", "Landlord / Property Manager"),
        ("assistant", "Assistant"),
        ("admin", "Platform Admin"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="tenant")
    invite_code = models.CharField(max_length=6, blank=True, null=True, unique=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        if not self.invite_code:
            self.invite_code = self.generate_unique_code()

        if self.role == "tenant":
            self.is_staff = False
            self.is_superuser = False

        super().save(*args, **kwargs)

        if is_new and self.email and self.invite_code:
            send_mail(
                "Your Bowling Legacy Resident Portal Access Code",
                f"""Hello {self.username},

Your Bowling Legacy resident portal access code is:

{self.invite_code}

Portal login:
https://bowlinglegacy.com/login/

Thank you,
Bowling Legacy Housing
""",
                getattr(settings, "DEFAULT_FROM_EMAIL", None),
                [self.email],
                fail_silently=True,
            )

    def generate_unique_code(self):
        while True:
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if not User.objects.filter(invite_code=code).exists():
                return code

    def __str__(self):
        return self.username


class Property(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to="property_photos/", blank=True, null=True)

    owner_email = models.EmailField(blank=True)

    unit_size = models.CharField(max_length=100, blank=True)
    cable_ready = models.BooleanField(default=True)
    available_date = models.DateField(blank=True, null=True)
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    utilities_cost = models.CharField(max_length=255, blank=True)

    AVAILABILITY_CHOICES = [
        ("available", "Available Now"),
        ("waitlist", "Waitlist Open"),
        ("full", "Currently Full"),
    ]

    availability_status = models.CharField(
        max_length=20,
        choices=AVAILABILITY_CHOICES,
        default="full",
    )

    availability_message = models.CharField(
        max_length=255,
        default="Join Waitlist for Availability",
    )

    def __str__(self):
        return self.name
