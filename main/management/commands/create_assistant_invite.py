from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from main.invite_utils import send_portal_access_invite_email
from main.models import User


class Command(BaseCommand):
    help = "Create or refresh an assistant portal invite code."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True, help="Assistant full name.")
        parser.add_argument("--email", required=True, help="Assistant email address.")
        parser.add_argument(
            "--no-email",
            action="store_true",
            help="Create the setup code without attempting to email it.",
        )

    def handle(self, *args, **options):
        full_name = options["name"].strip()
        email = options["email"].strip().lower()

        if not full_name:
            raise CommandError("Assistant name is required.")

        if not email:
            raise CommandError("Assistant email is required.")

        user = User.objects.filter(email__iexact=email).first()
        created = False

        if user and user.has_usable_password():
            raise CommandError(
                f"{email} already has a completed portal account ({user.username}). "
                "Use password reset or edit that user instead of creating a new invite."
            )

        if not user:
            base_username = slugify(full_name) or "assistant"
            username = f"{base_username}-assistant"
            original_username = username
            counter = 1

            while User.objects.filter(username=username).exists():
                counter += 1
                username = f"{original_username}-{counter}"

            user = User.objects.create_user(
                username=username,
                email=email,
                password=None,
                role="assistant",
                is_staff=True,
                is_superuser=False,
            )
            created = True
        else:
            user.role = "assistant"
            user.is_staff = True
            user.is_superuser = False
            user.email = email
            user.save(update_fields=["role", "is_staff", "is_superuser", "email"])

        user.refresh_invite_code()

        email_sent = False
        email_error = ""
        if not options["no_email"]:
            try:
                email_sent = send_portal_access_invite_email(user, full_name, "Assistant")
            except Exception as exc:
                email_error = str(exc)

        self.stdout.write("Assistant invite ready.")
        self.stdout.write(f"User: {user.username}")
        self.stdout.write(f"Email: {user.email}")
        self.stdout.write(f"Created new pending user: {'yes' if created else 'no'}")
        self.stdout.write(f"Setup code: {user.invite_code}")
        self.stdout.write("Setup link: https://bowlinglegacy.com/enter-invite-code/")

        if options["no_email"]:
            self.stdout.write("Email not attempted because --no-email was used.")
        elif email_sent:
            self.stdout.write(self.style.SUCCESS("Invite email sent."))
        else:
            self.stdout.write(self.style.WARNING("Invite email was not confirmed. Use the backup setup code above."))
            if email_error:
                self.stdout.write(self.style.WARNING(f"Email error: {email_error}"))
