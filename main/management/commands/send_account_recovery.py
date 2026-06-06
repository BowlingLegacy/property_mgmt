from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from main.models import HousingApplication, User


class Command(BaseCommand):
    help = "Email a portal user their username and a password reset link."

    def add_arguments(self, parser):
        lookup = parser.add_mutually_exclusive_group(required=True)
        lookup.add_argument("--name", help="Resident or portal user name to search for.")
        lookup.add_argument("--email", help="Resident or portal user email to search for.")
        lookup.add_argument("--username", help="Exact portal username to recover.")
        parser.add_argument(
            "--site-url",
            default="https://bowlinglegacy.com",
            help="Public site URL used to build the reset link.",
        )
        parser.add_argument(
            "--no-email",
            action="store_true",
            help="Print the recovery details without sending the email.",
        )

    def handle(self, *args, **options):
        user = self._resolve_user(options)
        if not user.email:
            raise CommandError(f"User {user.username} does not have an email address.")

        reset_url = self._build_reset_url(user, options["site_url"])
        display_name = self._display_name_for_user(user)

        subject = "Bowling Legacy portal account recovery"
        body = (
            f"Hello {display_name},\n\n"
            "We received a request to help you get back into your Bowling Legacy resident portal.\n\n"
            f"Your username is: {user.username}\n\n"
            "Use this link to reset your password:\n"
            f"{reset_url}\n\n"
            "If you did not ask for this, you can ignore this email and your password will not change.\n"
        )

        if not options["no_email"]:
            send_mail(
                subject,
                body,
                getattr(settings, "DEFAULT_FROM_EMAIL", None),
                [user.email],
                fail_silently=False,
            )

        self.stdout.write("Account recovery ready.")
        self.stdout.write(f"Username: {user.username}")
        self.stdout.write(f"Email: {user.email}")
        self.stdout.write(f"Password reset link: {reset_url}")
        if options["no_email"]:
            self.stdout.write("Email not sent because --no-email was used.")
        else:
            self.stdout.write(self.style.SUCCESS("Recovery email sent."))

    def _resolve_user(self, options):
        if options["username"]:
            try:
                return User.objects.get(username=options["username"].strip())
            except User.DoesNotExist as exc:
                raise CommandError("No user found with that username.") from exc

        if options["email"]:
            email = options["email"].strip()
            users = list(User.objects.filter(email__iexact=email).order_by("id"))
            if not users:
                users = [
                    app.user
                    for app in HousingApplication.objects.select_related("user")
                    .filter(email__iexact=email, user__isnull=False)
                    .order_by("id")
                ]
            return self._one_user_or_error(users)

        name = options["name"].strip()
        users = [
            app.user
            for app in HousingApplication.objects.select_related("user")
            .filter(full_name__icontains=name, user__isnull=False)
            .order_by("property__name", "space_label", "id")
        ]
        if not users:
            users = list(User.objects.filter(username__icontains=name).order_by("id"))
        return self._one_user_or_error(users)

    def _one_user_or_error(self, users):
        unique_users = []
        seen = set()
        for user in users:
            if not user or user.id in seen:
                continue
            seen.add(user.id)
            unique_users.append(user)

        if not unique_users:
            raise CommandError("No matching completed portal user was found.")

        if len(unique_users) > 1:
            lines = ["More than one matching user was found. Re-run with --email or --username:"]
            for user in unique_users:
                lines.append(f"  {user.username} | {user.email or 'no email'}")
            raise CommandError("\n".join(lines))

        return unique_users[0]

    def _build_reset_url(self, user, site_url):
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        path = reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})
        return f"{site_url.rstrip('/')}{path}"

    def _display_name_for_user(self, user):
        application = (
            HousingApplication.objects.filter(user=user)
            .exclude(full_name="")
            .order_by("id")
            .first()
        )
        if application:
            return application.full_name
        return user.get_full_name() or user.username
