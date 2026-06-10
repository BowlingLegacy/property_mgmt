from django.core.management.base import BaseCommand

from main.models import SmsMessageLog


class Command(BaseCommand):
    help = "Print recent SMS delivery logs, including resident and staff copy messages."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=25)

    def handle(self, *args, **options):
        limit = options["limit"]
        logs = SmsMessageLog.objects.select_related("application").order_by("-created_at")[:limit]

        self.stdout.write("Recent SMS logs")
        self.stdout.write("===============")

        for log in logs:
            recipient = log.recipient_label
            if log.application:
                recipient = log.application.full_name
            recipient = recipient or "Unknown recipient"

            self.stdout.write(
                f"{log.id} | {recipient} | {log.to_phone} | {log.status} | "
                f"provider={log.provider_message_id or '-'} | "
                f"provider_status={log.provider_status or '-'} | "
                f"delivery_updated={log.delivery_updated_at or '-'} | "
                f"error={log.error_message or '-'}"
            )
