from django.db import models
from django.contrib.auth.models import AbstractUser


# -----------------------
# BLOG
# -----------------------

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

    def __str__(self):
        return f"{self.name}"


# -----------------------
# USER
# -----------------------

class User(AbstractUser):
    role = models.CharField(max_length=20, default="tenant")
    invite_code = models.CharField(max_length=6, blank=True, null=True)


# -----------------------
# PROPERTY
# -----------------------

class Property(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to="property_photos/", blank=True, null=True)

    def __str__(self):
        return self.name


class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="property_gallery/")
    caption = models.CharField(max_length=255, blank=True)


# -----------------------
# APPLICATION
# -----------------------

class HousingApplication(models.Model):
    property = models.ForeignKey(Property, on_delete=models.SET_NULL, null=True, blank=True)

    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    age = models.IntegerField()

    space_type = models.CharField(max_length=50, blank=True)
    space_label = models.CharField(max_length=50, blank=True)

    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rent_due_day = models.IntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)


# -----------------------
# DOCUMENTS
# -----------------------

class ApplicantDocument(models.Model):
    application = models.ForeignKey(HousingApplication, on_delete=models.CASCADE, related_name="documents")
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to="documents/", blank=True, null=True)


# -----------------------
# RENT HISTORY
# -----------------------

class RentHistory(models.Model):
    application = models.ForeignKey(HousingApplication, on_delete=models.CASCADE)
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    effective_date = models.DateField()


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
