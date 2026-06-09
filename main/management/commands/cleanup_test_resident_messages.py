from django.core.management.base import BaseCommand

from main.models import ResidentMessage


class Command(BaseCommand):
    help = "Delete resident messages with test subject lines from resident files."

    DEFAULT_SUBJECTS = ["test", "testing", "retest", "final test"]

    def add_arguments(self, parser):
        parser.add_argument(
            "--subject",
            action="append",
            dest="subjects",
            help="Exact subject to remove. Can be provided multiple times. Defaults to common test subjects.",
        )
        parser.add_argument(
            "--property-name",
            help="Limit cleanup to one property.",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Actually delete matching resident messages.",
        )

    def handle(self, *args, **options):
        subjects = options["subjects"] or self.DEFAULT_SUBJECTS
        normalized_subjects = {subject.strip().lower() for subject in subjects if subject.strip()}

        messages = (
            ResidentMessage.objects
            .select_related("application", "application__property")
            .prefetch_related("replies")
            .order_by("-created_at")
        )

        if options["property_name"]:
            messages = messages.filter(application__property__name=options["property_name"])

        selected = [
            message for message in messages
            if message.subject.strip().lower() in normalized_subjects
        ]

        self.stdout.write("Resident test message cleanup preview")
        self.stdout.write("====================================")
        self.stdout.write(f"Subjects: {', '.join(sorted(normalized_subjects))}")
        if options["property_name"]:
            self.stdout.write(f"Property: {options['property_name']}")
        self.stdout.write(f"Messages selected: {len(selected)}")
        self.stdout.write("")

        for message in selected:
            property_name = message.application.property.name if message.application and message.application.property else "No Property"
            resident_name = message.application.full_name if message.application else "No Resident"
            self.stdout.write(
                f"DELETE | message {message.id} | {property_name} | {resident_name} | "
                f"{message.created_at:%Y-%m-%d %H:%M} | {message.subject!r} | replies {message.replies.count()}"
            )

        if not options["confirm"]:
            self.stdout.write("")
            self.stdout.write("Dry run only. No messages were deleted.")
            self.stdout.write("Run again with --confirm to delete these messages.")
            return

        deleted_count = 0
        for message in selected:
            message.delete()
            deleted_count += 1

        self.stdout.write("")
        self.stdout.write("Resident test message cleanup complete.")
        self.stdout.write(f"Messages deleted: {deleted_count}")
