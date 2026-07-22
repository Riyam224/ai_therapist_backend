from django.db import migrations


def create_cache_table(apps, schema_editor):
    # Uses createcachetable's own DDL generation so this works against
    # whichever backend is connected (SQLite locally, Postgres on Railway)
    # instead of hardcoding dialect-specific SQL.
    from django.core.management import call_command

    call_command("createcachetable", "django_cache_table")


def drop_cache_table(apps, schema_editor):
    schema_editor.execute('DROP TABLE IF EXISTS "django_cache_table"')


class Migration(migrations.Migration):

    dependencies = [
        ("therapist", "0006_backfill_crisis_flagged"),
    ]

    operations = [
        migrations.RunPython(create_cache_table, drop_cache_table),
    ]
