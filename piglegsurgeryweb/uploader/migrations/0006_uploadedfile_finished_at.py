# Generated by Django 3.2.8 on 2021-12-21 15:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("uploader", "0005_uploadedfile_started_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="uploadedfile",
            name="finished_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Finished at"
            ),
        ),
    ]
