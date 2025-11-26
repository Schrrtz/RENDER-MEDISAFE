from django.core.management.base import BaseCommand
from django.test import Client
from urllib.parse import urlparse
import os


class Command(BaseCommand):
    help = 'Verify media URLs returned by doctor endpoints map to existing files on disk'

    def handle(self, *args, **options):
        from django.conf import settings
        from myapp.models import Doctor

        c = Client()
        # simulate admin session as views require it
        session = c.session
        session['is_admin'] = True
        session.save()

        doctor = Doctor.objects.first()
        if not doctor:
            self.stdout.write(self.style.WARNING('No doctor found to test'))
            return

        did = doctor.doctor_id
        self.stdout.write(f'Checking media for doctor id={did}')

        urls_to_check = []

        # Get doctor details
        resp = c.get(f'/mod_doctors/get/{did}/', HTTP_ACCEPT='application/json')
        if resp.status_code != 200:
            self.stdout.write(self.style.ERROR(f'Failed to get doctor details: {resp.status_code}'))
        else:
            data = resp.json()
            if data.get('photo_url'):
                urls_to_check.append(data['photo_url'])

        # Get patients/appointments/prescriptions
        resp2 = c.get(f'/mod_doctors/patients/{did}/', HTTP_ACCEPT='application/json')
        if resp2.status_code != 200:
            self.stdout.write(self.style.ERROR(f'Failed to get doctor patients: {resp2.status_code}'))
        else:
            data2 = resp2.json()
            for p in data2.get('patients', []):
                if p.get('photo_url'):
                    urls_to_check.append(p['photo_url'])
            for pres in data2.get('prescriptions', []):
                if pres.get('file_url'):
                    urls_to_check.append(pres['file_url'])

        if not urls_to_check:
            self.stdout.write(self.style.WARNING('No media URLs returned by endpoints'))
            return

        self.stdout.write(f'Found {len(urls_to_check)} URLs to check')

        checked = 0
        missing = []
        for u in urls_to_check:
            parsed = urlparse(u)
            path = parsed.path
            # If MEDIA_URL is set and path starts with it, map to MEDIA_ROOT
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            media_root = getattr(settings, 'MEDIA_ROOT', None)
            if media_root and path.startswith(media_url):
                rel = path[len(media_url):].lstrip('/')
                # Normalize duplicated 'media/' segments (e.g. '/media/media/...')
                while rel.startswith('media/'):
                    rel = rel[len('media/'):]
                fs_path = os.path.join(media_root, rel)
                exists = os.path.exists(fs_path)
                checked += 1
                if exists:
                    self.stdout.write(self.style.SUCCESS(f'[OK] {u} -> {fs_path}'))
                else:
                    self.stdout.write(self.style.ERROR(f'[MISSING] {u} -> {fs_path}'))
                    missing.append((u, fs_path))
            else:
                # If not under MEDIA_URL, just report the URL (can't map)
                self.stdout.write(self.style.WARNING(f'[SKIP] Cannot map URL to MEDIA_ROOT: {u}'))

        self.stdout.write(self.style.NOTICE(f'Checked {checked} media URLs, missing: {len(missing)}'))
        if missing:
            self.stdout.write(self.style.ERROR('Missing files:'))
            for u, p in missing:
                self.stdout.write(f' - {u} -> {p}')
