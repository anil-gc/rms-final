from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Project user foundation; membership and roles belong to a later phase."""
