from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('mis_engine', '0002_seed_ledger_mappings'),
    ]

    operations = [
        migrations.CreateModel(
            name='Building',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('display_name', models.CharField(
                    max_length=100, unique=True,
                    help_text="UI label used as matrix column header, e.g. 'Kalyan Nagar'")),
                ('general_cc', models.CharField(
                    max_length=150, blank=True, null=True,
                    help_text="Exact Tally CC name for this building's General overhead CC. Null = none.")),
                ('rent_ledger', models.CharField(
                    max_length=200, blank=True, null=True,
                    help_text="Exact Tally ledger name for rent. Null = fall back to per-unit CC breakup.")),
                ('column_order', models.PositiveSmallIntegerField(
                    default=0,
                    help_text="Left-to-right order in the matrix report.")),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'ordering': ['column_order', 'display_name']},
        ),
        migrations.CreateModel(
            name='CostCenter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('building', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='cost_centers',
                    to='mis_engine.building',
                    help_text="Parent building. Null only for the General Office virtual column.")),
                ('display_name', models.CharField(
                    max_length=100,
                    help_text="UI column header, e.g. 'KN 101'")),
                ('tally_cc', models.CharField(
                    max_length=150, blank=True, null=True,
                    help_text="Exact Tally cost centre name. Null = General Office virtual column.")),
                ('column_order', models.PositiveSmallIntegerField(
                    default=0,
                    help_text="Order within the building (left-to-right in unit-wise table).")),
                ('is_excluded_from_split', models.BooleanField(
                    default=False,
                    help_text="True for Penthouse and General virtual columns — skip in salary/rent splits.")),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'ordering': ['building__column_order', 'column_order', 'display_name']},
        ),
        migrations.AddConstraint(
            model_name='costcenter',
            constraint=models.UniqueConstraint(
                fields=['building', 'display_name'],
                name='unique_cc_per_building',
            ),
        ),
    ]
