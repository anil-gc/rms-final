import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_phase_two_migration_preserves_legacy_users_without_assigning_privileges():
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    baseline = [("accounts", "0001_initial")]
    executor.migrate(baseline)
    old_user = executor.loader.project_state(baseline).apps.get_model("accounts", "User")
    old = old_user.objects.create(username="legacy-user", password="!existing-unusable-password")
    try:
        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        new_user = executor.loader.project_state(latest).apps.get_model("accounts", "User")
        migrated = new_user.objects.get(pk=old.pk)
        assert migrated.username == "legacy-user"
        assert migrated.password == "!existing-unusable-password"
        assert migrated.is_active is True
        assert migrated.role == ""
        assert migrated.pin_hash == ""
        assert migrated.auth_version == 1
    finally:
        MigrationExecutor(connection).migrate(latest)
