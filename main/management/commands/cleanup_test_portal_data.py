from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from main.models import ApplicantDocument, HousingApplication, Payment, ResidentMessage, User


class Command(BaseCommand):
    help = (
        "Preview or delete test portal data: applications, resident messages, "
        "incoming documents, payment records, and non-staff tenant users linked "
        "to deleted applications."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Actually delete the selected records. Without this flag, this command is a dry run.",
        )
        parser.add_argument(
            "--preserve-email",
            action="append",
            default=[],
            help=(
                "Application/user email to keep. Can be supplied more than once, "
                "for example --preserve-email michael@example.com."
            ),
        )
        parser.add_argument(
            "--delete-files",
            action="store_true",
            help="Also delete uploaded document files from storage for deleted ApplicantDocument records.",
        )

    def handle(self, *args, **options):
        confirm = options["confirm"]
        delete_files = options["delete_files"]
        preserve_emails = {
            email.strip().lower()
            for email in options["preserve_email"]
            if email and email.strip()
        }

        applications = HousingApplication.objects.select_related("user").all()
        for email in preserve_emails:
            applications = applications.exclude(email__iexact=email)

        application_ids = list(applications.values_list("id", flat=True))
        linked_user_ids = set(
            applications
            .exclude(user__isnull=True)
            .values_list("user_id", flat=True)
        )

        users = User.objects.filter(
            id__in=linked_user_ids,
            is_staff=False,
            is_superuser=False,
            role="tenant",
        )

        for email in preserve_emails:
            users = users.exclude(email__iexact=email)

        documents = ApplicantDocument.objects.filter(application_id__in=application_ids)
        messages = ResidentMessage.objects.filter(application_id__in=application_ids)
        payments = Payment.objects.filter(application_id__in=application_ids)

        self.stdout.write("Portal cleanup preview")
        self.stdout.write("======================")
        self.stdout.write(f"Preserved emails: {', '.join(sorted(preserve_emails)) or 'none'}")
        self.stdout.write(f"Applications selected: {len(application_ids)}")
        self.stdout.write(f"Incoming documents selected: {documents.count()}")
        self.stdout.write(f"Resident messages selected: {messages.count()}")
        self.stdout.write(f"Payment records selected: {payments.count()}")
        self.stdout.write(f"Linked tenant users selected: {users.count()}")

        if not confirm:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Dry run only. No records were deleted."))
            self.stdout.write("Run again with --confirm to delete these records.")
            return

        if not application_ids:
            self.stdout.write(self.style.SUCCESS("No matching portal records found."))
            return

        document_files = []
        if delete_files:
            document_files = [
                document.file
                for document in documents
                if document.file
            ]

        selected_counts = {
            "applications": len(application_ids),
            "documents": documents.count(),
            "messages": messages.count(),
            "payments": payments.count(),
            "users": users.count(),
        }

        try:
            with transaction.atomic():
                payments.delete()
                messages.delete()
                documents.delete()
                applications.delete()
                users.delete()

            for document_file in document_files:
                document_file.delete(save=False)

        except Exception as exc:
            raise CommandError(f"Cleanup failed: {exc}") from exc

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Cleanup complete."))
        self.stdout.write(f"Applications deleted: {selected_counts['applications']}")
        self.stdout.write(f"Incoming documents deleted: {selected_counts['documents']}")
        self.stdout.write(f"Resident messages deleted: {selected_counts['messages']}")
        self.stdout.write(f"Payment records deleted: {selected_counts['payments']}")
        self.stdout.write(f"Linked tenant users deleted: {selected_counts['users']}")
        if delete_files:
            self.stdout.write(f"Uploaded document files deleted: {len(document_files)}")
