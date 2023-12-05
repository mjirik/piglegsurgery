# Generated by Django 3.2.8 on 2021-10-08 13:56

from django.db import migrations, models
import uploader.models_tools


class Migration(migrations.Migration):

    dependencies = [
        ('uploader', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='uploadedfile',
            name='mediafile',
            field=models.FileField(default='none.txt', max_length=500, upload_to=uploader.models_tools.upload_to_unqiue_folder, verbose_name='Media File'),
            preserve_default=False,
        ),
    ]
