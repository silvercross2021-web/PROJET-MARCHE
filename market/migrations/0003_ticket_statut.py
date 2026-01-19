from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0002_historiqueattribution'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='statut',
            field=models.CharField(choices=[('disponible', 'Disponible'), ('utilise', 'Utilisé'), ('annule', 'Annulé')], default='disponible', max_length=20),
        ),
    ]

