from django.db import migrations

from therapist.crisis import contains_crisis_language


def backfill_crisis_flagged(apps, schema_editor):
    MoodEntry = apps.get_model("therapist", "MoodEntry")
    flagged_ids = [
        entry.id
        for entry in MoodEntry.objects.only("id", "thoughts").iterator()
        if contains_crisis_language(entry.thoughts)
    ]
    if flagged_ids:
        MoodEntry.objects.filter(id__in=flagged_ids).update(crisis_flagged=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("therapist", "0005_moodentry_crisis_flagged"),
    ]

    operations = [
        migrations.RunPython(backfill_crisis_flagged, noop_reverse),
    ]
