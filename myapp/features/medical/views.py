from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, FileResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.utils.encoding import smart_str
from datetime import date, datetime
import base64
import json
import mimetypes
import logging

logger = logging.getLogger(__name__)

@csrf_protect
@require_POST
def book_service(request):
    """AJAX endpoint to book a service"""
    user_id = request.session.get("user_id") or request.session.get("user")
    
    if not user_id:
        return JsonResponse({
            'success': False,
            'message': 'Please login to book a service'
        }, status=401)
    
    try:
        from ...models import User, BookedService
        user = User.objects.get(user_id=user_id)
        
        # Parse JSON request body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid request format'
            }, status=400)
        
        # Validate required fields
        service_name = data.get('service_name', '').strip()
        booking_date = data.get('booking_date', '').strip()
        booking_time = data.get('booking_time', '').strip()
        notes = data.get('notes', '').strip()
        
        if not service_name or not booking_date or not booking_time:
            return JsonResponse({
                'success': False,
                'message': 'All required fields must be filled'
            }, status=400)
        
        # Validate date is not in the past
        try:
            booking_datetime = datetime.strptime(f"{booking_date} {booking_time}", "%Y-%m-%d %H:%M")
            if booking_datetime < datetime.now():
                return JsonResponse({
                    'success': False,
                    'message': 'Booking date and time must be in the future'
                }, status=400)
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid date or time format'
            }, status=400)
        
        # Create the booking
        booked_service = BookedService.objects.create(
            user=user,
            service_name=service_name,
            booking_date=booking_date,
            booking_time=booking_time,
            status='Pending',
            notes=notes if notes else None
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Service booked successfully! We will send you a confirmation soon.',
            'booking_id': booked_service.booking_id
        }, status=201)
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'User not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error booking service: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error booking service: {str(e)}'
        }, status=500)

def get_service_details(request):
    """AJAX endpoint to get service booking details"""
    user_id = request.session.get("user_id") or request.session.get("user")
    
    if not user_id:
        return JsonResponse({
            'success': False,
            'message': 'Please login to view service details'
        }, status=401)
    
    try:
        booking_id = request.GET.get('booking_id')
        
        if not booking_id:
            return JsonResponse({
                'success': False,
                'message': 'Booking ID is required'
            }, status=400)
        
        from ...models import User, BookedService
        user = User.objects.get(user_id=user_id)
        booked_service = BookedService.objects.get(booking_id=booking_id, user=user)
        
        # Format the response data
        response_data = {
            'success': True,
            'booking_id': booked_service.booking_id,
            'service_name': booked_service.service_name,
            'booking_date': booked_service.booking_date.strftime('%B %d, %Y'),
            'booking_time': booked_service.booking_time.strftime('%I:%M %p'),
            'status': booked_service.status,
            'notes': booked_service.notes or 'No notes added',
            'created_at': booked_service.created_at.strftime('%B %d, %Y at %I:%M %p'),
            'updated_at': booked_service.updated_at.strftime('%B %d, %Y at %I:%M %p')
        }
        
        return JsonResponse(response_data, status=200)
        
    except BookedService.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Service booking not found or access denied'
        }, status=404)
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'User not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error fetching service details: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error fetching service details: {str(e)}'
        }, status=500)

def lab_results(request):
    user_id = request.session.get("user_id") or request.session.get("user")
    is_logged_in = user_id is not None
    
    if not is_logged_in:
        # Show encouraging message for non-logged-in users
        return render(request, "lab_results.html", {
            "is_logged_in": False,
            "encouraging_message": "Access your comprehensive lab results and medical reports in one secure place. Login to view your complete medical history, track test results over time, and share important health data with your healthcare providers."
        })
    
    try:
        from ...models import User, UserProfile, LabResult, BookedService
        user = User.objects.get(user_id=user_id)
        user_profile = UserProfile.objects.get(user=user)
        
        # Get all lab results for this user
        lab_results = LabResult.objects.filter(user=user).order_by('-upload_date')
        
        # Get all booked services for this user
        booked_services = BookedService.objects.filter(user=user).order_by('-booking_date', '-booking_time')
        
        # Get filter parameter
        filter_type = request.GET.get('filter', 'all')
        
        # Filter results based on lab type
        if filter_type != 'all':
            lab_results = lab_results.filter(lab_type__icontains=filter_type)
        
        context = {
            'user': user,
            'user_profile': user_profile,
            'lab_results': lab_results,
            'booked_services': booked_services,
            'current_filter': filter_type,
            'total_results': lab_results.count(),
            'is_logged_in': True
        }
        
    except Exception as e:
        messages.error(request, f"Error loading lab results: {str(e)}")
        context = {
            'user': None,
            'user_profile': None,
            'lab_results': [],
            'booked_services': [],
            'current_filter': 'all',
            'total_results': 0,
            'is_logged_in': True
        }
    
    return render(request, "lab_results.html", context)

