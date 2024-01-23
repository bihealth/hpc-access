# Generated by Django 4.0.2 on 2022-03-02 12:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("usersec", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="hpcgroup",
            name="owner",
            field=models.ForeignKey(
                help_text="User registered as owner of the group",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="%(class)s_owner",
                to="usersec.hpcuser",
            ),
        ),
        migrations.AlterField(
            model_name="hpcgroup",
            name="status",
            field=models.CharField(
                choices=[
                    ("INITIAL", "INITIAL"),
                    ("ACTIVE", "ACTIVE"),
                    ("DELETED", "DELETED"),
                    ("EXPIRED", "EXPIRED"),
                ],
                help_text="Status of the group object",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="hpcgroupversion",
            name="owner",
            field=models.ForeignKey(
                help_text="User registered as owner of the group",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="%(class)s_owner",
                to="usersec.hpcuser",
            ),
        ),
        migrations.AlterField(
            model_name="hpcgroupversion",
            name="status",
            field=models.CharField(
                choices=[
                    ("INITIAL", "INITIAL"),
                    ("ACTIVE", "ACTIVE"),
                    ("DELETED", "DELETED"),
                    ("EXPIRED", "EXPIRED"),
                ],
                help_text="Status of the group object",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="hpcuser",
            name="status",
            field=models.CharField(
                choices=[
                    ("INITIAL", "INITIAL"),
                    ("ACTIVE", "ACTIVE"),
                    ("DELETED", "DELETED"),
                    ("EXPIRED", "EXPIRED"),
                ],
                help_text="Status of the user object",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="hpcuserversion",
            name="status",
            field=models.CharField(
                choices=[
                    ("INITIAL", "INITIAL"),
                    ("ACTIVE", "ACTIVE"),
                    ("DELETED", "DELETED"),
                    ("EXPIRED", "EXPIRED"),
                ],
                help_text="Status of the user object",
                max_length=16,
            ),
        ),
    ]
