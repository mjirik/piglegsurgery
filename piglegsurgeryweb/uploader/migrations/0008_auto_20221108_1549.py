# Generated by Django 3.2.12 on 2022-11-08 14:49

from django.db import migrations, models
import django.db.models.deletion
import uploader.models


class Migration(migrations.Migration):

    dependencies = [
        ('uploader', '0007_uploadedfile_preview'),
    ]

    operations = [
        migrations.CreateModel(
            name='Owner',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=200)),
                ('hash', models.CharField(blank=True, default=uploader.models._hash, max_length=255)),
            ],
        ),
        migrations.AddField(
            model_name='uploadedfile',
            name='owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='uploader.owner'),
        ),
    ]
