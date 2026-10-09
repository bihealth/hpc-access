from django.db import migrations, models
from django.utils import timezone

#: Models whose ``<Model>Version`` rows are copied into ``<Model>Event``.
TRACKED_MODELS = (
    "HpcUser",
    "HpcGroup",
    "HpcProject",
    "HpcGroupCreateRequest",
    "HpcGroupChangeRequest",
    "HpcGroupDeleteRequest",
    "HpcUserCreateRequest",
    "HpcUserChangeRequest",
    "HpcUserDeleteRequest",
    "HpcProjectCreateRequest",
    "HpcProjectChangeRequest",
    "HpcProjectDeleteRequest",
    "HpcProjectInvitation",
    "HpcGroupInvitation",
)

#: Event fields that are not copied from the version row.
NOT_COPIED = {"pgh_id", "pgh_created_at", "pgh_label", "pgh_obj_id", "pgh_context_id", "id", "uuid"}


def backfill_history(apps, schema_editor):
    """Copy every version row into the event table, then snapshot the current state.

    Version rows keep their own timestamp. The final snapshot (label ``snapshot``)
    records the live row at migration time, because some writes never created a
    version row.
    """
    now = timezone.now()

    for name in TRACKED_MODELS:
        model = apps.get_model("usersec", name)
        version_model = apps.get_model("usersec", f"{name}Version")
        event_model = apps.get_model("usersec", f"{name}Event")

        # Keep the copied timestamps instead of setting them to now on insert
        for field in event_model._meta.fields:
            if isinstance(field, models.DateTimeField):
                field.auto_now = field.auto_now_add = False

        copied = [
            f.attname for f in event_model._meta.concrete_fields if f.attname not in NOT_COPIED
        ]
        events = []
        previous_obj_id = None

        versions = (
            version_model.objects.exclude(belongs_to=None)
            .select_related("belongs_to")
            .order_by("belongs_to_id", "version")
        )
        for version in versions:
            obj = version.belongs_to
            event = event_model(
                pgh_created_at=version.date_created,
                pgh_label="insert" if obj.id != previous_obj_id else "update",
                pgh_obj_id=obj.id,
                id=obj.id,
                uuid=obj.uuid,
                **{attname: getattr(version, attname) for attname in copied},
            )
            # Version rows have their own creation date, the event keeps the object's
            event.date_created = obj.date_created
            events.append(event)
            previous_obj_id = obj.id

        for obj in model.objects.all():
            events.append(
                event_model(
                    pgh_created_at=now,
                    pgh_label="snapshot",
                    pgh_obj_id=obj.id,
                    id=obj.id,
                    uuid=obj.uuid,
                    **{attname: getattr(obj, attname) for attname in copied},
                )
            )

        event_model.objects.bulk_create(events, batch_size=1000)


class Migration(migrations.Migration):

    dependencies = [
        ("usersec", "0032_pghistory_events"),
    ]

    operations = [
        migrations.RunPython(backfill_history, migrations.RunPython.noop),
    ]
