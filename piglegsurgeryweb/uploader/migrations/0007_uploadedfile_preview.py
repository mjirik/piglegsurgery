# Generated by Django 3.2.12 on 2022-04-01 18:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('uploader', '0006_uploadedfile_finished_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='uploadedfile',
            name='preview',
            field=models.ImageField(blank=True, null=True, upload_to=''),
        ),
    ]
