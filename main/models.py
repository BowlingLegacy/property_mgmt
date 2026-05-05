from django.db import models
from django.contrib.auth.models import AbstractUser


# -----------------------
# USER
# -----------------------

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


# -----------------------
# PROPERTY
# -----------------------

class Property(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


# -----------------------
# APPLICATION
# -----------------------

class HousingApplication(models.Model):
    property = models.ForeignKey(Property, on_delete=models.SET_NULL, null=True, blank=True)

    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    age = models.PositiveIntegerField()

    # NEW SPACE SYSTEM
    space_type = models.CharField(max_length=50, blank=True)
    space_label = models.CharField(max_length=50, blank=True)

    # RENT
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    rent_due_day = models.IntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


# -----------------------
# DOCUMENTS
# -----------------------

class ApplicantDocument(models.Model):
    application = models.ForeignKey(HousingApplication, on_delete=models.CASCADE, related_name="documents")
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to="documents/", blank=True, null=True)
    status = models.CharField(max_length=50, default="uploaded")

    def __str__(self):
        return self.name


# -----------------------
# RENT HISTORY
# -----------------------

class RentHistory(models.Model):
    application = models.ForeignKey(HousingApplication, on_delete=models.CASCADE)
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    effective_date = models.DateField()

    def __str__(self):
        return f"{self.application.full_name} - {self.rent_amount}"


# -----------------------
# PAYMENTS
# -----------------------

class Payment(models.Model):
    application = models.ForeignKey(HousingApplication, on_delete=models.CASCADE)

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, default="pending")

    stripe_session_id = models.CharField(max_length=255, blank=True)
    stripe_payment_intent = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.application.full_name} - {self.amount}"
