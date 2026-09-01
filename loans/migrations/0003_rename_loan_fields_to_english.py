from django.db import migrations, models
import django.db.models.deletion


def update_status_values(apps, schema_editor):
    Loan = apps.get_model('loans', 'Loan')
    status_map = {
        'reservado': 'reserved',
        'prestado': 'borrowed',
        'devuelto': 'returned',
        'cancelado': 'cancelled',
    }
    for old_val, new_val in status_map.items():
        Loan.objects.filter(status=old_val).update(status=new_val)


class Migration(migrations.Migration):

    dependencies = [
        ('loans', '0002_loan_renovaciones'),
    ]

    operations = [
        migrations.RenameField(
            model_name='loan',
            old_name='estado',
            new_name='status',
        ),
        migrations.RenameField(
            model_name='loan',
            old_name='fecha_reserva',
            new_name='reservation_date',
        ),
        migrations.RenameField(
            model_name='loan',
            old_name='fecha_recogida',
            new_name='pickup_date',
        ),
        migrations.RenameField(
            model_name='loan',
            old_name='fecha_devolucion',
            new_name='return_date',
        ),
        migrations.RenameField(
            model_name='loan',
            old_name='renovaciones',
            new_name='renewals',
        ),
        migrations.AlterField(
            model_name='loan',
            name='status',
            field=models.CharField(
                choices=[
                    ('reserved', 'Reserved (pending pickup)'),
                    ('borrowed', 'Borrowed (checked out)'),
                    ('returned', 'Returned'),
                    ('cancelled', 'Cancelled'),
                ],
                default='reserved',
                max_length=15,
            ),
        ),
        migrations.AlterField(
            model_name='loan',
            name='book',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='loans',
                to='catalog.book',
            ),
        ),
        migrations.AlterField(
            model_name='loan',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='loans',
                to='accounts.user',
            ),
        ),
        migrations.RunPython(update_status_values, reverse_code=migrations.RunPython.noop),
    ]
