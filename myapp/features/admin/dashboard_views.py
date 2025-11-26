from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from datetime import date, timedelta
from ...models import User, UserProfile, Patient, LabResult, Appointment, BookedService, RolePermission
from django.core.cache import cache
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import datetime


def _display_name_of_user(user):
    if not user:
        return None
    try:
        full = getattr(user, 'get_full_name', None)
        if callable(full):
            name = full()
            if name:
                return name
    except Exception:
        pass
    return getattr(user, 'username', str(user))

def moddashboard(request):
    """Admin dashboard view"""
    if request.session.get("is_admin"):
        # For secret admin login
        user_profiles = UserProfile.objects.select_related('user').all()
        patients = Patient.objects.select_related('user').all()
        
        # Aggregate statistics
        total_users = User.objects.count()
        total_patients = Patient.objects.count()
        total_profiles = UserProfile.objects.count()
        total_lab_results = LabResult.objects.count()
        total_appointments = Appointment.objects.count()
        total_booked_services = BookedService.objects.count()
        booked_services_pending = BookedService.objects.filter(status='Pending').count()
        booked_services_confirmed = BookedService.objects.filter(status='Confirmed').count()
        booked_services_completed = BookedService.objects.filter(status='Completed').count()
        
        # Today's data
        today = date.today()
        today_appointments = Appointment.objects.filter(consultation_date=today).select_related('doctor','doctor__user','patient','patient__userprofile').order_by('consultation_time')
        today_booked_services = BookedService.objects.filter(booking_date=today).select_related('user','user__userprofile').order_by('booking_time')
        
        latest_accounts = User.objects.order_by('-date_joined')[:5]
        latest_lab_results = LabResult.objects.select_related('user','uploaded_by').order_by('-upload_date')[:5]
        latest_appointments = Appointment.objects.select_related('doctor','doctor__user','patient','patient__userprofile').order_by('-created_at')[:5]
        # Collect cached auth events (login/logout) from in-memory cache
        recent_activities = []
        try:
            cached_events = cache.get('site_recent_activity_events', [])
            for ev in cached_events:
                recent_activities.append({
                    'type': 'Auth',
                    'summary': ev.get('summary'),
                    'detail': ev.get('detail'),
                    'link': ev.get('link', 'mod_users'),
                    'date': ev.get('date')
                })
        except Exception:
            # cache may be unavailable in some environments
            pass

        # Build a unified recent activity list from appointments, lab results and booked services
        for appt in latest_appointments:
            try:
                dt = getattr(appt, 'created_at', None)
            except Exception:
                dt = None
            # Resolve doctor name safely
            doctor_name = None
            try:
                if getattr(appt, 'doctor', None) and getattr(appt.doctor, 'user', None):
                    doctor_name = _display_name_of_user(appt.doctor.user)
            except Exception:
                doctor_name = None
            patient_name = None
            try:
                if getattr(appt, 'patient', None):
                    patient_name = _display_name_of_user(appt.patient)
            except Exception:
                patient_name = None
            summary = 'Appointment'
            if doctor_name:
                summary = f"Appointment: Dr. {doctor_name}"
            elif patient_name:
                summary = f"Appointment: {patient_name}"
            recent_activities.append({
                'type': 'Appointment',
                'summary': summary,
                'detail': getattr(appt, 'consultation_type', ''),
                'link': 'mod_consultations',
                'date': dt
            })

        for lr in latest_lab_results:
            user_obj = getattr(lr, 'user', None)
            user_name = _display_name_of_user(user_obj) if user_obj else ''
            recent_activities.append({
                'type': 'LabResult',
                'summary': f"Lab: {getattr(lr, 'lab_type', 'Result')}",
                'detail': user_name,
                'link': 'mod_records',
                'date': getattr(lr, 'upload_date', None)
            })

        latest_bookings = BookedService.objects.select_related('user').order_by('-created_at')[:5]
        for b in latest_bookings:
            user_name = _display_name_of_user(getattr(b, 'user', None))
            recent_activities.append({
                'type': 'ServiceBooking',
                'summary': f"Service: {getattr(b, 'service_name', 'Service')} {f'({user_name})' if user_name else ''}",
                'detail': getattr(b, 'status', ''),
                'link': 'mod_consultations',
                'date': getattr(b, 'created_at', None)
            })

        # Sort activities by date desc and take latest 8
        recent_activities = sorted([r for r in recent_activities if r.get('date')], key=lambda x: x['date'], reverse=True)[:8]

        # Build schedule summary for next 14 days (appointments and booked services counts)
        schedule_summary = []
        try:
            base = today
            for i in range(0, 14):
                d = base + timedelta(days=i)
                appt_count = Appointment.objects.filter(consultation_date=d).count()
                lab_count = BookedService.objects.filter(booking_date=d).count()
                appt_link = reverse('mod_consultations') + f'?date={d.isoformat()}'
                lab_link = reverse('labresults') + f'?date={d.isoformat()}'
                schedule_summary.append({
                    'date': d,
                    'date_str': d.strftime('%a %b %d'),
                    'iso': d.isoformat(),
                    'appt_count': appt_count,
                    'lab_count': lab_count,
                    'appt_link': appt_link,
                    'lab_link': lab_link,
                })
        except Exception:
            schedule_summary = []
        
        # Ensure user is in context - use request.user if authenticated, otherwise use an existing admin user
        # This prevents template errors when accessing user variable
        # For secret admin login, we use an existing admin user from the database if available
        current_user = None
        if hasattr(request, 'user') and request.user.is_authenticated and hasattr(request.user, 'user_id'):
            current_user = request.user
        else:
            # For secret admin login, try to get an existing admin user
            try:
                admin_user_obj = User.objects.filter(role='admin').first()
                if admin_user_obj:
                    current_user = admin_user_obj
                else:
                    # If no admin exists, create a minimal object that won't cause template errors
                    # This should rarely happen, but we need a fallback
                    class AdminUser:
                        def __init__(self):
                            self.username = "Administrator"
                            self.user_id = None
                            self.email = ""
                            self.role = "admin"
                            self.is_authenticated = True
                            self.is_active = True
                            self.is_staff = True
                            self.is_superuser = True
                    current_user = AdminUser()
            except Exception:
                # Ultimate fallback
                class AdminUser:
                    def __init__(self):
                        self.username = "Administrator"
                        self.is_authenticated = True
                current_user = AdminUser()
        
        context = {
            "user_profiles": user_profiles,
            "patients": patients,
            "total_users": total_users,
            "total_patients": total_patients,
            "total_profiles": total_profiles,
            "admin": {"username": "Administrator"},
            "user": current_user,  # Add user to context to prevent template errors
            "total_lab_results": total_lab_results,
            "total_appointments": total_appointments,
            "total_booked_services": total_booked_services,
            "booked_services_pending": booked_services_pending,
            "booked_services_confirmed": booked_services_confirmed,
            "booked_services_completed": booked_services_completed,
            "today_appointments": today_appointments,
            "today_appointments_count": today_appointments.count(),
            "today_booked_services": today_booked_services,
            "today_booked_services_count": today_booked_services.count(),
            "latest_accounts": latest_accounts,
            "latest_lab_results": latest_lab_results,
            "latest_appointments": latest_appointments,
            "recent_activities": recent_activities,
            "schedule_summary": schedule_summary,
            "is_super_admin": request.session.get("is_super_admin", False),
        }
        return render(request, "ModDashboard.html", context)
        
    # For regular admin login
    user_id = request.session.get("user_id") or request.session.get("user")
    if not user_id:
        messages.error(request, "Please login to access admin dashboard")
        return redirect("homepage2")
    
    try:
        admin_user = User.objects.get(user_id=user_id, role="admin")
        user_profiles = UserProfile.objects.select_related('user').all()
        patients = Patient.objects.select_related('user').all()
        
        # Aggregate statistics
        total_users = User.objects.count()
        total_patients = Patient.objects.count()
        total_profiles = UserProfile.objects.count()
        total_lab_results = LabResult.objects.count()
        total_appointments = Appointment.objects.count()
        total_booked_services = BookedService.objects.count()
        booked_services_pending = BookedService.objects.filter(status='Pending').count()
        booked_services_confirmed = BookedService.objects.filter(status='Confirmed').count()
        booked_services_completed = BookedService.objects.filter(status='Completed').count()
        
        # Today's data
        today = date.today()
        today_appointments = Appointment.objects.filter(consultation_date=today).select_related('doctor','doctor__user','patient','patient__userprofile').order_by('consultation_time')
        today_booked_services = BookedService.objects.filter(booking_date=today).select_related('user','user__userprofile').order_by('booking_time')
        
        latest_accounts = User.objects.order_by('-date_joined')[:5]
        latest_lab_results = LabResult.objects.select_related('user','uploaded_by').order_by('-upload_date')[:5]
        latest_appointments = Appointment.objects.select_related('doctor','doctor__user','patient','patient__userprofile').order_by('-created_at')[:5]
        # Include cached auth events for non-secret path as well
        recent_activities = []
        try:
            cached_events = cache.get('site_recent_activity_events', [])
            for ev in cached_events:
                recent_activities.append({
                    'type': 'Auth',
                    'summary': ev.get('summary'),
                    'detail': ev.get('detail'),
                    'link': ev.get('link', 'mod_users'),
                    'date': ev.get('date')
                })
        except Exception:
            pass
        for appt in latest_appointments:
            doctor_name = None
            try:
                if getattr(appt, 'doctor', None) and getattr(appt.doctor, 'user', None):
                    doctor_name = _display_name_of_user(appt.doctor.user)
            except Exception:
                doctor_name = None
            patient_name = None
            try:
                if getattr(appt, 'patient', None):
                    patient_name = _display_name_of_user(appt.patient)
            except Exception:
                patient_name = None
            summary = 'Appointment'
            if doctor_name:
                summary = f"Appointment: Dr. {doctor_name}"
            elif patient_name:
                summary = f"Appointment: {patient_name}"
            recent_activities.append({
                'type': 'Appointment',
                'summary': summary,
                'detail': getattr(appt, 'consultation_type', ''),
                'link': 'mod_consultations',
                'date': getattr(appt, 'created_at', None)
            })

        for lr in latest_lab_results:
            user_obj = getattr(lr, 'user', None)
            user_name = _display_name_of_user(user_obj) if user_obj else ''
            recent_activities.append({
                'type': 'LabResult',
                'summary': f"Lab: {getattr(lr, 'lab_type', 'Result')}",
                'detail': user_name,
                'link': 'mod_records',
                'date': getattr(lr, 'upload_date', None)
            })

        latest_bookings = BookedService.objects.select_related('user').order_by('-created_at')[:5]
        for b in latest_bookings:
            user_name = _display_name_of_user(getattr(b, 'user', None))
            recent_activities.append({
                'type': 'ServiceBooking',
                'summary': f"Service: {getattr(b, 'service_name', 'Service')} {f'({user_name})' if user_name else ''}",
                'detail': getattr(b, 'status', ''),
                'link': 'mod_consultations',
                'date': getattr(b, 'created_at', None)
            })
        recent_activities = sorted([r for r in recent_activities if r.get('date')], key=lambda x: x['date'], reverse=True)[:8]
        # Build schedule summary for next 14 days (appointments and booked services counts)
        schedule_summary = []
        try:
            base = today
            for i in range(0, 14):
                d = base + timedelta(days=i)
                appt_count = Appointment.objects.filter(consultation_date=d).count()
                lab_count = BookedService.objects.filter(booking_date=d).count()
                appt_link = reverse('mod_consultations') + f'?date={d.isoformat()}'
                lab_link = reverse('labresults') + f'?date={d.isoformat()}'
                schedule_summary.append({
                    'date': d,
                    'date_str': d.strftime('%a %b %d'),
                    'iso': d.isoformat(),
                    'appt_count': appt_count,
                    'lab_count': lab_count,
                    'appt_link': appt_link,
                    'lab_link': lab_link,
                })
        except Exception:
            schedule_summary = []

        context = {
            "user_profiles": user_profiles,
            "patients": patients,
            "total_users": total_users,
            "total_patients": total_patients,
            "total_profiles": total_profiles,
            "admin": admin_user,
            "user": admin_user,  # Add user to context to prevent template errors
            "total_lab_results": total_lab_results,
            "total_appointments": total_appointments,
            "total_booked_services": total_booked_services,
            "booked_services_pending": booked_services_pending,
            "booked_services_confirmed": booked_services_confirmed,
            "booked_services_completed": booked_services_completed,
            "today_appointments": today_appointments,
            "today_appointments_count": today_appointments.count(),
            "today_booked_services": today_booked_services,
            "today_booked_services_count": today_booked_services.count(),
            "latest_accounts": latest_accounts,
            "latest_lab_results": latest_lab_results,
            "latest_appointments": latest_appointments,
            "recent_activities": recent_activities,
            "schedule_summary": schedule_summary,
            "is_super_admin": request.session.get("is_super_admin", False),
        }
        return render(request, "ModDashboard.html", context)
    except User.DoesNotExist:
        messages.error(request, "Unauthorized access")
        return redirect("homepage2")


