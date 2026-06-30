from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError

from main.models import SmsMessageLog


class Command(BaseCommand):
    help = "Print recipients for the most recent resident group SMS batch."

    def add_arguments(self, parser):
        parser.add_argument(
            "--window-minutes",
            type=int,
            default=30,
            help="How far back from the newest matching SMS to include logs with the same message body.",
        )
        parser.add_argument(
            "--include-staff",
            action="store_true",
            help="Also include staff copy SMS rows with the same message body.",
        )
        parser.add_argument(
            "--csv",
            action="store_true",
            help="Print comma-separated rows for export.",
        )

    def handle(self, *args, **options):
        latest = (
            SmsMessageLog.objects
            .filter(application__isnull=False)
            .exclude(body="")
            .order_by("-created_at")
            .first()
        )
        if not latest:
            raise CommandError("No resident SMS logs were found.")

        window_start = latest.created_at - timedelta(minutes=options["window_minutes"])
        logs = (
            SmsMessageLog.objects
            .select_related("application")
            .filter(body=latest.body, created_at__gte=window_start, created_at__lte=latest.created_at)
            .order_by("application__property__name", "application__space_label", "application__full_name", "recipient_label", "created_at")
        )
        if not options["include_staff"]:
            logs = logs.filter(application__isnull=False)

        rows = []
        for log in logs:
            rows.append({
                "id": log.id,
                "recipient": log.application.full_name if log.application else log.recipient_label or "Staff copy",
                "property": log.application.property.name if log.application and log.application.property else "",
                "unit": log.application.space_label if log.application else "",
                "phone": log.to_phone,
                "status": log.status,
                "provider_status": log.provider_status or "-",
                "error": log.error_message or "-",
                "created": log.created_at,
            })

        counts = {}
        for row in rows:
            counts[row["status"]] = counts.get(row["status"], 0) + 1

        if options["csv"]:
            self.stdout.write("id,recipient,property,unit,phone,status,provider_status,error,created")
            for row in rows:
                self.stdout.write(
                    ",".join(
                        [
                            str(row["id"]),
                            self.csv_cell(row["recipient"]),
                            self.csv_cell(row["property"]),
                            self.csv_cell(row["unit"]),
                            self.csv_cell(row["phone"]),
                            self.csv_cell(row["status"]),
                            self.csv_cell(row["provider_status"]),
                            self.csv_cell(row["error"]),
                            self.csv_cell(row["created"]),
                        ]
                    )
                )
            return

        self.stdout.write("Last house SMS recipient list")
        self.stdout.write("=============================")
        self.stdout.write(f"Newest SMS log: {latest.id} | {latest.created_at}")
        self.stdout.write(f"Subject/body preview: {latest.body.splitlines()[0][:120] if latest.body else '-'}")
        self.stdout.write("Totals: " + ", ".join(f"{status}={count}" for status, count in sorted(counts.items())) if counts else "Totals: none")
        self.stdout.write("")

        for row in rows:
            self.stdout.write(
                f"{row['id']} | {row['recipient']} | {row['property']} | {row['unit'] or '-'} | "
                f"{row['phone'] or '-'} | {row['status']} | provider_status={row['provider_status']} | error={row['error']}"
            )

    def csv_cell(self, value):
        text = str(value or "")
        return '"' + text.replace('"', '""') + '"'
