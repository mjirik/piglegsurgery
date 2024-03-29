# Generated by Django 3.2.23 on 2024-02-05 11:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('uploader', '0017_auto_20240107_1459'),
    ]

    operations = [
        migrations.AddField(
            model_name='mediafileannotation',
            name='distance_between_stitches_is_correct',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='mediafileannotation',
            name='equal_sized_wound_portions',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='mediafileannotation',
            name='forceps_grabs_the_edge',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='mediafileannotation',
            name='instrument_handling',
            field=models.IntegerField(default=-1),
        ),
        migrations.AddField(
            model_name='mediafileannotation',
            name='knots_are_done_right',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='mediafileannotation',
            name='needle_grabbed_correctly',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='mediafileannotation',
            name='needle_holder_stabilized',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='mediafileannotation',
            name='needle_pierced_at_first_try',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='mediafileannotation',
            name='needle_pierced_at_right_angle',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='mediafileannotation',
            name='needle_rotated_correctly_on_opposite_side',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='mediafileannotation',
            name='needle_rotated_correctly_on_students_side',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='mediafileannotation',
            name='no_excessive_tension',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='mediafileannotation',
            name='procedure_flow',
            field=models.IntegerField(default=-1),
        ),
        migrations.AddField(
            model_name='mediafileannotation',
            name='respect_for_tissue',
            field=models.IntegerField(default=-1),
        ),
        migrations.AddField(
            model_name='mediafileannotation',
            name='stitch_to_wound_distance_is_correct',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='mediafileannotation',
            name='stitches_perpendicular_to_wound',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='mediafileannotation',
            name='threads_shortened_appropriately',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='mediafileannotation',
            name='three_knots_per_stitch',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='mediafileannotation',
            name='time_and_movements',
            field=models.IntegerField(default=-1),
        ),
    ]
