from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('myapp', '0003_labresult'),
	]

	operations = [
		migrations.AddField(
			model_name='appointment',
			name='appointment_number',
			field=models.CharField(max_length=50, null=True, blank=True),
		),
	]



