from getpass import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Create the first single-location Owner with a hidden, validated password prompt."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)

    def handle(self, *args, **options):
        if User.objects.filter(role=User.Role.OWNER).exists():
            raise CommandError("An Owner already exists; no account was changed.")
        user = User(username=options["username"], role=User.Role.OWNER, is_staff=True)
        password = getpass("Owner password (at least 15 characters): ")
        if password != getpass("Confirm Owner password: "):
            raise CommandError("Passwords do not match.")
        try:
            validate_password(password, user)
            user.set_password(password)
            user.full_clean()
            with transaction.atomic():
                user.save()
        except (ValidationError, IntegrityError) as error:
            raise CommandError(
                "Owner creation failed: check username and password requirements."
            ) from error
        self.stdout.write(self.style.SUCCESS("Owner created. No credentials were printed."))
