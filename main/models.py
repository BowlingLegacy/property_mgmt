from django.db import models

class HousingApplication(models.Model):
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=50)
    email = models.EmailField(blank=True)
    age = models.IntegerField(blank=True, null=True)
    income_source = models.CharField(max_length=200, blank=True)
    monthly_income = models.CharField(max_length=100, blank=True)
    housing_need = models.TextField()
    additional_notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.phone})"