def clear_recent_activity(request):
    """Admin endpoint to clear cached recent activity events (POST).
    This avoids DB migrations and provides a quick admin control.
    """
    # Only allow via POST and only for admins
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required'}, status=400)

    # Check admin session or user role
    is_admin = False
    try:
        if request.session.get('is_admin'):
            is_admin = True
        elif hasattr(request, 'user') and request.user.is_authenticated and getattr(request.user, 'role', None) == 'admin':
            is_admin = True
    except Exception:
        is_admin = False

    if not is_admin:
        return JsonResponse({'ok': False, 'error': 'Unauthorized'}, status=403)

    try:
        cache.delete('site_recent_activity_events')
        return JsonResponse({'ok': True})
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Failed to clear'}, status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def manage_permissions(request):
    """API endpoint to get and update role permissions (Super Admin only)"""
    # Check if user is Super Admin
    is_super_admin = request.session.get("is_super_admin", False) or request.session.get("is_admin", False)
    
    if not is_super_admin:
        return JsonResponse({'error': 'Unauthorized. Only Super Admin can manage permissions.'}, status=403)
    
    if request.method == 'GET':
        # Get current permissions
        permissions = {}
        for role in ['doctor', 'nurse', 'lab_tech', 'patient']:
            try:
                perm = RolePermission.objects.get(role=role)
                permissions[role] = perm.is_enabled
            except RolePermission.DoesNotExist:
                # Default to enabled if not set
                permissions[role] = True
        
        return JsonResponse({'permissions': permissions})
    
    elif request.method == 'POST':
        # Update permission
        try:
            data = json.loads(request.body)
            role = data.get('role')
            is_enabled = data.get('is_enabled', True)
            
            if role not in ['doctor', 'nurse', 'lab_tech', 'patient']:
                return JsonResponse({'success': False, 'error': 'Invalid role'}, status=400)
            
            # Get or create permission
            perm, created = RolePermission.objects.get_or_create(role=role, defaults={'is_enabled': is_enabled})
            if not created:
                perm.is_enabled = is_enabled
                perm.save()
            
            return JsonResponse({'success': True, 'role': role, 'is_enabled': is_enabled})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_notification_file(request, notification_id):
    """Download notification file attachment"""
    try:
        from django.core.files.storage import default_storage
        from django.http import FileResponse
        from ...models import Notification
        
        notification = Notification.objects.get(notification_id=notification_id)
        
        if not notification.file:
            return JsonResponse({'error': 'No file attached'}, status=404)
        
        # Get the file from storage
        file_path = notification.file.name
        if default_storage.exists(file_path):
            file_obj = default_storage.open(file_path, 'rb')
            response = FileResponse(file_obj, content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{file_path.split("/")[-1]}"'
            return response
        else:
            return JsonResponse({'error': 'File not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_password_reset_notifications(request):
    """Get all password reset notifications for admin"""
    try:
        from ...models import Notification
        
        # Get password reset notifications
        notifications = Notification.objects.filter(
            notification_type='password_reset'
        ).order_by('-created_at')[:50]
        
        notif_data = []
        for notif in notifications:
            # Try to get user info from notification
            user_id = None
            try:
                # Extract user_id from notification_id if available
                if hasattr(notif, 'notification_id') and notif.notification_id:
                    # notification_id might be formatted as "user_id_password_reset_timestamp"
                    user_id = notif.user_id if hasattr(notif, 'user_id') else None
            except:
                pass
            
            notif_data.append({
                'notification_id': notif.notification_id,
                'title': notif.title or 'Password Reset Request',
                'message': notif.message or 'User requested password reset',
                'user_id': user_id,
                'created_at': notif.created_at.isoformat() if notif.created_at else '',
                'is_read': notif.is_read,
                'user_name': notif.title or 'User'
            })
        
        return JsonResponse({
            'success': True,
            'notifications': notif_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def mark_password_reset_read(request, notification_id):
    """Mark a password reset notification as read"""
    try:
        from ...models import Notification
        
        notification = Notification.objects.get(notification_id=notification_id)
        notification.is_read = True
        notification.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Notification marked as read'
        })
    except Notification.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Notification not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
