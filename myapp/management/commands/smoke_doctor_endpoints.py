from django.core.management.base import BaseCommand
from django.test import Client


class Command(BaseCommand):
    help = 'Smoke test doctor detail and patients endpoints using test client'

    def handle(self, *args, **options):
        from myapp.models import Doctor
        c = Client()
        doctor = Doctor.objects.first()
        if not doctor:
            self.stdout.write(self.style.WARNING('No Doctor found to test'))
            return

        self.stdout.write(f'Testing doctor id: {doctor.doctor_id}')

        # Mark the test client as admin via session keys used by views
        session = c.session
        session['is_admin'] = True
        session.save()

        resp = c.get(f'/mod_doctors/get/{doctor.doctor_id}/', HTTP_ACCEPT='application/json')
        self.stdout.write(f'/mod_doctors/get/ status: {resp.status_code}')
        try:
            data = resp.json()
            self.stdout.write(f'Keys: {list(data.keys())}')
        except Exception as e:
            self.stdout.write(f'Failed to parse JSON: {e}')

        resp2 = c.get(f'/mod_doctors/patients/{doctor.doctor_id}/', HTTP_ACCEPT='application/json')
        self.stdout.write(f'/mod_doctors/patients/ status: {resp2.status_code}')
        try:
            data2 = resp2.json()
            self.stdout.write(f'Keys: {list(data2.keys())}')
            self.stdout.write(f"Patients: {len(data2.get('patients', []))}, Appointments: {len(data2.get('appointments', []))}, Prescriptions: {len(data2.get('prescriptions', []))}")
        except Exception as e:
            self.stdout.write(f'Failed to parse JSON: {e}')
