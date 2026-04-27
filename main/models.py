from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    ROLE_CHOICES = [
        ("tenant", "Tenant / Applicant"),
        ("landlord", "Landlord / Property Manager"),
        ("admin", "Platform Admin"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="tenant")
    invite_code = models.CharField(max_length=6, blank=True, null=True, unique=True)

    def __str__(self):
        return self.username


class Property(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to="property_photos/", blank=True, null=True)

    def __str__(self):
        return self.name


class PropertyImage(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="images"
    )
    image = models.ImageField(upload_to="property_gallery/")
    caption = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.property.name} Image"


class HousingApplication(models.Model):
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    age = models.PositiveIntegerField()
    income_source = models.CharField(max_length=255)
    monthly_income = models.DecimalField(max_digits=10, decimal_places=2)
    housing_need = models.TextField()
    additional_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


# 🔥 BLOG / JOURNAL MODEL (THIS WAS MISSING)
class BlogPost(models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    image = models.ImageField(upload_to="blog_images/", blank=True, null=True)
    published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
