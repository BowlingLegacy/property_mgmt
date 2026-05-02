
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils import timezone

from main.models import HousingApplication, ApplicantDocument
from reportlab.pdfgen import canvas
from io import BytesIO


class Command(BaseCommand):
    help = "Backfill PDFs for existing housing applications"

    def handle(self, *args, **kwargs):
        applications = HousingApplication.objects.all()

        created_count = 0

        for app in applications:

            # Skip if PDF already exists
            if ApplicantDocument.objects.filter(
                application=app,
                document_type="application_pdf"
            ).exists():
                continue

            buffer = BytesIO()
            p = canvas.Canvas(buffer)

            # Simple PDF layout (can improve later)
            p.drawString(100, 800, f"Application: {app.full_name}")
            p.drawString(100, 780, f"Email: {app.email}")
            p.drawString(100, 760, f"Phone: {app.phone}")
            p.drawString(100, 740, f"Income: {app.monthly_income}")
            p.drawString(100, 720, f"Submitted: {app.created_at}")

            p.showPage()
            p.save()

            buffer.seek(0)

            file_name = f"{app.full_name.replace(' ', '_')}_application.pdf"

            document = ApplicantDocument.objects.create(
                application=app,
                document_type="application_pdf",
                name="Application PDF",
                status="locked",
                locked=True,
                submitted_at=timezone.now(),
            )

            document.file.save(
                file_name,
                ContentFile(buffer.read()),
                save=True
            )

            created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Created {created_count} application PDFs")
        )
