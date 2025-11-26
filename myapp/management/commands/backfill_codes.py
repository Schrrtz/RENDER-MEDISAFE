from django.core.management.base import BaseCommand
from myapp.models import LiveAppointment, Prescription

class Command(BaseCommand):
    help = 'Backfill missing live_appointment_number and prescription_number values'

    def handle(self, *args, **options):
        self.stdout.write('Backfilling LiveAppointment numbers...')
        count_la = 0
        for la in LiveAppointment.objects.filter(live_appointment_number__isnull=True):
            la.save()
            count_la += 1
        self.stdout.write(f'Backfilled {count_la} LiveAppointment records.')

        self.stdout.write('Backfilling Prescription numbers...')
        count_pr = 0
        for p in Prescription.objects.filter(prescription_number__isnull=True):
            p.save()
            count_pr += 1
        self.stdout.write(f'Backfilled {count_pr} Prescription records.')

        self.stdout.write(self.style.SUCCESS('Backfill complete.'))