def download_lab_result(request, result_id):
    """Download a lab result file"""
    user_id = request.session.get("user_id") or request.session.get("user")
    if not user_id:
        messages.error(request, "Please login to download lab results")
        return redirect("homepage2")
    
    try:
        from ...models import User, LabResult
        user = User.objects.get(user_id=user_id)
        lab_result = LabResult.objects.get(lab_result_id=result_id, user=user)
        
        # Decode the base64 file content
        file_content = base64.b64decode(lab_result.result_file)
        
        # Create HTTP response with file
        response = HttpResponse(file_content, content_type=lab_result.file_type)
        response['Content-Disposition'] = f'attachment; filename="{lab_result.file_name}"'
        
        return response
        
    except LabResult.DoesNotExist:
        messages.error(request, "Lab result not found or access denied")
        return redirect("labresults")
    except Exception as e:
        messages.error(request, f"Error downloading file: {str(e)}")
        return redirect("labresults")

def view_lab_result(request, result_id):
    """View lab result details"""
    user_id = request.session.get("user_id") or request.session.get("user")
    if not user_id:
        messages.error(request, "Please login to view lab results")
        return redirect("homepage2")
    
    try:
        from ...models import User, LabResult
        user = User.objects.get(user_id=user_id)
        lab_result = LabResult.objects.get(lab_result_id=result_id, user=user)
        
        context = {
            'user': user,
            'lab_result': lab_result
        }
        
        return render(request, "lab_result_detail.html", context)
        
    except LabResult.DoesNotExist:
        messages.error(request, "Lab result not found or access denied")
        return redirect("labresults")
    except Exception as e:
        messages.error(request, f"Error viewing lab result: {str(e)}")
        return redirect("labresults")

def vitals(request):
    user_id = request.session.get("user_id") or request.session.get("user")
    is_logged_in = user_id is not None
    
    if not is_logged_in:
        # Show encouraging message for non-logged-in users
        return render(request, "vitals.html", {
            "is_logged_in": False,
            "encouraging_message": "Monitor your vital signs and health metrics with our advanced tracking system. Login to record your blood pressure, heart rate, temperature, and other important health indicators to maintain optimal wellness."
        })
    # Load user and profile for header details
    try:
        from ...models import User, UserProfile
        user = User.objects.get(user_id=user_id)
        user_profile = UserProfile.objects.get(user=user)
    except Exception:
        user = None
        user_profile = None

    computed_age = None
    if user_profile and getattr(user_profile, 'birth_date', None):
        try:
            today = date.today()
            bd = user_profile.birth_date
            computed_age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
        except Exception:
            computed_age = None

    context = {
        'user': user,
        'user_profile': user_profile,
        'computed_age': computed_age,
        'is_logged_in': True
    }
    return render(request, "vitals.html", context)

