from django.conf import settings
from django.db import models
from django.utils.text import slugify


class OwnerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owner_profile')
    company_name = models.CharField(max_length=255, blank=True)
    # You are the Site Controller globally, so no per-owner site controller fields needed.

    def __str__(self):
        return self.company_name or self.user.get_username()


class Property(models.Model):
    owner = models.ForeignKey(OwnerProfile, on_delete=models.CASCADE, related_name='properties')
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=50, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    amenities = models.TextField(blank=True)
    main_image_url = models.URLField(blank=True)  # fallback if no primary PropertyPhoto

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            counter = 1
            while Property.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def primary_photo(self):
        primary = self.photos.filter(is_primary=True).first()
        if primary:
            return primary
        return self.photos.first()


class PropertyPhoto(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='photos')
    image_url = models.URLField(blank=True)  # URL now; file upload can be added later
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_primary', 'id']

    def __str__(self):
        return f"{self.property.name} photo"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_primary:
            PropertyPhoto.objects.filter(property=self.property).exclude(pk=self.pk).update(is_primary=False)


class Unit(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='units')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    rent = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.property.name} - {self.name}"


class OwnerDocument(models.Model):
    DOCUMENT_TYPES = [
        ('application', 'Application Form'),
        ('lease', 'Lease Agreement'),
        ('rules', 'House Rules'),
        ('other', 'Other'),
    ]

    owner = models.ForeignKey(OwnerProfile, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='other')
    document_url = models.URLField()  # URL now; file upload later
    show_to_public = models.BooleanField(default=False)
    show_to_applicants = models.BooleanField(default=True)
    show_to_residents = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.owner} - {self.title}"


class Application(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='applications')
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name='applications')
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pending')  # pending, approved, rejected

    def __str__(self):
        return f"{self.full_name} - {self.property.name}"


class BackgroundCheckRequest(models.Model):
    STATUS_CHOICES = [
        ('pending_not_connected', 'Pending – Service Not Connected'),
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='background_checks')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending_not_connected')

    def __str__(self):
        return f"Background check for {self.application.full_name} ({self.application.property.name})"

