# Generated by Django 4.0.3 on 2022-05-30 19:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("usersec", "0015_remove_hpcuserchangerequest_resources_requested_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="hpcproject",
            name="group",
            field=models.ForeignKey(
                help_text="Group that requested project. Group PI is owner of project",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="%(class)ss",
                to="usersec.hpcgroup",
            ),
        ),
        migrations.AlterField(
            model_name="hpcprojectversion",
            name="group",
            field=models.ForeignKey(
                help_text="Group that requested project. Group PI is owner of project",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="%(class)ss",
                to="usersec.hpcgroup",
            ),
        ),
    ]