import json
from datetime import date
from django.core.management.base import BaseCommand, CommandError
from main.late_fees import assess_late_fees


class Command(BaseCommand):
    help = "Assess each agreed late fee once, separately from rent."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--as-of", type=date.fromisoformat)

    def handle(self, *args, **options):
        if options["as_of"] and not options["dry_run"]:
            raise CommandError(
                "--as-of is available only with --dry-run; live assessments use the current date."
            )
        self.stdout.write(
            json.dumps(
                assess_late_fees(as_of=options["as_of"], dry_run=options["dry_run"])
            )
        )
