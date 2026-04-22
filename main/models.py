from django.db import models

# Stores every uploaded homepage image
class HomepageImage(models.Model):
    image = models.ImageField(upload_to="homepage/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Homepage Image {self.id}"


# Stores which image is currently active on the homepage
class ActiveHomepageImage(models.Model):
    active_image = models.ForeignKey(
        HomepageImage,
        on_delete=models.CASCADE,
        related_name="active_selection"
    )

    def __str__(self):
        return f"Active Image: {self.active_image.id}"

    class Meta:
        verbose_name = "Active Homepage Image"
        verbose_name_plural = "Active Homepage Image"

