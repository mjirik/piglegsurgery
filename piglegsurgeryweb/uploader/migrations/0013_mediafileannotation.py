# Generated by Django 3.2.23 on 2024-01-03 22:10

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('uploader', '0012_rename_is_microscopy_uploadedfile_is_microsurgery'),
    ]

    operations = [
        migrations.CreateModel(
            name='MediaFileAnnotation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('annotation', models.TextField()),
                ('created_at', models.DateTimeField(default=datetime.datetime.now, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(default=datetime.datetime.now, verbose_name='Updated at')),
                ('stars', models.IntegerField(default=-1)),
                ('annotator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='uploader.owner')),
                ('uploaded_file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='uploader.uploadedfile')),
            ],
        ),
    ]
