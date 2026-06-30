from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from main.models import HousingApplication, Property, SignedDocument


ADDENDUM_TITLE = "Minor Occupancy / Responsible Adult Guarantor Addendum"


class Command(BaseCommand):
    help = "Issue a one-off minor occupancy addendum to a specific resident file."

    def add_arguments(self, parser):
        parser.add_argument("--resident-name", required=True, help="Resident or applicant name to receive the addendum.")
        parser.add_argument("--property-name", default="The Painted Lady Inn", help="Property name for the resident file.")
        parser.add_argument("--confirm", action="store_true", help="Required to create the addendum document.")

    def handle(self, *args, **options):
        property_obj = Property.objects.filter(name__iexact=options["property_name"]).first()
        if not property_obj:
            raise CommandError(f'Property not found: "{options["property_name"]}"')

        matches = HousingApplication.objects.filter(
            property=property_obj,
            full_name__icontains=options["resident_name"],
        ).order_by("-user_id", "-landlord_reviewed_at", "-created_at")

        if not matches.exists():
            raise CommandError(f'No resident file matched "{options["resident_name"]}" at {property_obj.name}.')

        if matches.count() > 1:
            self.stdout.write("Multiple matches found; using the most complete recent file:")
            for application in matches[:5]:
                self.stdout.write(
                    f"  app {application.id} | {application.full_name} | unit {application.space_label or '-'} | "
                    f"user {'yes' if application.user_id else 'no'}"
                )

        application = matches.first()
        existing = SignedDocument.objects.filter(
            application=application,
            document_type="other",
            title=ADDENDUM_TITLE,
            locked=False,
        ).first()

        self.stdout.write("Minor occupancy addendum preview")
        self.stdout.write("==============================")
        self.stdout.write(f"Property: {property_obj.name}")
        self.stdout.write(f"Resident file: app {application.id} | {application.full_name} | unit {application.space_label or '-'}")

        if existing:
            self.stdout.write(f"SKIP | unsigned addendum already exists | document {existing.id}")
            return

        if not options["confirm"]:
            self.stdout.write("Dry run only. No document was created.")
            self.stdout.write("Run again with --confirm to issue this one-off addendum.")
            return

        document = SignedDocument.objects.create(
            application=application,
            document_type="other",
            title=ADDENDUM_TITLE,
            lease_sent_date=timezone.localdate(),
            landlord_name="Michael Bowling",
            landlord_signature="Michael Bowling",
        )

        self.stdout.write(self.style.SUCCESS(f"Created addendum document {document.id}."))
