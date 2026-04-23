from django.db import models
from django.contrib.auth.models import AbstractUser

# -----------------------------
# Custom User Model (Multi‑Role)
# -----------------------------
class User(AbstractUser):
    ROLE_CHOICES = [
        ("tenant", "Tenant / Applicant"),
        ("landlord", "Landlord / Property Manager"),
        ("admin", "Platform Admin"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="tenant")
invite_code = models.CharField(max_length=6, blank=True, null=True, unique=True)


# -----------------------------
# -----------------------------
# This will expand in Phase 2 with:
# - Photo gallery
# - Documents
# - Slug
# - Owner (landlord)
# - Address
# - Amenities
# - Age restrictions
# - Application link
# -----------------------------
class Property(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to="property_photos/", blank=True, null=True)

    def __str__(self):
        return self.name

