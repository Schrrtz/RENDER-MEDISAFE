from django.db import migrations


class Migration(migrations.Migration):

	dependencies = [
		('myapp', '0001_initial'),
	]

	operations = [
		# Rename the Django model from Consultation to Appointment
		migrations.RenameModel(
			old_name='Consultation',
			new_name='Appointment',
		),
		# Rename the underlying database table to `appointments`
		migrations.AlterModelTable(
			name='appointment',
			table='appointments',
		),
	]


