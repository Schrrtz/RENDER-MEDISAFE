from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Backfill Prescription.doctor from live_appointment -> appointment -> doctor when missing'

    def handle(self, *args, **options):
        from myapp.models import Prescription
        qs = Prescription.objects.filter(doctor__isnull=True)
        total = qs.count()
        backfilled = 0
        for p in qs:
            try:
                ap = getattr(p, 'live_appointment', None)
                if ap and getattr(ap, 'appointment', None) and getattr(ap.appointment, 'doctor', None):
                    p.doctor = ap.appointment.doctor
                    p.save(update_fields=['doctor'])
                    backfilled += 1
            except Exception:
                continue

        self.stdout.write(self.style.SUCCESS(f'Processed {total} prescriptions, backfilled: {backfilled}'))
