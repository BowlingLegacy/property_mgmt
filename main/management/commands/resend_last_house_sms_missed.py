from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from main.models import SmsMessageLog
from main.views import send_sms_message


DELIVERED_STATUSES = {"sent", "delivered"}


class Command(BaseCommand):
    help = "Resend the most recent resident group SMS only to residents who did not already get an accepted send."

    def add_arguments(self, parser):
        parser.add_argument(
            "--window-minutes",
            type=int,
            default=30,
            help="How far back from the newest matching SMS to include logs from the same original batch.",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Required to actually resend SMS messages.",
        )
        parser.add_argument(
            "--sent-by-email",
            default="",
            help="Optional staff user email to record as the sender.",
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
        batch_logs = (
            SmsMessageLog.objects
            .select_related("application", "application__property")
            .filter(
                application__isnull=False,
                body=latest.body,
                created_at__gte=window_start,
                created_at__lte=latest.created_at,
            )
            .order_by("application__property__name", "application__space_label", "application__full_name", "created_at")
        )

        if not batch_logs.exists():
            raise CommandError("No matching resident SMS batch logs were found.")

        sender = None
        sent_by_email = options["sent_by_email"].strip()
        if sent_by_email:
            sender = get_user_model().objects.filter(email__iexact=sent_by_email).first()
            if not sender:
                raise CommandError(f'No staff user found for "{sent_by_email}".')

        by_application = {}
        for log in batch_logs:
            by_application.setdefault(log.application_id, []).append(log)

        candidates = []
        already_sent = []
        not_eligible = []

        for logs in by_application.values():
            application = logs[0].application
            if any(log.status in DELIVERED_STATUSES for log in logs):
                already_sent.append(application)
                continue

            if not application.sms_opted_in or application.sms_opted_out_at or not application.phone:
                not_eligible.append(application)
                continue

            candidates.append(application)

        self.stdout.write("Resend last house SMS preview")
        self.stdout.write("=============================")
        self.stdout.write(f"Newest original log: {latest.id} | {latest.created_at}")
        self.stdout.write(f"Message preview: {latest.body.splitlines()[0][:120] if latest.body else '-'}")
        self.stdout.write(f"Original recipient files in window: {len(by_application)}")
        self.stdout.write(f"Already accepted/delivered: {len(already_sent)}")
        self.stdout.write(f"Eligible to resend: {len(candidates)}")
        self.stdout.write(f"Still not eligible: {len(not_eligible)}")
        self.stdout.write("")

        if candidates:
            self.stdout.write("Will resend to:")
            for application in candidates:
                property_name = application.property.name if application.property else "No Property"
                self.stdout.write(f"  app {application.id} | {property_name} | {application.space_label or '-'} | {application.full_name} | {application.phone}")
        else:
            self.stdout.write("No eligible missed recipients found.")

        if not options["confirm"]:
            self.stdout.write("")
            self.stdout.write("Dry run only. No SMS messages were sent.")
            self.stdout.write("Run again with --confirm to resend to the eligible missed recipients.")
            return

        sent = 0
        failed = 0
        self.stdout.write("")
        self.stdout.write("Resending:")
        for application in candidates:
            log = send_sms_message(application, latest.body, sender)
            if log.status == "sent":
                sent += 1
            else:
                failed += 1
            self.stdout.write(
                f"  {log.id} | {application.full_name} | {application.phone} | {log.status} | "
                f"provider={log.provider_message_id or '-'} | error={log.error_message or '-'}"
            )

        self.stdout.write(self.style.SUCCESS(f"Resend complete. Accepted by provider: {sent}. Failed/skipped: {failed}."))