def alertnotification(request):
    user_id = request.session.get("user_id") or request.session.get("user")
    is_logged_in = user_id is not None
    
    if not is_logged_in:
        # Show encouraging message for non-logged-in users
        return render(request, "alertNotification_Comments.html", {
            "is_logged_in": False,
            "encouraging_message": "Stay informed about your health with our comprehensive notification system. Login to receive important updates about your appointments, lab results, and health alerts."
        })
    
    try:
        from ...models import User, UserProfile, Notification, Appointment, LabResult
        from django.utils import timezone
        from datetime import datetime, timedelta
        
        user = User.objects.get(user_id=user_id)
        user_profile = UserProfile.objects.get(user=user)
        
        # Get filter parameters
        filter_type = request.GET.get('filter', 'all')
        date_filter = request.GET.get('date', 'all')
        
        # Get all notifications for this user
        notifications = Notification.objects.filter(user=user).order_by('-created_at')
        
        # Apply type filter
        if filter_type != 'all':
            notifications = notifications.filter(notification_type=filter_type)
        
        # Apply date filter
        now = timezone.now()
        if date_filter == 'today':
            notifications = notifications.filter(created_at__date=now.date())
        elif date_filter == 'week':
            week_ago = now - timedelta(days=7)
            notifications = notifications.filter(created_at__gte=week_ago)
        elif date_filter == 'month':
            month_ago = now - timedelta(days=30)
            notifications = notifications.filter(created_at__gte=month_ago)
        
        # Get related data for context
        appointments = Appointment.objects.filter(patient=user).order_by('-created_at')[:5]
        lab_results = LabResult.objects.filter(user=user).order_by('-upload_date')[:5]
        
        # Generate notifications from database data if none exist yet
        if not notifications.exists():
            create_notifications_from_data(user, appointments, lab_results, user_profile)
            notifications = Notification.objects.filter(user=user).order_by('-created_at')
        
        # Count unread notifications
        unread_count = notifications.filter(is_read=False).count()
        
        context = {
            'user': user,
            'user_profile': user_profile,
            'notifications': notifications,
            'appointments': appointments,
            'lab_results': lab_results,
            'current_filter': filter_type,
            'current_date_filter': date_filter,
            'unread_count': unread_count,
            'total_notifications': notifications.count(),
            'is_logged_in': True
        }
        
    except Exception as e:
        messages.error(request, f"Error loading notifications: {str(e)}")
        context = {
            'user': None,
            'user_profile': None,
            'notifications': [],
            'appointments': [],
            'lab_results': [],
            'current_filter': 'all',
            'current_date_filter': 'all',
            'unread_count': 0,
            'total_notifications': 0,
            'is_logged_in': True
        }
    
    return render(request, "alertNotification_Comments.html", context)

def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    user_id = request.session.get("user_id") or request.session.get("user")
    if not user_id:
        return JsonResponse({"error": "Not authenticated"}, status=401)
    
    try:
        from ...models import User, Notification
        user = User.objects.get(user_id=user_id)
        notification = Notification.objects.get(notification_id=notification_id, user=user)
        notification.is_read = True
        notification.save()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def dismiss_notification(request, notification_id):
    """Dismiss/delete a notification"""
    user_id = request.session.get("user_id") or request.session.get("user")
    if not user_id:
        return JsonResponse({"error": "Not authenticated"}, status=401)
    
    try:
        from ...models import User, Notification
        user = User.objects.get(user_id=user_id)
        notification = Notification.objects.get(notification_id=notification_id, user=user)
        notification.delete()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def create_notifications_from_data(user, appointments, lab_results, user_profile=None):
    """Create notifications based on database data"""
    from ...models import Notification
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    
    # Create appointment notifications
    for appointment in appointments:
        if appointment.approval_status == 'Pending':
            Notification.objects.get_or_create(
                user=user,
                title="Appointment Pending Approval",
                message=f"Your {appointment.consultation_type} appointment with Dr. {appointment.doctor.user.get_full_name()} on {appointment.consultation_date} is pending approval.",
                notification_type='appointment',
                priority='medium',
                related_id=appointment.consultation_id,
                defaults={'is_read': False}
            )
        # Notify when an appointment is approved
        if appointment.approval_status == 'Approved':
            Notification.objects.get_or_create(
                user=user,
                title="Appointment Approved",
                message=f"Your appointment with Dr. {appointment.doctor.user.get_full_name()} on {appointment.consultation_date} at {appointment.consultation_time} has been approved.",
                notification_type='appointment',
                priority='medium',
                related_id=appointment.consultation_id,
                defaults={'is_read': False}
            )

        if appointment.approval_status == 'Approved' and appointment.status == 'Scheduled':
            # Check if appointment is today or tomorrow
            days_until = (appointment.consultation_date - now.date()).days
            if days_until == 0:
                Notification.objects.get_or_create(
                    user=user,
                    title="Appointment Today",
                    message=f"Your appointment with Dr. {appointment.doctor.user.get_full_name()} is scheduled for today at {appointment.consultation_time}.",
                    notification_type='urgent',
                    priority='high',
                    related_id=appointment.consultation_id,
                    defaults={'is_read': False}
                )
            elif days_until == 1:
                Notification.objects.get_or_create(
                    user=user,
                    title="Appointment Tomorrow",
                    message=f"Your appointment with Dr. {appointment.doctor.user.get_full_name()} is scheduled for tomorrow at {appointment.consultation_time}.",
                    notification_type='appointment',
                    priority='medium',
                    related_id=appointment.consultation_id,
                    defaults={'is_read': False}
                )
    
    # Create lab result notifications
    for lab_result in lab_results:
        # Check if lab result was uploaded recently (within last 7 days)
        if (now - lab_result.upload_date).days <= 7:
            Notification.objects.get_or_create(
                user=user,
                title="New Lab Results Available",
                message=f"Your {lab_result.lab_type} results are now available for review.",
                notification_type='lab_result',
                priority='medium',
                related_id=lab_result.lab_result_id,
                defaults={'is_read': False}
            )
    
    # Create account security notifications
    if user.last_login:
        days_since_login = (now - user.last_login).days
        if days_since_login > 30:
            Notification.objects.get_or_create(
                user=user,
                title="Account Security Alert",
                message="Your account hasn't been accessed in over 30 days. Please verify your account security.",
                notification_type='account',
                priority='high',
                defaults={'is_read': False}
            )
    
    # Create profile update notifications
    if user_profile:
        if not user_profile.emergency_contact or not user_profile.contact_number:
            Notification.objects.get_or_create(
                user=user,
                title="Profile Update Required",
                message="Please complete your emergency contact information for better care coordination.",
                notification_type='account',
                priority='medium',
                defaults={'is_read': False}
            )



