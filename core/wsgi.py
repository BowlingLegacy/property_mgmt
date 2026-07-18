import os

from django.core.management import call_command
from django.core.wsgi import get_wsgi_application
from django.db import connection

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

application = get_wsgi_application()


def run_render_migrations():
    if os.environ.get("RENDER", "").lower() != "true":
        return
    if os.environ.get("RUN_MIGRATIONS_ON_STARTUP", "true").lower() not in {"1", "true", "yes", "on"}:
        return

    # Gunicorn can start more than one worker. A PostgreSQL advisory lock keeps
    # those workers from attempting the same migration concurrently.
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_lock(%s)", [947201826])
        try:
            call_command("migrate", interactive=False, verbosity=1)
        finally:
            cursor.execute("SELECT pg_advisory_unlock(%s)", [947201826])


run_render_migrations()
