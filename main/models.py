from django.db import models

class Property(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to='property_photos/', blank=True, null=True)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.title