def get_notification_count(request):
    """Get unread notification count"""
    try:
        user_id = request.session.get("user_id") or request.session.get("user")
        
        if not user_id:
            return JsonResponse({'count': 0})
        
        from ...models import Notification
        count = Notification.objects.filter(user_id=user_id, is_read=False).count()
        
        return JsonResponse({'count': count})
    except Exception as e:
        return JsonResponse({'count': 0})

def prescriptions(request):
    """View prescriptions for logged-in user"""
    user_id = request.session.get("user_id") or request.session.get("user")
    is_logged_in = user_id is not None
    
    if not is_logged_in:
        # Show encouraging message for non-logged-in users
        return render(request, "prescriptions.html", {
            "is_logged_in": False,
            "encouraging_message": "Access your prescription history and medication records in one secure place. Login to view your prescriptions, track medication schedules, and manage your health records."
        })
    
    try:
        from ...models import User, UserProfile, Prescription, LiveAppointment, Appointment
        user = User.objects.get(user_id=user_id)
        user_profile = UserProfile.objects.get(user=user)
        
        # Get all prescriptions for this user through their appointments
        prescriptions = Prescription.objects.filter(
            live_appointment__appointment__patient=user
        ).select_related(
            'live_appointment',
            'live_appointment__appointment'
        ).order_by('-created_at')
        
        # Get consultation_id from query parameter for highlighting
        consultation_id = request.GET.get('consultation_id')
        highlight_prescription_id = None
        if consultation_id:
            try:
                # Find prescription linked to this consultation
                prescription = prescriptions.filter(
                    live_appointment__appointment__consultation_id=consultation_id
                ).first()
                if prescription:
                    highlight_prescription_id = prescription.prescription_id
            except Exception:
                pass
        
        context = {
            'user': user,
            'user_profile': user_profile,
            'prescriptions': prescriptions,
            'highlight_prescription_id': highlight_prescription_id,
            'is_logged_in': True
        }
        
    except Exception as e:
        messages.error(request, f"Error loading prescriptions: {str(e)}")
        context = {
            'user': None,
            'user_profile': None,
            'prescriptions': [],
            'is_logged_in': True
        }
    
    return render(request, "prescriptions.html", context)

