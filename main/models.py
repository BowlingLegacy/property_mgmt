from django.db import models
from django.contrib.auth.models import User

# Extend the built-in User model
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('new', 'New Applicant'),
            ('submitted', 'Application Submitted'),
            ('approved', 'Approved'),
            ('tenant', 'Tenant'),
        ],
        default='new'
    )

    def __str__(self):
        return self.user.username


# Rental Application Model
class Application(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=200)
    dob = models.DateField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    income = models.CharField(max_length=200)
    current_address = models.CharField(max_length=300)
    emergency_contact = models.CharField(max_length=200)
    background_info = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Application from {self.full_name}"