def prescription_print(request, prescription_id):
    """Generate print view for prescription"""
    user_id = request.session.get("user_id") or request.session.get("user")
    if not user_id:
        return JsonResponse({"error": "Not authenticated"}, status=401)
    
    try:
        from ...models import User, Prescription, LiveAppointment, Appointment
        user = User.objects.get(user_id=user_id)
        prescription = Prescription.objects.get(
            prescription_id=prescription_id,
            live_appointment__appointment__patient=user
        )
        
        # Generate HTML content for printing
        # Safely access patient profile fields (UserProfile may be missing)
        patient = prescription.live_appointment.appointment.patient
        patient_profile = getattr(patient, 'userprofile', None)
        patient_dob = patient_profile.birth_date if (patient_profile and getattr(patient_profile, 'birth_date', None)) else 'N/A'
        patient_contact = patient_profile.contact_number if (patient_profile and getattr(patient_profile, 'contact_number', None)) else 'N/A'

        html_content = f"""
        <div class="prescription-header">
            <h1>PRESCRIPTION</h1>
            <p>MediSafe Medical Center</p>
        </div>
        
        <div class="prescription-info">
            <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
                <div>
                    <strong>Patient:</strong> {patient.get_full_name()}<br>
                    <strong>Date of Birth:</strong> {patient_dob}<br>
                    <strong>Contact:</strong> {patient_contact}
                </div>
                <div>
                    <strong>Prescription #:</strong> {prescription.prescription_number}<br>
                    <strong>Date:</strong> {prescription.created_at.strftime('%B %d, %Y')}<br>
                    <strong>Doctor:</strong> Dr. {prescription.live_appointment.appointment.doctor.user.get_full_name()}
                </div>
            </div>
        </div>
        
        <div class="medicines">
            <h3>Medications Prescribed:</h3>
            {''.join([f'''
            <div class="medicine">
                <div class="medicine-name">{medicine.get("name", "Unknown Medicine")}</div>
                <div class="medicine-details">
                    <strong>Dosage:</strong> {medicine.get("dosage", "As prescribed")}<br>
                    <strong>Frequency:</strong> {medicine.get("frequency", "As directed")}<br>
                    <strong>Duration:</strong> {medicine.get("duration", "As directed")}<br>
                    <strong>Instructions:</strong> {medicine.get("instructions", "As directed by doctor")}
                </div>
            </div>
            ''' for medicine in prescription.medicines])}
        </div>
        
        <div class="instructions">
            <h3>General Instructions:</h3>
            <p>{prescription.general_instructions if hasattr(prescription, 'general_instructions') else 'Please follow the medication schedule as prescribed and consult your doctor if you experience any adverse effects.'}</p>
        </div>
        
        <div class="signature">
            <p>Doctor's Signature:</p>
            {(f'<div class="doctor-signature"><img src="data:image/png;base64,{prescription.doctor_signature}" alt="Doctor Signature" style="max-width:300px;max-height:120px;"/></div>') if getattr(prescription, 'doctor_signature', None) else '<p>_________________________</p>'}
            <div class="date">
                Date: {prescription.signature_date.strftime('%B %d, %Y') if getattr(prescription, 'signature_date', None) else prescription.created_at.strftime('%B %d, %Y')}
            </div>
        </div>
        """
        
        return JsonResponse({
            "success": True,
            "html_content": html_content
        })
        
    except Prescription.DoesNotExist:
        return JsonResponse({"error": "Prescription not found or access denied"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def prescription_view(request, prescription_id):
    """View prescription details in new tab"""
    user_id = request.session.get("user_id") or request.session.get("user")
    if not user_id:
        messages.error(request, "Please login to view prescriptions")
        return redirect("homepage2")
    
    try:
        from ...models import User, Prescription, LiveAppointment, Appointment
        user = User.objects.get(user_id=user_id)
        prescription = Prescription.objects.get(
            prescription_id=prescription_id,
            live_appointment__appointment__patient=user
        )
        
        context = {
            'user': user,
            'prescription': prescription
        }
        
        return render(request, "prescription_detail.html", context)
        
    except Prescription.DoesNotExist:
        messages.error(request, "Prescription not found or access denied")
        return redirect("prescriptions")
    except Exception as e:
        messages.error(request, f"Error viewing prescription: {str(e)}")
        return redirect("prescriptions")


@csrf_protect
@require_POST
def book_lab_service(request):
    """Create a booking for a laboratory service.
    Expects POST form data: service_name, booking_date (YYYY-MM-DD), booking_time (HH:MM), notes (optional)
    Returns JSON { success: bool, message: str }
    """
    try:
        # DEBUG: Log all incoming POST data
        print('\n🔍 [book_lab_service] DEBUG INFO:')
        print(f'  Request.POST keys: {list(request.POST.keys())}')
        print(f'  Request.POST data: {request.POST}')
        print(f'  Request method: {request.method}')
        print(f'  User: {request.user}')
        print(f'  Session user_id: {request.session.get("user_id")}')
        print(f'  Session user: {request.session.get("user")}')
        
        # Get user from either Django auth or session (for custom auth)
        user = None
        user_id = request.session.get('user_id') or request.session.get('user')
        
        # Try Django's request.user first
        if request.user and getattr(request.user, 'is_authenticated', False) and getattr(request.user, 'user_id', None):
            user = request.user
            user_id = request.user.user_id
            print('  ✓ Using Django auth user')
        elif user_id:
            print(f'  ✓ Using session-based auth with user_id: {user_id}')
        else:
            print('  ❌ No authentication found')
            return JsonResponse({"success": False, "error": "Not authenticated"}, status=401)

        # Get form data
        service_name = (request.POST.get('service_name') or '').strip()
        booking_date_str = (request.POST.get('booking_date') or '').strip()
        booking_time_str = (request.POST.get('booking_time') or '').strip()
        notes = (request.POST.get('notes') or '').strip() or None
        
        print(f'  Service: "{service_name}"')
        print(f'  Date: "{booking_date_str}"')
        print(f'  Time: "{booking_time_str}"')
        print(f'  Notes: "{notes}"')

        # Validate inputs
        errors = {}
        if not service_name:
            errors['service_name'] = 'Service name is required.'
            print('  ❌ No service name provided')
        
        # Parse date
        booking_date_obj = None
        try:
            if booking_date_str:
                booking_date_obj = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
                print(f'  ✓ Parsed date: {booking_date_obj}')
            else:
                errors['booking_date'] = 'Date is required.'
        except ValueError:
            errors['booking_date'] = 'Invalid date format. Use YYYY-MM-DD.'
            print(f'  ❌ Failed to parse date: {booking_date_str}')
        
        # Parse time
        booking_time_obj = None
        try:
            if booking_time_str:
                booking_time_obj = datetime.strptime(booking_time_str, '%H:%M').time()
                print(f'  ✓ Parsed time: {booking_time_obj}')
            else:
                errors['booking_time'] = 'Time is required.'
        except ValueError:
            errors['booking_time'] = 'Invalid time format. Use HH:MM.'
            print(f'  ❌ Failed to parse time: {booking_time_str}')

        # Return errors if any validation failed
        if errors:
            print(f'  ❌ Validation errors: {errors}')
            return JsonResponse({"success": False, "errors": errors, "message": "Validation failed"}, status=400)

        # Prevent booking in the past (validation check)
        try:
            if booking_date_obj and booking_time_obj:
                dt = datetime.combine(booking_date_obj, booking_time_obj)
                if dt < datetime.now():
                    print(f'  ❌ Booking date/time is in the past: {dt}')
                    return JsonResponse({
                        "success": False, 
                        "errors": {"booking_date": "Booking must be in the future."}, 
                        "message": "Booking date and time must be in the future"
                    }, status=400)
        except Exception as e:
            print(f'  ⚠️ Error checking future booking: {str(e)}')

        # Resolve user object if needed
        from ...models import User, BookedService
        if not user:
            try:
                user = User.objects.get(user_id=user_id)
                print(f'  ✓ Resolved user from DB: {user}')
            except User.DoesNotExist:
                print(f'  ❌ User not found in DB: {user_id}')
                return JsonResponse({"success": False, "error": "User not found"}, status=401)
        
        print(f'  ✓ User confirmed: {user} (ID: {user.user_id})')

        # Create booking in database
        booking = BookedService.objects.create(
            user=user,
            service_name=service_name,
            booking_date=booking_date_obj,
            booking_time=booking_time_obj,
            status='Pending',
            notes=notes
        )
        
        print(f'  ✅ Booking created successfully!')
        print(f'     - Booking ID: {booking.booking_id}')
        print(f'     - Service: {booking.service_name}')
        print(f'     - Date: {booking.booking_date}')
        print(f'     - Time: {booking.booking_time}')
        print('  End of request\n')

        return JsonResponse({
            "success": True,
            "message": "Laboratory service booked successfully!",
            "booking_id": booking.booking_id
        })
    except Exception as e:
        import traceback
        print(f'  ❌ Exception occurred: {str(e)}')
        print(f'  Traceback:\n{traceback.format_exc()}')
        return JsonResponse({"success": False, "error": str(e), "message": f"Error: {str(e)}"}, status=500)


def prescription_details(request, prescription_id):
    """Get prescription details as JSON for modal display"""
    user_id = request.session.get("user_id") or request.session.get("user")
    if not user_id:
        return JsonResponse({"success": False, "error": "Not authenticated"}, status=401)
    
    try:
        from ...models import User, Prescription, LiveAppointment, Appointment
        user = User.objects.get(user_id=user_id)
        prescription = Prescription.objects.get(
            prescription_id=prescription_id,
            live_appointment__appointment__patient=user
        )
        
        # Generate HTML content for details display
        patient = prescription.live_appointment.appointment.patient
        patient_profile = getattr(patient, 'userprofile', None)
        patient_dob = patient_profile.birthday if (patient_profile and getattr(patient_profile, 'birthday', None)) else 'N/A'
        patient_contact = patient_profile.contact_number if (patient_profile and getattr(patient_profile, 'contact_number', None)) else 'N/A'
        
        doctor = prescription.live_appointment.appointment.doctor
        doctor_name = doctor.user.get_full_name() if doctor else 'Unknown Doctor'

        preview_url = None
        if prescription.prescription_file:
            preview_url = f"{reverse('prescription_download', args=[prescription_id])}?mode=preview"

        medicine_html = ''.join([
            f"""
            <div class="medicine">
                <div class="medicine-name">{medicine.get("name", "Unknown Medicine")}</div>
                <div class="medicine-details">
                    <strong>Dosage:</strong> {medicine.get("dosage", "As prescribed")}<br>
                    <strong>Frequency:</strong> {medicine.get("frequency", "As directed")}<br>
                    <strong>Duration:</strong> {medicine.get("duration", "As directed")}<br>
                    <strong>Instructions:</strong> {medicine.get("instructions", "As directed by doctor")}
                </div>
            </div>
            """ for medicine in prescription.medicines
        ]) or "<p>No medicines recorded for this prescription.</p>"

        file_section = ""
        if preview_url:
            file_section = f"""
            <div class="preview-panel">
                <h3>Prescription File</h3>
                <iframe src="{preview_url}&v={int(datetime.now().timestamp())}" title="Prescription Preview" frameborder="0"></iframe>
            </div>
            """

        html_content = f"""
        <div class="prescription-detail-layout">
            <div class="detail-column">
                <div class="prescription-header">
                    <div>
                        <p class="label">Prescription #</p>
                        <h2>{prescription.prescription_number}</h2>
                    </div>
                    <div>
                        <p class="label">Status</p>
                        <span class="status-chip status-{prescription.status}">{prescription.status.title()}</span>
                    </div>
                </div>
                <div class="info-grid">
                    <div>
                        <p class="label">Patient</p>
                        <p class="value">{patient.get_full_name()}</p>
                    </div>
                    <div>
                        <p class="label">Doctor</p>
                        <p class="value">{doctor_name}</p>
                    </div>
                    <div>
                        <p class="label">Date</p>
                        <p class="value">{prescription.created_at.strftime('%B %d, %Y')}</p>
                    </div>
                    <div>
                        <p class="label">Birthdate</p>
                        <p class="value">{patient_dob}</p>
                    </div>
                    <div>
                        <p class="label">Contact</p>
                        <p class="value">{patient_contact}</p>
                    </div>
                    <div>
                        <p class="label">Follow-up</p>
                        <p class="value">{prescription.follow_up_date.strftime('%B %d, %Y') if prescription.follow_up_date else 'Not set'}</p>
                    </div>
                </div>
                <div class="medicines">
                    <h3>Medications</h3>
                    {medicine_html}
                </div>
                <div class="instructions">
                    <h3>Clinical Notes & Instructions</h3>
                    <p>{prescription.instructions or 'Please follow the medication schedule as prescribed and consult your doctor if you experience any adverse effects.'}</p>
                </div>
                <div class="signature">
                    <p class="label">Doctor's Signature</p>
                    {(f'<div class="doctor-signature"><img src="data:image/png;base64,{prescription.doctor_signature}" alt="Doctor Signature" /></div>') if getattr(prescription, 'doctor_signature', None) else '<div class="doctor-signature blank">_________________________</div>'}
                    <div class="date">
                        Signed on: {prescription.signature_date.strftime('%B %d, %Y') if getattr(prescription, 'signature_date', None) else prescription.created_at.strftime('%B %d, %Y')}
                    </div>
                </div>
            </div>
            {file_section}
        </div>
        """
        
        return JsonResponse({
            "success": True,
            "html_content": html_content
        })
        
    except Prescription.DoesNotExist:
        return JsonResponse({"success": False, "error": "Prescription not found or access denied"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def prescription_download(request, prescription_id):
    """Download prescription file (patient) with proper error handling for Render ephemeral storage"""
    user_id = request.session.get('user_id') or request.session.get('user')
    
    if not user_id:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        from ...models import User, Prescription
        user = User.objects.get(user_id=user_id)
        
        # Get prescription and verify ownership (patient can only download their own prescriptions)
        prescription = Prescription.objects.get(
            prescription_id=prescription_id,
            live_appointment__appointment__patient=user
        )
        
        # Check if prescription has a file
        if not prescription.prescription_file:
            return JsonResponse({
                'error': 'No file attached to this prescription. Please ask your doctor to upload a prescription file.'
            }, status=404)
        
        file_obj = prescription.prescription_file
        file_name = file_obj.name.split('/')[-1]
        mime_type, _ = mimetypes.guess_type(file_name)
        mode = request.GET.get('mode', 'download')
        disposition = 'inline' if mode == 'preview' else 'attachment'
        
        try:
            response = FileResponse(file_obj.open('rb'), content_type=mime_type or 'application/octet-stream')
            response['Content-Disposition'] = f'{disposition}; filename="{smart_str(prescription.prescription_number)}_{smart_str(file_name)}"'
            return response
        except FileNotFoundError:
            # File path in DB but file not on disk (Render ephemeral storage)
            return JsonResponse({
                'error': 'Prescription file not available',
                'message': 'The file has been removed from temporary storage. Please ask your doctor to re-upload the prescription.',
                'type': 'ephemeral_storage_missing'
            }, status=410)  # 410 Gone
        
    except Prescription.DoesNotExist:
        return JsonResponse({'error': 'Prescription not found'}, status=404)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error downloading prescription {prescription_id}: {str(e)}")
        return JsonResponse({'error': f'Error downloading file: {str(e)}'}, status=500)


# ===== Global Notification API Endpoints =====
@csrf_protect
def get_unread_notifications(request):
    """Get unread notifications for logged-in user (for notification bell)"""
    user_id = request.session.get('user_id') or request.session.get('user')
    if not user_id:
        return JsonResponse({'unread_count': 0, 'notifications': []}, status=200)
    
    try:
        from ...models import User, Notification
        user = User.objects.get(user_id=user_id)
        
        # Get last 5 unread notifications
        unread_notifs = Notification.objects.filter(user=user, is_read=False).order_by('-created_at')[:5]
        
        notif_list = [{
            'notification_id': n.notification_id,
            'title': n.title,
            'message': n.message,
            'notification_type': n.notification_type,
            'is_read': n.is_read,
            'priority': n.priority,
            'related_id': n.related_id,
            'created_at': n.created_at.isoformat(),
        } for n in unread_notifs]
        
        return JsonResponse({
            'unread_count': Notification.objects.filter(user=user, is_read=False).count(),
            'notifications': notif_list
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_protect
def api_mark_notification_read(request, notification_id):
    """API endpoint to mark a notification as read (for notification bell)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    user_id = request.session.get('user_id') or request.session.get('user')
    if not user_id:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        from ...models import User, Notification
        user = User.objects.get(user_id=user_id)
        
        notification = Notification.objects.get(notification_id=notification_id, user=user)
        notification.is_read = True
        notification.save()
        
        # Get updated unread count
        unread_count = Notification.objects.filter(user=user, is_read=False).count()
        
        return JsonResponse({
            'success': True,
            'message': 'Notification marked as read',
            'unread_count': unread_count
        })
    except Notification.DoesNotExist:
        return JsonResponse({'error': 'Notification not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_protect
def get_password_reset_notifications(request):
    """Get password reset notifications for admin users"""
    user_id = request.session.get('user_id') or request.session.get('user')
    if not user_id:
        return JsonResponse({'count': 0, 'notifications': []}, status=200)
    
    try:
        from ...models import User, Notification
        user = User.objects.get(user_id=user_id)
        
        # Only admins can see password reset notifications
        if user.role != 'admin':
            return JsonResponse({'count': 0, 'notifications': []}, status=200)
        
        # Get unread password reset notifications
        password_reset_notifs = Notification.objects.filter(
            user=user,
            notification_type='password_reset',
            is_read=False
        ).order_by('-created_at')
        
        notif_list = []
        for n in password_reset_notifs:
            file_url = None
            file_name = None
            if n.file:
                file_url = n.file.url
                file_name = n.file.name.split('/')[-1]  # Get just the filename
            
            notif_list.append({
                'notification_id': n.notification_id,
                'title': n.title,
                'message': n.message,
                'notification_type': n.notification_type,
                'is_read': n.is_read,
                'priority': n.priority,
                'related_id': n.related_id,  # User ID of the person requesting password reset
                'file_url': file_url,
                'file_name': file_name,
                'created_at': n.created_at.isoformat(),
            })
        
        return JsonResponse({
            'count': len(notif_list),
            'notifications': notif_list
        })
    except Exception as e:
        logger.error(f"Error in get_password_reset_notifications: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
